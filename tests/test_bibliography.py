"""Literaturdatei aus der Frontmatter (bibliography:) im References-Dock."""

from pathlib import Path

from widgets.frontmatter import set_yaml_property

DOCS = Path(__file__).resolve().parent.parent / "docs"


def _open(win, path: Path):
  win.doc.load_from_markdown(str(path))
  win.set_current_filepath(str(path))


def test_bibliography_from_frontmatter_is_loaded(rosida_win, tmp_path):
  (tmp_path / "example.bib").write_text((DOCS / "example.bib").read_text(encoding="utf-8"), encoding="utf-8")
  doc_file = tmp_path / "doc.md"
  doc_file.write_text("---\ntitle: X\nbibliography: example.bib\n---\n\nText\n", encoding="utf-8")
  _open(rosida_win, doc_file)

  dock = rosida_win.dock_bibitems
  assert dock.stack.currentIndex() == 1
  assert dock.list_widget.count() > 0
  assert dock.lbl_source.text() == "example.bib"


def test_missing_bibliography_shows_button_with_hint(rosida_win, tmp_path):
  doc_file = tmp_path / "doc.md"
  doc_file.write_text("---\ntitle: X\nbibliography: fehlt.bib\n---\n\nText\n", encoding="utf-8")

  _open(rosida_win, doc_file)

  dock = rosida_win.dock_bibitems
  assert dock.stack.currentIndex() == 0
  assert "fehlt.bib" in dock.lbl_hint.text()


def test_chosen_file_is_written_relative_to_document(rosida_win, tmp_path):
  (tmp_path / "refs").mkdir()
  bib = tmp_path / "refs" / "lit.bib"
  bib.write_text((DOCS / "example.bib").read_text(encoding="utf-8"), encoding="utf-8")
  doc_file = tmp_path / "doc.md"
  doc_file.write_text("---\ntitle: X\n---\n\nText\n", encoding="utf-8")
  _open(rosida_win, doc_file)
  assert rosida_win.dock_bibitems.stack.currentIndex() == 0

  rosida_win.dock_bibitems.bib_file_chosen.emit(str(bib))

  props = rosida_win.doc.frontmatter_cell.editor.toPlainText()
  assert props == "title: X\nbibliography: refs/lit.bib"
  assert rosida_win.doc.is_modified()
  assert rosida_win.dock_bibitems.stack.currentIndex() == 1


def test_new_document_forgets_bibliography(rosida_win):
  _open(rosida_win, DOCS / "example.md")

  rosida_win.act_new.trigger()

  props = rosida_win.doc.frontmatter_cell.editor.toPlainText()
  assert props.startswith("title: ") and "bibliography" not in props
  assert "author: " in props
  assert rosida_win.dock_bibitems.stack.currentIndex() == 0


def test_set_yaml_property_keeps_formatting():
  text = 'title: "Pendel"\nbibliography:\n  - a.bib\n  - b.bib\n\ntags: [x]  # Kommentar'
  assert set_yaml_property(text, "bibliography", "lit.bib") == (
    'title: "Pendel"\nbibliography: lit.bib\n\ntags: [x]  # Kommentar'
  )
  assert set_yaml_property("title: X", "bibliography", "mit leer.bib") == (
    'title: X\nbibliography: "mit leer.bib"'
  )
