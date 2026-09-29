import html
from io import BytesIO
import itertools
import math
from pathlib import Path
import re
from xml.etree import ElementTree as etree

from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import math_to_image
import markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from markdown.treeprocessors import Treeprocessor
import sympy as sp

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage, QTextDocument
from PySide6.QtWidgets import QTextBrowser

from config.settings import markdown_css
from widgets.math_svg import MathSvg, embed_math_objects, latex_to_svg


# Breite, auf die eingebettete Bilder (![..](..)) höchstens skaliert werden.
MAX_IMAGE_WIDTH = 680

MATH_COLOR = "#334155"  # = Textfarbe (body) im Standard-Stylesheet

# Dokumentweit eindeutige Ressourcennamen: Der PDF-Export führt die Formeln
# aller Zellen in einem QTextDocument zusammen.
_formula_ids = itertools.count(1)


def pt_to_px(pt: float) -> float:
    return pt * 96 / 72


def formula_html(
    latex: str,
    display: bool,
    fontsize: float,
    formulas: dict[str, MathSvg],
    images: dict[str, QImage],
) -> str:
    """Returns an <img> placeholder for latex and registers the rendering.

    ziamath (vector, via formulas) is preferred; Matplotlib mathtext (raster,
    via images) is the fallback for syntax ziamath rejects. Raises if both fail.
    """
    name = f"math://{next(_formula_ids)}"
    try:
        svg = latex_to_svg(latex, pt_to_px(fontsize), display, MATH_COLOR)
        formulas[name] = svg
        w, h = math.ceil(svg.width), math.ceil(svg.ascent + svg.descent)
        return f'<img src="{name}" width="{w}" height="{h}">'
    except Exception:
        qimg, w, h = math_to_png_qimage(latex, fontsize=fontsize, dpi=192)
        images[name] = qimg
        return f'<img src="{name}" width="{w}" height="{h}" style="vertical-align: middle;">'


def _clean_latex_for_mathtext(expr: str) -> str:
    """Prepares LaTeX formulas for Matplotlib's mathtext parser by stripping unsupported switches."""
    expr = expr.strip()
    while expr.startswith("$") and expr.endswith("$") and len(expr) >= 2:
        expr = expr[1:-1].strip()

    expr = re.sub(r"\\(display|text|script|scriptscript)style\b", "", expr)
    expr = re.sub(r"\\text\{", r"\\mathrm{", expr)
    expr = re.sub(r"\\operatorname\{", r"\\mathrm{", expr)
    return expr.strip()


def math_to_png_qimage(
    latex_expr: str,
    fontsize: int = 14,
    dpi: int = 192,
    color: str = "#0f172a",
) -> tuple[QImage, int, int]:
    """Renders LaTeX expression directly to a crisp, high-DPI QImage using Matplotlib mathtext."""
    clean_expr = _clean_latex_for_mathtext(latex_expr)
    buf = BytesIO()
    prop = FontProperties(size=fontsize)
    try:
        math_to_image(
            f"${clean_expr}$", buf, prop=prop, dpi=dpi, format="png", color=color
        )
    except TypeError:
        math_to_image(f"${clean_expr}$", buf, prop=prop, dpi=dpi, format="png")
    buf.seek(0)

    img = QImage()
    img.loadFromData(buf.getvalue())

    scale = dpi / 96.0
    img.setDevicePixelRatio(scale)
    logical_w = max(1, int(img.width() / scale))
    logical_h = max(1, int(img.height() / scale))
    return img, logical_w, logical_h


