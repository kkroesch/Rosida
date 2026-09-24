import os

from pathlib import Path
from PySide6.QtCore import Qt, QSettings
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
    super().__init__("&Neues Dokument", parent)
    self.win = main_window

    self.setShortcut(QKeySequence.StandardKey.New)
    self.setToolTip("Neues, leeres Dokument erstellen (Cmd+N / Ctrl+N)")
    self.set_icon_name("fa5s.file")

    self.triggered.connect(self._execute)

  def _execute(self):
    doc = self.win.doc
    while doc.cells:
      cell = doc.cells.pop()
      doc.layout.removeWidget(cell)
      cell.deleteLater()

    self.win.set_current_filepath(None)
    doc.undo_stack.clear()
    doc.undo_stack.setClean()
    doc.insert_cell()
    doc.set_modified(False)
    self.win.statusbar.showMessage("Neues Dokument erstellt", 2000)


class OpenDocumentAction(RosidaAction):

    def __init__(self, main_window, parent=None):
        super().__init__("&Öffnen...", parent)
        self.win = main_window

        self.setShortcut(QKeySequence.StandardKey.Open)
        self.setToolTip("Dokument öffnen (Cmd+O / Ctrl+O)")
        self.set_icon_name("fa5s.folder-open")

        self.triggered.connect(self._execute)

    def _execute(self):
        filter_str = (
            "Unterstützte Dokumente (*.md *.markdown *.qmd *.ipynb);;"
            "Markdown & Quarto (*.md *.markdown *.qmd);;"
            "Jupyter Notebooks (*.ipynb);;"
            "Alle Dateien (*)"
        )

        filepath, _ = QFileDialog.getOpenFileName(
            self.win,
            "Rosida Dokument öffnen",
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
                    f"Importiert: {path.name} → Speichern als {target_md.name}", 4000
                )
            else:
                # Standard: Markdown / Quarto laden[cite: 1]
                self.win.doc.load_from_markdown(filepath)
                self.win.set_current_filepath(filepath)
                self.win.statusbar.showMessage(f"Geöffnet: {path.name}", 3000)

        except Exception as err:
            QMessageBox.critical(
                self.win,
                "Fehler beim Öffnen",
                f"Datei konnte nicht geöffnet werden:\n{err}",
            )
        finally:
            QApplication.restoreOverrideCursor()


class RecentFilesMenu(QMenu):
  """Datei-Untermenü "Zuletzt geöffnet", wird bei jedem Öffnen neu aus QSettings gebaut."""

  def __init__(self, main_window, parent=None):
    super().__init__("Zuletzt &geöffnet", parent)
    self.win = main_window
    self.aboutToShow.connect(self._rebuild)

  def _rebuild(self):
    self.clear()
    files = get_recent_files()
    if not files:
      empty_action = self.addAction("(keine)")
      empty_action.setEnabled(False)
      return

    for filepath in files:
      action = self.addAction(os.path.basename(filepath))
      action.setToolTip(filepath)
      action.triggered.connect(lambda checked=False, p=filepath: self._open(p))

    self.addSeparator()
    self.addAction("Liste leeren").triggered.connect(self._clear)

  def _open(self, filepath: str):
    try:
      QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
      self.win.doc.load_from_markdown(filepath)
      self.win.set_current_filepath(filepath)
      self.win.statusbar.showMessage(f"Geöffnet: {filepath}", 3000)
    except Exception as err:
      QMessageBox.critical(self.win, "Fehler beim Öffnen", f"Datei konnte nicht geöffnet werden:\n{err}")
    finally:
      QApplication.restoreOverrideCursor()

  def _clear(self):
    QSettings().remove(_RECENT_FILES_SETTINGS_KEY)


