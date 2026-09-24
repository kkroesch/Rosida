from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPlainTextEdit

from widgets.resize_grip import MacResizeGrip


class InlineEditor(QPlainTextEdit):
    """Plain text editor supporting Shift+Enter, Escape, Focus-Reporting, and resizing."""

    run_requested = Signal()
    escape_pressed = Signal()
    mode_toggle_requested = Signal()
    focused_in = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("JetBrains Mono", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setStyleSheet("""
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
            QScrollBar:vertical {
                border: none;
                background: #f1f5f9;
                width: 6px;
                margin: 4px 2px 4px 0;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
        """)
        self.grip = MacResizeGrip(self, self)
        self.adjust_initial_height()
        self.textChanged.connect(self._on_content_changed)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focused_in.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.grip.move(self.width() - self.grip.width() - 2, self.height() - self.grip.height() - 2)

    def adjust_initial_height(self):
        doc_height = int(self.document().size().height())
        target_height = max(56, min(doc_height + 22, 280))
        self.setFixedHeight(target_height)

    def _on_content_changed(self):
        doc_height = int(self.document().size().height()) + 22
        if doc_height > self.height() and self.height() < 350:
            self.setFixedHeight(doc_height)

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
        if event.key() == Qt.Key.Key_M and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.mode_toggle_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)
