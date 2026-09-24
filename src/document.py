import ast
import base64
import contextlib
from io import BytesIO, StringIO
import os
import re
import sys

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import math_to_image
import matplotlib.pyplot as plt
import numpy as np
import sympy as sp

from PySide6.QtCore import QByteArray, QMarginsF, QPoint, QRect, QSize, Qt, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QFont,
    QImage,
    QMouseEvent,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
    QPixmap,
    QTextCursor,
    QTextDocument,
    QUndoCommand,
    QUndoStack,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


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


def math_to_svg_bytes(
    latex_expr: str,
    fontsize: int = 15,
    color: str = "#0f172a",
) -> bytes:
    """Renders a LaTeX expression into an SVG byte stream using Matplotlib's mathtext engine."""
    clean_expr = _clean_latex_for_mathtext(latex_expr)
    fig = Figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${clean_expr}$", fontsize=fontsize, color=color, va="baseline")
    buf = BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.03, transparent=True)
    plt.close(fig)
    return buf.getvalue()


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


class MacResizeGrip(QWidget):
    """Subtle corner resize grip with diagonal ridges."""

    def __init__(self, target_editor: QPlainTextEdit, parent=None):
        super().__init__(parent)
        self.target = target_editor
        self.setFixedSize(16, 16)
        self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        self.drag_start_y = 0
        self.initial_height = 0
        self.is_dragging = False
        self.setToolTip("Ziehen, um Eingabefeld zu vergrößern")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_y = event.globalPosition().y()
            self.initial_height = self.target.height()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging:
            delta_y = event.globalPosition().y() - self.drag_start_y
            new_height = max(50, int(self.initial_height + delta_y))
            self.target.setFixedHeight(new_height)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.is_dragging = False
        event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(QColor("#94a3b8"), 1.2)
        painter.setPen(pen)
        w, h = self.width(), self.height()
        painter.drawLine(w - 3, h - 11, w - 11, h - 3)
        painter.drawLine(w - 3, h - 7, w - 7, h - 3)
        painter.drawLine(w - 3, h - 3, w - 3, h - 3)


class InlineEditor(QPlainTextEdit):
    """Plain text editor supporting Shift+Enter, Escape, Focus-Reporting, and resizing."""

    run_requested = Signal()
    escape_pressed = Signal()
    mode_toggle_requested = Signal()
    focused_in = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("JetBrains Mono", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-left: 3px solid #2563eb;
                border-radius: 6px;
                padding: 8px 18px 10px 8px;
            }
            QPlainTextEdit:focus {
                border-color: #93c5fd;
                border-left: 3px solid #1d4ed8;
            }
            QScrollBar:vertical {
                border: none;
                background: #f1f5f9;
                width: 6px;
                margin: 4px 2px 4px 0;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
        """)
        self.grip = MacResizeGrip(self, self)
        self.adjust_initial_height()
        self.textChanged.connect(self._on_content_changed)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focused_in.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.grip.move(self.width() - self.grip.width() - 2, self.height() - self.grip.height() - 2)

    def adjust_initial_height(self):
        doc_height = int(self.document().size().height())
        target_height = max(56, min(doc_height + 22, 280))
        self.setFixedHeight(target_height)

    def _on_content_changed(self):
        doc_height = int(self.document().size().height()) + 22
        if doc_height > self.height() and self.height() < 350:
            self.setFixedHeight(doc_height)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.run_requested.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_M and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.mode_toggle_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ClickableOutputFrame(QFrame):
    """Clickable interactive container routing mouse clicks to switch into edit mode."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Klicken, um Inhalt zu bearbeiten (Escape im Editor zum Schließen)")
        self.setStyleSheet("""
            ClickableOutputFrame {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px;
            }
            ClickableOutputFrame:hover {
                background-color: #f8fafc;
                border: 1px dashed #cbd5e1;
            }
        """)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def attach_click_listeners(self, widget: QWidget):
        """Recursively registers event filter for seamless child clicking."""
        widget.installEventFilter(self)
        if isinstance(widget, QScrollArea) and widget.viewport():
            widget.viewport().installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            return True
        return super().eventFilter(watched, event)


