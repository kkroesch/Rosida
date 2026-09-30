from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QKeySequence, QUndoCommand
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from .base import RosidaAction


class InsertCellCommand(QUndoCommand):
    """Undoable command for inserting a notebook cell."""

    def __init__(
        self,
        doc_canvas,
        index: int,
        text: str = "",
        mode: str = "auto",
        auto_run: bool = False,
        description: str | None = None,
    ):
        super().__init__(
            description or QCoreApplication.translate("InsertCellCommand", "Insert cell")
        )
        self.doc = doc_canvas
        self.index = index
        self.text = text
        self.mode = mode
        self.auto_run = auto_run
        self.cell = None

    def redo(self):
        if self.cell is None:
            self.cell = self.doc._create_cell_widget(self.text, self.mode)
            if self.auto_run:
                self.cell.render()
        self.doc._attach_cell_widget(self.cell, self.index)
        self.cell.switch_to_edit()
        self.doc.set_active_cell(self.cell)
        self.doc.structure_changed.emit(self.doc.cells)

    def undo(self):
        if self.cell and self.cell in self.doc.cells:
            self.doc._detach_cell_widget(self.cell)
            if self.doc.cells:
                prev_idx = max(0, min(self.index - 1, len(self.doc.cells) - 1))
                self.doc.set_active_cell(self.doc.cells[prev_idx])
            self.doc.structure_changed.emit(self.doc.cells)


class DeleteCellCommand(QUndoCommand):
    """Undoable command for deleting a notebook cell."""

    def __init__(self, doc_canvas, cell, description: str | None = None):
        super().__init__(
            description or QCoreApplication.translate("DeleteCellCommand", "Delete cell")
        )
        self.doc = doc_canvas
        self.cell = cell
        self.index = self.doc.cells.index(cell) if cell in self.doc.cells else -1

    def redo(self):
        if self.cell in self.doc.cells:
            self.index = self.doc.cells.index(self.cell)
            self.doc._detach_cell_widget(self.cell)
            if self.doc.cells:
                next_idx = min(self.index, len(self.doc.cells) - 1)
                self.doc.set_active_cell(self.doc.cells[next_idx])
            self.doc.structure_changed.emit(self.doc.cells)

    def undo(self):
        if self.index >= 0:
            self.doc._attach_cell_widget(self.cell, self.index)
            self.doc.set_active_cell(self.cell)
            self.cell.switch_to_edit()
            self.doc.structure_changed.emit(self.doc.cells)


class MoveCellCommand(QUndoCommand):
    """Undoable command for moving a notebook cell up (offset < 0) or down (offset > 0)."""

    def __init__(self, doc_canvas, cell, offset: int):
        super().__init__(
            QCoreApplication.translate("MoveCellCommand", "Move cell up")
            if offset < 0
            else QCoreApplication.translate("MoveCellCommand", "Move cell down")
        )
        self.doc = doc_canvas
        self.cell = cell
        self.offset = offset

    def _move(self, offset: int):
        if self.cell not in self.doc.cells:
            return
        target = self.doc.cells.index(self.cell) + offset
        if not 0 <= target < len(self.doc.cells):
            return
        in_edit = self.cell.stack.currentIndex() == 0
        self.doc._detach_cell_widget(self.cell)
        self.doc._attach_cell_widget(self.cell, target)
        if in_edit:
            self.cell.editor.setFocus()
        self.doc.set_active_cell(self.cell)
        self.doc.structure_changed.emit(self.doc.cells)

    def redo(self):
        self._move(self.offset)

    def undo(self):
        self._move(-self.offset)


