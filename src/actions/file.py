import os

from pathlib import Path
from PySide6.QtCore import QCoreApplication, Qt, QSettings
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox

from .base import RosidaAction

MAX_RECENT_FILES = 8
_RECENT_FILES_SETTINGS_KEY = "recent_files"


def add_recent_file(filepath: str):
    """Trägt filepath vorne in die persistierte Liste der zuletzt geöffneten Dateien ein."""
    settings = QSettings()
    files = [f for f in get_recent_files() if f != filepath]
    files.insert(0, filepath)
    settings.setValue(_RECENT_FILES_SETTINGS_KEY, files[:MAX_RECENT_FILES])


def get_recent_files() -> list[str]:
    """Liest die persistierte Liste zuletzt geöffneter Dateien, ohne inzwischen gelöschte Pfade."""
    raw = QSettings().value(_RECENT_FILES_SETTINGS_KEY)
    if isinstance(raw, str):
        files = [raw] if raw else []
    else:
        files = list(raw or [])
    return [f for f in files if f and os.path.exists(f)]


class NewDocumentAction(RosidaAction):
    def __init__(self, main_window, parent=None):
        super().__init__(QCoreApplication.translate("NewDocumentAction", "&New document"), parent)
        self.win = main_window

        self.setShortcut(QKeySequence.StandardKey.New)
        self.setToolTip(self.tr("Create a new, empty document (Cmd+N / Ctrl+N)"))
        self.set_icon_name("fa5s.file")

        self.triggered.connect(self._execute)

    def _execute(self):
        doc = self.win.doc
        while doc.cells:
            cell = doc.cells.pop()
            doc.layout.removeWidget(cell)
            cell.deleteLater()

        # Eigenschaften (Titel, bibliography, ...) nicht ins neue Dokument erben
        doc.frontmatter_cell.editor.setPlainText("")
        doc.frontmatter_cell.commit_and_collapse()
        self.win.set_current_filepath(None)
        doc.undo_stack.clear()
        doc.undo_stack.setClean()
        doc.insert_cell()
        doc.set_modified(False)
        self.win.statusbar.showMessage(self.tr("New document created"), 2000)


class OpenDocumentAction(RosidaAction):
    def __init__(self, main_window, parent=None):
        super().__init__(QCoreApplication.translate("OpenDocumentAction", "&Open..."), parent)
        self.win = main_window

        self.setShortcut(QKeySequence.StandardKey.Open)
        self.setToolTip(self.tr("Open a document (Cmd+O / Ctrl+O)"))
        self.set_icon_name("fa5s.folder-open")

        self.triggered.connect(self._execute)

    def _execute(self):
        filter_str = ";;".join(
            [
                self.tr("Supported documents (*.md *.markdown *.qmd *.ipynb)"),
                self.tr("Markdown & Quarto (*.md *.markdown *.qmd)"),
                self.tr("Jupyter notebooks (*.ipynb)"),
                self.tr("All files (*)"),
            ]
        )

        filepath, _ = QFileDialog.getOpenFileName(
            self.win,
            self.tr("Open Rosida document"),
            "",
            filter_str,
        )
        if not filepath:
            return

        path = Path(filepath)

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            if path.suffix.lower() == ".ipynb":
                # 1. Jupyter Notebook importieren
                self.win.doc.load_from_ipynb(filepath)

                # 2. Zielpfad auf .md umbiegen, damit das Original nicht mit rohem Markdown überschrieben wird
                target_md = path.with_suffix(".md")
                self.win.set_current_filepath(str(target_md))
                self.win.statusbar.showMessage(
                    self.tr("Imported: {0} → will be saved as {1}").format(
                        path.name, target_md.name
                    ),
                    4000,
                )
            else:
                # Standard: Markdown / Quarto laden[cite: 1]
                self.win.doc.load_from_markdown(filepath)
                self.win.set_current_filepath(filepath)
                self.win.statusbar.showMessage(self.tr("Opened: {0}").format(path.name), 3000)

        except Exception as err:
            QMessageBox.critical(
                self.win,
                self.tr("Error opening file"),
                self.tr("The file could not be opened:\n{0}").format(err),
            )
        finally:
            QApplication.restoreOverrideCursor()


class RecentFilesMenu(QMenu):
    """Datei-Untermenü "Zuletzt geöffnet", wird bei jedem Öffnen neu aus QSettings gebaut."""

    def __init__(self, main_window, parent=None):
        super().__init__(QCoreApplication.translate("RecentFilesMenu", "Open &recent"), parent)
        self.win = main_window
        self.aboutToShow.connect(self._rebuild)

    def _rebuild(self):
        self.clear()
        files = get_recent_files()
        if not files:
            empty_action = self.addAction(self.tr("(none)"))
            empty_action.setEnabled(False)
            return

        for filepath in files:
            action = self.addAction(os.path.basename(filepath))
            action.setToolTip(filepath)
            action.triggered.connect(lambda checked=False, p=filepath: self._open(p))

        self.addSeparator()
        self.addAction(self.tr("Clear list")).triggered.connect(self._clear)

    def _open(self, filepath: str):
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.win.doc.load_from_markdown(filepath)
            self.win.set_current_filepath(filepath)
            self.win.statusbar.showMessage(self.tr("Opened: {0}").format(filepath), 3000)
        except Exception as err:
            QMessageBox.critical(
                self.win,
                self.tr("Error opening file"),
                self.tr("The file could not be opened:\n{0}").format(err),
            )
        finally:
            QApplication.restoreOverrideCursor()

    def _clear(self):
        QSettings().remove(_RECENT_FILES_SETTINGS_KEY)