class InPlaceCell(QWidget):
    """Interactive notebook cell with smart mode detection, no radio buttons, and in-place switching."""

    executed = Signal()
    cell_focused = Signal(object)
    content_updated = Signal()

    def __init__(self, kernel_namespace: dict, parent=None):
        super().__init__(parent)
        self.namespace = kernel_namespace
        self.mode = "auto"  # "auto", "python", or "markdown"
        self.has_rendered_once = False
        self.last_rendered_height = 80
        self.last_stdout = ""
        self.last_val = None

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        self.stack = QStackedLayout(self)
        self.stack.setContentsMargins(0, 2, 0, 2)

        # 1. Edit mode container (clean mode badge instead of bulky radio buttons)
        self.edit_container = QWidget()
        self.edit_layout = QVBoxLayout(self.edit_container)
        self.edit_layout.setContentsMargins(0, 0, 0, 0)
        self.edit_layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)

        self.btn_mode_pill = QPushButton("⚡ Auto")
        self.btn_mode_pill.setToolTip("Klicken oder Ctrl+M zum Umschalten (Auto / Python / Text)")
        self.btn_mode_pill.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_mode_pill.clicked.connect(self.cycle_mode)
        header.addWidget(self.btn_mode_pill)
        header.addStretch()

        lbl_hint = QLabel("Shift+Enter zum Ausführen")
        lbl_hint.setStyleSheet("color: #94a3b8; font-size: 11px;")
        header.addWidget(lbl_hint)
        self.edit_layout.addLayout(header)

        # Editor
        self.editor = InlineEditor(self)
        self.editor.run_requested.connect(self.render)
        self.editor.escape_pressed.connect(self.cancel_edit)
        self.editor.mode_toggle_requested.connect(self.cycle_mode)
        self.editor.focused_in.connect(lambda: self.cell_focused.emit(self))
        self.editor.textChanged.connect(self.content_updated.emit)
        self.edit_layout.addWidget(self.editor)

        self.stack.addWidget(self.edit_container)

        # 2. Rendered mode container
        self.view_frame = ClickableOutputFrame(self)
        self.view_layout = QVBoxLayout(self.view_frame)
        self.view_layout.setContentsMargins(10, 8, 10, 8)
        self.view_frame.clicked.connect(self.switch_to_edit)
        self.stack.addWidget(self.view_frame)

        self.stack.setCurrentIndex(0)
        self._update_mode_pill()

    def cycle_mode(self):
        """Cycles mode override between auto, python, and markdown."""
        modes = ["auto", "python", "markdown"]
        cur_idx = modes.index(self.mode) if self.mode in modes else 0
        self.mode = modes[(cur_idx + 1) % len(modes)]
        self._update_mode_pill()
        self.content_updated.emit()

    def set_mode(self, mode: str):
        self.mode = mode if mode in ("auto", "python", "markdown") else "auto"
        self._update_mode_pill()

    def get_mode(self) -> str:
        return self.mode

    def _update_mode_pill(self):
        if self.mode == "auto":
            self.btn_mode_pill.setText("⚡ Auto")
            self.btn_mode_pill.setStyleSheet("""
                QPushButton {
                    font-size: 11px; color: #475569; background-color: #f1f5f9;
                    border: 1px solid #cbd5e1; border-radius: 4px; padding: 2px 8px; font-weight: 500;
                }
                QPushButton:hover { background-color: #e2e8f0; color: #0f172a; }
            """)
        elif self.mode == "python":
            self.btn_mode_pill.setText("⚡ Python")
            self.btn_mode_pill.setStyleSheet("""
                QPushButton {
                    font-size: 11px; color: #1e40af; background-color: #dbeafe;
                    border: 1px solid #93c5fd; border-radius: 4px; padding: 2px 8px; font-weight: bold;
                }
            """)
        else:
            self.btn_mode_pill.setText("📝 Text")
            self.btn_mode_pill.setStyleSheet("""
                QPushButton {
                    font-size: 11px; color: #92400e; background-color: #fef3c7;
                    border: 1px solid #fde68a; border-radius: 4px; padding: 2px 8px; font-weight: bold;
                }
            """)

    def _detect_effective_mode(self, content: str) -> str:
        """Determines whether content should be executed as Python or rendered as Markdown."""
        if self.mode in ("python", "markdown"):
            return self.mode

        text = content.strip()
        if not text:
            return "markdown"

        if text.startswith("```python") or text.startswith("```py"):
            return "python"

        first_line = text.split("\n", 1)[0].strip()
        if (
            re.match(r"^#{1,6}\s", first_line)
            or first_line.startswith("> ")
            or re.match(r"^(\*|-|\+|\d+\.)\s", first_line)
        ):
            return "markdown"

        if "$" in text:
            try:
                ast.parse(text)
            except SyntaxError:
                return "markdown"

        try:
            parsed = ast.parse(text)
            if len(parsed.body) > 0:
                return "python"
            return "markdown"
        except SyntaxError:
            return "markdown"

    def switch_to_edit(self):
        if self.has_rendered_once and self.last_rendered_height > 60:
            target_editor_h = max(56, self.last_rendered_height - 28)
            self.editor.setFixedHeight(target_editor_h)

        self.stack.setCurrentIndex(0)
        self.editor.setFocus()
        self.cell_focused.emit(self)
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)

    def cancel_edit(self):
        if self.has_rendered_once:
            self.stack.setCurrentIndex(1)
            self.cell_focused.emit(self)

    def _clear_view(self):
        while self.view_layout.count():
            item = self.view_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

    def render(self):
        content = self.editor.toPlainText().strip()
        if not content:
            return

        self._clear_view()
        effective_mode = self._detect_effective_mode(content)

        if effective_mode == "markdown":
            self._render_markdown_mode(content)
        else:
            code_to_run = content
            if code_to_run.startswith("```python") or code_to_run.startswith("```py"):
                lines = code_to_run.split("\n")
                if lines[-1].strip() == "```":
                    code_to_run = "\n".join(lines[1:-1])
                else:
                    code_to_run = "\n".join(lines[1:])
            self._render_python_mode(code_to_run)

        QApplication.processEvents()
        self.last_rendered_height = max(self.view_frame.sizeHint().height(), self.view_frame.height())
        self.has_rendered_once = True
        self.stack.setCurrentIndex(1)
        self.executed.emit()
        self.content_updated.emit()

    def _render_markdown_mode(self, text: str):
        browser = MathTextBrowser()
        browser.setFrameShape(QFrame.Shape.NoFrame)
        browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setStyleSheet("background-color: transparent;")
        browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        render_markdown_with_math(text, browser, fontsize=13)
        doc = browser.document()
        doc.setTextWidth(720)
        browser.setFixedHeight(int(doc.size().height()) + 10)

        self.view_layout.addWidget(browser)
        self.view_frame.attach_click_listeners(browser)

    def _render_python_mode(self, code: str):
        stdout_capture = StringIO()
        last_val = None

        try:
            parsed = ast.parse(code)
            body = parsed.body

            with contextlib.redirect_stdout(stdout_capture):
                if body and isinstance(body[-1], ast.Expr):
                    if len(body) > 1:
                        exec_mod = ast.Module(body=body[:-1], type_ignores=[])
                        exec(compile(exec_mod, "<cell>", "exec"), self.namespace)
                    expr_mod = ast.Expression(body=body[-1].value)
                    last_val = eval(compile(expr_mod, "<cell>", "eval"), self.namespace)
                else:
                    exec(code, self.namespace)

            stdout_text = stdout_capture.getvalue().strip()
            self.last_stdout = stdout_text
            self.last_val = last_val

            if stdout_text:
                out_lbl = QLabel(stdout_text)
                out_lbl.setStyleSheet(
                    "font-family: 'JetBrains Mono', monospace; color: #475569; font-size: 12px; margin: 4px 0;"
                )
                self.view_layout.addWidget(out_lbl)
                self.view_frame.attach_click_listeners(out_lbl)

            if last_val is not None:
                if isinstance(last_val, sp.Basic):
                    latex_str = sp.latex(last_val)
                    qimg, w, h = math_to_png_qimage(latex_str, fontsize=17, dpi=192)
                    pixmap = QPixmap.fromImage(qimg)

                    lbl = QLabel()
                    lbl.setPixmap(pixmap)
                    lbl.setFixedSize(w, h)

                    row = QHBoxLayout()
                    row.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    row.addWidget(lbl)
                    self.view_layout.addLayout(row)
                    self.view_frame.attach_click_listeners(lbl)

                elif isinstance(last_val, Figure):
                    canvas = FigureCanvasQTAgg(last_val)
                    canvas.setMinimumHeight(280)
                    canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                    self.view_layout.addWidget(canvas)
                    self.view_frame.attach_click_listeners(canvas)

                else:
                    val_lbl = QLabel(str(last_val))
                    val_lbl.setStyleSheet(
                        "color: #0284c7; font-family: 'JetBrains Mono', monospace; font-size: 13px;"
                    )
                    self.view_layout.addWidget(val_lbl)
                    self.view_frame.attach_click_listeners(val_lbl)

        except Exception as err:
            self.last_stdout = f"Error: {err}"
            self.last_val = None
            err_lbl = QLabel(f"⚠️ {type(err).__name__}: {err}")
            err_lbl.setStyleSheet("color: #dc2626; font-family: monospace; font-size: 12px; font-weight: bold;")
            self.view_layout.addWidget(err_lbl)
            self.view_frame.attach_click_listeners(err_lbl)

    def generate_html_fragment(self) -> str:
        """Generates self-contained HTML for this cell with embedded base64 SVG assets."""
        content = self.editor.toPlainText().strip()
        if not content:
            return ""

        effective = self._detect_effective_mode(content)

        if effective == "markdown":
            text = content

            def _export_block_math(match):
                raw = match.group(1).strip()
                try:
                    svg_bytes = math_to_svg_bytes(raw, fontsize=18)
                    b64 = base64.b64encode(svg_bytes).decode("ascii")
                    return f'<div style="text-align: center; margin: 18px 0;"><img src="data:image/svg+xml;base64,{b64}" style="max-width: 100%; height: auto;"></div>'
                except Exception:
                    return f'<pre style="color: red;">$${raw}$$</pre>'

            def _export_inline_math(match):
                raw = match.group(1).strip()
                try:
                    svg_bytes = math_to_svg_bytes(raw, fontsize=13)
                    b64 = base64.b64encode(svg_bytes).decode("ascii")
                    return f'<img src="data:image/svg+xml;base64,{b64}" style="vertical-align: middle; margin: 0 2px;">'
                except Exception:
                    return f'<code>${raw}$</code>'

            text = re.sub(r"\$\$(.+?)\$\$", _export_block_math, text, flags=re.DOTALL)
            text = re.sub(r"(?<!\$)\$([^\$\n]+?)\$(?!\$)", _export_inline_math, text)

            html_lines = []
            for para in text.split("\n\n"):
                para = para.strip()
                if not para:
                    continue
                if para.startswith("# "):
                    html_lines.append(f'<h1 style="color: #0f172a; margin: 18px 0 8px 0; font-size: 24px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;">{para[2:]}</h1>')
                elif para.startswith("## "):
                    html_lines.append(f'<h2 style="color: #1e293b; margin: 14px 0 6px 0; font-size: 19px;">{para[3:]}</h2>')
                elif para.startswith("### "):
                    html_lines.append(f'<h3 style="color: #334155; margin: 12px 0 4px 0; font-size: 15px;">{para[4:]}</h3>')
                elif para.startswith("> "):
                    html_lines.append(f'<blockquote style="color: #64748b; border-left: 3px solid #cbd5e1; margin: 10px 0; padding: 4px 12px; font-style: italic;">{para[2:]}</blockquote>')
                elif para.startswith("<div style=\"text-align: center;"):
                    html_lines.append(para)
                else:
                    html_lines.append(f'<p style="color: #334155; line-height: 1.6; margin: 8px 0; font-size: 14px;">{para.replace(chr(10), "<br>")}</p>')
            return "\n".join(html_lines)

        else:
            escaped_code = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            out_parts = [
                '<div style="margin: 16px 0; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; background: #ffffff;">',
                '<div style="background: #f8fafc; padding: 5px 12px; font-size: 11px; font-family: monospace; color: #64748b; border-bottom: 1px solid #e2e8f0;">⚡ Python</div>',
                f'<pre style="margin: 0; padding: 10px 14px; font-family: monospace; font-size: 12px; background: #f8fafc; color: #0f172a; overflow-x: auto;">{escaped_code}</pre>',
            ]

            has_output = False
            output_body = []

            if self.last_stdout:
                has_output = True
                escaped_stdout = self.last_stdout.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                output_body.append(f'<div style="font-family: monospace; font-size: 12px; color: #475569; margin-bottom: 8px; white-space: pre-wrap;">{escaped_stdout}</div>')

            if self.last_val is not None:
                has_output = True
                if isinstance(self.last_val, sp.Basic):
                    latex_str = sp.latex(self.last_val)
                    svg_bytes = math_to_svg_bytes(latex_str, fontsize=20)
                    b64 = base64.b64encode(svg_bytes).decode("ascii")
                    output_body.append(f'<div style="text-align: center; margin: 12px 0;"><img src="data:image/svg+xml;base64,{b64}"></div>')
                elif isinstance(self.last_val, Figure):
                    buf = BytesIO()
                    self.last_val.savefig(buf, format="svg", bbox_inches="tight", transparent=True)
                    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                    output_body.append(f'<div style="text-align: center; margin: 12px 0;"><img src="data:image/svg+xml;base64,{b64}" style="max-width: 100%; height: auto;"></div>')
                else:
                    output_body.append(f'<div style="font-family: monospace; font-size: 13px; color: #0284c7;">{self.last_val}</div>')

            if has_output:
                out_parts.append('<div style="padding: 12px; border-top: 1px solid #e2e8f0; background: #ffffff;">')
                out_parts.extend(output_body)
                out_parts.append('</div>')

            out_parts.append('</div>')
            return "\n".join(out_parts)