class MathTextBrowser(QTextBrowser):
    """Custom QTextBrowser serving in-memory math formula images reliably without broken box placeholders."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._resources: dict[str, QImage] = {}
        self._formulas: dict[str, MathSvg] = {}

    def add_math_resource(self, name: str, img: QImage):
        self._resources[name] = img
        self.document().addResource(
            QTextDocument.ResourceType.ImageResource, QUrl(name), img
        )

    def loadResource(self, res_type, name):
        url_str = name.toString()
        if url_str in self._resources:
            return self._resources[url_str]
        for key, val in self._resources.items():
            if key.endswith(url_str) or url_str.endswith(key):
                return val
        data = super().loadResource(res_type, name)
        if res_type == QTextDocument.ResourceType.ImageResource and data is not None:
            return _limit_image_width(data)
        return data


def _limit_image_width(data):
    """Scales oversized document images down so they fit the cell width."""
    img = data if isinstance(data, QImage) else QImage.fromData(data)
    if img.isNull() or img.width() <= MAX_IMAGE_WIDTH:
        return data
    return img.scaledToWidth(
        MAX_IMAGE_WIDTH, Qt.TransformationMode.SmoothTransformation
    )


def _evaluate_template_expressions(text: str, namespace: dict) -> str:
    """Replaces {{ expr }} with the evaluated Python expression from namespace.

    A SymPy result is turned into LaTeX math markup ($...$ or, if the
    expression stands alone on its own line, $$...$$) so the surrounding
    math pipeline renders it; anything else is inserted via str().
    """

    def _replace(match):
        expr = match.group(1).strip()

        start = match.string.rfind("\n", 0, match.start()) + 1
        end = match.string.find("\n", match.end())
        prefix = match.string[start : match.start()].strip()
        suffix = (
            match.string[match.end() : end].strip()
            if end != -1
            else match.string[match.end() :].strip()
        )
        is_block = prefix == "" and suffix == ""

        try:
            val = eval(expr, {}, namespace)
        except Exception as err:
            return f'<code class="math-error">Fehler: {html.escape(expr)} → {html.escape(str(err))}</code>'

        if isinstance(val, (sp.Basic, sp.MatrixBase)):
            latex = sp.latex(val)
            return f"$${latex}$$" if is_block else f"${latex}$"

        return str(val)

    return re.sub(r"\{\{\s*(.*?)\s*\}\}", _replace, text)



_CODE_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_DIV_OPEN_RE = re.compile(r"^\s*:{3,}\s*(\{[^}]*\}|[\w-]+)\s*$")
_DIV_CLOSE_RE = re.compile(r"^\s*:{3,}\s*$")
_CALLOUT_RE = re.compile(r"\.callout-(\w+)")
_TITLE_ATTR_RE = re.compile(r"""title\s*=\s*(?:"([^"]*)"|'([^']*)')""")


class _MathPreprocessor(Preprocessor):
    """Renders $$...$$ and $...$ to images and stashes the resulting HTML.

    Runs before any Markdown parsing, so backslashes, underscores and
    asterisks inside formulas never reach the inline patterns. Code
    blocks and code spans are left alone.
    """

    def __init__(self, md, render_math):
        super().__init__(md)
        self.render_math = render_math

    def run(self, lines):
        out, chunk, fence = [], [], None
        for line in lines:
            m = _CODE_FENCE_RE.match(line)
            if fence is None and m:
                out.extend(self._convert("\n".join(chunk)).split("\n"))
                chunk, fence = [], m.group(1)
                out.append(line)
            elif fence is not None:
                out.append(line)
                if line.strip().startswith(fence):
                    fence = None
            else:
                chunk.append(line)
        out.extend(self._convert("\n".join(chunk)).split("\n"))
        return out

    def _convert(self, text: str) -> str:
        # Ungerade Indizes sind Code-Spans (`...`) und bleiben unverändert.
        parts = re.split(r"(`+[^`]*?`+)", text)
        for i in range(0, len(parts), 2):
            parts[i] = re.sub(
                r"\$\$(.+?)\$\$",
                lambda m: "\n\n" + self._stash(m.group(1), block=True) + "\n\n",
                parts[i],
                flags=re.DOTALL,
            )
            parts[i] = re.sub(
                r"(?<!\$)\$([^\$\n]+?)\$(?!\$)",
                lambda m: self._stash(m.group(1), block=False),
                parts[i],
            )
        return "".join(parts)

    def _stash(self, latex: str, block: bool) -> str:
        return self.md.htmlStash.store(self.render_math(latex.strip(), block))


