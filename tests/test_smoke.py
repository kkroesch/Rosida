def test_rosida_app_starts_with_one_empty_cell(rosida_win):
  assert len(rosida_win.doc.cells) == 1
  assert rosida_win.act_save.isEnabled() is False