class InsertCellCommand(QUndoCommand):
    """Undoable command for inserting a notebook cell."""

    def __init__(self, doc_canvas, index: int, text: str = "", mode: str = "auto", auto_run: bool = False, description: str = "Zelle einfügen"):
        super().__init__(description)
        self.doc = doc_canvas
        self.index = index
        self.text = text
        self.mode = mode
        self.auto_run = auto_run
        self.cell = None

    def redo(self):
        if self.cell is None:
            self.cell = self.doc._create_cell_widget(self.text, self.mode)
            if self.auto_run:
                self.cell.render()
        self.doc._attach_cell_widget(self.cell, self.index)
        self.cell.switch_to_edit()
        self.doc.set_active_cell(self.cell)
        self.doc.structure_changed.emit(self.doc.cells)

    def undo(self):
        if self.cell and self.cell in self.doc.cells:
            self.doc._detach_cell_widget(self.cell)
            if self.doc.cells:
                prev_idx = max(0, min(self.index - 1, len(self.doc.cells) - 1))
                self.doc.set_active_cell(self.doc.cells[prev_idx])
            self.doc.structure_changed.emit(self.doc.cells)


class DeleteCellCommand(QUndoCommand):
    """Undoable command for deleting a notebook cell."""

    def __init__(self, doc_canvas, cell: InPlaceCell, description: str = "Zelle löschen"):
        super().__init__(description)
        self.doc = doc_canvas
        self.cell = cell
        self.index = self.doc.cells.index(cell) if cell in self.doc.cells else -1

    def redo(self):
        if self.cell in self.doc.cells:
            self.index = self.doc.cells.index(self.cell)
            self.doc._detach_cell_widget(self.cell)
            if self.doc.cells:
                next_idx = min(self.index, len(self.doc.cells) - 1)
                self.doc.set_active_cell(self.doc.cells[next_idx])
            self.doc.structure_changed.emit(self.doc.cells)

    def undo(self):
        if self.index >= 0:
            self.doc._attach_cell_widget(self.cell, self.index)
            self.doc.set_active_cell(self.cell)
            self.cell.switch_to_edit()
            self.doc.structure_changed.emit(self.doc.cells)