class _FencedDivPreprocessor(Preprocessor):
    """Turns Pandoc/Quarto fenced divs (::: {.callout-note} ... :::) into HTML divs.

    Only a rough preview: callouts get a coloured box and a title, every
    other div (layouts, columns, ...) just keeps its content. The real
    rendering is left to the Quarto export.
    """

    def run(self, lines):
        out, depth, fence = [], 0, None
        for line in lines:
            m = _CODE_FENCE_RE.match(line)
            if fence is not None or m:
                if fence is None:
                    fence = m.group(1)
                elif line.strip().startswith(fence):
                    fence = None
                out.append(line)
                continue

            if depth and _DIV_CLOSE_RE.match(line):
                depth -= 1
                out.extend(["", "</div>", ""])
                continue

            m = _DIV_OPEN_RE.match(line)
            if not m:
                out.append(line)
                continue

            depth += 1
            attrs = m.group(1)
            callout = _CALLOUT_RE.search(attrs)
            if not callout:
                out.extend(["", '<div markdown="1">', ""])
                continue

            kind = callout.group(1)
            t = _TITLE_ATTR_RE.search(attrs)
            title = (t.group(1) or t.group(2)) if t else kind.capitalize()
            out.extend(
                [
                    "",
                    f'<div class="callout-{kind}" markdown="1">',
                    "",
                    f'<p class="callout-title-{kind}">{html.escape(title)}</p>',
                    "",
                ]
            )
        out.extend(["", "</div>", ""] * depth)
        return out


class _CalloutTitleTreeprocessor(Treeprocessor):
    """Uses a leading heading inside a callout as its title (Quarto convention)."""

    def run(self, root):
        for div in root.iter("div"):
            cls = div.get("class", "")
            if not cls.startswith("callout-") or len(div) < 2:
                continue
            title, first = div[0], div[1]
            if first.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                title.text = "".join(first.itertext())
                div.remove(first)


class _FigureTreeprocessor(Treeprocessor):
    """Renders a paragraph holding nothing but an image as a centred figure with caption."""

    def run(self, root):
        for p in root.iter("p"):
            if len(p) != 1 or p[0].tag != "img":
                continue
            if (p.text or "").strip() or (p[0].tail or "").strip():
                continue
            img = p[0]
            img.tail = None
            p.tag = "div"
            p.text = None
            p.set("class", "figure")
            p.set("align", "center")
            caption = img.get("alt", "")
            if caption:
                cap = etree.SubElement(p, "p")
                cap.set("class", "caption")
                cap.set("align", "center")
                cap.text = caption


class _RosidaExtension(Extension):
    def __init__(self, render_math):
        super().__init__()
        self.render_math = render_math

    def extendMarkdown(self, md):
        # Vor normalize_whitespace (30) bzw. html_block (20), damit Formeln
        # und die erzeugten <div>-Tags wie normales Roh-HTML behandelt werden.
        md.preprocessors.register(_MathPreprocessor(md, self.render_math), "math", 29)
        md.preprocessors.register(_FencedDivPreprocessor(md), "fenced_div", 28)
        md.treeprocessors.register(_FigureTreeprocessor(md), "figure", 5)
        md.treeprocessors.register(_CalloutTitleTreeprocessor(md), "callout_title", 4)


def render_markdown_with_math(
    md_text: str,
    browser: MathTextBrowser,
    fontsize: float = 16,
    namespace: dict | None = None,
    base_dir: Path | None = None,
    embed_formulas: bool = True,
) -> None:
    """Renders Markdown (incl. Quarto callouts/figures, {{ expr }} templates and $/$$ math) into browser.

    fontsize (pt) should match the body text of the stylesheet. With
    embed_formulas=False the formulas stay <img> placeholders (listed in
    browser._formulas), so the HTML can be merged into another document.
    """
    browser._resources.clear()
    browser._formulas.clear()
    browser.document().clear()
    browser.document().setDefaultStyleSheet(markdown_css())
    if base_dir is not None:
        browser.setSearchPaths([str(base_dir)])

    text = md_text.strip()
    if not text:
        browser.setHtml("")
        return

    text = _evaluate_template_expressions(text, namespace or {})

    def render_math(latex: str, block: bool) -> str:
        images: dict[str, QImage] = {}
        try:
            img = formula_html(latex, block, fontsize, browser._formulas, images)
        except Exception:
            delim = "$$" if block else "$"
            err = f'<code class="math-error">{delim}{html.escape(latex)}{delim}</code>'
            return f'<div align="center">{err}</div>' if block else err

        for name, qimg in images.items():
            browser.add_math_resource(name, qimg)
        if block:
            return f'<div class="math-block" align="center">{img}</div>'
        return img

    body = markdown.markdown(
        text, extensions=["extra", "sane_lists", _RosidaExtension(render_math)]
    )
    browser.setHtml(body)
    if embed_formulas:
        embed_math_objects(browser.document(), browser._formulas)
