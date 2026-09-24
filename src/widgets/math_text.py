from io import BytesIO
import re

from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import math_to_image

from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage, QTextDocument
from PySide6.QtWidgets import QTextBrowser


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
        math_to_image(f"${clean_expr}$", buf, prop=prop, dpi=dpi, format="png", color=color)
    except TypeError:
        math_to_image(f"${clean_expr}$", buf, prop=prop, dpi=dpi, format="png")
    buf.seek(0)

    img = QImage()
    img.loadFromData(buf.getvalue(), "PNG")

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

    def add_math_resource(self, name: str, img: QImage):
        self._resources[name] = img
        self.document().addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), img)

    def loadResource(self, res_type: int, name: QUrl):
        url_str = name.toString()
        if url_str in self._resources:
            return self._resources[url_str]
        for key, val in self._resources.items():
            if key.endswith(url_str) or url_str.endswith(key):
                return val
        return super().loadResource(res_type, name)


def _format_text_line(text: str, inlines: dict[str, str]) -> str:
    """Helper converting basic markdown formatting while preserving math tokens."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!⟦)\*([^\*]+?)\*(?!⟧)", r"<i>\1</i>", text)
    text = re.sub(
        r"`([^`]+?)`",
        r'<code style="background-color: #f1f5f9; color: #0f172a; padding: 1px 4px; border-radius: 3px; font-family: monospace;">\1</code>',
        text,
    )
    for placeholder, inline_html in inlines.items():
        if placeholder in text:
            text = text.replace(placeholder, inline_html)
    return text


def render_markdown_with_math(md_text: str, browser: MathTextBrowser, fontsize: int = 13) -> None:
    """Robust two-pass parser for Markdown with inline ($...$) and block ($$...$$) math."""
    browser._resources.clear()
    doc = browser.document()
    doc.clear()

    text = md_text.strip()
    if not text:
        browser.setHtml("")
        return

    res_counter = 0
    blocks: dict[str, str] = {}
    inlines: dict[str, str] = {}

    def _replace_block(match):
        nonlocal res_counter
        res_counter += 1
        raw_math = match.group(1).strip()
        placeholder = f"⟦BLOCK_MATH_{res_counter}⟧"
        res_name = f"math://block_{res_counter}.png"
        try:
            qimg, w, h = math_to_png_qimage(raw_math, fontsize=fontsize + 2, dpi=192)
            browser.add_math_resource(res_name, qimg)
            blocks[placeholder] = (
                f'<div align="center" style="margin: 14px 0;">'
                f'<img src="{res_name}" width="{w}" height="{h}"></div>'
            )
        except Exception:
            blocks[placeholder] = (
                f'<div align="center" style="margin: 8px 0;"><code style="color: #dc2626; '
                f'background: #fee2e2; padding: 2px 6px; border-radius: 4px;">$${raw_math}$$</code></div>'
            )
        return f"\n\n{placeholder}\n\n"

    text = re.sub(r"\$\$(.+?)\$\$", _replace_block, text, flags=re.DOTALL)

    def _replace_inline(match):
        nonlocal res_counter
        res_counter += 1
        raw_math = match.group(1).strip()
        placeholder = f"⟦INLINE_MATH_{res_counter}⟧"
        res_name = f"math://inline_{res_counter}.png"
        try:
            qimg, w, h = math_to_png_qimage(raw_math, fontsize=fontsize, dpi=192)
            browser.add_math_resource(res_name, qimg)
            inlines[placeholder] = (
                f'<img src="{res_name}" width="{w}" height="{h}" '
                f'style="vertical-align: middle; margin: 0 2px;">'
            )
        except Exception:
            inlines[placeholder] = (
                f'<code style="color: #dc2626; background: #fee2e2; padding: 1px 3px; '
                f'border-radius: 3px;">${raw_math}$</code>'
            )
        return placeholder

    text = re.sub(r"(?<!\$)\$([^\$\n]+?)\$(?!\$)", _replace_inline, text)

    html_parts = []
    raw_paragraphs = text.split("\n\n")

    for para in raw_paragraphs:
        para = para.strip()
        if not para:
            continue

        if para in blocks:
            html_parts.append(blocks[para])
            continue

        lines = para.split("\n")
        if lines[0].startswith("# "):
            heading_text = _format_text_line(lines[0][2:].strip(), inlines)
            html_parts.append(
                f'<h1 style="color: #0f172a; margin: 10px 0 6px 0; font-size: 20px; font-weight: 700;">{heading_text}</h1>'
            )
            if len(lines) > 1:
                rest = _format_text_line("<br>".join(lines[1:]), inlines)
                html_parts.append(f'<p style="color: #334155; line-height: 1.6; margin: 4px 0; font-size: 13px;">{rest}</p>')
            continue
        elif lines[0].startswith("## "):
            heading_text = _format_text_line(lines[0][3:].strip(), inlines)
            html_parts.append(
                f'<h2 style="color: #1e293b; margin: 8px 0 4px 0; font-size: 16px; font-weight: 600;">{heading_text}</h2>'
            )
            if len(lines) > 1:
                rest = _format_text_line("<br>".join(lines[1:]), inlines)
                html_parts.append(f'<p style="color: #334155; line-height: 1.6; margin: 4px 0; font-size: 13px;">{rest}</p>')
            continue
        elif lines[0].startswith("### "):
            heading_text = _format_text_line(lines[0][4:].strip(), inlines)
            html_parts.append(
                f'<h3 style="color: #334155; margin: 6px 0 3px 0; font-size: 14px; font-weight: 600;">{heading_text}</h3>'
            )
            if len(lines) > 1:
                rest = _format_text_line("<br>".join(lines[1:]), inlines)
                html_parts.append(f'<p style="color: #334155; line-height: 1.6; margin: 4px 0; font-size: 13px;">{rest}</p>')
            continue
        elif lines[0].startswith("> "):
            quote_content = "\n".join([l[2:] if l.startswith("> ") else l for l in lines])
            inner = _format_text_line(quote_content.replace("\n", "<br>"), inlines)
            html_parts.append(
                f'<blockquote style="color: #64748b; border-left: 3px solid #cbd5e1; '
                f'margin: 8px 0; padding: 4px 0 4px 10px; font-style: italic;">{inner}</blockquote>'
            )
            continue

        p_content = _format_text_line("<br>".join(lines), inlines)
        for placeholder, block_html in blocks.items():
            if placeholder in p_content:
                p_content = p_content.replace(placeholder, block_html)

        html_parts.append(f'<p style="color: #334155; line-height: 1.6; margin: 5px 0; font-size: 13px;">{p_content}</p>')

    full_html = "".join(html_parts)
    for placeholder, inline_html in inlines.items():
        full_html = full_html.replace(placeholder, inline_html)
    for placeholder, block_html in blocks.items():
        full_html = full_html.replace(placeholder, block_html)

    browser.setHtml(full_html)
