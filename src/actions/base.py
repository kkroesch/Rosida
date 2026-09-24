from PySide6.QtGui import QAction

try:
  import qtawesome as qta
except ImportError:
  qta = None


class RosidaAction(QAction):
  """Gemeinsame Basisklasse für alle Rosida-Aktionen."""

  def __init__(self, text: str, parent=None):
    super().__init__(text, parent)

  def set_icon_name(self, name: str):
    """Setzt das Icon über qtawesome (z.B. "fa5s.save"). Bleibt bei fehlendem
    qtawesome oder unbekanntem Namen einfach ohne Icon, statt abzustürzen."""
    if qta is None:
      return
    try:
      self.setIcon(qta.icon(name))
    except Exception:
      pass
