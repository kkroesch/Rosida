import os
import sys
from pathlib import Path

from PySide6.QtGui import QIcon, QCloseEvent, QFontDatabase
from PySide6.QtCore import Qt, QSize, QCoreApplication, QSettings

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
    InsertCellAction,
    MoveCellAboveAction,
    MoveCellBelowAction,
    RedoAction,
    ToggleModeAction,
    UndoAction,
)
from actions.file import (
    ExportHtmlAction,
    ExportIpynbAction,
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
from actions.help import (
    AboutAction,
    ManualAction,
    SettingsAction,
    maybe_show_manual_on_first_run,
)
from actions.view import (
    ToggleBibitemsDockAction,
    ToggleStructureDockAction,
    TogglePaletteDockAction,
    ToggleVariablesDockAction,
)
from docks.latex import LatexPaletteDock
from docks.structure_outline import StructureOutlineDock
from docks.inspector import VariableInspectorDock
from docks.bibitems import BibDock
from config.i18n import install_translators
from config.settings import FONTS_DIR
from exporters.bibtex import bibliography_files

try:
    from document import DocumentCanvas
except ImportError:
    from native_document import DocumentCanvas
from widgets.inplace import InPlaceCell

import matplotlib

matplotlib.use("Agg")  # <- Crasht sonst bei Verwendung von Workern
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
        self.doc.kernel.busy_changed.connect(self._on_kernel_busy_changed)
        self.doc.modified_changed.connect(lambda _: self._update_window_title())

        self.read_settings()
        self._load_document_on_start()

    def read_settings(self):
        settings = QSettings()

        # Geometrie des Hauptfensters wiederherstellen
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # Zustand und Position der Docks/Toolbars wiederherstellen
        window_state = settings.value("windowState")
        if window_state:
            self.restoreState(window_state)

    def _setup_statusbar(self):
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)
        self.statusbar.setStyleSheet(
            "QStatusBar { background: #f1f5f9; border-top: 1px solid #e2e8f0; font-size: 11px; }"
        )

        self.lbl_cell_info = QLabel(self.tr("Cell {0} of {1}").format(1, 1))
        self.lbl_cell_info.setStyleSheet(
            "color: #475569; padding: 0 10px; font-weight: 500;"
        )

        self.lbl_mode_badge = QLabel("⚡ Auto")
        self.lbl_mode_badge.setStyleSheet(
            "background-color: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px; font-weight: 500;"
        )

        self.lbl_kernel_status = QLabel(self.tr("● Kernel: ready"))
        self.lbl_kernel_status.setStyleSheet(
            "color: #16a34a; font-weight: bold; padding: 0 10px;"
        )

        self.statusbar.addPermanentWidget(self.lbl_cell_info)
        self.statusbar.addPermanentWidget(self.lbl_mode_badge)
        self.statusbar.addPermanentWidget(self.lbl_kernel_status)
        self.statusbar.showMessage(self.tr("Rosida is ready"), 3000)

    def _setup_docks(self):
        self.dock_structure = StructureOutlineDock(self)
        self.dock_structure.setObjectName("structure_dock")
        self.dock_structure.item_selected.connect(self.doc.scroll_to_cell)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_structure)

        self.dock_palette = LatexPaletteDock(self)
        self.dock_palette.setObjectName("palette_dock")
        self.dock_palette.insert_requested.connect(self.doc.insert_text_into_active)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_palette)

        self.dock_variables = VariableInspectorDock(self)
        self.dock_variables.setObjectName("variables_dock")
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_variables)

        self.dock_bibitems = BibDock(self)
        self.dock_bibitems.setObjectName("bibitems_dock")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_bibitems)
        self.dock_bibitems.citation_selected.connect(self.doc.insert_text_into_active)
        self.dock_bibitems.bib_file_chosen.connect(self._on_bib_file_chosen)
        self.doc.frontmatter_cell.frontmatter_updated.connect(
            lambda _meta: self._sync_bibliography()
        )

        self.act_toggle_variables = ToggleVariablesDockAction(self.dock_variables, self)
        self.doc.variables_updated.connect(self.dock_variables.update_variables)
        self.dock_variables.variable_double_clicked.connect(
            self.doc.insert_text_into_active
        )

    def _setup_actions(self):
        # Datei
        self.act_new = NewDocumentAction(self, self)
        self.act_open = OpenDocumentAction(self, self)
        self.act_save = SaveAction(self, self)
        self.act_save_as = SaveAsAction(self, self)
        self.act_export_pdf = ExportPdfAction(self, self)
        self.act_export_html = ExportHtmlAction(self, self)
        self.act_export_qmd = ExportQmdAction(self, self)
        self.act_export_ipynb = ExportIpynbAction(self, self)
        self.act_settings = SettingsAction(self, self)
        self.act_quit = QuitAction(self, self)
        self.menu_recent_files = RecentFilesMenu(self, self)

        # Bearbeiten
        self.act_undo = UndoAction(self.doc, self)
        self.act_redo = RedoAction(self.doc, self)
        self.act_insert_cell = InsertCellAction(self.doc, self)
        self.act_move_up = MoveCellAboveAction(self.doc, self)
        self.act_move_down = MoveCellBelowAction(self.doc, self)
        self.act_delete_cell = DeleteCellAction(self.doc, self)
        self.act_toggle_mode = ToggleModeAction(self.doc, self)

        # Zelle
        self.act_run_cell = RunCellAction(self.doc, self)
        self.act_run_all = RunAllAction(self.doc, self)

        # Ansicht
        self.act_toggle_structure = ToggleStructureDockAction(self.dock_structure, self)
        self.act_toggle_palette = TogglePaletteDockAction(self.dock_palette, self)
        self.act_toogle_bibitem = ToggleBibitemsDockAction(self.dock_bibitems, self)

        # Hilfe
        self.act_manual = ManualAction(self, self)
        self.act_about = AboutAction(self, self)

    def _setup_menus(self):
        menubar = self.menuBar()

        menu_file = menubar.addMenu(self.tr("&File"))
        menu_file.addAction(self.act_new)
        menu_file.addAction(self.act_open)
        menu_file.addMenu(self.menu_recent_files)
        menu_file.addSeparator()
        menu_file.addAction(self.act_save)
        menu_file.addAction(self.act_save_as)

        menu_file.addSeparator()
        menu_export = menu_file.addMenu(self.tr("E&xport"))
        menu_export.addAction(self.act_export_pdf)
        menu_export.addAction(self.act_export_html)
        menu_export.addAction(self.act_export_qmd)
        menu_export.addAction(self.act_export_ipynb)

        menu_file.addSeparator()
        menu_file.addAction(self.act_settings)
        menu_file.addSeparator()
        menu_file.addAction(self.act_quit)

        menu_edit = menubar.addMenu(self.tr("&Edit"))
        menu_edit.addAction(self.act_undo)
        menu_edit.addAction(self.act_redo)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_insert_cell)
        menu_edit.addAction(self.act_move_up)
        menu_edit.addAction(self.act_move_down)
        menu_edit.addAction(self.act_delete_cell)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_toggle_mode)

        menu_cell = menubar.addMenu(self.tr("&Cell"))
        menu_cell.addAction(self.act_run_cell)
        menu_cell.addAction(self.act_run_all)

        menu_view = menubar.addMenu(self.tr("&View"))
        menu_view.addAction(self.act_toggle_structure)
        menu_view.addAction(self.act_toggle_palette)
        menu_view.addAction(self.act_toggle_variables)
        menu_view.addAction(self.act_toogle_bibitem)

        menu_help = menubar.addMenu(self.tr("&Help"))
        menu_help.addAction(self.act_manual)
        menu_help.addSeparator()
        menu_help.addAction(self.act_about)

    def _setup_toolbars(self):
        toolbar = QToolBar(self.tr("Main actions"), self)
        toolbar.setObjectName("toolbar")
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
        toolbar.addAction(self.act_insert_cell)
        toolbar.addAction(self.act_move_up)
        toolbar.addAction(self.act_move_down)
        toolbar.addAction(self.act_delete_cell)
        toolbar.addSeparator()
        toolbar.addAction(self.act_run_cell)
        toolbar.addAction(self.act_run_all)
        toolbar.addAction(self.act_toggle_mode)
        toolbar.addSeparator()
        toolbar.addAction(self.act_export_pdf)
        toolbar.addAction(self.act_export_html)
        toolbar.addAction(self.act_export_qmd)
        toolbar.addSeparator()
        toolbar.addAction(self.act_toggle_structure)
        toolbar.addAction(self.act_toggle_palette)

    def set_current_filepath(self, filepath: str | None):
        self.current_filepath = filepath
        if filepath:
            add_recent_file(filepath)
        self._update_window_title()
        self._sync_bibliography()

    def _document_dir(self) -> Path | None:
        return Path(self.current_filepath).resolve().parent if self.current_filepath else None

    def _sync_bibliography(self):
        """Loads the .bib file(s) named in the frontmatter into the references dock."""
        base = self._document_dir() or Path.cwd()
        files = bibliography_files(self.doc.frontmatter_cell.metadata(), base)
        self.dock_bibitems.show_bibliography(files, start_dir=str(base))

    def _on_bib_file_chosen(self, filepath: str):
        """Stores the chosen .bib file as bibliography, relative to the document."""
        path = Path(filepath).resolve()
        base = self._document_dir()
        if base:
            value = Path(os.path.relpath(path, base)).as_posix()
        else:
            # Noch nicht gespeichert: kein Bezugsordner, daher absolut
            value = path.as_posix()
        self.doc.frontmatter_cell.set_property("bibliography", value)
        self.doc.set_modified(True)

    def _update_window_title(self):
        dirty_flag = " *" if hasattr(self, "doc") and self.doc.is_modified() else ""
        if self.current_filepath:
            name = os.path.basename(self.current_filepath)
        else:
            name = self.tr("Untitled document")
        self.setWindowTitle(f"Rosida – {name}{dirty_flag}")

    def _on_active_cell_changed(self, cell: InPlaceCell, index: int, total: int):
        self.lbl_cell_info.setText(
            self.tr("Cell {0} of {1}").format(index + 1, max(1, total))
        )
        mode = cell.get_mode()
        if mode == "auto":
            self.lbl_mode_badge.setText("⚡ Auto")
            self.lbl_mode_badge.setStyleSheet(
                "background-color: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px; font-weight: 500;"
            )
        elif mode == "markdown":
            self.lbl_mode_badge.setText(self.tr("📝 Text (fixed)"))
            self.lbl_mode_badge.setStyleSheet(
                "background-color: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
            )
        else:
            self.lbl_mode_badge.setText(self.tr("⚡ Python (fixed)"))
            self.lbl_mode_badge.setStyleSheet(
                "background-color: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
            )
        self._update_window_title()

    def _on_cell_executed(self, cell):
        if self.doc.kernel.is_busy():
            return
        self.lbl_kernel_status.setText(self.tr("● Kernel: cell computed"))
        self.lbl_kernel_status.setStyleSheet(
            "color: #0284c7; font-weight: bold; padding: 0 10px;"
        )
        self.statusbar.showMessage(self.tr("Execution finished"), 2500)

    def _on_kernel_busy_changed(self, busy: bool):
        if busy:
            self.lbl_kernel_status.setText(self.tr("● Kernel: computing …"))
            self.lbl_kernel_status.setStyleSheet(
                "color: #d97706; font-weight: bold; padding: 0 10px;"
            )

    def _load_document_on_start(self):
        if self.current_filepath and os.path.exists(self.current_filepath):
            try:
                self.doc.load_from_markdown(self.current_filepath)
                add_recent_file(self.current_filepath)
            except Exception as err:
                self.statusbar.showMessage(self.tr("Warning: {0}").format(err), 3000)
                self.doc.insert_cell()
        else:
            self.doc.insert_cell()

        self.doc.undo_stack.clear()
        self.doc.undo_stack.setClean()
        self.doc.set_modified(False)
        self._update_window_title()
        self.dock_structure.update_outline(self.doc.cells)

    def closeEvent(self, event: QCloseEvent):
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

        # Model direkt abfragen statt über den Button-State
        if not self.doc.is_modified():
            event.accept()
            return

        # Dokument ist schmutzig (dirty) -> Prompt anzeigen
        filename = (
            Path(self.current_filepath).name
            if self.current_filepath
            else self.tr("Untitled document")
        )
        box = QMessageBox(self)
        box.setWindowTitle(self.tr("Save changes?"))
        box.setText(
            self.tr(
                "Do you want to save the changes to “{0}” before quitting?"
            ).format(filename)
        )
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


def load_application_fonts():
    if not FONTS_DIR.is_dir():
        return

    for font_file in FONTS_DIR.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(font_file))


def main():
    # Icon & App Name for MacOS
    sys.argv[0] = "Rosida"

    app = QApplication(["Rosida"] + sys.argv[1:])
    load_application_fonts()
    app.setOrganizationDomain("kroesch.ch")
    app.setApplicationName("Rosida")
    # Nach setApplicationName (QSettings) und vor dem ersten Fenster
    install_translators(app)

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
    initial_file = (
        sys.argv[1] if len(sys.argv) > 1 and os.path.exists(sys.argv[1]) else None
    )
    win = RosidaApp(initial_filepath=initial_file)
    win.show()

    maybe_show_manual_on_first_run(win)

    exit_code = app.exec()
    if win.doc.kernel.is_computing():
        # Python-Code in einem Thread lässt sich nicht abbrechen (auch
        # QThread.terminate() hängt am GIL), und ein noch laufender QThread
        # bringt Qt beim Aufräumen zum Absturz. Deshalb hart beenden.
        QSettings().sync()
        os._exit(exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
