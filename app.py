import os
import sys
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from palettes.latex import LatexPaletteDock

try:
    from document import (
        DocumentCanvas,
        InPlaceCell,
        math_to_png_qimage,
        math_to_svg_bytes,
        render_markdown_with_math,
    )
except ImportError:
    from native_document import (
        DocumentCanvas,
        InPlaceCell,
        math_to_png_qimage,
        math_to_svg_bytes,
        render_markdown_with_math,
    )

import matplotlib.pyplot as plt
import numpy as np
import sympy as sp


class StructureOutlineDock(QDockWidget):
    """Collapsible dock displaying the outline hierarchy of the notebook."""

    item_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__("Dokumentstruktur", parent)
        self.setObjectName("DocumentStructureDock")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 8, 6, 6)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background-color: #ffffff;
                font-size: 12px;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 5px 6px;
                border-radius: 4px;
                color: #334155;
            }
            QTreeWidget::item:hover {
                background-color: #f1f5f9;
            }
            QTreeWidget::item:selected {
                background-color: #e0f2fe;
                color: #0369a1;
                font-weight: 600;
            }
        """)
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

        self.setWidget(container)
        self.setMinimumWidth(220)

    def _on_item_clicked(self, item: QTreeWidgetItem):
        idx = item.data(0, Qt.ItemDataRole.UserRole)
        if idx is not None:
            self.item_selected.emit(idx)

    def update_outline(self, cells: list[InPlaceCell]):
        """Parses cell content into hierarchical outline headings."""
        self.tree.clear()
        for idx, cell in enumerate(cells):
            text = cell.editor.toPlainText().strip()
            if not text:
                continue

            effective = cell._detect_effective_mode(text)
            if effective == "markdown":
                for line in text.split("\n"):
                    line = line.strip()
                    if line.startswith("# "):
                        item = QTreeWidgetItem([f"H1  {line[2:].strip()}"])
                        item.setData(0, Qt.ItemDataRole.UserRole, idx)
                        self.tree.addTopLevelItem(item)
                    elif line.startswith("## "):
                        item = QTreeWidgetItem([f"  H2  {line[3:].strip()}"])
                        item.setData(0, Qt.ItemDataRole.UserRole, idx)
                        self.tree.addTopLevelItem(item)
                    elif line.startswith("### "):
                        item = QTreeWidgetItem([f"    H3  {line[4:].strip()}"])
                        item.setData(0, Qt.ItemDataRole.UserRole, idx)
                        self.tree.addTopLevelItem(item)
            else:
                first_line = text.split("\n")[0][:28]
                item = QTreeWidgetItem([f"⚡ {first_line}..."])
                item.setData(0, Qt.ItemDataRole.UserRole, idx)
                self.tree.addTopLevelItem(item)


class RosidaApp(QMainWindow):
    """Main application frame window embedding DocumentCanvas and providing menus, toolbars, and docks."""

    def __init__(self, initial_filepath: str | None = None):
        super().__init__()
        self.current_filepath: str | None = initial_filepath
        self._update_window_title()
        self.resize(1340, 920)

        self.namespace = {
            "sp": sp,
            "np": np,
            "plt": plt,
        }

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: #f8fafc; }")

        # Instantiate DocumentCanvas directly from document / native_document
        self.doc = DocumentCanvas(self.namespace, parent=self)
        self.scroll.setWidget(self.doc)
        self.setCentralWidget(self.scroll)

        self._setup_statusbar()
        self._setup_docks()
        self._setup_actions()
        self._setup_menus()
        self._setup_toolbars()

        self.doc.active_cell_changed.connect(self._on_active_cell_changed)
        self.doc.structure_changed.connect(self.dock_structure.update_outline)
        self.doc.cell_executed.connect(self._on_cell_executed)
        self.doc.undo_stack.cleanChanged.connect(lambda _: self._update_window_title())

        self._load_document_on_start()

    def _setup_statusbar(self):
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)
        self.statusbar.setStyleSheet("QStatusBar { background: #f1f5f9; border-top: 1px solid #e2e8f0; font-size: 11px; }")

        self.lbl_cell_info = QLabel("Zelle 1 von 1")
        self.lbl_cell_info.setStyleSheet("color: #475569; padding: 0 10px; font-weight: 500;")

        self.lbl_mode_badge = QLabel("⚡ Auto")
        self.lbl_mode_badge.setStyleSheet(
            "background-color: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px; font-weight: 500;"
        )

        self.lbl_kernel_status = QLabel("● Kernel: Bereit")
        self.lbl_kernel_status.setStyleSheet("color: #16a34a; font-weight: bold; padding: 0 10px;")

        self.statusbar.addPermanentWidget(self.lbl_cell_info)
        self.statusbar.addPermanentWidget(self.lbl_mode_badge)
        self.statusbar.addPermanentWidget(self.lbl_kernel_status)
        self.statusbar.showMessage("Rosida betriebsbereit", 3000)

    def _setup_docks(self):
        self.dock_structure = StructureOutlineDock(self)
        self.dock_structure.item_selected.connect(self.doc.scroll_to_cell)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_structure)

        self.dock_palette = LatexPaletteDock(self)
        self.dock_palette.insert_requested.connect(self.doc.insert_text_into_active)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_palette)

    def _setup_actions(self):
        self.act_undo = QAction("↶ Rückgängig", self)
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.act_undo.setStatusTip("Letzte Aktion rückgängig machen (Ctrl+Z)")
        self.act_undo.triggered.connect(self._smart_undo)

        self.act_redo = QAction("↷ Wiederholen", self)
        self.act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.act_redo.setStatusTip("Letzte rückgängig gemachte Aktion wiederholen (Ctrl+Y)")
        self.act_redo.triggered.connect(self._smart_redo)

        self.act_run_cell = QAction("▶ Zelle ausführen", self)
        self.act_run_cell.setShortcut(QKeySequence("Shift+Return"))
        self.act_run_cell.triggered.connect(self.doc.run_active_cell)

        self.act_run_all = QAction("⏩ Alle ausführen", self)
        self.act_run_all.setShortcut(QKeySequence("Ctrl+Shift+Return"))
        self.act_run_all.triggered.connect(self.doc.run_all_cells)

        self.act_insert_above = QAction("⇧ Zelle darüber einfügen", self)
        self.act_insert_above.setShortcut(QKeySequence("Ctrl+Shift+A"))
        self.act_insert_above.triggered.connect(self.doc.insert_cell_above)

        self.act_insert_below = QAction("⇩ Zelle darunter einfügen", self)
        self.act_insert_below.setShortcut(QKeySequence("Ctrl+Shift+B"))
        self.act_insert_below.triggered.connect(self.doc.insert_cell_below)

        self.act_delete_cell = QAction("🗑 Zelle löschen", self)
        self.act_delete_cell.setShortcut(QKeySequence("Ctrl+Shift+D"))
        self.act_delete_cell.triggered.connect(self.doc.delete_active_cell)

        self.act_toggle_mode = QAction("⇄ Modus umschalten (Auto/Python/Text)", self)
        self.act_toggle_mode.setShortcut(QKeySequence("Ctrl+M"))
        self.act_toggle_mode.triggered.connect(self.doc.toggle_active_mode)

        self.act_open = QAction("📂 Dokument öffnen...", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self._on_open_file)

        self.act_save = QAction("💾 Speichern", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self._on_save_file)

        self.act_save_as = QAction("💾 Speichern unter...", self)
        self.act_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.act_save_as.triggered.connect(self._on_save_as_file)

        self.act_export_html = QAction("🌐 Als HTML exportieren...", self)
        self.act_export_html.setShortcut(QKeySequence("Ctrl+Shift+H"))
        self.act_export_html.triggered.connect(self._on_export_html)

        self.act_export_pdf = QAction("📄 Als PDF exportieren...", self)
        self.act_export_pdf.setShortcut(QKeySequence("Ctrl+Shift+P"))
        self.act_export_pdf.triggered.connect(self._on_export_pdf)

        self.act_toggle_structure = self.dock_structure.toggleViewAction()
        self.act_toggle_structure.setText("Dokumentstruktur (Sidebar)")
        self.act_toggle_structure.setShortcut(QKeySequence("F3"))

        self.act_toggle_palette = self.dock_palette.toggleViewAction()
        self.act_toggle_palette.setText("LaTeX-Palette (Sidebar)")
        self.act_toggle_palette.setShortcut(QKeySequence("F4"))

    def _setup_menus(self):
        menubar = self.menuBar()

        menu_file = menubar.addMenu("&Datei")
        act_new = menu_file.addAction("&Neues Dokument")
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._on_new_document)

        menu_file.addAction(self.act_open)
        menu_file.addSeparator()
        menu_file.addAction(self.act_save)
        menu_file.addAction(self.act_save_as)

        menu_file.addSeparator()
        menu_export = menu_file.addMenu("E&xportieren")
        menu_export.addAction(self.act_export_html)
        menu_export.addAction(self.act_export_pdf)

        menu_file.addSeparator()
        act_quit = menu_file.addAction("&Beenden")
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)

        menu_edit = menubar.addMenu("&Bearbeiten")
        menu_edit.addAction(self.act_undo)
        menu_edit.addAction(self.act_redo)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_insert_above)
        menu_edit.addAction(self.act_insert_below)
        menu_edit.addAction(self.act_delete_cell)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_toggle_mode)

        menu_cell = menubar.addMenu("&Zelle")
        menu_cell.addAction(self.act_run_cell)
        menu_cell.addAction(self.act_run_all)

        menu_view = menubar.addMenu("&Ansicht")
        menu_view.addAction(self.act_toggle_structure)
        menu_view.addAction(self.act_toggle_palette)

    def _setup_toolbars(self):
        toolbar = QToolBar("Hauptaktionen", self)
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background: #ffffff;
                border-bottom: 1px solid #e2e8f0;
                padding: 3px 6px;
                spacing: 6px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                color: #334155;
            }
            QToolButton:hover {
                background: #f1f5f9;
                border-color: #cbd5e1;
            }
            QToolButton:pressed {
                background: #e2e8f0;
            }
        """)
        self.addToolBar(toolbar)

        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)
        toolbar.addSeparator()
        toolbar.addAction(self.act_undo)
        toolbar.addAction(self.act_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.act_insert_above)
        toolbar.addAction(self.act_insert_below)
        toolbar.addAction(self.act_delete_cell)
        toolbar.addSeparator()
        toolbar.addAction(self.act_run_cell)
        toolbar.addAction(self.act_run_all)
        toolbar.addAction(self.act_toggle_mode)
        toolbar.addSeparator()
        toolbar.addAction(self.act_export_html)
        toolbar.addAction(self.act_export_pdf)
        toolbar.addSeparator()
        toolbar.addAction(self.act_toggle_structure)
        toolbar.addAction(self.act_toggle_palette)

    def _smart_undo(self):
        focus_w = QApplication.focusWidget()
        if isinstance(focus_w, QPlainTextEdit) and focus_w.document().isUndoAvailable():
            focus_w.undo()
            return
        if self.doc.undo_stack.canUndo():
            self.doc.undo_stack.undo()
            self._update_window_title()

    def _smart_redo(self):
        focus_w = QApplication.focusWidget()
        if isinstance(focus_w, QPlainTextEdit) and focus_w.document().isRedoAvailable():
            focus_w.redo()
            return
        if self.doc.undo_stack.canRedo():
            self.doc.undo_stack.redo()
            self._update_window_title()

    def _update_window_title(self):
        dirty_flag = " *" if hasattr(self, 'doc') and not self.doc.undo_stack.isClean() else ""
        if self.current_filepath:
            name = os.path.basename(self.current_filepath)
            self.setWindowTitle(f"Rosida – {name}{dirty_flag}")
        else:
            self.setWindowTitle(f"Rosida – Unbenanntes Dokument{dirty_flag}")

    def _on_active_cell_changed(self, cell: InPlaceCell, index: int, total: int):
        self.lbl_cell_info.setText(f"Zelle {index + 1} von {max(1, total)}")
        mode = cell.get_mode()
        if mode == "auto":
            self.lbl_mode_badge.setText("⚡ Auto")
            self.lbl_mode_badge.setStyleSheet(
                "background-color: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px; font-weight: 500;"
            )
        elif mode == "markdown":
            self.lbl_mode_badge.setText("📝 Text (fix)")
            self.lbl_mode_badge.setStyleSheet(
                "background-color: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
            )
        else:
            self.lbl_mode_badge.setText("⚡ Python (fix)")
            self.lbl_mode_badge.setStyleSheet(
                "background-color: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
            )
        self._update_window_title()

    def _on_cell_executed(self, cell):
        self.lbl_kernel_status.setText("● Kernel: Zelle berechnet")
        self.lbl_kernel_status.setStyleSheet("color: #0284c7; font-weight: bold; padding: 0 10px;")
        self.statusbar.showMessage("Ausführung abgeschlossen", 2500)

    def _on_open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Rosida Dokument öffnen",
            "",
            "Markdown-Dateien (*.md *.markdown);;Alle Dateien (*)",
        )
        if filepath:
            try:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                self.doc.load_from_markdown(filepath)
                self.current_filepath = filepath
                self._update_window_title()
                self.statusbar.showMessage(f"Geöffnet: {filepath}", 3000)
            except Exception as err:
                QMessageBox.critical(self, "Fehler beim Öffnen", f"Datei konnte nicht geöffnet werden:\n{err}")
            finally:
                QApplication.restoreOverrideCursor()

    def _on_save_file(self):
        if self.current_filepath:
            try:
                self.doc.save_to_markdown(self.current_filepath)
                self._update_window_title()
                self.statusbar.showMessage(f"Gespeichert: {self.current_filepath}", 3000)
            except Exception as err:
                QMessageBox.critical(self, "Fehler beim Speichern", f"Datei konnte nicht gespeichert werden:\n{err}")
        else:
            self._on_save_as_file()

    def _on_save_as_file(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Dokument speichern unter",
            "berechnung.md",
            "Markdown-Dokument (*.md);;Alle Dateien (*)",
        )
        if filepath:
            try:
                self.doc.save_to_markdown(filepath)
                self.current_filepath = filepath
                self._update_window_title()
                self.statusbar.showMessage(f"Gespeichert: {filepath}", 3000)
            except Exception as err:
                QMessageBox.critical(self, "Fehler beim Speichern", f"Datei konnte nicht gespeichert werden:\n{err}")

    def _on_export_html(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Dokument als HTML exportieren",
            "rosida_dokument.html",
            "HTML-Dokument (*.html *.htm)",
        )
        if filepath:
            try:
                self.doc.export_html(filepath)
                self.statusbar.showMessage(f"HTML-Export erfolgreich: {filepath}", 4000)
            except Exception as err:
                QMessageBox.critical(self, "Exportfehler", f"Fehler beim HTML-Export:\n{err}")

    def _on_export_pdf(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Dokument als PDF exportieren",
            "rosida_dokument.pdf",
            "PDF-Dokument (*.pdf)",
        )
        if filepath:
            try:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                self.doc.export_pdf(filepath)
                self.statusbar.showMessage(f"PDF-Export erfolgreich: {filepath}", 4000)
            except Exception as err:
                QMessageBox.critical(self, "Exportfehler", f"Fehler beim PDF-Export:\n{err}")
            finally:
                QApplication.restoreOverrideCursor()

    def _on_new_document(self):
        while self.doc.cells:
            c = self.doc.cells.pop()
            self.doc.layout.removeWidget(c)
            c.deleteLater()
        self.current_filepath = None
        self.doc.undo_stack.clear()
        self.doc.undo_stack.setClean()
        self._update_window_title()
        self.doc.insert_cell()
        self.statusbar.showMessage("Neues Dokument erstellt", 2000)

    def _load_document_on_start(self):
        if self.current_filepath and os.path.exists(self.current_filepath):
            try:
                self.doc.load_from_markdown(self.current_filepath)
            except Exception as err:
                self.statusbar.showMessage(f"Warnung: {err}", 3000)
                self.doc.insert_cell()
        else:
            self.doc.insert_cell()

        self.doc.undo_stack.clear()
        self.doc.undo_stack.setClean()
        self._update_window_title()
        self.dock_structure.update_outline(self.doc.cells)


def main():
    sys.argv[0] = "Rosida"
    QCoreApplication.setApplicationName("Rosida")
    QCoreApplication.setOrganizationName("Rosida")

    app = QApplication(["Rosida"] + sys.argv[1:])

    initial_file = sys.argv[1] if len(sys.argv) > 1 and os.path.exists(sys.argv[1]) else None
    win = RosidaApp(initial_filepath=initial_file)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
