from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QPlainTextEdit, QWidget


class MacResizeGrip(QWidget):
    """Subtle corner resize grip with diagonal ridges."""

    def __init__(self, target_editor: QPlainTextEdit, parent=None):
        super().__init__(parent)
        self.target = target_editor
        self.setFixedSize(16, 16)
        self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        self.drag_start_y = 0
        self.initial_height = 0
        self.is_dragging = False
        self.setToolTip("Ziehen, um Eingabefeld zu vergrößern")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_y = event.globalPosition().y()
            self.initial_height = self.target.height()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging:
            delta_y = event.globalPosition().y() - self.drag_start_y
            new_height = max(50, int(self.initial_height + delta_y))
            self.target.setFixedHeight(new_height)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.is_dragging = False
        event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(QColor("#94a3b8"), 1.2)
        painter.setPen(pen)
        w, h = self.width(), self.height()
        painter.drawLine(w - 3, h - 11, w - 11, h - 3)
        painter.drawLine(w - 3, h - 7, w - 7, h - 3)
        painter.drawLine(w - 3, h - 3, w - 3, h - 3)
