from pathlib import Path
import re
import json
import inspect

from exporters.html import export_html as render_html
from exporters.pdf import export_pdf as render_pdf
from exporters.qmd import QmdRenderer
from widgets.frontmatter import FrontmatterCell
from widgets.inplace import InPlaceCell
from worker.kernel import Kernel

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from actions.edit import DeleteCellCommand, InsertCellCommand, MoveCellCommand


def get_namespace_snapshot(ns: dict) -> list[dict]:
    """Helper: Collect all variables from namespace."""
    snapshot = []
    for name, val in ns.items():
        if name.startswith("_"):
            continue
        if inspect.ismodule(val) or inspect.isfunction(val) or inspect.isclass(val):
            continue

        # Typ & lesbare Repräsentation ableiten
        type_name = type(val).__name__

        # Polars / DataFrames
        if hasattr(val, "shape") and hasattr(val, "schema"):
            h, w = val.shape
            value_str = f"[{h} × {w}]"
        # NumPy
        elif hasattr(val, "shape") and hasattr(val, "dtype"):
            value_str = f"shape {val.shape}, {val.dtype}"
        # Standard-Typen
        elif isinstance(val, (int, float, bool)):
            value_str = str(val)
        elif isinstance(val, str):
            value_str = repr(val[:37] + "..." if len(val) > 40 else val)
        elif isinstance(val, (list, tuple, set)):
            value_str = f"len {len(val)}"
        elif isinstance(val, dict):
            value_str = f"{len(val)} Schlüssel"
        else:
            raw = repr(val)
            value_str = raw[:37] + "..." if len(raw) > 40 else raw

        snapshot.append({"name": name, "type": type_name, "value": value_str})

    # Sortiert nach Name
    return sorted(snapshot, key=lambda x: x["name"].lower())


