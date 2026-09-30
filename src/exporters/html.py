"""HTML-Export: eigenständige Seite, Formeln setzt KaTeX im Browser.

Bis auf KaTeX (vom CDN, per SRI-Hash abgesichert) ist die Datei in sich
geschlossen: CMU-Schriften, Bilder und Plots (als SVG) werden eingebettet.
Ohne Netz bleibt statt der Formeln der LaTeX-Quelltext lesbar stehen.
"""

import base64
from collections.abc import Iterable
import html
import json
from io import BytesIO
import mimetypes
from pathlib import Path
import re

from matplotlib.figure import Figure
import polars as pl
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer
import sympy as sp
import yaml

from config.settings import FONTS_DIR
from exporters.bibtex import Citations, bibliography_files, load_bibliography
from exporters.terms import document_language, terms
from widgets.math_text import evaluate_templates, markdown_to_html

KATEX_VERSION = "0.18.9"
_KATEX_CDN = f"https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist"
# Subresource Integrity: Der Browser verwirft die Dateien, falls das CDN
# etwas anderes ausliefert. Bei einem Versionswechsel neu berechnen:
#   openssl dgst -sha384 -binary katex.min.js | openssl base64 -A
_KATEX_JS_SRI = (
    "sha384-19KE2cFb3U+RUWmyhBz7aLOGDG8WrRC6hE3oY/HTZZlAAVWYTdmvLC//+TIV3zUx"
)
_KATEX_CSS_SRI = (
    "sha384-lPx0C4zIUZLpveABMwOFcFeGZwsvKBJfhJ85FN1PYOV7xApBcFMhcAEMVKF8loOI"
)

# (Familie, Stil, Gewicht, Datei in assets/fonts)
_FONTS = [
    ("CMU Serif", "normal", "normal", "cmu.serif-roman.ttf"),
    ("CMU Serif", "italic", "normal", "cmu.serif-italic.ttf"),
    ("CMU Sans Serif", "normal", "bold", "cmu.sans-serif-bold.ttf"),
    ("CMU Typewriter Text", "normal", "normal", "cmu.typewriter-text-regular.ttf"),
]

CSS = """
body {
    margin: 0;
    background: #f8fafc;
    color: #334155;
    font-family: 'CMU Serif', 'Latin Modern Roman', Georgia, serif;
    font-size: 1.2rem;
    line-height: 1.6;
}
main {
    max-width: 46rem;
    margin: 0 auto;
    padding: 3rem 1.5rem 5rem;
    background: #fff;
    min-height: 100vh;
    box-sizing: border-box;
}
h1, h2, h3, h4 {
    font-family: 'CMU Sans Serif', 'Helvetica Neue', sans-serif;
    font-weight: bold;
    color: #0f172a;
    line-height: 1.25;
    margin: 2rem 0 0.6rem;
}
h1 { font-size: 1.9rem; }
h2 { font-size: 1.5rem; }
h3 { font-size: 1.25rem; color: #334155; }
header.doc { border-bottom: 1px solid #e2e8f0; margin-bottom: 2rem; padding-bottom: 1rem; }
header.doc h1 { margin-top: 0; font-size: 2.3rem; }
header.doc .meta { color: #64748b; font-size: 1rem; }
header.doc .summary { font-style: italic; color: #475569; }
a { color: #2563eb; }
blockquote {
    margin: 1.2rem 0;
    padding: 0.2rem 1rem;
    border-left: 3px solid #cbd5e1;
    color: #64748b;
    font-style: italic;
}
code, pre { font-family: 'CMU Typewriter Text', 'JetBrains Mono', monospace; font-size: 0.95rem; }
:not(pre) > code { background: #f1f5f9; color: #0f172a; padding: 0.05rem 0.3rem; border-radius: 3px; }
pre {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 3px solid #2563eb;
    border-radius: 6px;
    padding: 0.7rem 1rem;
    overflow-x: auto;
    line-height: 1.45;
}
/* Syntax-Hervorhebung (Pygments) und Kopier-Knopf */
.highlight { position: relative; margin: 1rem 0; }
.highlight pre { margin: 0; }
.copy {
    position: absolute; top: 0.4rem; right: 0.4rem;
    display: flex; align-items: center; gap: 0.3rem;
    padding: 0.2rem 0.5rem;
    font: 0.75rem 'CMU Sans Serif', sans-serif;
    color: #475569; background: #fff;
    border: 1px solid #cbd5e1; border-radius: 4px;
    cursor: pointer;
    opacity: 0; transition: opacity 0.15s;
}
.copy svg { width: 0.9rem; height: 0.9rem; }
.highlight:hover .copy, .copy:focus-visible, .copy.done { opacity: 1; }
.copy:hover { color: #2563eb; border-color: #93c5fd; }
.copy.done { color: #16a34a; border-color: #86efac; }
@media (hover: none) { .copy { opacity: 1; } }
/* Zitate und Quellen */
.citation a { color: inherit; text-decoration: none; border-bottom: 1px dotted #94a3b8; }
.citation a:hover { color: #2563eb; border-bottom-color: #2563eb; }
.citation .unknown { color: #dc2626; font-weight: bold; }
.references ul { list-style: none; padding: 0; }
.references li { padding-left: 1.5em; text-indent: -1.5em; margin-bottom: 0.6rem; font-size: 1.05rem; }
.references li:target { background: #fef9c3; }
.references a { overflow-wrap: anywhere; }
pre.stdout { border-left-color: #94a3b8; color: #475569; background: #fff; }
pre.result { border: none; background: none; color: #0284c7; padding-left: 0; }
.error { color: #dc2626; background: #fee2e2; border-left-color: #dc2626; }
.math-error { color: #dc2626; background: #fee2e2; }
.math.display { display: block; margin: 1.2rem 0; text-align: center; overflow-x: auto; }
table { border-collapse: collapse; margin: 1rem 0; font-size: 1rem; }
td, th { border: 1px solid #cbd5e1; padding: 0.25rem 0.6rem; }
th { background: #f1f5f9; }
.figure, .plot { text-align: center; margin: 1.5rem 0; }
.figure img, .plot svg { max-width: 100%; height: auto; }
.caption { font-size: 1rem; font-style: italic; color: #64748b; margin-top: 0.4rem; }
[class^="callout-"]:not([class^="callout-title"]) {
    border-left: 4px solid #2563eb;
    background: #eff6ff;
    border-radius: 4px;
    padding: 0.2rem 1rem;
    margin: 1.2rem 0;
}
[class^="callout-title"] { font-family: 'CMU Sans Serif', sans-serif; font-weight: bold; margin-bottom: 0.2rem; }
.callout-note { border-left-color: #2563eb !important; background: #eff6ff !important; }
.callout-title-note { color: #2563eb; }
.callout-tip { border-left-color: #16a34a !important; background: #f0fdf4 !important; }
.callout-title-tip { color: #16a34a; }
.callout-warning, .callout-important { border-left-color: #d97706 !important; background: #fffbeb !important; }
.callout-title-warning, .callout-title-important { color: #d97706; }
.callout-caution { border-left-color: #dc2626 !important; background: #fef2f2 !important; }
.callout-title-caution { color: #dc2626; }
"""

