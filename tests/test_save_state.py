"""Speichern-Button: aktiv nur nach echter Änderung, deaktiviert nach Speichern/Neu."""


def test_save_disabled_on_fresh_document(rosida_win):
  assert rosida_win.act_save.isEnabled() is False


def test_typing_in_a_cell_enables_save(rosida_win, slow_step):
  cell = rosida_win.doc.get_active_cell()
  cell.editor.setPlainText("x = 1")
  slow_step()

  assert rosida_win.act_save.isEnabled() is True


def test_save_writes_file_and_disables_button_again(rosida_win, tmp_path, slow_step):
  target = tmp_path / "dokument.md"

  cell = rosida_win.doc.get_active_cell()
  cell.editor.setPlainText("# Titel")
  assert rosida_win.act_save.isEnabled() is True

  rosida_win.doc.save_to_markdown(str(target))
  rosida_win.set_current_filepath(str(target))
  slow_step()

  assert target.exists()
  assert "# Titel" in target.read_text(encoding="utf-8")
  assert rosida_win.act_save.isEnabled() is False


def test_new_document_action_resets_modified_state(rosida_win, slow_step):
  cell = rosida_win.doc.get_active_cell()
  cell.editor.setPlainText("etwas Text")
  assert rosida_win.act_save.isEnabled() is True

  rosida_win.act_new.trigger()
  slow_step()

  assert rosida_win.act_save.isEnabled() is False
  assert rosida_win.current_filepath is None
  assert len(rosida_win.doc.cells) == 1
