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
def test_finishing_edit_keeps_scroll_position(loaded_win, qtbot, key, modifier, wait_idle):
  bar = loaded_win.scroll.verticalScrollBar()
  for cell in loaded_win.doc.cells[1:-2]:
    loaded_win.scroll.ensureWidgetVisible(cell, 0, 0)
    cell.switch_to_edit()
    qtbot.wait(20)
    before = bar.value()

    qtbot.keyClick(cell.editor, key, modifier)
    wait_idle(loaded_win.doc)
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


def test_collapsed_properties_are_compact(rosida_win, qtbot):
  """Eingeklappt nur so hoch wie der Knopf, nicht wie der (lange) YAML-Editor,
  und auch bei kurzen Dokumenten in großen Fenstern keine Lücke darüber."""
  rosida_win.resize(1200, 900)
  props = rosida_win.doc.frontmatter_cell
  first_cell = rosida_win.doc.cells[0]

  for text in ("\n".join(f"key{i}: value" for i in range(20)), ""):
    props.editor.setPlainText(text)
    props.expand()
    qtbot.wait(20)
    expanded = props.height()

    props.commit_and_collapse()
    qtbot.wait(20)

    assert props.height() < 40, text[:20]
    gap = first_cell.y() - (props.y() + props.height())
    assert gap < 30
  assert expanded > 40  # leerer Editor: Mindesthöhe
