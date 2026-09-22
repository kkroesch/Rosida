from PySide6.QtGui import QAction


class RosidaAction(QAction):
  """Gemeinsame Basisklasse für alle Rosida-Aktionen."""

  def __init__(self, text: str, parent=None):
    super().__init__(text, parent)
