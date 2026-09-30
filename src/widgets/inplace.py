import ast
from pathlib import Path
import re

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import sympy as sp
import polars as pl

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from worker.kernel import CellOutcome, Kernel
from widgets.clickable_frame import ClickableOutputFrame
from widgets.data import PolarsTableWidget
from widgets.inline_editor import InlineEditor
from widgets.callout import CalloutWidget
from widgets.figure import FigureWidget
from widgets.math_svg import latex_to_svg, svg_to_qimage
from widgets.math_text import (
    MATH_COLOR,
    MathTextBrowser,
    math_to_png_qimage,
    pt_to_px,
    render_markdown_with_math,
)


class InPlaceCell(QWidget):
    """Interactive notebook cell with smart mode detection, no radio buttons, and in-place switching."""

    executed = Signal()
    cell_focused = Signal(object)
    content_updated = Signal()

    # Erst nach dieser Zeit erscheint der Warteindikator; schnelle Zellen
    # wechseln so ohne Flackern direkt zum Ergebnis.
    BUSY_INDICATOR_DELAY_MS = 150

    def __init__(
        self, kernel_namespace: dict, kernel: Kernel | None = None, parent=None
    ):
        super().__init__(parent)
        self.namespace = kernel_namespace
        self.kernel = kernel or Kernel(kernel_namespace, self)
        self.mode = "auto"  # "auto", "python", or "markdown"
        self.has_rendered_once = False
        self.last_stdout = ""
        self.last_val = None
        self._is_collapsed_empty = False
        self.is_running = False  # in der Warteschlange oder in Berechnung
        self._edited_while_running = False

        self._busy_timer = QTimer(self)
        self._busy_timer.setSingleShot(True)
        self._busy_timer.setInterval(self.BUSY_INDICATOR_DELAY_MS)
        self._busy_timer.timeout.connect(self._show_busy_indicator)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

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
            self.tr("Click or press Ctrl+M to switch (Auto / Python / Text)")
        )
        self.btn_mode_pill.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_mode_pill.clicked.connect(self.cycle_mode)
        header.addWidget(self.btn_mode_pill)
        header.addStretch()

        lbl_hint = QLabel(self.tr("Shift+Enter to run"))
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
        if index == 1 and self.editor.hasFocus():
            # Fokus in der Zelle parken, bevor der Editor verschwindet. Sonst
            # reicht Qt ihn per focusNextPrevChild weiter und die QScrollArea
            # scrollt zum nächsten fokussierbaren Widget (z.B. ans Dokumentende).
            self.setFocus(Qt.FocusReason.OtherFocusReason)
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
        if self.is_running:
            self._edited_while_running = True
        self._show_stack_page(0)
        self.editor.fit_to_content()
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
        """Executes/renders the cell via the kernel; Python code runs in a worker thread."""
        content = self.editor.toPlainText().strip()
        if not content or self.is_running:
            return

        self.is_running = True
        self._edited_while_running = False

        if self._detect_effective_mode(content) == "markdown":
            # Textzellen rendern im GUI-Thread, aber erst wenn alle vorher
            # gestarteten Zellen fertig sind ({{ ... }} braucht deren Werte).
            self.kernel.run_call(lambda: self._render_markdown_content(content))
            return

        code = content
        if code.startswith("```python") or code.startswith("```py"):
            lines = code.split("\n")
            if lines[-1].strip() == "```":
                code = "\n".join(lines[1:-1])
            else:
                code = "\n".join(lines[1:])

        self.editor.setReadOnly(True)
        self._busy_timer.start()
        self.kernel.run_code(code, self._on_python_done)

    def _render_markdown_content(self, content: str):
        self._clear_view()
        self._is_collapsed_empty = False

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

        self._finish_render()

    def _show_busy_indicator(self):
        """Replaces the view with a wait indicator while the cell is computing."""
        self._clear_view()
        row = QHBoxLayout()
        row.setSpacing(10)
        bar = QProgressBar()
        bar.setRange(0, 0)  # unbestimmt: Lauflicht
        bar.setTextVisible(False)
        bar.setFixedSize(120, 6)
        bar.setStyleSheet(
            "QProgressBar { background: #e2e8f0; border: none; border-radius: 3px; }"
            "QProgressBar::chunk { background: #2563eb; border-radius: 3px; }"
        )
        text = self.tr("Computing …") if self.kernel.is_computing() else self.tr("Waiting …")
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #64748b; font-size: 12px; font-style: italic;")
        row.addWidget(bar)
        row.addWidget(lbl)
        row.addStretch()
        self.view_layout.addLayout(row)
        self.view_frame.attach_click_listeners(lbl)
        if not self._edited_while_running:
            self._show_stack_page(1)

    def _on_python_done(self, outcome: CellOutcome):
        self._busy_timer.stop()
        self.editor.setReadOnly(False)
        self._clear_view()
        self._is_collapsed_empty = False
        self._show_python_outcome(outcome)
        if self.view_layout.count() == 0:
            self._render_collapsed_placeholder()
            self._is_collapsed_empty = True
        self._finish_render()

    def _finish_render(self):
        QApplication.processEvents()
        self.has_rendered_once = True
        self.is_running = False
        # Wer während der Berechnung in den Editor gewechselt ist, bleibt dort.
        if not self._edited_while_running:
            self._show_stack_page(1)
        # content_updated vor executed: Das Dokument erkennt daran noch, ob der
        # Lauf beim Laden gestartet wurde (siehe DocumentCanvas._loading_runs).
        self.content_updated.emit()
        self.executed.emit()

    def _render_markdown_mode(self, text: str, base_dir: Path):
        browser = MathTextBrowser()
        browser.setFrameShape(QFrame.Shape.NoFrame)
        browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setStyleSheet("background-color: transparent;")
        browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        render_markdown_with_math(
            text, browser, namespace=self.namespace, base_dir=base_dir
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
        plus_lbl.setToolTip(self.tr("No output – click to edit"))
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

    def _show_python_outcome(self, outcome: CellOutcome):
        """Builds the output widgets for a finished Python run."""
        stdout_text = outcome.stdout.strip()
        last_val = outcome.value

        if outcome.error:
            # Letzte Traceback-Zeile ist "Typ: Meldung", der Rest als Tooltip.
            message = outcome.error.strip().splitlines()[-1]
            self.last_stdout = f"Error: {message}"
            self.last_val = None
            if stdout_text:
                self._add_stdout_label(stdout_text)
            err_lbl = QLabel(f"⚠️ {message}")
            err_lbl.setToolTip(outcome.error)
            err_lbl.setStyleSheet(
                "color: #dc2626; font-family: monospace; font-size: 12px; font-weight: bold;"
            )
            self.view_layout.addWidget(err_lbl)
            self.view_frame.attach_click_listeners(err_lbl)
            return

        self.last_stdout = stdout_text
        self.last_val = last_val

        if stdout_text:
            self._add_stdout_label(stdout_text)

        if last_val is not None:
            if isinstance(last_val, (sp.Basic, sp.MatrixBase)):
                latex_str = sp.latex(last_val)
                try:
                    svg = latex_to_svg(latex_str, pt_to_px(18), True, MATH_COLOR)
                    qimg = svg_to_qimage(svg)
                    w = round(svg.width)
                    h = round(svg.ascent + svg.descent)
                except Exception:
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
                table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
                self.view_layout.addWidget(table)
                # WICHTIG: KEIN attach_click_listeners(table) hier!

            else:
                val_lbl = QLabel(str(last_val))
                val_lbl.setStyleSheet(
                    "color: #0284c7; font-family: 'JetBrains Mono', monospace; font-size: 13px;"
                )
                self.view_layout.addWidget(val_lbl)
                self.view_frame.attach_click_listeners(val_lbl)

    def _add_stdout_label(self, text: str):
        out_lbl = QLabel(text)
        out_lbl.setStyleSheet(
            "font-family: 'JetBrains Mono', monospace; color: #475569; font-size: 12px; margin: 4px 0;"
        )
        self.view_layout.addWidget(out_lbl)
        self.view_frame.attach_click_listeners(out_lbl)
