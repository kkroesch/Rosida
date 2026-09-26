from pathlib import Path
import re
import urllib.request
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class FigureWidget(QFrame):

  def __init__(self, raw_text: str, base_dir: Path, parent=None):
    super().__init__(parent)
    self.setFrameShape(QFrame.Shape.NoFrame)
    self.setStyleSheet("background: transparent;")

    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 8, 0, 8)
    layout.setSpacing(6)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # Syntax parsen: ![Caption](Pfad/URL){#fig-label}
    pattern = r"!\[(.*?)\]\((.*?)\)(?:\{#(.*?)\})?"
    m = re.search(pattern, raw_text.strip())

    caption = m.group(1) if m else ""
    src = m.group(2) if m else raw_text.strip()
    label_id = m.group(3) if (m and m.group(3)) else ""

    # 1. Bild laden (Web oder Lokal)
    pixmap = self._load_pixmap(src, base_dir)

    self.img_lbl = QLabel()
    self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if pixmap and not pixmap.isNull():
      # Maximalbreite für lesbare Dokumentansicht
      scaled = pixmap.scaled(
          720,
          900,
          Qt.AspectRatioMode.KeepAspectRatio,
          Qt.TransformationMode.SmoothTransformation,
      )
      self.img_lbl.setPixmap(scaled)
    else:
      self.img_lbl.setText(f"⚠️ Bild konnte nicht geladen werden: {src}")
      self.img_lbl.setStyleSheet(
          "color: #dc2626; font-family: monospace; font-size: 12px;"
      )
    layout.addWidget(self.img_lbl)

    # 2. Beschriftungs-Leiste (Caption + #fig-ID Badge)
    if caption or label_id:
      cap_row = QHBoxLayout()
      cap_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
      cap_row.setSpacing(8)

      if label_id:
        badge = QLabel(f"#{label_id}")
        badge.setStyleSheet("""
                    background-color: #e2e8f0; color: #475569;
                    font-family: 'JetBrains Mono', monospace; font-size: 11px;
                    font-weight: bold; padding: 2px 6px; border-radius: 4px;
                """)
        cap_row.addWidget(badge)

      if caption:
        cap_lbl = QLabel(caption)
        cap_lbl.setStyleSheet(
            "color: #475569; font-size: 12px; font-style: italic;"
        )
        cap_row.addWidget(cap_lbl)

      layout.addLayout(cap_row)

  def _load_pixmap(self, src: str, base_dir: Path) -> QPixmap | None:
    try:
      if src.startswith(("http://", "https://")):
        req = urllib.request.Request(src, headers={"User-Agent": "Rosida/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
          img = QImage()
          img.loadFromData(resp.read())
          return QPixmap.fromImage(img)
      else:
        path = Path(src)
        if not path.is_absolute():
          path = base_dir / path
        if path.is_file():
          return QPixmap(str(path))
    except Exception:
      return None
    return None
