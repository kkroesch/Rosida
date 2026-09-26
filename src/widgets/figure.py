from pathlib import Path
import re
import urllib.request
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class FigureWidget(QFrame):

  def __init__(
      self,
      raw_text: str,
      base_dir: Path,
      fig_number: int | None = None,
      parent=None,
  ):
    super().__init__(parent)
    self.setFrameShape(QFrame.Shape.NoFrame)
    self.setStyleSheet("background: transparent;")

    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 10, 0, 12)
    layout.setSpacing(8)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # 1. Quarto-Syntax robust parsen (auch mehrzeilig)
    pattern = r"!\[(.*?)\]\((.*?)\)(?:\s*\{#(.*?)\})?"
    m = re.search(pattern, raw_text.strip(), flags=re.DOTALL)

    raw_caption = m.group(1).strip() if m else ""
    src = m.group(2).strip() if m else raw_text.strip()
    label_id = m.group(3).strip() if (m and m.group(3)) else ""

    # 2. Bild zentriert laden
    pixmap = self._load_pixmap(src, base_dir)
    self.img_lbl = QLabel()
    self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    if pixmap and not pixmap.isNull():
      scaled = pixmap.scaled(
          720,
          900,
          Qt.AspectRatioMode.KeepAspectRatio,
          Qt.TransformationMode.SmoothTransformation,
      )
      self.img_lbl.setPixmap(scaled)
    else:
      self.img_lbl.setText(f"⚠️ Bild nicht gefunden: {src}")
      self.img_lbl.setStyleSheet(
          "color: #dc2626; font-family: monospace; font-size: 12px;"
      )
    layout.addWidget(self.img_lbl)

    # 3. Caption ermitteln (Fallback: Dateiname ohne Endung)
    if raw_caption:
      caption_text = raw_caption
    elif src and not src.startswith(("http://", "https://")):
      caption_text = (
          Path(src).stem.replace("_", " ").replace("-", " ").capitalize()
      )
    else:
      caption_text = ""

    # 4. Bildunterschrift-Leiste (Abbildung X: [Text] + [#fig-...])
    if caption_text or label_id:
      cap_container = QFrame()
      cap_layout = QHBoxLayout(cap_container)
      cap_layout.setContentsMargins(0, 4, 0, 0)
      cap_layout.setSpacing(8)
      cap_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

      prefix = (
          f"Abbildung {fig_number}:" if fig_number is not None else "Abbildung:"
      )

      # Textzeile mit hervorgehobenem Präfix
      cap_lbl = QLabel(f"<b>{prefix}</b> {caption_text}")
      cap_lbl.setTextFormat(Qt.TextFormat.RichText)
      cap_lbl.setStyleSheet(
          "color: #334155; font-size: 12px; line-height: 1.4;"
      )
      cap_layout.addWidget(cap_lbl)

      # Dezenter QMD-Referenz-Badge (#fig-name) am rechten Rand
      if label_id:
        badge = QLabel(f"#{label_id}")
        badge.setToolTip(f"Quarto-Referenzanker: @{label_id}")
        badge.setStyleSheet("""
                    background-color: #e2e8f0;
                    color: #64748b;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 1px 6px;
                    border-radius: 4px;
                """)
        cap_layout.addWidget(badge)

      layout.addWidget(cap_container)

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
