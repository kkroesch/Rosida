"""Einzelne Menü-/Toolbar-Actions auslösen und den resultierenden Zustand prüfen."""


def test_insert_cell_below_adds_a_cell(rosida_win, slow_step):
  before = len(rosida_win.doc.cells)

  rosida_win.act_insert_below.trigger()
  slow_step()

  assert len(rosida_win.doc.cells) == before + 1


def test_delete_active_cell_removes_it(rosida_win, slow_step):
  rosida_win.doc.insert_cell(initial_text="wird gelöscht")
  before = len(rosida_win.doc.cells)

  rosida_win.act_delete_cell.trigger()
  slow_step()

  assert len(rosida_win.doc.cells) == before - 1


def test_undo_redo_of_insert_cell(rosida_win, slow_step):
  before = len(rosida_win.doc.cells)

  rosida_win.act_insert_below.trigger()
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