# Pygments-Farben; der Hintergrund kommt vom pre-Stil oben.
_PYGMENTS_STYLE = "friendly"
_HIGHLIGHT_CSS = (
    HtmlFormatter(style=_PYGMENTS_STYLE).get_style_defs(".highlight")
    + "\n.highlight { background: none; }"
)

# Kopier-Knopf an jedem Codeblock; Fallback für Browser ohne Clipboard-API.
_COPY_JS = """
const COPY_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
  + 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" '
  + 'width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  for (const block of document.querySelectorAll(".highlight")) {
    const code = block.querySelector("pre");
    if (!code) continue;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy";
    button.setAttribute("aria-label", LABELS.copyCode);
    button.innerHTML = COPY_ICON + "<span>" + LABELS.copy + "</span>";
    button.addEventListener("click", async () => {
      await copyText(code.innerText.replace(/\\n$/, ""));
      button.classList.add("done");
      button.lastChild.textContent = LABELS.copied;
      setTimeout(() => {
        button.classList.remove("done");
        button.lastChild.textContent = LABELS.copy;
      }, 1500);
    });
    block.appendChild(button);
  }
});
"""

# Rendert alle .math-Elemente; ohne KaTeX (offline) bleibt das LaTeX stehen.
_KATEX_RENDER_JS = """
document.addEventListener("DOMContentLoaded", () => {
  if (!window.katex) return;
  for (const el of document.querySelectorAll(".math")) {
    katex.render(el.textContent, el, {
      displayMode: el.classList.contains("display"),
      throwOnError: false,
    });
  }
});
"""


def _math_html(latex: str, display: bool) -> str:
    latex = html.escape(latex.strip())
    if display:
        return f'<div class="math display">{latex}</div>'
    return f'<span class="math inline">{latex}</span>'


def _data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _embed_images(body: str, base_dir: Path) -> str:
    """Inlines local <img> sources so the page works without its folder."""

    def replace(match):
        src = html.unescape(match.group(2))
        if re.match(r"^(https?:|data:)", src):
            return match.group(0)
        path = (base_dir / src).resolve()
        if not path.is_file():
            return match.group(0)
        return f'{match.group(1)}src="{_data_uri(path)}"'

    return re.sub(r'(<img\b[^>]*?)src="([^"]*)"', replace, body)


