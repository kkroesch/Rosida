"""Kleiner BibTeX-Leser und Autor-Jahr-Formatierung für den HTML-Export.

Kein vollständiger BibTeX-Parser, aber robust gegenüber dem, was Zotero,
JabRef & Co. schreiben: verschachtelte Klammern, "..."-Werte, #-Verkettung,
Monats-Makros und die üblichen LaTeX-Maskierungen.
"""

from dataclasses import dataclass, field
import html
from pathlib import Path
import re
import unicodedata

from exporters.terms import format_date, terms

# Pandoc/Quarto-Zitierschlüssel: beginnt und endet mit Wortzeichen,
# dazwischen ist auch interne Interpunktion erlaubt.
CITE_KEY = r"[\w](?:[\w:.#$%&+?<>~/-]*[\w])?"

_MONTHS = {
    m: str(i)
    for i, m in enumerate(
        "jan feb mar apr may jun jul aug sep oct nov dec".split(), start=1
    )
}

# Akzent-Befehle -> kombinierende Unicode-Zeichen (danach NFC-normalisiert)
_ACCENTS = {
    '"': "\u0308",
    "'": "\u0301",
    "`": "\u0300",
    "^": "\u0302",
    "~": "\u0303",
    "=": "\u0304",
    ".": "\u0307",
    "c": "\u0327",
    "v": "\u030c",
    "u": "\u0306",
    "H": "\u030b",
    "k": "\u0328",
}
_SYMBOLS = {
    "ss": "ß",
    "o": "ø",
    "O": "Ø",
    "aa": "å",
    "AA": "Å",
    "ae": "æ",
    "AE": "Æ",
    "oe": "œ",
    "OE": "Œ",
    "l": "ł",
    "L": "Ł",
    "i": "ı",
    "textbar": "|",
    "textendash": "–",
    "textemdash": "—",
    "textquoteright": "’",
    "textquoteleft": "‘",
    "textquotedblleft": "“",
    "textquotedblright": "”",
    "textasciitilde": "~",
    "textunderscore": "_",
    "textbackslash": "\\",
    "LaTeX": "LaTeX",
    "TeX": "TeX",
    "dots": "…",
    "ldots": "…",
}


@dataclass
class BibEntry:
    type: str
    key: str
    fields: dict[str, str] = field(default_factory=dict)

    def get(self, name: str) -> str:
        """Field as plain text (LaTeX markup resolved)."""
        return latex_to_text(self.fields.get(name, ""))

    @property
    def url(self) -> str:
        # URLs nur entmaskieren, ~ und -- sind hier keine Typografie
        raw = self.fields.get("url", "")
        raw = re.sub(r"\\url\{(.*)\}", r"\1", raw.strip())
        return re.sub(r"\\([_%&#$])", r"\1", raw).strip("{}")

    @property
    def year(self) -> str:
        """Year, or "" if unknown (callers print the localized "n.d.")."""
        return self.get("year") or self.get("date")[:4]

    @property
    def authors(self) -> list[str]:
        raw = self.fields.get("author") or self.fields.get("editor") or ""
        return [latex_to_text(a) for a in _split_names(raw)]


