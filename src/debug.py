import os
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QAbstractButton, QWidget


class ClickDebugFilter(QObject):

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            # Widget-Infos ermitteln
            cls_name = watched.__class__.__name__
            obj_name = watched.objectName() or "<unnamed>"

            # Falls es ein Button ist: Text mitloggen
            extra = ""
            if isinstance(watched, QAbstractButton):
                extra = f" | text='{watched.text()}'"
            elif hasattr(watched, "currentText"):
                extra = f" | text='{watched.currentText()}'"

            # Geometrie & Klickposition
            pos = event.position().toPoint()
            print(
                f"[DEBUG CLICK] {cls_name} (#{obj_name}){extra} at ({pos.x()}, {pos.y()}) | Button: {event.button().name}"
            )

        return super().eventFilter(watched, event)
