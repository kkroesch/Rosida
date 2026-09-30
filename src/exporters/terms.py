"""Sprachabhängige Begriffe in exportierten Dokumenten.

Exporte folgen der Sprache des Dokuments (`lang:` in der Frontmatter, wie bei
Quarto), nicht der Oberfläche: Ein deutsches Dokument bekommt "Quellen"
auch dann, wenn Rosida englisch läuft.
"""

from datetime import date

from config.i18n import ui_language

TERMS: dict[str, dict] = {
    "en": {
        "references": "References",
        "and": "and",
        "no_year": "n.d.",
        "number": "no.",
        "pages": "p.",
        "accessed": "accessed {0}",
        "copy": "Copy",
        "copied": "Copied",
        "copy_code": "Copy code",
        "quotes": ("“", "”"),
    },
    "de": {
        "references": "Quellen",
        "and": "und",
        "no_year": "o. J.",
        "number": "Nr.",
        "pages": "S.",
        "accessed": "abgerufen am {0}",
        "copy": "Kopieren",
        "copied": "Kopiert",
        "copy_code": "Code kopieren",
        "quotes": ("„", "“"),
    },
}


def document_language(properties: dict) -> str:
    """Language code from the frontmatter's lang (e.g. "de-CH" -> "de"), else the UI language."""
    lang = str(properties.get("lang") or ui_language())
    code = lang.replace("_", "-").split("-")[0].lower()
    return code if code in TERMS else "en"


def terms(lang: str) -> dict:
    return TERMS.get(lang, TERMS["en"])


def format_date(iso: str, lang: str) -> str:
    """9.10.2023 in German, 2023-10-09 otherwise; unparsable values unchanged."""
    try:
        d = date.fromisoformat(iso[:10])
    except ValueError:
        return iso
    return f"{d.day}.{d.month}.{d.year}" if lang == "de" else d.isoformat()
