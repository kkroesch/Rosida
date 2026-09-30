"""Sprache der Oberfläche: Systemsprache oder Override aus den Einstellungen.

Die Texte im Code sind englisch (Qt-Konvention); Übersetzungen liegen als
Qt-Linguist-Dateien in assets/i18n (rosida_<lang>.ts, kompiliert .qm).
Aktualisieren mit `just i18n`.
"""

from PySide6.QtCore import QLibraryInfo, QLocale, QSettings, QTranslator

from config.settings import ASSETS_DIR

LANGUAGE_KEY = "ui/language"
SYSTEM = "system"
DEFAULT_LANGUAGE = "en"

# Sprachcode -> Name in der jeweiligen Sprache (für die Auswahl im Dialog)
LANGUAGES = {"en": "English", "de": "Deutsch"}

I18N_DIR = ASSETS_DIR / "i18n"

# Referenzen halten: Ein vom Garbage Collector entsorgter QTranslator
# nimmt seine Übersetzungen mit.
_translators: list[QTranslator] = []


def language_setting() -> str:
    """The stored choice: "system" or a language code."""
    value = str(QSettings().value(LANGUAGE_KEY, SYSTEM))
    return value if value in LANGUAGES else SYSTEM


def set_language_setting(value: str) -> None:
    QSettings().setValue(LANGUAGE_KEY, value if value in LANGUAGES else SYSTEM)


def system_language() -> str:
    """First supported language from the system's UI language list, else English."""
    for name in QLocale.system().uiLanguages():
        code = name.replace("_", "-").split("-")[0].lower()
        if code in LANGUAGES:
            return code
    return DEFAULT_LANGUAGE


def ui_language() -> str:
    """Language actually used for the user interface."""
    setting = language_setting()
    return system_language() if setting == SYSTEM else setting


def install_translators(app) -> str:
    """Loads Qt's own and Rosida's translations for the UI language; returns its code.

    Must run before any window is created: texts are translated when widgets
    are built, a later change needs a restart.
    """
    lang = ui_language()
    QLocale.setDefault(QLocale(lang))
    if lang == DEFAULT_LANGUAGE:
        return lang  # Quellsprache, nichts zu laden

    qt_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for name, directory in ((f"qtbase_{lang}", qt_dir), (f"rosida_{lang}", str(I18N_DIR))):
        translator = QTranslator(app)
        if translator.load(name, directory):
            app.installTranslator(translator)
            _translators.append(translator)
    return lang
