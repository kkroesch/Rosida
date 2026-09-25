"""Zellen ausführen, Text einfügen, Collapse-Verhalten bei leerem Output."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

import sympy as sp


def test_insert_text_via_latex_palette_button_click(rosida_win, qtbot, slow_step):
  active = rosida_win.doc.get_active_cell()
  active.set_mode("markdown")

  fraction_btn = None
  for btn in rosida_win.dock_palette.findChildren(QPushButton):
    if btn.text() == "a/b":
      fraction_btn = btn
      break
  assert fraction_btn is not None, "Bruch-Button (a/b) nicht in der LaTeX-Palette gefunden"

  qtbot.mouseClick(fraction_btn, Qt.MouseButton.LeftButton)
  slow_step()

  assert r"\frac{a}{b}" in active.editor.toPlainText()


def test_run_python_cell_computes_value(rosida_win, slow_step):
  cell = rosida_win.doc.get_active_cell()
  cell.set_mode("python")
  cell.editor.setPlainText("2 + 2")

  cell.render()
  slow_step()

  assert cell.last_val == 4
  assert cell.stack.currentIndex() == 1
  assert cell._is_collapsed_empty is False


def test_run_sympy_cell_renders_symbolic_result(rosida_win, slow_step):
  rosida_win.namespace["sp"] = sp
  cell = rosida_win.doc.get_active_cell()
  cell.set_mode("python")
  cell.editor.setPlainText("x = sp.symbols('x')\nsp.diff(x**2, x)")

  cell.render()
  slow_step()

  assert isinstance(cell.last_val, sp.Basic)
  assert cell.last_val == 2 * sp.symbols("x")


def test_cell_without_output_collapses_to_plus_marker(rosida_win, slow_step):
  cell = rosida_win.doc.get_active_cell()
  cell.set_mode("python")
  cell.editor.setPlainText("y = 42")

  cell.render()
  slow_step()

  assert cell.last_val is None
  assert cell.last_stdout == ""
  assert cell._is_collapsed_empty is True
  assert cell.view_layout.count() == 1  # nur die Plus-Zeile, keine leere große Box


def test_run_all_cells_action_executes_every_cell(rosida_win, slow_step):
  rosida_win.doc.get_active_cell().editor.setPlainText("1 + 1")
  second = rosida_win.doc.insert_cell(mode="python", initial_text="3 + 3")

  rosida_win.act_run_all.trigger()
  slow_step()

  assert rosida_win.doc.cells[0].last_val == 2
  assert second.last_val == 6
