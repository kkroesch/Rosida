"""Asynchrone Zellausführung: Worker-Thread, Warteindikator, Reihenfolge."""

import time

from PySide6.QtWidgets import QProgressBar


def _python_cell(doc, code, index=0):
  cell = doc.cells[index] if index < len(doc.cells) else doc.insert_cell()
  cell.set_mode("python")
  cell.editor.setPlainText(code)
  return cell


def test_gui_stays_responsive_and_shows_busy_indicator(rosida_win, qtbot, wait_idle):
  cell = _python_cell(rosida_win.doc, "import time\ntime.sleep(0.8)\n42")

  start = time.monotonic()
  cell.render()
  # Die Event-Loop läuft weiter: qtbot.wait kehrt pünktlich zurück.
  qtbot.wait(300)
  assert time.monotonic() - start < 0.7
  assert cell.is_running
  assert cell.editor.isReadOnly()
  assert cell.view_frame.findChildren(QProgressBar)
  assert cell.stack.currentIndex() == 1

  wait_idle(rosida_win.doc)
  assert cell.last_val == 42
  assert not cell.is_running
  assert not cell.editor.isReadOnly()
  qtbot.waitUntil(lambda: not cell.view_frame.findChildren(QProgressBar))


def test_cells_run_in_order_including_text_templates(rosida_win, wait_idle):
  doc = rosida_win.doc
  _python_cell(doc, "import time\ntime.sleep(0.3)\nx = 5")
  text = doc.insert_cell(mode="markdown", initial_text="x ist {{ x }}")
  last = _python_cell(doc, "x * 2", index=2)

  rosida_win.act_run_all.trigger()
  wait_idle(doc)

  assert last.last_val == 10
  browser = text.view_frame.findChildren(__import__("widgets.math_text").math_text.MathTextBrowser)[0]
  assert "x ist 5" in browser.toPlainText()


def test_stdout_and_errors(rosida_win, wait_idle):
  doc = rosida_win.doc
  cell = _python_cell(doc, "print('hallo')\n1 / 0")

  cell.render()
  print("GUI-Thread schreibt dazwischen")
  wait_idle(doc)

  assert cell.last_val is None
  assert cell.last_stdout == "Error: ZeroDivisionError: division by zero"
  texts = [w.text() for w in cell.view_frame.findChildren(__import__("PySide6.QtWidgets").QtWidgets.QLabel)]
  assert "hallo" in texts
  assert any("ZeroDivisionError" in t for t in texts)
  assert not any("GUI-Thread" in t for t in texts)


def test_editing_during_run_is_not_interrupted(rosida_win, qtbot, wait_idle):
  cell = _python_cell(rosida_win.doc, "import time\ntime.sleep(0.4)\n1")
  cell.render()
  qtbot.wait(200)

  cell.switch_to_edit()
  wait_idle(rosida_win.doc)

  assert cell.last_val == 1
  assert cell.stack.currentIndex() == 0  # bleibt im Editor


def test_loading_does_not_mark_document_modified(rosida_win, wait_idle):
  doc = rosida_win.doc
  doc.load_from_markdown("docs/example.md")
  doc.set_modified(False)  # wie RosidaApp._load_document_on_start

  wait_idle(doc)

  assert not doc.is_modified()
