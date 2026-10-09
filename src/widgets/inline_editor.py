from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPlainTextEdit

from widgets.resize_grip import MacResizeGrip
from widgets.syntax import CellHighlighter


MIN_HEIGHT = 56

PYTHON_STYLE = """
    QPlainTextEdit {
        background-color: #ffffff;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        border-left: 3px solid #2563eb;
        border-radius: 6px;
        padding: 8px 18px 10px 8px;
    }
    QPlainTextEdit:focus {
        border-color: #93c5fd;
        border-left: 3px solid #1d4ed8;
    }
"""

# Textzellen: Schrift und Farbe wie die gerenderte Ansicht (CMU Serif 16pt,
# #334155, transparent), damit der Klick in den Absatz kaum überrascht. Der
# linke Rand ist die einzige Markierung "hier wird editiert"; das Padding
# gleicht den Rahmen der Ansicht aus, damit der Text nicht verspringt.
MARKDOWN_STYLE = """
    QPlainTextEdit {
        background-color: transparent;
        color: #334155;
        border: 1px solid transparent;
        border-left: 3px solid #e2e8f0;
        border-radius: 6px;
        padding: 4px 18px 6px 8px;
    }
    QPlainTextEdit:focus {
        border-left: 3px solid #93c5fd;
    }
"""


class InlineEditor(QPlainTextEdit):
    """Plain text editor supporting Shift+Enter, Escape, Focus-Reporting, and resizing."""

    run_requested = Signal()
    escape_pressed = Signal()
    mode_toggle_requested = Signal()
    focused_in = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = CellHighlighter(self.document())
        font = QFont("JetBrains Mono", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self._kind = "python"
        self.setStyleSheet(PYTHON_STYLE)
        # Der Editor wächst mit dem Inhalt; gescrollt wird nur der Canvas.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.manual_height = 0  # per Grip gezogene Mindesthöhe
        self.grip = MacResizeGrip(self, self)
        self.textChanged.connect(self.fit_to_content)
        self.fit_to_content()

    def set_kind(self, kind: str):
        """Styles the editor as "markdown" (looks like the rendered text) or "python"."""
        if kind == self._kind:
            return
        self._kind = kind
        self.highlighter.set_mode(kind)
        if kind == "markdown":
            font = QFont("CMU Serif", 16)
            font.setStyleHint(QFont.StyleHint.Serif)
            self.setStyleSheet(MARKDOWN_STYLE)
        else:
            font = QFont("JetBrains Mono", 11)
            font.setStyleHint(QFont.StyleHint.Monospace)
            self.setStyleSheet(PYTHON_STYLE)
        self.setFont(font)
        self.fit_to_content()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focused_in.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Andere Breite -> anderer Zeilenumbruch -> andere Höhe
        if event.oldSize().width() != event.size().width():
            self.fit_to_content()
        self.grip.move(
            self.width() - self.grip.width() - 2, self.height() - self.grip.height() - 2
        )

    def fit_to_content(self):
        """Sets the height so that all (wrapped) lines are visible without scrolling."""
        # Beim QPlainTextEdit liefert document().size().height() die Anzahl
        # sichtbarer Zeilen (inkl. Umbrüche), nicht Pixel.
        self.document().size()  # erzwingt das Layout
        # Summe der Blockhöhen statt Zeilen * Zeilenhöhe: Überschriften und
        # Formeln in Textzellen sind höher als normale Zeilen.
        text_h = 0.0
        block = self.document().firstBlock()
        while block.isValid():
            text_h += self.blockBoundingRect(block).height()
            block = block.next()
        text_h = int(max(text_h, self.fontMetrics().lineSpacing()))
        text_h += int(self.document().documentMargin() * 2)
        chrome = self.height() - self.viewport().height()  # Rahmen + Padding
        target = max(MIN_HEIGHT, self.manual_height, text_h + chrome + 4)
        if target != self.height():
            self.setFixedHeight(target)
        # Falls der Viewport noch nicht aktuell ist, steht der Text evtl. verschoben.
        self.verticalScrollBar().setValue(0)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.run_requested.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_M and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.mode_toggle_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def setPlainText(self, text: str):
        super().setPlainText(text)
        self.fit_to_content()
