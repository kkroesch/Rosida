import ast
import contextlib
from io import StringIO
from pathlib import Path
import re

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import sympy as sp
import polars as pl

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from widgets.clickable_frame import ClickableOutputFrame
from widgets.data import PolarsTableWidget
from widgets.inline_editor import InlineEditor
from widgets.callout import CalloutWidget
from widgets.figure import FigureWidget
from widgets.math_text import (
    MathTextBrowser,
    math_to_png_qimage,
    render_markdown_with_math,
)



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
        self._is_collapsed_empty = False

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
        self.btn_mode_pill.setToolTip(
            "Klicken oder Ctrl+M zum Umschalten (Auto / Python / Text)"
        )
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

        self._show_stack_page(0)
        self._update_mode_pill()

    def _show_stack_page(self, index: int):
        """Switches the edit/view page and makes the inactive page's size ignored.

        QStackedLayout otherwise sizes itself to the largest of all pages (even
        hidden ones), so a tall editor would keep the cell tall even while a
        tiny collapsed output is shown, and vice versa.
        """
        self.edit_container.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred if index == 0 else QSizePolicy.Policy.Ignored,
        )
        self.view_frame.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred if index == 1 else QSizePolicy.Policy.Ignored,
        )
        self.stack.setCurrentIndex(index)
        self.updateGeometry()

    def cycle_mode(self):
        """Cycles mode override between auto, python, and markdown."""
        modes = ["auto", "python", "markdown"]
        cur_idx = modes.index(self.mode) if self.mode in modes else 0
        self.mode = modes[(cur_idx + 1) % len(modes)]
        self.editor.highlighter.set_mode(self.mode)
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
        if self._is_collapsed_empty:
            doc_height = int(self.editor.document().size().height()) + 22
            self.editor.setFixedHeight(max(56, doc_height))
        elif self.has_rendered_once and self.last_rendered_height > 60:
            target_editor_h = max(56, self.last_rendered_height - 28)
            self.editor.setFixedHeight(target_editor_h)

        self._show_stack_page(0)
        self.editor.setFocus()
        self.cell_focused.emit(self)
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)

    def cancel_edit(self):
        if self.has_rendered_once:
            self._show_stack_page(1)
            self.cell_focused.emit(self)

    def _clear_view(self):
        self.view_layout.setContentsMargins(10, 8, 10, 8)
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

        self._is_collapsed_empty = False

        if effective_mode == "markdown":
            # Basisverzeichnis ermitteln
            win = self.window()
            base_dir = (
                Path(win.current_filepath).parent
                if getattr(win, "current_filepath", None)
                else Path.cwd()
            )

            # Fall A: Quarto Callout-Box
            if content.startswith(":::") and "{.callout-" in content:
                widget = CalloutWidget(content, namespace=self.namespace, parent=self)
                self.view_layout.addWidget(widget)
                self.view_frame.attach_click_listeners(widget)

            # Fall B: Quarto / Markdown Abbildung
            elif content.startswith("![") and "](" in content:
                widget = FigureWidget(content, base_dir=base_dir, parent=self)
                self.view_layout.addWidget(widget)
                self.view_frame.attach_click_listeners(widget)

            # Fall C: Regulärer Fließtext mit Mathe
            else:
                self._render_markdown_mode(content, base_dir)
        else:
            code_to_run = content
            if code_to_run.startswith("```python") or code_to_run.startswith("```py"):
                lines = code_to_run.split("\n")
                if lines[-1].strip() == "```":
                    code_to_run = "\n".join(lines[1:-1])
                else:
                    code_to_run = "\n".join(lines[1:])
            self._render_python_mode(code_to_run)

            if self.view_layout.count() == 0:
                self._render_collapsed_placeholder()
                self._is_collapsed_empty = True

        QApplication.processEvents()
        self.last_rendered_height = max(
            self.view_frame.sizeHint().height(), self.view_frame.height()
        )
        self.has_rendered_once = True
        self._show_stack_page(1)
        self.executed.emit()
        self.content_updated.emit()

    def _render_markdown_mode(self, text: str, base_dir: Path):
        browser = MathTextBrowser()
        browser.setFrameShape(QFrame.Shape.NoFrame)
        browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setStyleSheet("background-color: transparent;")
        browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        render_markdown_with_math(
            text, browser, fontsize=13, namespace=self.namespace, base_dir=base_dir
        )
        doc = browser.document()
        doc.setTextWidth(720)
        browser.setFixedHeight(int(doc.size().height()) + 10)

        self.view_layout.addWidget(browser)
        self.view_frame.attach_click_listeners(browser)

    def _render_collapsed_placeholder(self):
        """Compact left-aligned "+" marker for Python cells without visible output (imports, assignments, ...)."""
        self.view_layout.setContentsMargins(2, 0, 2, 0)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        plus_lbl = QLabel("+")
        plus_lbl.setFixedSize(18, 18)
        plus_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus_lbl.setToolTip("Kein Output – klicken zum Bearbeiten")
        plus_lbl.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                background-color: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 9px;
                font-size: 12px;
                font-weight: 600;
            }
        """)
        row.addWidget(plus_lbl)

        self.view_layout.addLayout(row)
        self.view_frame.attach_click_listeners(plus_lbl)

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
                    canvas.setSizePolicy(
                        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                    )
                    self.view_layout.addWidget(canvas)
                    self.view_frame.attach_click_listeners(canvas)

                # NEU: Polars DataFrame abfangen
                elif pl is not None and isinstance(last_val, pl.DataFrame):
                    table = PolarsTableWidget(last_val)
                    table.setMaximumHeight(320)
                    table.setSizePolicy(
                        QSizePolicy.Policy.Expanding, QSizePolicy.Preferred
                    )
                    self.view_layout.addWidget(table)
                    # WICHTIG: KEIN attach_click_listeners(table) hier!

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
            err_lbl.setStyleSheet(
                "color: #dc2626; font-family: monospace; font-size: 12px; font-weight: bold;"
            )
            self.view_layout.addWidget(err_lbl)
            self.view_frame.attach_click_listeners(err_lbl)
