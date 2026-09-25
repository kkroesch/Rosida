"""Datei öffnen: über die echte OpenDocumentAction, nur der native Dialog wird gemockt."""

from actions.file import get_recent_files


def test_open_action_loads_file_and_updates_recent_files(rosida_win, tmp_path, monkeypatch, slow_step):
  source = tmp_path / "beispiel.md"
  source.write_text("# Meine Notiz\n\nText mit $x^2$.\n", encoding="utf-8")

  monkeypatch.setattr(
    "actions.file.QFileDialog.getOpenFileName",
    lambda *args, **kwargs: (str(source), "Markdown-Dateien (*.md *.markdown)"),
  )

  rosida_win.act_open.trigger()
  slow_step()

  assert rosida_win.current_filepath == str(source)
  assert len(rosida_win.doc.cells) >= 1
  assert "Meine Notiz" in rosida_win.doc.cells[0].editor.toPlainText()
  assert str(source) in get_recent_files()


def test_open_action_shows_error_on_broken_file(rosida_win, tmp_path, monkeypatch, qtbot):
  missing = tmp_path / "existiert-nicht.md"

  monkeypatch.setattr(
    "actions.file.QFileDialog.getOpenFileName",
    lambda *args, **kwargs: (str(missing), ""),
  )
  monkeypatch.setattr("actions.file.QMessageBox.critical", lambda *args, **kwargs: None)

  rosida_win.act_open.trigger()

  # current_filepath darf bei fehlgeschlagenem Laden nicht auf die kaputte Datei zeigen
  assert rosida_win.current_filepath != str(missing)
