from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from .base import RosidaAction


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
    filepath, _ = QFileDialog.getOpenFileName(
      self.win,
      "Rosida Dokument öffnen",
      "",
      "Markdown-Dateien (*.md *.markdown);;Alle Dateien (*)",
    )
    if not filepath:
      return

    try:
      QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
      self.win.doc.load_from_markdown(filepath)
      self.win.set_current_filepath(filepath)
      self.win.statusbar.showMessage(f"Geöffnet: {filepath}", 3000)
    except Exception as err:
      QMessageBox.critical(self.win, "Fehler beim Öffnen", f"Datei konnte nicht geöffnet werden:\n{err}")
    finally:
      QApplication.restoreOverrideCursor()


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
