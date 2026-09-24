from PySide6.QtGui import QIcon, QKeySequence
from .base import RosidaAction


class SaveAction(RosidaAction):

  def __init__(self, document_canvas, parent=None):
    super().__init__("&Speichern", parent)
    self.doc = document_canvas

    self.setShortcut(QKeySequence.StandardKey.Save)
    self.setToolTip("Dokument speichern (Cmd+S / Ctrl+S)")
    self.setIcon(QIcon.fromTheme("document-save"))

    self.triggered.connect(self.doc.save)

    # Reaktiv an UndoStack koppeln
    self.doc.undo_stack.cleanChanged.connect(self._update_state)
    self._update_state(self.doc.undo_stack.isClean())

  def _update_state(self, is_clean: bool):
    self.setEnabled(not is_clean)
