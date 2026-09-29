"""Zitate und Quellenverzeichnis (HTML-Export) sowie bibliography im QMD-Export."""

from pathlib import Path

from exporters.bibtex import Citations, latex_to_text, parse_bibtex
from widgets.math_text import markdown_to_html

DOCS = Path(__file__).resolve().parent.parent / "docs"

BIB = r"""
@string{ix = "iX -- Magazin"}
@article{pleger_2023,
  title = {Zeitreihen mit {Python}},
  journal = ix,
  author = {Pleger, Roland},
  year = {2023}, month = feb, pages = {128ff.},
  note = {Kontakt: autor@example.com},
}
@book{fp_2018,
  title = "Big {Data} in der {Praxis}",
  author = {Freiknecht, J. and Papp, S.},
  publisher = {Hanser \& Co},
  url = {https://books.google.ch/books?id=0SC\_DwAAQBAJ},
  urldate = {2023-10-09},
  year = {2018},
}
"""


def _render(text, citations):
  return markdown_to_html(text, lambda latex, display: latex, cite=citations)


def test_parser_handles_zotero_output():
  entries = parse_bibtex(BIB)
  assert set(entries) == {"pleger_2023", "fp_2018"}
  assert entries["pleger_2023"].get("journal") == "iX – Magazin"
  assert entries["pleger_2023"].fields["month"] == "2"
  assert entries["fp_2018"].authors == ["Freiknecht, J.", "Papp, S."]
  assert entries["fp_2018"].url == "https://books.google.ch/books?id=0SC_DwAAQBAJ"
  assert latex_to_text(r'{\"U}ber M\"{u}ller \& Stra\ss e') == "Über Müller & Straße"


def test_citation_forms():
  cit = Citations(parse_bibtex(BIB))
  html = _render(
    "Siehe [@pleger_2023], [vgl. @fp_2018, S. 5; -@pleger_2023] und @fp_2018. "
    "Unbekannt: [@gibtsnicht]. Mail: [autor@example.com], `[@pleger_2023]`",
    cit,
  )
  assert '(<a href="#ref-pleger_2023">Pleger 2023</a>)' in html
  assert '(vgl. <a href="#ref-fp_2018">Freiknecht und Papp 2018</a>, S. 5; <a href="#ref-pleger_2023">2023</a>)' in html
  assert '<a href="#ref-fp_2018">Freiknecht und Papp (2018)</a>' in html
  assert '<span class="unknown">?gibtsnicht</span>' in html
  assert "[autor@example.com]" in html  # keine Zitation
  assert "<code>[@pleger_2023]</code>" in html  # Code bleibt Code


def test_reference_list_contains_only_cited_entries_sorted():
  cit = Citations(parse_bibtex(BIB))
  _render("[@pleger_2023] und [@fp_2018]", cit)

  refs = cit.references_html()
  assert '<h2 id="quellen">Quellen</h2>' in refs
  assert refs.index("ref-fp_2018") < refs.index("ref-pleger_2023")  # Freiknecht vor Pleger
  assert '<a href="https://books.google.ch/books?id=0SC_DwAAQBAJ">' in refs
  assert "(abgerufen am 9.10.2023)" in refs
  assert "S. 128ff." in refs and "128ff.." not in refs

  assert Citations(parse_bibtex(BIB)).references_html() == ""  # nichts zitiert


def test_html_export_appends_sources(rosida_win, tmp_path, wait_idle):
  doc = rosida_win.doc
  rosida_win.current_filepath = str(DOCS / "example.md")
  doc.frontmatter_cell.editor.setPlainText("title: T\nbibliography: example.bib")
  doc.cells[0].editor.setPlainText("Wie in [@wohlenberg_3_2023] beschrieben.")
  wait_idle(doc)

  out = tmp_path / "out.html"
  doc.export_html(str(out))
  page = out.read_text(encoding="utf-8")

  assert '<a href="#ref-wohlenberg_3_2023">Wohlenberg 2023</a>' in page
  assert '<li id="ref-wohlenberg_3_2023">' in page
  assert "https://towardsdatascience.com/three-versions-of-k-means-cf939b65f4ea" in page
  assert page.count("<li id=") == 1


def test_qmd_export_keeps_frontmatter_and_rebases_bibliography(rosida_win, tmp_path):
  doc = rosida_win.doc
  rosida_win.current_filepath = str(DOCS / "example.md")
  doc.frontmatter_cell.editor.setPlainText('title: "Pendel"\nbibliography: example.bib')

  out = tmp_path / "export" / "doc.qmd"
  doc.export_qmd(str(out))
  head = out.read_text(encoding="utf-8").split("---")[1]

  assert 'title: "Pendel"' in head
  assert "format:" in head
  bib = head.split("bibliography: ")[1].splitlines()[0].strip('"')
  assert (out.parent / bib).resolve() == (DOCS / "example.bib").resolve()