def _font_faces() -> str:
    faces = []
    for family, style, weight, filename in _FONTS:
        path = FONTS_DIR / filename
        if path.is_file():
            faces.append(
                f"@font-face {{ font-family: '{family}'; font-style: {style}; "
                f"font-weight: {weight}; src: url({_data_uri(path)}) format('truetype'); }}"
            )
    return "\n".join(faces)


def _figure_svg(fig: Figure) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    svg = buf.getvalue().decode()
    return svg[svg.index("<svg") :]  # XML-Deklaration/Doctype entfernen


def _python_cell_html(code: str, stdout: str, value) -> str:
    code_html = highlight(code, PythonLexer(), HtmlFormatter(nowrap=True))
    parts = [f'<div class="highlight"><pre><code>{code_html}</code></pre></div>']
    if stdout.startswith("Error: "):
        parts.append(f'<pre class="stdout error">{html.escape(stdout[7:])}</pre>')
        return "\n".join(parts)
    if stdout:
        parts.append(f'<pre class="stdout">{html.escape(stdout)}</pre>')
    if value is None:
        pass
    elif isinstance(value, (sp.Basic, sp.MatrixBase)):
        parts.append(_math_html(sp.latex(value), display=True))
    elif isinstance(value, Figure):
        parts.append(f'<div class="plot">{_figure_svg(value)}</div>')
    elif isinstance(value, pl.DataFrame):
        parts.append(value._repr_html_())
    else:
        parts.append(f'<pre class="result">{html.escape(str(value))}</pre>')
    return "\n".join(parts)


def _header_html(properties: dict) -> str:
    title = properties.get("title")
    if not title:
        return ""
    lines = [f"<h1>{html.escape(str(title))}</h1>"]
    if properties.get("subtitle"):
        lines.append(f'<p class="meta">{html.escape(str(properties["subtitle"]))}</p>')

    authors = properties.get("authors") or properties.get("author") or []
    if isinstance(authors, (str, dict)):
        authors = [authors]
    names = [
        a.get("name") if isinstance(a, dict) else str(a)
        for a in authors
        if (a.get("name") if isinstance(a, dict) else a)
    ]
    meta = ", ".join(names)
    if properties.get("date"):
        meta = f"{meta} · {properties['date']}" if meta else str(properties["date"])
    if meta:
        lines.append(f'<p class="meta">{html.escape(meta)}</p>')
    if properties.get("summary"):
        lines.append(
            f'<p class="summary">{html.escape(str(properties["summary"]))}</p>'
        )
    return '<header class="doc">\n' + "\n".join(lines) + "\n</header>"


def _parse_properties(frontmatter: str) -> dict:
    try:
        data = yaml.safe_load(frontmatter) if frontmatter.strip() else {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def export_html(
    cells: Iterable, filepath: str, frontmatter: str = "", base_dir: Path | None = None
) -> None:
    """Writes the notebook as a standalone HTML page with KaTeX math."""
    out_path = Path(filepath)
    base_dir = base_dir or out_path.parent
    properties = _parse_properties(frontmatter)
    lang = document_language(properties)
    t = terms(lang)
    citations = Citations(
        load_bibliography(bibliography_files(properties, base_dir)), lang
    )
    labels = json.dumps(
        {"copy": t["copy"], "copied": t["copied"], "copyCode": t["copy_code"]},
        ensure_ascii=False,
    )

    body = []
    for cell in cells:
        content = cell.editor.toPlainText().strip()
        if not content:
            continue
        if cell._detect_effective_mode(content) == "markdown":
            text = evaluate_templates(content, cell.namespace)
            body.append(
                markdown_to_html(text, _math_html, highlight=True, cite=citations)
            )
        else:
            code = re.sub(r"^```(?:python|py)?\s*\n|\n?```\s*$", "", content)
            body.append(_python_cell_html(code, cell.last_stdout, cell.last_val))

    # Wie Quartos Literaturverzeichnis: nur tatsächlich zitierte Einträge
    body.append(citations.references_html())

    title = properties.get("title") or out_path.stem
    page = f"""<!DOCTYPE html>
<html lang="{html.escape(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="Rosida">
<title>{html.escape(str(title))}</title>
<link rel="stylesheet" href="{_KATEX_CDN}/katex.min.css" integrity="{_KATEX_CSS_SRI}" crossorigin="anonymous">
<script defer src="{_KATEX_CDN}/katex.min.js" integrity="{_KATEX_JS_SRI}" crossorigin="anonymous"></script>
<style>
{_font_faces()}
{CSS}
{_HIGHLIGHT_CSS}
</style>
</head>
<body>
<main>
{_header_html(properties)}
{_embed_images(chr(10).join(body), base_dir)}
</main>
<script>const LABELS = {labels};{_KATEX_RENDER_JS}{_COPY_JS}</script>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