class SaveAction(RosidaAction):
    def __init__(self, main_window, parent=None):
        super().__init__(QCoreApplication.translate("SaveAction", "&Save"), parent)
        self.win = main_window

        self.setShortcut(QKeySequence.StandardKey.Save)
        self.setToolTip(self.tr("Save the document (Cmd+S / Ctrl+S)"))
        self.set_icon_name("fa5s.save")

        self.triggered.connect(self._execute)

        # Reaktiv an den Änderungsstatus des Dokuments koppeln
        self.win.doc.modified_changed.connect(self._update_state)
        self._update_state(self.win.doc.is_modified())

    def _update_state(self, is_modified: bool):
        self.setEnabled(is_modified)

    def _execute(self):
        if not self.win.current_filepath:
            self.win.act_save_as.trigger()
            return
        try:
            self.win.doc.save_to_markdown(self.win.current_filepath)
            self.win.statusbar.showMessage(
                self.tr("Saved: {0}").format(self.win.current_filepath), 3000
            )
        except Exception as err:
            QMessageBox.critical(
                self.win,
                self.tr("Error saving file"),
                self.tr("The file could not be saved:\n{0}").format(err),
            )


class SaveAsAction(RosidaAction):
    def __init__(self, main_window, parent=None):
        super().__init__(QCoreApplication.translate("SaveAsAction", "Save &as..."), parent)
        self.win = main_window

        self.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.setToolTip(
            self.tr("Save the document under a new name (Cmd+Shift+S / Ctrl+Shift+S)")
        )
        self.set_icon_name("fa5s.file-export")

        self.triggered.connect(self._execute)

    def _execute(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self.win,
            self.tr("Save document as"),
            self.tr("calculation.md"),
            self.tr("Markdown document (*.md)") + ";;" + self.tr("All files (*)"),
        )
        if not filepath:
            return
        try:
            self.win.doc.save_to_markdown(filepath)
            self.win.set_current_filepath(filepath)
            self.win.statusbar.showMessage(self.tr("Saved: {0}").format(filepath), 3000)
        except Exception as err:
            QMessageBox.critical(
                self.win,
                self.tr("Error saving file"),
                self.tr("The file could not be saved:\n{0}").format(err),
            )


class ExportPdfAction(RosidaAction):
    def __init__(self, main_window, parent=None):
        super().__init__(QCoreApplication.translate("ExportPdfAction", "Export &PDF..."), parent)
        self.win = main_window

        self.setShortcut(QKeySequence("Ctrl+Shift+P"))
        self.setToolTip(self.tr("Export the document as a PDF file (Ctrl+Shift+P)"))
        self.set_icon_name("fa5s.file-pdf")

        self.triggered.connect(self._execute)

    def _execute(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self.win,
            self.tr("Export document as PDF"),
            self.tr("rosida_document.pdf"),
            self.tr("PDF document (*.pdf)"),
        )
        if not filepath:
            return
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.win.doc.export_pdf(filepath)
            self.win.statusbar.showMessage(
                self.tr("PDF export successful: {0}").format(filepath), 4000
            )
        except Exception as err:
            QMessageBox.critical(
                self.win,
                self.tr("Export error"),
                self.tr("PDF export failed:\n{0}").format(err),
            )
        finally:
            QApplication.restoreOverrideCursor()


class ExportHtmlAction(RosidaAction):
    def __init__(self, main_window, parent=None):
        super().__init__(QCoreApplication.translate("ExportHtmlAction", "Export &HTML..."), parent)
        self.win = main_window

        self.setShortcut(QKeySequence("Ctrl+Shift+H"))
        self.setToolTip(
            self.tr("Export the document as an HTML page, formulas via KaTeX (Ctrl+Shift+H)")
        )
        self.set_icon_name("fa5s.file-code")

        self.triggered.connect(self._execute)

    def _execute(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self.win,
            self.tr("Export document as HTML"),
            self.tr("rosida_document.html"),
            self.tr("HTML page (*.html)"),
        )
        if not filepath:
            return
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.win.doc.export_html(filepath)
            self.win.statusbar.showMessage(
                self.tr("HTML export successful: {0}").format(filepath), 4000
            )
        except Exception as err:
            QMessageBox.critical(
                self.win,
                self.tr("Export error"),
                self.tr("HTML export failed:\n{0}").format(err),
            )
        finally:
            QApplication.restoreOverrideCursor()


class ExportQmdAction(RosidaAction):
    def __init__(self, main_window, parent=None):
        super().__init__(QCoreApplication.translate("ExportQmdAction", "Export &Quarto..."), parent)
        self.win = main_window

        self.setShortcut(QKeySequence("Ctrl+Shift+Q"))
        self.setToolTip(
            self.tr("Export the document as a Quarto file (.qmd) (Ctrl+Shift+Q)")
        )
        self.set_icon_name("fa5s.file-alt")

        self.triggered.connect(self._execute)

    def _execute(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self.win,
            self.tr("Export document as Quarto"),
            self.tr("rosida_document.qmd"),
            self.tr("Quarto document (*.qmd)"),
        )
        if not filepath:
            return
        try:
            self.win.doc.export_qmd(filepath)
            self.win.statusbar.showMessage(
                self.tr("Quarto export successful: {0}").format(filepath), 4000
            )
        except Exception as err:
            QMessageBox.critical(
                self.win,
                self.tr("Export error"),
                self.tr("Quarto export failed:\n{0}").format(err),
            )


class QuitAction(RosidaAction):
    def __init__(self, main_window, parent=None):
        super().__init__(QCoreApplication.translate("QuitAction", "&Quit"), parent)
        self.win = main_window

        self.setShortcut(QKeySequence.StandardKey.Quit)
        self.setToolTip(self.tr("Quit Rosida"))
        self.set_icon_name("fa5s.sign-out-alt")

        self.triggered.connect(self.win.close)