class SaveAction(RosidaAction):

  def __init__(self, main_window, parent=None):
    super().__init__("&Speichern", parent)
    self.win = main_window

    self.setShortcut(QKeySequence.StandardKey.Save)
    self.setToolTip("Dokument speichern (Cmd+S / Ctrl+S)")
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
      self.win.statusbar.showMessage(f"Gespeichert: {self.win.current_filepath}", 3000)
    except Exception as err:
      QMessageBox.critical(self.win, "Fehler beim Speichern", f"Datei konnte nicht gespeichert werden:\n{err}")


class SaveAsAction(RosidaAction):

  def __init__(self, main_window, parent=None):
    super().__init__("Speichern &unter...", parent)
    self.win = main_window

    self.setShortcut(QKeySequence.StandardKey.SaveAs)
    self.setToolTip("Dokument unter neuem Namen speichern (Cmd+Shift+S / Ctrl+Shift+S)")
    self.set_icon_name("fa5s.file-export")

    self.triggered.connect(self._execute)

  def _execute(self):
    filepath, _ = QFileDialog.getSaveFileName(
      self.win,
      "Dokument speichern unter",
      "berechnung.md",
      "Markdown-Dokument (*.md);;Alle Dateien (*)",
    )
    if not filepath:
      return
    try:
      self.win.doc.save_to_markdown(filepath)
      self.win.set_current_filepath(filepath)
      self.win.statusbar.showMessage(f"Gespeichert: {filepath}", 3000)
    except Exception as err:
      QMessageBox.critical(self.win, "Fehler beim Speichern", f"Datei konnte nicht gespeichert werden:\n{err}")


class ExportPdfAction(RosidaAction):

  def __init__(self, main_window, parent=None):
    super().__init__("&PDF exportieren...", parent)
    self.win = main_window

    self.setShortcut(QKeySequence("Ctrl+Shift+P"))
    self.setToolTip("Dokument als PDF-Datei exportieren (Ctrl+Shift+P)")
    self.set_icon_name("fa5s.file-pdf")

    self.triggered.connect(self._execute)

  def _execute(self):
    filepath, _ = QFileDialog.getSaveFileName(
      self.win,
      "Dokument als PDF exportieren",
      "rosida_dokument.pdf",
      "PDF-Dokument (*.pdf)",
    )
    if not filepath:
      return
    try:
      QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
      self.win.doc.export_pdf(filepath)
      self.win.statusbar.showMessage(f"PDF-Export erfolgreich: {filepath}", 4000)
    except Exception as err:
      QMessageBox.critical(self.win, "Exportfehler", f"Fehler beim PDF-Export:\n{err}")
    finally:
      QApplication.restoreOverrideCursor()


class ExportQmdAction(RosidaAction):

  def __init__(self, main_window, parent=None):
    super().__init__("&Quarto exportieren...", parent)
    self.win = main_window

    self.setShortcut(QKeySequence("Ctrl+Shift+Q"))
    self.setToolTip("Dokument als Quarto-Datei (.qmd) exportieren (Ctrl+Shift+Q)")
    self.set_icon_name("fa5s.file-alt")

    self.triggered.connect(self._execute)

  def _execute(self):
    filepath, _ = QFileDialog.getSaveFileName(
      self.win,
      "Dokument als Quarto exportieren",
      "rosida_dokument.qmd",
      "Quarto-Dokument (*.qmd)",
    )
    if not filepath:
      return
    try:
      self.win.doc.export_qmd(filepath)
      self.win.statusbar.showMessage(f"Quarto-Export erfolgreich: {filepath}", 4000)
    except Exception as err:
      QMessageBox.critical(self.win, "Exportfehler", f"Fehler beim Quarto-Export:\n{err}")


class QuitAction(RosidaAction):

  def __init__(self, main_window, parent=None):
    super().__init__("&Beenden", parent)
    self.win = main_window

    self.setShortcut(QKeySequence.StandardKey.Quit)
    self.setToolTip("Rosida beenden")
    self.set_icon_name("fa5s.sign-out-alt")

    self.triggered.connect(self.win.close)