class UndoAction(RosidaAction):
    def __init__(self, document_canvas, parent=None):
        super().__init__(QCoreApplication.translate("UndoAction", "&Undo"), parent)
        self.doc = document_canvas

        self.setShortcut(QKeySequence.StandardKey.Undo)
        self.setStatusTip(self.tr("Undo the last action (Ctrl+Z)"))
        self.set_icon_name("fa5s.undo")

        self.triggered.connect(self._execute)

    def _execute(self):
        # Lokales Textfeld-Undo hat Vorrang vor dem dokumentweiten UndoStack.
        focus_w = QApplication.focusWidget()
        if isinstance(focus_w, QPlainTextEdit) and focus_w.document().isUndoAvailable():
            focus_w.undo()
            return
        if self.doc.undo_stack.canUndo():
            self.doc.undo_stack.undo()


class RedoAction(RosidaAction):
    def __init__(self, document_canvas, parent=None):
        super().__init__(QCoreApplication.translate("RedoAction", "&Redo"), parent)
        self.doc = document_canvas

        self.setShortcut(QKeySequence.StandardKey.Redo)
        self.setStatusTip(self.tr("Redo the last undone action (Ctrl+Y)"))
        self.set_icon_name("fa5s.redo")

        self.triggered.connect(self._execute)

    def _execute(self):
        focus_w = QApplication.focusWidget()
        if isinstance(focus_w, QPlainTextEdit) and focus_w.document().isRedoAvailable():
            focus_w.redo()
            return
        if self.doc.undo_stack.canRedo():
            self.doc.undo_stack.redo()


class InsertCellAction(RosidaAction):
    def __init__(self, document_canvas, parent=None):
        super().__init__(QCoreApplication.translate("InsertCellAction", "Insert cell"), parent)
        self.doc = document_canvas

        self.setShortcut(QKeySequence("Ctrl+Shift+A"))
        self.setToolTip(
            self.tr("Insert a new cell before the active cell (Ctrl+Shift+A)")
        )
        self.set_icon_name("fa5s.plus-circle")

        self.triggered.connect(self.doc.insert_cell_before_active)


class MoveCellAboveAction(RosidaAction):
    def __init__(self, document_canvas, parent=None):
        super().__init__(QCoreApplication.translate("MoveCellAboveAction", "Move cell up"), parent)
        self.doc = document_canvas

        self.setShortcut(QKeySequence("Ctrl+Shift+Up"))
        self.setToolTip(
            self.tr("Move the active cell up by one position (Ctrl+Shift+Up)")
        )
        self.set_icon_name("fa5s.arrow-circle-up")

        self.triggered.connect(lambda: self.doc.move_active_cell(-1))


class MoveCellBelowAction(RosidaAction):
    def __init__(self, document_canvas, parent=None):
        super().__init__(QCoreApplication.translate("MoveCellBelowAction", "Move cell down"), parent)
        self.doc = document_canvas

        self.setShortcut(QKeySequence("Ctrl+Shift+Down"))
        self.setToolTip(
            self.tr("Move the active cell down by one position (Ctrl+Shift+Down)")
        )
        self.set_icon_name("fa5s.arrow-circle-down")

        self.triggered.connect(lambda: self.doc.move_active_cell(1))


class DeleteCellAction(RosidaAction):
    def __init__(self, document_canvas, parent=None):
        super().__init__(QCoreApplication.translate("DeleteCellAction", "Delete cell"), parent)
        self.doc = document_canvas

        self.setShortcut(QKeySequence("Ctrl+Shift+D"))
        self.setToolTip(self.tr("Delete the active cell (Ctrl+Shift+D)"))
        self.set_icon_name("fa5s.trash-alt")

        self.triggered.connect(self.doc.delete_active_cell)


class ToggleModeAction(RosidaAction):
    def __init__(self, document_canvas, parent=None):
        super().__init__(QCoreApplication.translate("ToggleModeAction", "Toggle mode (Auto/Python/Text)"), parent)
        self.doc = document_canvas

        self.setShortcut(QKeySequence("Ctrl+M"))
        self.setToolTip(self.tr("Toggle cell mode: Auto → Python → Text (Ctrl+M)"))
        self.set_icon_name("fa5s.sync-alt")

        self.triggered.connect(self.doc.toggle_active_mode)
