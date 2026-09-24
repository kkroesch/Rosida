from io import BytesIO

from matplotlib.figure import Figure
import sympy as sp

from PySide6.QtCore import QMarginsF, QUrl
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from widgets.math_text import MathTextBrowser, math_to_png_qimage, render_markdown_with_math


def export_pdf(cells, filepath: str) -> None:
    """Renders notebook cells directly to a vector-grade A4 PDF using Qt QPdfWriter."""
    doc = QTextDocument()
    doc.setDocumentMargin(24)

    res_counter = 0
    html_fragments = []

    for cell in cells:
        content = cell.editor.toPlainText().strip()
        if not content:
            continue

        effective = cell._detect_effective_mode(content)

        if effective == "markdown":
            browser = MathTextBrowser()
            render_markdown_with_math(content, browser, fontsize=12, namespace=cell.namespace)
            for url_str, qimg in browser._resources.items():
                doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(url_str), qimg)
            sub_doc = browser.document()
            html_fragments.append(sub_doc.toHtml())
        else:
            escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_fragments.append(
                f'<div style="margin: 12px 0; background-color: #f8fafc; border: 1px solid #cbd5e1; '
                f'padding: 8px; border-radius: 4px; font-family: monospace; font-size: 11px;">'
                f'<pre style="margin: 0; color: #0f172a;">{escaped}</pre></div>'
            )
            if cell.last_stdout:
                esc_out = cell.last_stdout.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_fragments.append(f'<div style="font-family: monospace; font-size: 10px; color: #475569; margin: 4px 0;">{esc_out}</div>')

            if cell.last_val is not None:
                if isinstance(cell.last_val, sp.Basic):
                    res_counter += 1
                    res_url = QUrl(f"pdfres://math_{res_counter}.png")
                    qimg, w, h = math_to_png_qimage(sp.latex(cell.last_val), fontsize=18, dpi=200)
                    doc.addResource(QTextDocument.ResourceType.ImageResource, res_url, qimg)
                    html_fragments.append(f'<div align="center" style="margin: 12px 0;"><img src="{res_url.toString()}" width="{w}" height="{h}"></div>')
                elif isinstance(cell.last_val, Figure):
                    res_counter += 1
                    res_url = QUrl(f"pdfres://plot_{res_counter}.png")
                    buf = BytesIO()
                    cell.last_val.savefig(buf, format="png", dpi=200, bbox_inches="tight")
                    qimg = QImage.fromData(buf.getvalue())
                    doc.addResource(QTextDocument.ResourceType.ImageResource, res_url, qimg)
                    w = int(qimg.width() / 2)
                    h = int(qimg.height() / 2)
                    html_fragments.append(f'<div align="center" style="margin: 14px 0;"><img src="{res_url.toString()}" width="{w}" height="{h}"></div>')
                else:
                    html_fragments.append(f'<div style="font-family: monospace; font-size: 11px; color: #0284c7;">{cell.last_val}</div>')

    doc.setHtml("<br>".join(html_fragments))

    writer = QPdfWriter(filepath)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
    doc.print_(writer)
