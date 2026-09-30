"""Übersicht aller Architecture Decision Records (docs/adr) als Markdown-Tabelle.

Aufruf (über `just adr-report`):

    uv run scripts/adr_report.py            # schreibt docs/adr/README.md
    uv run scripts/adr_report.py --stdout   # nur ausgeben

Liest die Frontmatter jeder Datei `adr-NNN-*.md` (adr, title, status, date,
author, implemented) und meldet Unstimmigkeiten: fehlende Frontmatter,
Nummer im Dateinamen passt nicht zu `adr:`, Lücken in der Nummerierung.
"""

import argparse
from collections import Counter
from pathlib import Path
import re
import sys

import yaml

REPO = Path(__file__).resolve().parent.parent
ADR_DIR = REPO / "docs" / "adr"
FILE_RE = re.compile(r"^adr-(\d{3})-[\w-]+\.md$")


def read_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    try:
        _, header, _ = text.split("---\n", 2)
        data = yaml.safe_load(header)
    except (ValueError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def collect() -> tuple[list[dict], list[str]]:
    records, problems = [], []
    for path in sorted(ADR_DIR.glob("adr-*.md")):
        match = FILE_RE.match(path.name)
        if not match:
            problems.append(f"`{path.name}`: Dateiname folgt nicht dem Muster `adr-NNN-stichwort.md`")
            continue
        meta = read_frontmatter(path)
        if meta is None:
            problems.append(f"`{path.name}`: keine lesbare Frontmatter")
            continue
        number = int(match.group(1))
        if meta.get("adr") != number:
            problems.append(f"`{path.name}`: `adr: {meta.get('adr')}` passt nicht zur Nummer im Dateinamen")
        for key in ("title", "status"):
            if not meta.get(key):
                problems.append(f"`{path.name}`: `{key}` fehlt")
        records.append({"number": number, "file": path.name, **meta})

    numbers = [r["number"] for r in records]
    if numbers:
        missing = sorted(set(range(1, max(numbers) + 1)) - set(numbers))
        if missing:
            problems.append("Nicht vergebene Nummern: " + ", ".join(f"{n:03d}" for n in missing))
    return records, problems


def cell(value) -> str:
    """Tabellenzelle: leer als Gedankenstrich, | maskiert."""
    return str(value).replace("|", "\\|") if value not in (None, "") else "–"


def render(records: list[dict], problems: list[str]) -> str:
    lines = [
        "---",
        "title: Architecture Decision Records",
        "tags:",
        "  - adr",
        "---",
        "",
        "# Architecture Decision Records",
        "",
        "<!-- Generiert von scripts/adr_report.py (just adr-report), nicht von Hand bearbeiten. -->",
        "",
    ]
    counts = Counter(r.get("status", "–") for r in records)
    summary = ", ".join(f"{status}: {n}" for status, n in sorted(counts.items()))
    lines += [f"{len(records)} Entscheidungen – {summary}.", ""]

    lines += [
        "| ADR | Titel | Status | Implementiert | Datum | Autor |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(records, key=lambda r: r["number"]):
        link = f"[{r['number']:03d}]({r['file']})"
        lines.append(
            f"| {link} | {cell(r.get('title'))} | {cell(r.get('status'))} "
            f"| {cell(r.get('implemented'))} | {cell(r.get('date'))} | {cell(r.get('author'))} |"
        )

    if problems:
        lines += ["", "## Hinweise", ""] + [f"- {p}" for p in problems]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stdout", action="store_true", help="nur ausgeben, nichts schreiben")
    parser.add_argument("--out", type=Path, default=ADR_DIR / "README.md")
    args = parser.parse_args()

    records, problems = collect()
    report = render(records, problems)
    if args.stdout:
        sys.stdout.write(report)
    else:
        args.out.write_text(report, encoding="utf-8")
        print(f"{len(records)} ADRs -> {args.out.relative_to(REPO) if args.out.is_relative_to(REPO) else args.out}")
    for p in problems:
        print(f"Hinweis: {p}", file=sys.stderr)


if __name__ == "__main__":
    main()