class DocumentCanvas(QWidget):
    """Central interactive canvas managing the cell stack, execution, exports, and active states."""

    active_cell_changed = Signal(object, int, int)
    structure_changed = Signal(list)
    cell_executed = Signal(object)
    modified_changed = Signal(bool)
    variables_updated = Signal(list)

    def __init__(self, kernel_namespace: dict, parent=None):
        super().__init__(parent)
        self.namespace = kernel_namespace
        self.cells: list[InPlaceCell] = []
        self._active_cell: InPlaceCell | None = None
        self._is_loading: bool = False
        # Beim Laden gestartete Zellen; ihre (asynchronen) Ergebnisse sollen
        # das frisch geöffnete Dokument nicht als geändert markieren.
        self._loading_runs: set[InPlaceCell] = set()
        self.kernel = Kernel(self.namespace, self)
        self._is_modified: bool = False
        self.undo_stack = QUndoStack(self)

        self.setStyleSheet("background-color: #f8fafc;")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setContentsMargins(50, 30, 50, 40)
        self.layout.setSpacing(12)

        self.stretch_spacer = QWidget()
        self.stretch_spacer.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        self.layout.addWidget(self.stretch_spacer)

        self.frontmatter_cell = FrontmatterCell()
        self.layout.addWidget(self.frontmatter_cell)
        self.frontmatter_cell.commit_and_collapse()

        # Jede strukturelle oder inhaltliche Änderung (Text, Modus, Zellen) markiert das Dokument als geändert.
        self.structure_changed.connect(lambda _cells: self.set_modified(True))

    def is_modified(self) -> bool:
        return self._is_modified

    def set_modified(self, modified: bool = True):
        if self._is_modified != modified:
            self._is_modified = modified
            self.modified_changed.emit(modified)

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

    def _create_cell_widget(
        self, initial_text: str = "", mode: str = "auto"
    ) -> InPlaceCell:
        cell = InPlaceCell(self.namespace, kernel=self.kernel, parent=self)
        cell.set_mode(mode)
        if initial_text:
            cell.editor.setPlainText(initial_text)

        cell.cell_focused.connect(self.set_active_cell)
        cell.content_updated.connect(lambda: self._on_cell_content_updated(cell))
        cell.executed.connect(lambda: self._on_cell_executed(cell))
        return cell

    def _attach_cell_widget(self, cell: InPlaceCell, index: int = -1):
        self.layout.removeWidget(self.stretch_spacer)
        if index < 0 or index >= len(self.cells):
            self.layout.addWidget(cell)
            self.cells.append(cell)
        else:
            # Im Layout steht vor den Zellen noch die Frontmatter, deshalb
            # die Layout-Position der verdrängten Zelle statt des Listenindex.
            self.layout.insertWidget(self.layout.indexOf(self.cells[index]), cell)
            self.cells.insert(index, cell)
        cell.show()
        self.layout.addWidget(self.stretch_spacer)

    def _detach_cell_widget(self, cell: InPlaceCell):
        if cell in self.cells:
            self.cells.remove(cell)
            self.layout.removeWidget(cell)
            cell.hide()

    def insert_cell(
        self,
        index: int = -1,
        initial_text: str = "",
        mode: str = "auto",
        auto_run: bool = False,
    ) -> InPlaceCell:
        cell = self._create_cell_widget(initial_text, mode)
        self._attach_cell_widget(cell, index)
        if auto_run:
            if self._is_loading:
                self._loading_runs.add(cell)
            cell.render()
        self.set_active_cell(cell)
        self.structure_changed.emit(self.cells)
        return cell

    def _on_cell_content_updated(self, cell: InPlaceCell):
        if cell not in self._loading_runs:
            self.structure_changed.emit(self.cells)

    def _on_cell_executed(self, cell: InPlaceCell):
        self.cell_executed.emit(cell)
        # Snapshot aus dem geteilten Canvas-Namensraum ziehen und melden
        snapshot = get_namespace_snapshot(self.namespace)
        self.variables_updated.emit(snapshot)
        if cell in self._loading_runs:
            self._loading_runs.discard(cell)
            return
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
        is_rendered = last_cell.stack.currentIndex() == 1
        if has_content or is_rendered:
            new_cell = self.insert_cell()
            new_cell.editor.setFocus()

    def insert_cell_before_active(self):
        idx = max(0, self.get_active_index())
        cmd = InsertCellCommand(self, index=idx, description="Zelle einfügen")
        self.undo_stack.push(cmd)

    def move_active_cell(self, offset: int):
        """Moves the active cell by offset positions (-1 = up, +1 = down)."""
        active = self.get_active_cell()
        if not active:
            return
        target = self.cells.index(active) + offset
        if not 0 <= target < len(self.cells):
            return
        self.undo_stack.push(MoveCellCommand(self, active, offset))

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
        render_pdf(self.cells, filepath)

    def export_html(self, filepath: str):
        """Exports the document as a standalone HTML page; KaTeX renders the formulas."""
        win = self.window()
        current = getattr(win, "current_filepath", None)
        base_dir = Path(current).parent if current else Path.cwd()
        render_html(
            self.cells,
            filepath,
            frontmatter=self.frontmatter_cell.editor.toPlainText(),
            base_dir=base_dir,
        )

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
                body_chunks.append(
                    renderer.render(template=content, context=cell.namespace)
                )
            else:
                code = content
                if not (code.startswith("```python") or code.startswith("```py")):
                    code = f"```python\n{code}\n```"
                body_chunks.append(code)

                if cell.last_stdout:
                    body_chunks.append(f"```\n{cell.last_stdout}\n```")
                if cell.last_val is not None:
                    body_chunks.append(
                        renderer.format_value(cell.last_val, is_block=True)
                    )

        frontmatter = (
            "---\n"
            "title: Rosida Dokument\n"
            "format:\n"
            "  html: default\n"
            "  typst: default\n"
            "---\n\n"
        )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            frontmatter + "\n\n".join(body_chunks) + "\n", encoding="utf-8"
        )

    def save_to_markdown(self, filepath: str):
        """Saves notebook as a clean, human-readable Markdown file (.md)."""
        chunks = []
        prev_was_md = False

        doc_properties = self.frontmatter_cell.editor.toPlainText().strip()

        for cell in self.cells:
            content = cell.editor.toPlainText().strip()
            if not content:
                continue

            effective = cell._detect_effective_mode(content)
            is_md = effective == "markdown"

            if is_md:
                # ZWINGEND: Trenner zwischen zwei aufeinanderfolgenden Markdown-Zellen
                if prev_was_md:
                    chunks.append("---")
                chunks.append(content)
                prev_was_md = True
            else:
                if content.startswith("```python") or content.startswith("```py"):
                    chunks.append(content)
                else:
                    chunks.append(f"```python\n{content}\n```")
                prev_was_md = False

        full_md = f"---\n{doc_properties}\n---\n\n" + "\n\n".join(chunks) + "\n"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_md)

        self.undo_stack.setClean()
        self.set_modified(False)

    def _split_markdown_blocks(self, text: str) -> list[str]:
        """Trennt Textblöcke an '---' Linien, ignoriert Leerblöcke."""
        # Matcht '---' am Textanfang, Textende oder umgeben von Zeilenumbrüchen
        parts = re.split(r"(?:^|\n)\s*---\s*(?:\n|$)", text.strip())
        return [p.strip() for p in parts if p.strip()]

    def load_from_markdown(self, filepath: str):
        """Parses a Markdown file and reconstructs interactive notebook cells without ghost cells."""
        self._is_loading = True
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # 1. Frontmatter exakt an den '---' Markern abtrennen
            if content.startswith("---\n"):
                parts = content.split("---\n", 2)
                if len(parts) >= 3:
                    # parts[1] ist das YAML, parts[2] ist der Rest des Dokuments
                    yaml_text = parts[1].strip()
                    content = parts[2].lstrip()

                    self.frontmatter_cell.editor.setPlainText(yaml_text)
                    self.frontmatter_cell.commit_and_collapse()
            else:
                # Kein Frontmatter da
                self.frontmatter_cell.editor.setPlainText("")
                self.frontmatter_cell.commit_and_collapse()

            while self.cells:
                c = self.cells.pop()
                self.layout.removeWidget(c)
                c.deleteLater()

            pattern = re.compile(r"```(?:python|py)\s*\n(.*?)```", re.DOTALL)
            last_end = 0

            for match in pattern.finditer(content):
                text_before = content[last_end : match.start()].strip()
                if text_before:
                    if text_before:
                        # Hier die neue Zerlegung nutzen:
                        for part in self._split_markdown_blocks(text_before):
                            self.insert_cell(
                                initial_text=part, mode="markdown", auto_run=True
                            )

                code_content = match.group(1).strip()
                if code_content:
                    self.insert_cell(
                        initial_text=code_content, mode="python", auto_run=True
                    )

                last_end = match.end()

            trailing_text = content[last_end:].strip()
            if trailing_text:
                # Und auch beim Rest am Dokumentende:
                for part in self._split_markdown_blocks(trailing_text):
                    self.insert_cell(initial_text=part, mode="markdown", auto_run=True)

            if not self.cells:
                self.insert_cell()
        finally:
            self._is_loading = False

        self.ensure_trailing_cell()
        self.structure_changed.emit(self.cells)
        self.undo_stack.clear()
        self.undo_stack.setClean()
        self.set_modified(False)

    def load_from_ipynb(self, filepath: str, auto_run: bool = False):
        """Importiert ein Jupyter Notebook (.ipynb), ignoriert alten State/Outputs und erzeugt native Zellen."""
        self._is_loading = True
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                nb = json.load(f)

            # 1. Bestehende Zellen entfernen
            while self.cells:
                c = self.cells.pop()
                self.layout.removeWidget(c)
                c.deleteLater()

            # 2. Zellen sequenziell übernehmen
            for cell_data in nb.get("cells", []):
                cell_type = cell_data.get("cell_type", "")
                raw_source = cell_data.get("source", "")

                # Jupyter speichert source entweder als Zeilenliste oder String
                if isinstance(raw_source, list):
                    source = "".join(raw_source).strip()
                else:
                    source = str(raw_source).strip()

                if not source:
                    continue

                if cell_type == "markdown":
                    self.insert_cell(
                        initial_text=source, mode="markdown", auto_run=True
                    )

                elif cell_type == "code":
                    # IPython-Magics (% und !) auskommentieren, um SyntaxErrors zu verhindern
                    cleaned_lines = []
                    for line in source.split("\n"):
                        trimmed = line.strip()
                        if trimmed.startswith(("%", "!")):
                            cleaned_lines.append(f"# {line}  # ipython-magic")
                        else:
                            cleaned_lines.append(line)
                    code_content = "\n".join(cleaned_lines)

                    self.insert_cell(
                        initial_text=code_content,
                        mode="python",
                        auto_run=auto_run,
                    )

            if not self.cells:
                self.insert_cell()

        finally:
            self._is_loading = False

        self.ensure_trailing_cell()
        self.structure_changed.emit(self.cells)
        self.undo_stack.clear()
        self.undo_stack.setClean()
