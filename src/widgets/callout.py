# widgets/callout.py
from pathlib import Path
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout
import qtawesome as qta
from widgets.math_text import MathTextBrowser, render_markdown_with_math

THEMES = {
    "note": {"icon": "fa5s.info-circle", "color": "#2563eb", "bg": "#eff6ff"},
    "tip": {"icon": "fa5s.lightbulb", "color": "#16a34a", "bg": "#f0fdf4"},
    "warning": {
        "icon": "fa5s.exclamation-triangle",
        "color": "#d97706",
        "bg": "#fffbeb",
    },
    "caution": {"icon": "fa5s.fire", "color": "#dc2626", "bg": "#fef2f2"},
}


class CalloutWidget(QFrame):

  def __init__(self, raw_text: str, namespace: dict = None, parent=None):
    super().__init__(parent)

    # 1. Typ ermitteln: ::: {.callout-note} ... :::
    m_type = re.search(
        r":::\s*\{\.callout-(note|tip|warning|caution)\}", raw_text
    )
    c_type = m_type.group(1) if m_type else "note"
    theme = THEMES.get(c_type, THEMES["note"])

    # 2. Textkörper extrahieren (::: Zeilen entfernen)
    lines = [
        l
        for l in raw_text.splitlines()
        if not l.strip().startswith(":::") and l.strip()
    ]

    # Optionaler Titel auf Zeile 1 mit ##
    title = ""
    if lines and lines[0].startswith("## "):
      title = lines.pop(0)[3:].strip()
    content = "\n".join(lines).strip()

    # Styling Box
    self.setStyleSheet(f"""
            QFrame#CalloutWidget {{
                background-color: {theme['bg']};
                border-left: 4px solid {theme['color']};
                border-radius: 4px;
            }}
        """)
    self.setObjectName("CalloutWidget")

    root_layout = QVBoxLayout(self)
    root_layout.setContentsMargins(14, 10, 14, 10)
    root_layout.setSpacing(6)

    # Header-Zeile mit Icon
    header = QHBoxLayout()
    header.setSpacing(8)

    icon_lbl = QLabel()
    icon_lbl.setPixmap(qta.icon(theme["icon"], color=theme["color"]).pixmap(18, 18))
    header.addWidget(icon_lbl)

    title_lbl = QLabel(title or c_type.upper())
    title_lbl.setStyleSheet(f"""
            color: {theme['color']}; font-weight: bold; font-size: 13px;
        """)
    header.addWidget(title_lbl)
    header.addStretch()
    root_layout.addLayout(header)

    # Body (Formeln und Markdown bleiben funktional)
    if content:
      browser = MathTextBrowser()
      browser.setFrameShape(QFrame.Shape.NoFrame)
      browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
      browser.setStyleSheet("background: transparent;")
      render_markdown_with_math(content, browser, fontsize=12, namespace=namespace)

      doc = browser.document()
      doc.setTextWidth(700)
      browser.setFixedHeight(int(doc.size().height()) + 8)
      root_layout.addWidget(browser)