def _split_names(raw: str) -> list[str]:
    """Splits "A and B" on 'and' outside braces ({Firma and Co} bleibt ganz)."""
    names, depth, start, i = [], 0, 0, 0
    while i < len(raw):
        ch = raw[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0 and raw[i : i + 5].lower() == " and ":
            names.append(raw[start:i].strip())
            start = i = i + 5
            continue
        i += 1
    names.append(raw[start:].strip())
    return [n for n in names if n]


def latex_to_text(value: str) -> str:
    """Resolves common LaTeX markup in BibTeX values to plain Unicode text."""
    s = value

    def accent(m):
        return m.group(2) + _ACCENTS[m.group(1)]

    s = re.sub(r"\\([\"'`^~=.])\s*\{?\s*([A-Za-z])\}?", accent, s)
    s = re.sub(r"\\([cvuHk])\s*\{\s*([A-Za-z])\s*\}", accent, s)
    s = re.sub(r"\\([cvuHk])\s+([A-Za-z])", accent, s)
    s = re.sub(
        r"\\([A-Za-z]+)\b\s*(?:\{\})?",
        lambda m: _SYMBOLS.get(m.group(1), m.group(0)),
        s,
    )
    s = re.sub(r"\\([&%$#_{}])", r"\1", s)
    s = re.sub(r"\\href\s*\{[^{}]*\}\s*\{([^{}]*)\}", r"\1", s)
    # \emph{x}, \textit{x}, \url{x}, ... -> x (von innen nach außen)
    while True:
        new = re.sub(r"\\[A-Za-z]+\s*\{([^{}]*)\}", r"\1", s)
        if new == s:
            break
        s = new
    s = re.sub(r"\\[A-Za-z]+", "", s)
    s = s.replace("{", "").replace("}", "")
    s = s.replace("---", "—").replace("--", "–").replace("~", "\u00a0")
    s = re.sub(r"\s+", " ", s).strip()
    return unicodedata.normalize("NFC", s)


class _Reader:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0

    def skip_ws(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t\r\n,":
            self.pos += 1

    def braced(self) -> str:
        """Reads {...} with nested braces, returns the inside."""
        depth, start = 0, self.pos
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == "\\":
                self.pos += 2
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    self.pos += 1
                    return self.text[start + 1 : self.pos - 1]
            self.pos += 1
        return self.text[start + 1 :]

    def quoted(self) -> str:
        depth, start = 0, self.pos + 1
        self.pos += 1
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == "\\":
                self.pos += 2
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif ch == '"' and depth == 0:
                self.pos += 1
                return self.text[start : self.pos - 1]
            self.pos += 1
        return self.text[start:]

    def value(self, strings: dict[str, str]) -> str:
        parts = []
        while True:
            self.skip_ws_only()
            ch = self.text[self.pos : self.pos + 1]
            if ch == "{":
                parts.append(self.braced())
            elif ch == '"':
                parts.append(self.quoted())
            else:
                m = re.compile(r"[^\s,#}]+").match(self.text, self.pos)
                if not m:
                    break
                word = m.group(0)
                self.pos = m.end()
                parts.append(strings.get(word.lower(), _MONTHS.get(word.lower(), word)))
            self.skip_ws_only()
            if self.text[self.pos : self.pos + 1] == "#":
                self.pos += 1
                continue
            break
        return "".join(parts)

    def skip_ws_only(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t\r\n":
            self.pos += 1


def parse_bibtex(text: str) -> dict[str, BibEntry]:
    """Parses BibTeX source into entries by citation key."""
    entries: dict[str, BibEntry] = {}
    strings: dict[str, str] = {}
    reader = _Reader(text)
    head = re.compile(r"@\s*(\w+)\s*[{(]")
    while True:
        m = head.search(text, reader.pos)
        if not m:
            break
        kind = m.group(1).lower()
        reader.pos = m.end() - 1
        if kind in ("comment", "preamble"):
            reader.braced()
            continue
        inner = _Reader(reader.braced())

        if kind == "string":
            name_m = re.match(r"\s*(\w+)\s*=\s*", inner.text)
            if name_m:
                inner.pos = name_m.end()
                strings[name_m.group(1).lower()] = inner.value(strings)
            continue

        key_m = re.match(r"\s*([^,\s]+)\s*,", inner.text)
        if not key_m:
            continue
        entry = BibEntry(kind, key_m.group(1))
        inner.pos = key_m.end()
        while True:
            inner.skip_ws()
            name_m = re.compile(r"([\w-]+)\s*=\s*").match(inner.text, inner.pos)
            if not name_m:
                break
            inner.pos = name_m.end()
            name = name_m.group(1).lower()
            value = inner.value(strings)
            # Doppelte Felder (z.B. mehrere annote) nicht überschreiben
            entry.fields.setdefault(name, value)
        entries[entry.key] = entry
    return entries


def bibliography_files(properties: dict, base_dir: Path) -> list[Path]:
    """The .bib files named in the frontmatter (string or list), relative to base_dir."""
    value = properties.get("bibliography") or []
    names = [value] if isinstance(value, str) else [str(v) for v in value]
    return [base_dir / Path(name).expanduser() for name in names]


def load_bibliography(files: list[Path]) -> dict[str, BibEntry]:
    entries: dict[str, BibEntry] = {}
    for f in files:
        try:
            entries.update(parse_bibtex(f.read_text(encoding="utf-8")))
        except OSError:
            continue
    return entries


# --- Autor-Jahr-Formatierung -------------------------------------------------


def _family(name: str) -> str:
    """Nachname aus "Nachname, Vorname" oder "Vorname Nachname"."""
    if "," in name:
        return name.split(",")[0].strip()
    parts = name.split()
    return parts[-1] if parts else name


def _year(entry: BibEntry, lang: str) -> str:
    return entry.year or terms(lang)["no_year"]


def cite_label(entry: BibEntry, lang: str = "de") -> str:
    """Author part of an in-text citation: "Pleger", "Freiknecht und Papp", "Gutman et al."."""
    names = [_family(a) for a in entry.authors]
    if not names:
        title = entry.get("shorttitle") or entry.get("title")
        opening, closing = terms(lang)["quotes"]
        return f"{opening}{title}{closing}"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} {terms(lang)['and']} {names[1]}"
    return f"{names[0]} et al."


def sort_key(entry: BibEntry) -> tuple:
    first = entry.authors[0] if entry.authors else entry.get("title")
    return (_family(first).casefold(), entry.year, entry.get("title").casefold())


def _sentence(text: str) -> str:
    """Appends a full stop unless the text already ends with punctuation."""
    return text if re.search(r"[.!?]\s*(</em>)?$", text) else f"{text}."


def reference_html(entry: BibEntry, lang: str = "de") -> str:
    """One bibliography entry, roughly in author-date style."""
    e = lambda s: html.escape(s, quote=False)  # noqa: E731
    t = terms(lang)
    year = _year(entry, lang)
    parts = []
    authors = "; ".join(entry.authors)
    title = entry.get("title")
    container = (
        entry.get("journal") or entry.get("booktitle") or entry.get("howpublished")
    )
    in_container = entry.type in ("article", "inproceedings", "incollection") or (
        container and entry.type != "book"
    )

    if authors:
        parts.append(f"{e(authors)} ({e(year)}):")
        title_html = e(title) if in_container else f"<em>{e(title)}</em>"
        parts.append(_sentence(title_html))
    else:
        parts.append(f"{_sentence(f'<em>{e(title)}</em>')[:-1]} ({e(year)}).")

    if container:
        details = [f"<em>{e(container)}</em>"]
        volume, number = entry.get("volume"), entry.get("number")
        if volume and number and volume != entry.year:
            details.append(f"{e(volume)} ({e(number)})")
        elif number:
            details.append(f"{t['number']} {e(number)}")
        elif volume and volume != entry.year:
            details.append(e(volume))
        if entry.get("pages"):
            details.append(f"{t['pages']} {e(entry.get('pages'))}")
        parts.append(_sentence(", ".join(details)))

    for name in ("series", "edition", "publisher", "address"):
        if entry.get(name) and not (name == "publisher" and in_container):
            parts.append(_sentence(e(entry.get(name))))

    doi = entry.get("doi")
    url = f"https://doi.org/{doi}" if doi else entry.url
    if url:
        link = f'<a href="{html.escape(url)}">{e(url)}</a>'
        if entry.get("urldate"):
            accessed = format_date(entry.get("urldate"), lang)
            link += f" ({e(t['accessed'].format(accessed))})"
        parts.append(link)

    return " ".join(parts)


class Citations:
    """Renders Quarto citations for markdown_to_html(cite=...) and collects the used entries."""

    def __init__(self, entries: dict[str, BibEntry], lang: str = "de"):
        self.entries = entries
        self.lang = lang
        self.used: dict[str, BibEntry] = {}

    def _link(self, entry: BibEntry, text: str) -> str:
        self.used.setdefault(entry.key, entry)
        return (
            f'<a class="cite" href="#ref-{html.escape(entry.key)}">'
            f"{html.escape(text)}</a>"
        )

    def __call__(self, text: str, narrative: bool) -> str | None:
        if narrative:
            entry = self.entries.get(text)
            if entry is None:
                return None  # z.B. @decorator im Fließtext
            label = f"{cite_label(entry, self.lang)} ({_year(entry, self.lang)})"
            return f'<span class="citation">{self._link(entry, label)}</span>'

        items = []
        for part in text.split(";"):
            # @ nur am Anfang oder nach Leerraum: [mail@example.com] ist kein Zitat
            m = re.match(rf"^\s*(.*?\s)?(-?)@({CITE_KEY})(.*)$", part, re.S)
            if not m:
                return None
            prefix, suppress, key, rest = m.groups()
            locator = rest.strip().lstrip(",").strip()
            entry = self.entries.get(key)
            if entry is None:
                ref = f'<span class="unknown">?{html.escape(key)}</span>'
            elif suppress:
                ref = self._link(entry, _year(entry, self.lang))
            else:
                ref = self._link(
                    entry, f"{cite_label(entry, self.lang)} {_year(entry, self.lang)}"
                )
            if prefix and prefix.strip():
                ref = f"{html.escape(prefix.strip())} {ref}"
            if locator:
                ref += f", {html.escape(locator)}"
            items.append(ref)
        return f'<span class="citation">({"; ".join(items)})</span>'

    def references_html(self, heading: str | None = None) -> str:
        """The cited entries as a list, sorted by author and year."""
        if not self.used:
            return ""
        heading = heading or terms(self.lang)["references"]
        items = "\n".join(
            f'<li id="ref-{html.escape(e.key)}">{reference_html(e, self.lang)}</li>'
            for e in sorted(self.used.values(), key=sort_key)
        )
        return (
            f'<section class="references">\n<h2 id="references">{html.escape(heading)}</h2>\n'
            f"<ul>\n{items}\n</ul>\n</section>"
        )
