"""Oberflächensprache (System/Override) und Dokumentsprache der Exporte."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QLocale
from PySide6.QtWidgets import QApplication

import config.i18n as i18n
from exporters.terms import document_language

TS_FILE = Path(__file__).resolve().parent.parent / "assets" / "i18n" / "rosida_de.ts"


@pytest.fixture
def ui_lang(monkeypatch, qapp):
  """Setzt die Spracheinstellung, ohne echte QSettings zu ändern, und räumt Übersetzer ab."""

  def _set(value):
    monkeypatch.setattr(i18n, "language_setting", lambda: value)
    return i18n.install_translators(QApplication.instance())

  yield _set
  for translator in i18n._translators:
    QApplication.instance().removeTranslator(translator)
  i18n._translators.clear()
  QLocale.setDefault(QLocale("en"))


def test_german_override_translates_app_and_qt(ui_lang, qtbot):
  assert ui_lang("de") == "de"

  assert QCoreApplication.translate("SaveAction", "&Save") == "&Speichern"
  # Qt's eigene Übersetzung (Standardknöpfe)
  assert QCoreApplication.translate("QPlatformTheme", "Cancel") == "Abbrechen"

  from app import RosidaApp

  win = RosidaApp()
  qtbot.addWidget(win)
  menus = [a.text() for a in win.menuBar().actions()]
  assert menus[:3] == ["&Datei", "&Bearbeiten", "&Zelle"]


def test_english_needs_no_translator(ui_lang):
  assert ui_lang("en") == "en"
  assert i18n._translators == []
  assert QCoreApplication.translate("SaveAction", "&Save") == "&Save"


def test_system_setting_uses_system_language(ui_lang, monkeypatch):
  monkeypatch.setattr(i18n, "system_language", lambda: "de")
  assert ui_lang(i18n.SYSTEM) == "de"


def test_system_language_falls_back_to_english(monkeypatch):
  class FakeLocale:
    def uiLanguages(self):
      return ["fr-CH", "it"]

  monkeypatch.setattr(i18n.QLocale, "system", staticmethod(lambda: FakeLocale()))
  assert i18n.system_language() == "en"

  FakeLocale.uiLanguages = lambda self: ["fr-CH", "de-CH", "en"]
  assert i18n.system_language() == "de"


def test_document_language_from_frontmatter(monkeypatch):
  monkeypatch.setattr("exporters.terms.ui_language", lambda: "en")
  assert document_language({"lang": "de-CH"}) == "de"
  assert document_language({"lang": "fr"}) == "en"
  assert document_language({}) == "en"


def test_all_texts_are_translated():
  """Nach `just i18n` darf nichts unübersetzt bleiben."""
  unfinished = [
    msg.findtext("source")
    for msg in ET.parse(TS_FILE).getroot().iter("message")
    if msg.find("translation").get("type") == "unfinished"
  ]
  assert unfinished == []


def test_english_document_exports_english_terms(rosida_win, tmp_path, wait_idle):
  docs = Path(__file__).resolve().parent.parent / "docs"
  rosida_win.current_filepath = str(docs / "example.md")
  doc = rosida_win.doc
  doc.frontmatter_cell.editor.setPlainText("title: T\nlang: en\nbibliography: example.bib")
  doc.cells[0].editor.setPlainText("As shown by [@wohlenberg_3_2023].")
  wait_idle(doc)

  out = tmp_path / "out.html"
  doc.export_html(str(out))
  page = out.read_text(encoding="utf-8")

  assert '<html lang="en">' in page
  assert '<h2 id="references">References</h2>' in page
  assert "(accessed 2023-03-25)" in page
  assert '"copy": "Copy"' in page


def test_manual_follows_ui_language(monkeypatch):
  import actions.help as help_module

  monkeypatch.setattr(help_module, "ui_language", lambda: "en")
  assert help_module._find_quickstart_path().name == "quickstart.en.md"
  monkeypatch.setattr(help_module, "ui_language", lambda: "de")
  assert help_module._find_quickstart_path().name == "quickstart.md"
