"""Einzelne Menü-/Toolbar-Actions auslösen und den resultierenden Zustand prüfen."""


def test_insert_cell_adds_a_cell(rosida_win, slow_step):
  before = len(rosida_win.doc.cells)

  rosida_win.act_insert_cell.trigger()
  slow_step()

  assert len(rosida_win.doc.cells) == before + 1


def _texts(doc):
  return [c.editor.toPlainText() for c in doc.cells]


def _visual_texts(doc):
  """Zellinhalte in der Reihenfolge, in der sie im Layout stehen."""
  items = (doc.layout.itemAt(i).widget() for i in range(doc.layout.count()))
  return [w.editor.toPlainText() for w in items if w in doc.cells]


def _three_cells(win, qtbot):
  doc = win.doc
  doc.cells[0].editor.setPlainText("a")
  doc.insert_cell(initial_text="b")
  doc.insert_cell(initial_text="c")
  doc.cells[1].editor.setFocus()
  qtbot.waitUntil(lambda: doc.get_active_index() == 1)
  return doc


def test_insert_cell_goes_before_active_cell(rosida_win, qtbot, slow_step):
  doc = _three_cells(rosida_win, qtbot)

  rosida_win.act_insert_cell.trigger()
  slow_step()

  assert _texts(doc) == ["a", "", "b", "c"]
  assert _visual_texts(doc) == _texts(doc)
  assert doc.get_active_index() == 1


def test_move_cell_up_and_down(rosida_win, qtbot, slow_step):
  doc = _three_cells(rosida_win, qtbot)

  rosida_win.act_move_up.trigger()
  slow_step()
  assert _texts(doc) == ["b", "a", "c"]
  assert _visual_texts(doc) == _texts(doc)

  # Oben angekommen: kein weiterer Schritt, kein Undo-Eintrag
  rosida_win.act_move_up.trigger()
  assert _texts(doc) == ["b", "a", "c"]

  rosida_win.act_move_down.trigger()
  rosida_win.act_move_down.trigger()
  slow_step()
  assert _texts(doc) == ["a", "c", "b"]
  assert _visual_texts(doc) == _texts(doc)
  assert doc.get_active_cell().editor.toPlainText() == "b"

  doc.undo_stack.undo()
  doc.undo_stack.undo()
  doc.undo_stack.undo()
  assert _texts(doc) == ["a", "b", "c"]


def test_move_cell_via_shortcut_while_editing(rosida_win, qtbot, slow_step):
  from PySide6.QtCore import Qt

  doc = _three_cells(rosida_win, qtbot)
  editor = doc.cells[1].editor

  qtbot.keyClick(editor, Qt.Key.Key_Down, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
  slow_step()
  assert _texts(doc) == ["a", "c", "b"]
  assert editor.hasFocus()

  qtbot.keyClick(editor, Qt.Key.Key_Up, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
  slow_step()
  assert _texts(doc) == ["a", "b", "c"]


def test_delete_active_cell_removes_it(rosida_win, slow_step):
  rosida_win.doc.insert_cell(initial_text="wird gelöscht")
  before = len(rosida_win.doc.cells)

  rosida_win.act_delete_cell.trigger()
  slow_step()

  assert len(rosida_win.doc.cells) == before - 1


def test_undo_redo_of_insert_cell(rosida_win, slow_step):
  before = len(rosida_win.doc.cells)

  rosida_win.act_insert_cell.trigger()
  slow_step()
  assert len(rosida_win.doc.cells) == before + 1

  rosida_win.act_undo.trigger()
  slow_step()
  assert len(rosida_win.doc.cells) == before

  rosida_win.act_redo.trigger()
  slow_step()
  assert len(rosida_win.doc.cells) == before + 1


def test_toggle_mode_action_cycles_cell_mode(rosida_win, slow_step):
  cell = rosida_win.doc.get_active_cell()
  cell.set_mode("auto")

  rosida_win.act_toggle_mode.trigger()
  slow_step()
  assert cell.get_mode() == "python"

  rosida_win.act_toggle_mode.trigger()
  slow_step()
  assert cell.get_mode() == "markdown"


def test_toggle_structure_dock_action_hides_and_shows_dock(rosida_win, slow_step):
  assert rosida_win.dock_structure.isVisible() is True

  rosida_win.act_toggle_structure.trigger()
  slow_step()
  assert rosida_win.dock_structure.isVisible() is False

  rosida_win.act_toggle_structure.trigger()
  slow_step()
  assert rosida_win.dock_structure.isVisible() is True
