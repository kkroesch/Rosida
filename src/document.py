import ast
import contextlib
from io import BytesIO, StringIO
from pathlib import Path
import re

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import sympy as sp
import polars as pl

from exporters.qmd import QmdRenderer

from PySide6.QtCore import QMarginsF, Qt, QUrl, Signal
from PySide6.QtGui import (
    QImage,
    QPageLayout,
    QPageSize,
    QPdfWriter,
    QPixmap,
    QTextCursor,
    QTextDocument,
    QUndoStack,
)
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

from actions.edit import DeleteCellCommand, InsertCellCommand
from widgets.clickable_frame import ClickableOutputFrame
from widgets.data import PolarsTableWidget
from widgets.inline_editor import InlineEditor
from widgets.math_text import MathTextBrowser, math_to_png_qimage, render_markdown_with_math


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

        render_markdown_with_math(text, browser, fontsize=13, namespace=self.namespace)
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

        except Exception as err:
            self.last_stdout = f"Error: {err}"
            self.last_val = None
            err_lbl = QLabel(f"⚠️ {type(err).__name__}: {err}")
            err_lbl.setStyleSheet("color: #dc2626; font-family: monospace; font-size: 12px; font-weight: bold;")
            self.view_layout.addWidget(err_lbl)
            self.view_frame.attach_click_listeners(err_lbl)


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

    def export_qmd(self, filepath: str):
        """Exports the document as a Quarto (.qmd) file, evaluating {{ }} templates in markdown cells
        and embedding tables/figures/LaTeX for already-computed Python cell results."""
        out_path = Path(filepath)
        renderer = QmdRenderer(output_dir=out_path.parent)

        body_chunks = []
        for cell in self.cells:
            content = cell.editor.toPlainText().strip()
            if not content:
                continue

            effective = cell._detect_effective_mode(content)

            if effective == "markdown":
                body_chunks.append(renderer.render(template=content, context=cell.namespace))
            else:
                code = content
                if not (code.startswith("```python") or code.startswith("```py")):
                    code = f"```python\n{code}\n```"
                body_chunks.append(code)

                if cell.last_stdout:
                    body_chunks.append(f"```\n{cell.last_stdout}\n```")
                if cell.last_val is not None:
                    body_chunks.append(renderer.format_value(cell.last_val, is_block=True))

        frontmatter = (
            "---\n"
            "title: Rosida Dokument\n"
            "format:\n"
            "  html: default\n"
            "  typst: default\n"
            "---\n\n"
        )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(frontmatter + "\n\n".join(body_chunks) + "\n", encoding="utf-8")

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