class DocumentCanvas(QWidget):
    """Central interactive canvas managing the cell stack, execution, exports, and active states."""

    active_cell_changed = Signal(object, int, int)
    structure_changed = Signal(list)
    cell_executed = Signal(object)

    def __init__(self, kernel_namespace: dict, parent=None):
        super().__init__(parent)
        self.namespace = kernel_namespace
        self.cells: list[InPlaceCell] = []
        self._active_cell: InPlaceCell | None = None
        self._is_loading: bool = False
        self.undo_stack = QUndoStack(self)

        self.setStyleSheet("background-color: #f8fafc;")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setContentsMargins(50, 30, 50, 40)
        self.layout.setSpacing(12)

        self.stretch_spacer = QWidget()
        self.stretch_spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.stretch_spacer)

    def get_active_cell(self) -> InPlaceCell | None:
        if self._active_cell and self._active_cell in self.cells:
            return self._active_cell
        return self.cells[-1] if self.cells else None

    def get_active_index(self) -> int:
        active = self.get_active_cell()
        return self.cells.index(active) if active in self.cells else -1

    def set_active_cell(self, cell: InPlaceCell):
        self._active_cell = cell
        idx = self.get_active_index()
        self.active_cell_changed.emit(cell, idx, len(self.cells))

    def _create_cell_widget(self, initial_text: str = "", mode: str = "auto") -> InPlaceCell:
        cell = InPlaceCell(self.namespace, parent=self)
        cell.set_mode(mode)
        if initial_text:
            cell.editor.setPlainText(initial_text)
            cell.editor.adjust_initial_height()

        cell.cell_focused.connect(self.set_active_cell)
        cell.content_updated.connect(lambda: self.structure_changed.emit(self.cells))
        cell.executed.connect(lambda: self._on_cell_executed(cell))
        return cell

    def _attach_cell_widget(self, cell: InPlaceCell, index: int = -1):
        self.layout.removeWidget(self.stretch_spacer)
        if index < 0 or index >= len(self.cells):
            self.layout.addWidget(cell)
            self.cells.append(cell)
        else:
            self.layout.insertWidget(index, cell)
            self.cells.insert(index, cell)
        cell.show()
        self.layout.addWidget(self.stretch_spacer)

    def _detach_cell_widget(self, cell: InPlaceCell):
        if cell in self.cells:
            self.cells.remove(cell)
            self.layout.removeWidget(cell)
            cell.hide()

    def insert_cell(self, index: int = -1, initial_text: str = "", mode: str = "auto", auto_run: bool = False) -> InPlaceCell:
        cell = self._create_cell_widget(initial_text, mode)
        self._attach_cell_widget(cell, index)
        if auto_run:
            cell.render()
        self.set_active_cell(cell)
        self.structure_changed.emit(self.cells)
        return cell

    def _on_cell_executed(self, cell: InPlaceCell):
        self.cell_executed.emit(cell)
        if not self._is_loading:
            self.ensure_trailing_cell()
            self.structure_changed.emit(self.cells)

    def ensure_trailing_cell(self):
        if self._is_loading:
            return
        if not self.cells:
            self.insert_cell()
            return
        last_cell = self.cells[-1]
        has_content = bool(last_cell.editor.toPlainText().strip())
        is_rendered = (last_cell.stack.currentIndex() == 1)
        if has_content or is_rendered:
            new_cell = self.insert_cell()
            new_cell.editor.setFocus()

    def insert_cell_above(self):
        idx = max(0, self.get_active_index())
        cmd = InsertCellCommand(self, index=idx, description="Zelle darüber einfügen")
        self.undo_stack.push(cmd)

    def insert_cell_below(self):
        idx = self.get_active_index()
        target_idx = idx + 1 if idx >= 0 else len(self.cells)
        cmd = InsertCellCommand(self, index=target_idx, description="Zelle darunter einfügen")
        self.undo_stack.push(cmd)

    def delete_active_cell(self):
        active = self.get_active_cell()
        if not active:
            return
        if len(self.cells) <= 1:
            active.editor.clear()
            active.switch_to_edit()
            return
        cmd = DeleteCellCommand(self, active, description="Zelle löschen")
        self.undo_stack.push(cmd)

    def insert_text_into_active(self, text: str):
        active = self.get_active_cell()
        if not active:
            return
        if active.stack.currentIndex() == 1:
            active.switch_to_edit()

        editor = active.editor
        cursor = editor.textCursor()
        cursor.insertText(text)
        editor.setTextCursor(cursor)
        editor.setFocus()

    def run_active_cell(self):
        active = self.get_active_cell()
        if active:
            active.render()

    def run_all_cells(self):
        for cell in self.cells:
            cell.render()

    def toggle_active_mode(self):
        active = self.get_active_cell()
        if active:
            active.cycle_mode()
            self.set_active_cell(active)

    def scroll_to_cell(self, index: int):
        if 0 <= index < len(self.cells):
            cell = self.cells[index]
            cell.switch_to_edit()
            self.set_active_cell(cell)

    def export_html(self, filepath: str):
        """Exports the complete document to a standalone responsive HTML file."""
        body_fragments = []
        for cell in self.cells:
            fragment = cell.generate_html_fragment()
            if fragment:
                body_fragments.append(fragment)

        full_html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>Rosida Dokument</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    @media print {{
      body {{ margin: 0; padding: 0; background: #ffffff; }}
      .document-paper {{ box-shadow: none; border: none; padding: 0; }}
      .no-print {{ display: none; }}
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: #f8fafc;
      color: #1e293b;
      margin: 0;
      padding: 40px 20px;
    }}
    .document-paper {{
      max-width: 820px;
      margin: 0 auto;
      background: #ffffff;
      padding: 50px 60px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
  </style>
</head>
<body>
  <div class="document-paper">
    {"".join(body_fragments)}
  </div>
</body>
</html>"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_html)

    def export_pdf(self, filepath: str):
        """Exports the document directly to a vector-grade A4 PDF using Qt QPdfWriter."""
        doc = QTextDocument()
        doc.setDocumentMargin(24)

        res_counter = 0
        html_fragments = []

        for cell in self.cells:
            content = cell.editor.toPlainText().strip()
            if not content:
                continue

            effective = cell._detect_effective_mode(content)

            if effective == "markdown":
                browser = MathTextBrowser()
                render_markdown_with_math(content, browser, fontsize=12)
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

    def save_to_markdown(self, filepath: str):
        """Saves notebook as a clean, human-readable Markdown file (.md)."""
        md_chunks = []
        for cell in self.cells:
            content = cell.editor.toPlainText().strip()
            if not content:
                continue

            effective = cell._detect_effective_mode(content)
            if effective == "markdown":
                md_chunks.append(content)
            else:
                if content.startswith("```python") or content.startswith("```py"):
                    md_chunks.append(content)
                else:
                    md_chunks.append(f"```python\n{content}\n```")

        full_md = "\n\n".join(md_chunks) + "\n"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_md)

        self.undo_stack.setClean()

    def load_from_markdown(self, filepath: str):
        """Parses a Markdown file and reconstructs interactive notebook cells without ghost cells."""
        self._is_loading = True
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_text = f.read()

            while self.cells:
                c = self.cells.pop()
                self.layout.removeWidget(c)
                c.deleteLater()

            pattern = re.compile(r"```(?:python|py)\s*\n(.*?)```", re.DOTALL)
            last_end = 0

            for match in pattern.finditer(raw_text):
                text_before = raw_text[last_end:match.start()].strip()
                if text_before:
                    parts = re.split(r"\n\s*---\s*\n", text_before)
                    for part in parts:
                        cleaned = part.strip()
                        if cleaned:
                            self.insert_cell(initial_text=cleaned, mode="markdown", auto_run=True)

                code_content = match.group(1).strip()
                if code_content:
                    self.insert_cell(initial_text=code_content, mode="python", auto_run=True)

                last_end = match.end()

            trailing_text = raw_text[last_end:].strip()
            if trailing_text:
                parts = re.split(r"\n\s*---\s*\n", trailing_text)
                for part in parts:
                    cleaned = part.strip()
                    if cleaned:
                        self.insert_cell(initial_text=cleaned, mode="markdown", auto_run=True)

            if not self.cells:
                self.insert_cell()
        finally:
            self._is_loading = False

        self.ensure_trailing_cell()
        self.structure_changed.emit(self.cells)
        self.undo_stack.clear()
        self.undo_stack.setClean()


class PaperNotebook(QMainWindow):
    """Standalone runner for pure native document mode without sidebars."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rosida – Native Document Mode")
        self.resize(900, 940)

        self.namespace = {
            "sp": sp,
            "np": np,
            "plt": plt,
        }

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: #f8fafc; }")

        self.doc = DocumentCanvas(self.namespace, parent=self)
        self.scroll.setWidget(self.doc)
        self.setCentralWidget(self.scroll)

        # Starts with a single empty input cell ready to type
        self.doc.ensure_trailing_cell()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = PaperNotebook()
    win.show()
    sys.exit(app.exec())
