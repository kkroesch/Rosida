from PySide6.QtGui import QKeySequence, QUndoCommand
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from .base import RosidaAction


class InsertCellCommand(QUndoCommand):
  """Undoable command for inserting a notebook cell."""

  def __init__(self, doc_canvas, index: int, text: str = "", mode: str = "auto", auto_run: bool = False, description: str = "Zelle einfügen"):
    super().__init__(description)
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

  def __init__(self, doc_canvas, cell, description: str = "Zelle löschen"):
    super().__init__(description)
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


class UndoAction(RosidaAction):

  def __init__(self, document_canvas, parent=None):
    super().__init__("↶ Rückgängig", parent)
    self.doc = document_canvas

    self.setShortcut(QKeySequence.StandardKey.Undo)
    self.setStatusTip("Letzte Aktion rückgängig machen (Ctrl+Z)")
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
    super().__init__("↷ Wiederholen", parent)
    self.doc = document_canvas

    self.setShortcut(QKeySequence.StandardKey.Redo)
    self.setStatusTip("Letzte rückgängig gemachte Aktion wiederholen (Ctrl+Y)")
    self.set_icon_name("fa5s.redo")

    self.triggered.connect(self._execute)

  def _execute(self):
    focus_w = QApplication.focusWidget()
    if isinstance(focus_w, QPlainTextEdit) and focus_w.document().isRedoAvailable():
      focus_w.redo()
      return
    if self.doc.undo_stack.canRedo():
      self.doc.undo_stack.redo()


class InsertCellAboveAction(RosidaAction):

  def __init__(self, document_canvas, parent=None):
    super().__init__("⇧ Zelle darüber einfügen", parent)
    self.doc = document_canvas

    self.setShortcut(QKeySequence("Ctrl+Shift+A"))
    self.setToolTip("Neue Zelle oberhalb der aktiven Zelle einfügen (Ctrl+Shift+A)")
    self.set_icon_name("fa5s.arrow-circle-up")

    self.triggered.connect(self.doc.insert_cell_above)


class InsertCellBelowAction(RosidaAction):

  def __init__(self, document_canvas, parent=None):
    super().__init__("⇩ Zelle darunter einfügen", parent)
    self.doc = document_canvas

    self.setShortcut(QKeySequence("Ctrl+Shift+B"))
    self.setToolTip("Neue Zelle unterhalb der aktiven Zelle einfügen (Ctrl+Shift+B)")
    self.set_icon_name("fa5s.arrow-circle-down")

    self.triggered.connect(self.doc.insert_cell_below)


class DeleteCellAction(RosidaAction):

  def __init__(self, document_canvas, parent=None):
    super().__init__("🗑 Zelle löschen", parent)
    self.doc = document_canvas

    self.setShortcut(QKeySequence("Ctrl+Shift+D"))
    self.setToolTip("Aktive Zelle löschen (Ctrl+Shift+D)")
    self.set_icon_name("fa5s.trash-alt")

    self.triggered.connect(self.doc.delete_active_cell)


class ToggleModeAction(RosidaAction):

  def __init__(self, document_canvas, parent=None):
    super().__init__("⇄ Modus umschalten (Auto/Python/Text)", parent)
    self.doc = document_canvas

    self.setShortcut(QKeySequence("Ctrl+M"))
    self.setToolTip("Zellmodus umschalten: Auto → Python → Text (Ctrl+M)")
    self.set_icon_name("fa5s.sync-alt")

    self.triggered.connect(self.doc.toggle_active_mode)
