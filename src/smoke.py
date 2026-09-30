"""Rauchtest für die App-Pakete: `Rosida --smoke-test [dokument.md]`.

Startet das Hauptfenster, prüft, ob alle mitgelieferten Dateien gefunden werden
(Schriften, Übersetzungen, Handbuch, Logo) und ob die dynamisch geladenen
Pakete (Markdown-Erweiterungen, ziamath-Schriften, Pygments) funktionieren.
Mit Dokument wird es geladen, berechnet und nach HTML und PDF exportiert.
Exit-Code 0, wenn alles klappt; die Ergebnisse stehen auf stderr (die
Windows-Version hat kein Konsolenfenster, deshalb zusätzlich in
$ROSIDA_SMOKE_LOG, falls gesetzt).

Die Einstellungen landen in einem temporären Verzeichnis, damit der Test
weder echte Einstellungen liest noch den Erststart-Dialog auslöst.
"""

import os
import sys
import tempfile
import traceback
from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QLibraryInfo, QSettings, QTimer, QTranslator

FLAG = "--smoke-test"
TIMEOUT_MS = 120_000

_lines: list[str] = []
_errors: list[str] = []


def requested() -> bool:
    return FLAG in sys.argv


def strip_flag() -> None:
    sys.argv = [a for a in sys.argv if a != FLAG]


def isolate_settings() -> None:
    """Vor der QApplication aufrufen: Einstellungen in ein Wegwerf-Verzeichnis."""
    tmp = tempfile.mkdtemp(prefix="rosida-smoke-")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tmp)

    def hook(exc_type, exc, tb):
        _fail("Exception: " + "".join(traceback.format_exception(exc_type, exc, tb)))

    sys.excepthook = hook


def _log(line: str) -> None:
    _lines.append(line)
    if sys.stderr is not None:
        print(line, file=sys.stderr, flush=True)


def _ok(what: str) -> None:
    _log(f"ok    {what}")


def _fail(what: str) -> None:
    _errors.append(what)
    _log(f"FAIL  {what}")


def _check(what: str, func) -> None:
    try:
        result = func()
    except Exception as exc:  # noqa: BLE001 – jeder Fehler ist ein Testergebnis
        _fail(f"{what}: {exc!r}")
        return
    if result is False:
        _fail(what)
    else:
        _ok(what if result in (None, True) else f"{what}: {result}")


def _static_checks() -> None:
    from actions.help import _find_quickstart_path
    from config.i18n import I18N_DIR
    from config.settings import FONTS_DIR, find_logo
    from widgets.math_svg import latex_to_svg
    from widgets.math_text import markdown_to_html

    _check("Schriften", lambda: len(list(FONTS_DIR.glob("*.ttf"))) or False)
    _check(
        "Übersetzung rosida_de",
        lambda: QTranslator().load("rosida_de", str(I18N_DIR)),
    )
    _check(
        "Übersetzung qtbase_de",
        lambda: QTranslator().load(
            "qtbase_de", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        ),
    )
    _check("Handbuch", lambda: _find_quickstart_path() is not None)
    _check("Logo", lambda: find_logo() is not None)
    _check(
        "Formelsatz (ziamath)",
        lambda: latex_to_svg(r"\frac{a}{b} + \sqrt{x}", 16, True, "#000").width > 0,
    )
    _check(
        "Markdown mit Tabellen und Pygments",
        lambda: "<table>" in markdown_to_html(
            "|a|b|\n|-|-|\n|1|2|\n\n```python\nx = 1\n```\n",
            lambda latex, display: latex,
            highlight=True,
        ),
    )


def _export_checks(win) -> None:
    out = Path(tempfile.mkdtemp(prefix="rosida-smoke-export-"))
    for name, export in (("HTML", win.doc.export_html), ("PDF", win.doc.export_pdf)):
        target = out / f"smoke.{name.lower()}"
        _check(
            f"{name}-Export",
            lambda export=export, target=target: (
                export(str(target)) or target.stat().st_size
            ),
        )


def run(app, win, document: str | None) -> None:
    """Plant die Prüfungen, sobald die Ereignisschleife läuft, und beendet dann die App."""
    _check("Hauptfenster", lambda: win.isVisible())
    _static_checks()

    if document is None:
        QTimer.singleShot(500, app.quit)
        return

    _check("Dokument geladen", lambda: len(win.doc.cells) or False)
    clock = QElapsedTimer()
    clock.start()

    def wait_for_kernel():
        if win.doc.kernel.is_computing():
            if clock.elapsed() > TIMEOUT_MS:
                _fail("Berechnung dauert zu lange")
                app.quit()
            else:
                QTimer.singleShot(200, wait_for_kernel)
            return
        _ok(f"Berechnung ({clock.elapsed()} ms)")
        _export_checks(win)
        app.quit()

    QTimer.singleShot(500, wait_for_kernel)


def exit_code() -> int:
    if _errors:
        _log(f"Rauchtest fehlgeschlagen: {len(_errors)} Fehler")
    else:
        _log("Rauchtest bestanden")
    log_file = os.environ.get("ROSIDA_SMOKE_LOG")
    if log_file:
        Path(log_file).write_text("\n".join(_lines) + "\n", encoding="utf-8")
    return 1 if _errors else 0
