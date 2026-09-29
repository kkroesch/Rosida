"""Editor-Höhe und Scrollposition beim Bearbeiten/Abschließen von Zellen."""

import pytest
from PySide6.QtCore import Qt


@pytest.fixture
def loaded_win(rosida_win, qtbot):
  """Beispieldokument in einem aktiven Fenster, das kleiner als der Inhalt ist."""
  rosida_win.resize(1000, 700)
  rosida_win.activateWindow()
  qtbot.waitUntil(rosida_win.isActiveWindow)
  rosida_win.doc.load_from_markdown("docs/example.md")
  qtbot.wait(100)
  return rosida_win


@pytest.mark.parametrize(
  "key, modifier",
  [
    (Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
    (Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier),
  ],
)
def test_finishing_edit_keeps_scroll_position(loaded_win, qtbot, key, modifier):
  bar = loaded_win.scroll.verticalScrollBar()
  for cell in loaded_win.doc.cells[1:-2]:
    loaded_win.scroll.ensureWidgetVisible(cell, 0, 0)
    cell.switch_to_edit()
    qtbot.wait(20)
    before = bar.value()

    qtbot.keyClick(cell.editor, key, modifier)
    qtbot.wait(20)

    assert cell.stack.currentIndex() == 1
    assert bar.value() == before


def test_editor_shows_all_lines_when_opened(loaded_win, qtbot):
  for cell in loaded_win.doc.cells:
    cell.switch_to_edit()
    qtbot.wait(10)
    editor = cell.editor
    assert editor.verticalScrollBar().maximum() == 0, editor.toPlainText()[:40]


def test_editor_grows_with_new_lines(rosida_win, qtbot):
  editor = rosida_win.doc.get_active_cell().editor
  editor.setFocus()
  start = editor.height()

  for _ in range(15):
    qtbot.keyClicks(editor, "zeile")
    qtbot.keyClick(editor, Qt.Key.Key_Return)

  assert editor.height() > start
  assert editor.verticalScrollBar().maximum() == 0
