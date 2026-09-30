from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QKeySequence

from .base import RosidaAction


class RunCellAction(RosidaAction):
    def __init__(self, document_canvas, parent=None):
        super().__init__(QCoreApplication.translate("RunCellAction", "Run cell"), parent)
        self.doc = document_canvas

        self.setShortcut(QKeySequence("Shift+Return"))
        self.setToolTip(self.tr("Run the current cell (Shift+Enter)"))
        self.set_icon_name("fa5s.play")

        self.triggered.connect(self.doc.run_active_cell)


class RunAllAction(RosidaAction):
    def __init__(self, document_canvas, parent=None):
        super().__init__(QCoreApplication.translate("RunAllAction", "Run all"), parent)
        self.doc = document_canvas

        self.setShortcut(QKeySequence("Ctrl+Shift+Return"))
        self.setToolTip(self.tr("Run all cells (Ctrl+Shift+Enter)"))
        self.set_icon_name("fa5s.fast-forward")

        self.triggered.connect(self.doc.run_all_cells)
