"""Splash screen shown while the application builds up.

Deliberately imports only PySide6 and light modules, so it can appear before
the heavy scientific imports (numpy, sympy, polars, matplotlib) of app.py.
"""

import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from actions.help import APP_VERSION
from config.settings import ASSETS_DIR, FONTS_DIR

AUTHOR = "Karsten Kroesch"
AUTHOR_URL = "https://kroesch.ch/"


class SemiBoldLabel(QLabel):
    """CMU Serif has no semi-bold italic; a thin outline in the text colour fakes one."""

    def __init__(self, text: str, color: str, stroke: float = 1.6):
        super().__init__(text)
        self._color = QColor(color)
        self._stroke = stroke

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        metrics = painter.fontMetrics()
        path = QPainterPath()
        x = (self.width() - metrics.horizontalAdvance(self.text())) / 2
        y = (self.height() + metrics.ascent() - metrics.descent()) / 2
        path.addText(x, y, self.font(), self.text())
        painter.setPen(QPen(self._color, self._stroke, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(self._color)
        painter.drawPath(path)


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self._background = QPixmap(str(ASSETS_DIR / "splash.png"))
        self.setFixedSize(self._background.size())

        font_id = QFontDatabase.addApplicationFont(str(FONTS_DIR / "cmu.serif-italic.ttf"))
        families = QFontDatabase.applicationFontFamilies(font_id)
        family = families[0] if families else "serif"

        title = SemiBoldLabel("Rosida", "#3b1f2b")
        title_font = QFont(family, 64)
        title_font.setItalic(True)
        title.setFont(title_font)

        version = QLabel(APP_VERSION)
        version_font = QFont(family, 20)
        version_font.setItalic(True)
        version.setFont(version_font)
        version.setStyleSheet("color: #6b4a58; background: transparent;")

        author = QLabel(
            f'{AUTHOR} · <a href="{AUTHOR_URL}" style="color: #b0405e;">{AUTHOR_URL}</a>'
        )
        author_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
        author_font.setPointSize(11)
        author.setFont(author_font)
        author.setStyleSheet(
            "color: #3b1f2b; background: rgba(255, 255, 255, 170);"
            "padding: 3px 8px; border-radius: 6px;"
        )
        author.setTextFormat(Qt.TextFormat.RichText)
        author.setOpenExternalLinks(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 62, 0, 0)
        layout.setSpacing(4)
        for label in (title, version):
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(label)
        layout.addStretch(1)

        # Bottom right corner, outside the layout.
        author.setParent(self)
        author.adjustSize()
        author.move(self.width() - author.width() - 12, self.height() - author.height() - 12)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPixmap(0, 0, self._background)
        # Soft panel so the text stays readable on top of the busy background.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 170))
        panel = QRectF(self.width() * 0.31, 48, self.width() * 0.38, 190)
        painter.drawRoundedRect(panel, 18, 18)


def start_splash() -> tuple[QApplication, SplashScreen]:
    """Creates the QApplication and shows the splash right away."""
    sys.argv[0] = "Rosida"
    app = QApplication(["Rosida"] + sys.argv[1:])
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    return app, splash
