from PySide6.QtGui import QKeySequence

from .base import RosidaAction


class RunCellAction(RosidaAction):

  def __init__(self, document_canvas, parent=None):
    super().__init__("▶ Zelle ausführen", parent)
    self.doc = document_canvas

    self.setShortcut(QKeySequence("Shift+Return"))
    self.setToolTip("Aktuelle Zelle ausführen (Shift+Enter)")
    self.set_icon_name("fa5s.play")

    self.triggered.connect(self.doc.run_active_cell)


class RunAllAction(RosidaAction):

  def __init__(self, document_canvas, parent=None):
    super().__init__("⏩ Alle ausführen", parent)
    self.doc = document_canvas

    self.setShortcut(QKeySequence("Ctrl+Shift+Return"))
    self.setToolTip("Alle Zellen ausführen (Ctrl+Shift+Enter)")
    self.set_icon_name("fa5s.fast-forward")

    self.triggered.connect(self.doc.run_all_cells)
