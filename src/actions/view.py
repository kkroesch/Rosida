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
    super().__init__(dock_widget, "Dokumentstruktur (Sidebar)", parent)

    self.setShortcut(QKeySequence("F3"))
    self.setToolTip("Dokumentstruktur ein-/ausblenden (F3)")
    self.set_icon_name("fa5s.sitemap")


class TogglePaletteDockAction(ToggleDockAction):

  def __init__(self, dock_widget, parent=None):
    super().__init__(dock_widget, "LaTeX-Palette (Sidebar)", parent)

    self.setShortcut(QKeySequence("F4"))
    self.setToolTip("LaTeX-Palette ein-/ausblenden (F4)")
    self.set_icon_name("fa5s.square-root-alt")
