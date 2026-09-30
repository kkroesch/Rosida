from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QKeySequence

from .base import RosidaAction


class ToggleDockAction(RosidaAction):
    """Basisklasse für Aktionen, die die Sichtbarkeit eines Docks umschalten."""

    def __init__(self, dock_widget, text: str, parent=None):
        super().__init__(text, parent)
        self.dock = dock_widget

        self.setCheckable(True)
        self.setChecked(self.dock.isVisible())

        self.toggled.connect(self.dock.setVisible)
        self.dock.visibilityChanged.connect(self.setChecked)


class ToggleStructureDockAction(ToggleDockAction):
    def __init__(self, dock_widget, parent=None):
        super().__init__(
            dock_widget, QCoreApplication.translate("ToggleStructureDockAction", "Document outline"), parent
        )

        self.setShortcut(QKeySequence("F3"))
        self.setToolTip(self.tr("Show/hide the document outline (F3)"))
        self.set_icon_name("fa5s.sitemap")


class TogglePaletteDockAction(ToggleDockAction):
    def __init__(self, dock_widget, parent=None):
        super().__init__(
            dock_widget, QCoreApplication.translate("TogglePaletteDockAction", "LaTeX palette"), parent
        )

        self.setShortcut(QKeySequence("F4"))
        self.setToolTip(self.tr("Show/hide the LaTeX palette (F4)"))
        self.set_icon_name("fa5s.square-root-alt")


class ToggleBibitemsDockAction(ToggleDockAction):
    def __init__(self, dock_widget, parent=None):
        super().__init__(
            dock_widget, QCoreApplication.translate("ToggleBibitemsDockAction", "Bibliography"), parent
        )

        self.setShortcut(QKeySequence("F4"))
        self.setToolTip(self.tr("Show/hide the bibliography (F4)"))
        self.set_icon_name("fa5s.book")


class ToggleVariablesDockAction(ToggleDockAction):
    def __init__(self, dock_widget, parent=None):
        super().__init__(
            dock_widget, QCoreApplication.translate("ToggleVariablesDockAction", "Variables (sidebar)"), parent
        )

        self.setShortcut(QKeySequence("F3"))
        self.setToolTip(self.tr("Show/hide the variable inspector (F3)"))
        self.set_icon_name("fa5s.table")
