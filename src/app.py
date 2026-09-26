import os
import sys
from pathlib import Path

from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtCore import Qt, QSize, QCoreApplication

from PySide6.QtWidgets import (
    QMessageBox,
    QApplication,
    QLabel,
    QMainWindow,
    QScrollArea,
    QStatusBar,
    QToolBar,
)

from actions.cell import RunAllAction, RunCellAction
from actions.edit import (
    DeleteCellAction,
    InsertCellAboveAction,
    InsertCellBelowAction,
    RedoAction,
    ToggleModeAction,
    UndoAction,
)
from actions.file import (
    ExportPdfAction,
    ExportQmdAction,
    NewDocumentAction,
    OpenDocumentAction,
    QuitAction,
    RecentFilesMenu,
    SaveAction,
    SaveAsAction,
    add_recent_file,
)
from actions.help import AboutAction, ManualAction, SettingsAction, maybe_show_manual_on_first_run
from actions.view import ToggleStructureDockAction, TogglePaletteDockAction, ToggleVariablesDockAction
from docks.latex import LatexPaletteDock
from docks.structure_outline import StructureOutlineDock
from docks.inspector import VariableInspectorDock

try:
    from document import DocumentCanvas, InPlaceCell
except ImportError:
    from native_document import DocumentCanvas, InPlaceCell

import matplotlib.pyplot as plt
import numpy as np
import sympy as sp
import polars as pl


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
            "pl": pl,
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
        self.doc.modified_changed.connect(lambda _: self._update_window_title())

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

        self.dock_variables = VariableInspectorDock(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_variables)

        self.act_toggle_variables = ToggleVariablesDockAction(self.dock_variables, self)
        self.doc.variables_updated.connect(self.dock_variables.update_variables)

    def _setup_actions(self):
        # Datei
        self.act_new = NewDocumentAction(self, self)
        self.act_open = OpenDocumentAction(self, self)
        self.act_save = SaveAction(self, self)
        self.act_save_as = SaveAsAction(self, self)
        self.act_export_pdf = ExportPdfAction(self, self)
        self.act_export_qmd = ExportQmdAction(self, self)
        self.act_settings = SettingsAction(self, self)
        self.act_quit = QuitAction(self, self)
        self.menu_recent_files = RecentFilesMenu(self, self)

        # Bearbeiten
        self.act_undo = UndoAction(self.doc, self)
        self.act_redo = RedoAction(self.doc, self)
        self.act_insert_above = InsertCellAboveAction(self.doc, self)
        self.act_insert_below = InsertCellBelowAction(self.doc, self)
        self.act_delete_cell = DeleteCellAction(self.doc, self)
        self.act_toggle_mode = ToggleModeAction(self.doc, self)

        # Zelle
        self.act_run_cell = RunCellAction(self.doc, self)
        self.act_run_all = RunAllAction(self.doc, self)

        # Ansicht
        self.act_toggle_structure = ToggleStructureDockAction(self.dock_structure, self)
        self.act_toggle_palette = TogglePaletteDockAction(self.dock_palette, self)

        # Hilfe
        self.act_manual = ManualAction(self, self)
        self.act_about = AboutAction(self, self)

    def _setup_menus(self):
        menubar = self.menuBar()

        menu_file = menubar.addMenu("&Datei")
        menu_file.addAction(self.act_new)
        menu_file.addAction(self.act_open)
        menu_file.addMenu(self.menu_recent_files)
        menu_file.addSeparator()
        menu_file.addAction(self.act_save)
        menu_file.addAction(self.act_save_as)

        menu_file.addSeparator()
        menu_export = menu_file.addMenu("E&xportieren")
        menu_export.addAction(self.act_export_pdf)
        menu_export.addAction(self.act_export_qmd)

        menu_file.addSeparator()
        menu_file.addAction(self.act_settings)
        menu_file.addSeparator()
        menu_file.addAction(self.act_quit)

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
        menu_view.addAction(self.act_toggle_variables)


        menu_help = menubar.addMenu("&Hilfe")
        menu_help.addAction(self.act_manual)
        menu_help.addSeparator()
        menu_help.addAction(self.act_about)

    def _setup_toolbars(self):
        toolbar = QToolBar("Hauptaktionen", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setStyleSheet("""
            QToolBar {
                background: #ffffff;
                border-bottom: 1px solid #e2e8f0;
                padding: 2px 4px;
                spacing: 4px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 9px;
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
        toolbar.addAction(self.act_export_pdf)
        toolbar.addAction(self.act_export_qmd)
        toolbar.addSeparator()
        toolbar.addAction(self.act_toggle_structure)
        toolbar.addAction(self.act_toggle_palette)

    def set_current_filepath(self, filepath: str | None):
        self.current_filepath = filepath
        if filepath:
            add_recent_file(filepath)
        self._update_window_title()

    def _update_window_title(self):
        dirty_flag = " *" if hasattr(self, 'doc') and self.doc.is_modified() else ""
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

    def _load_document_on_start(self):
        if self.current_filepath and os.path.exists(self.current_filepath):
            try:
                self.doc.load_from_markdown(self.current_filepath)
                add_recent_file(self.current_filepath)
            except Exception as err:
                self.statusbar.showMessage(f"Warnung: {err}", 3000)
                self.doc.insert_cell()
        else:
            self.doc.insert_cell()

        self.doc.undo_stack.clear()
        self.doc.undo_stack.setClean()
        self.doc.set_modified(False)
        self._update_window_title()
        self.dock_structure.update_outline(self.doc.cells)

    def closeEvent(self, event: QCloseEvent):
        # Model direkt abfragen statt über den Button-State
        if not self.doc.is_modified():
          event.accept()
          return

        # Dokument ist schmutzig (dirty) -> Prompt anzeigen
        filename = Path(self.current_filepath).name if self.current_filepath else "Unbenanntes Dokument"
        box = QMessageBox(self)
        box.setWindowTitle("Änderungen speichern?")
        box.setText(f"Möchtest du die Änderungen in »{filename}« vor dem Beenden speichern?")
        box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)

        choice = box.exec()

        if choice == QMessageBox.StandardButton.Save:
          # Speichern triggern (SaveAction-Logik nutzen)
          if not self.current_filepath:
            self.act_save_as.trigger()
          else:
            self.act_save.trigger()

          # Falls Speichern erfolgreich war (nicht abgebrochen wurde)
          if not self.doc.is_modified():
            event.accept()
          else:
            event.ignore()

        elif choice == QMessageBox.StandardButton.Discard:
          event.accept()

        else:  # Cancel
          event.ignore()


def main():
    # Icon & App Name for MacOS
    sys.argv[0] = "Rosida"
    QCoreApplication.setApplicationName("Rosida")
    QCoreApplication.setOrganizationName("Rosida")

    app = QApplication(["Rosida"] + sys.argv[1:])

    # Debugger
    if os.environ.get("DEBUG") == "1" or "--debug" in sys.argv:
        from debug import ClickDebugFilter
        debug_filter = ClickDebugFilter(app)
        app.installEventFilter(debug_filter)
        print("==> Click-Debugging aktiviert.")

    # Icon for Linux/Wayland
    icon_path = Path(__file__).parent / "logo.svg"
    if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

    # Load file
    initial_file = sys.argv[1] if len(sys.argv) > 1 and os.path.exists(sys.argv[1]) else None
    win = RosidaApp(initial_filepath=initial_file)
    win.show()

    maybe_show_manual_on_first_run(win)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
