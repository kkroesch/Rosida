from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtWidgets import QFrame, QScrollArea, QWidget


class ClickableOutputFrame(QFrame):
    """Clickable interactive container routing mouse clicks to switch into edit mode."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Klicken, um Inhalt zu bearbeiten (Escape im Editor zum Schließen)")
        self.setStyleSheet("""
            ClickableOutputFrame {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px;
            }
            ClickableOutputFrame:hover {
                background-color: #f8fafc;
                border: 1px dashed #cbd5e1;
            }
        """)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def attach_click_listeners(self, widget: QWidget):
        """Recursively registers event filter for seamless child clicking."""
        widget.installEventFilter(self)
        if isinstance(widget, QScrollArea) and widget.viewport():
            widget.viewport().installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            return True
        return super().eventFilter(watched, event)
