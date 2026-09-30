"""Screenshots aller Rosida-Komponenten, z.B. für Doku und Release-Notes.

Aufruf (nutzt nur die Projekt-.venv):

    uv run scripts/screenshots.py [DOKUMENT] [--out DIR] [--lang en|de] [--size 1400x900] [--show]

Ablauf: Dokument laden (Standard: docs/example.md), alle Zellen berechnen,
dann Hauptfenster, Dokumenteigenschaften, Dokumentende, Editor der letzten
Zelle sowie jedes Dock, die Toolbar, Menü- und Statusleiste einzeln.

Isoliert: Rosida läuft mit temporären QSettings (keine Änderung an echten
Einstellungen, zuletzt geöffneten Dateien oder Fenstergeometrie) und
standardmäßig offscreen, also ohne sichtbares Fenster.
"""

import argparse
import os
from pathlib import Path
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("document", nargs="?", default=REPO / "docs" / "example.md", type=Path)
    parser.add_argument("--out", default=REPO / "out" / "screenshots", type=Path)
    parser.add_argument("--lang", default="de", choices=["de", "en"], help="Sprache der Oberfläche")
    parser.add_argument("--size", default="1400x900", help="Fenstergröße, z.B. 1400x900")
    parser.add_argument("--timeout", default=120, type=int, help="max. Sekunden fürs Rechnen")
    parser.add_argument("--show", action="store_true", help="echtes Fenster statt offscreen")
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.show:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PySide6.QtCore import QEventLoop, QPoint, QSettings, QTimer
    from PySide6.QtWidgets import QApplication, QDockWidget, QToolBar

    # Vor dem ersten QSettings-Zugriff: alles in ein Wegwerf-Verzeichnis
    settings_dir = tempfile.TemporaryDirectory(prefix="rosida-screenshots-")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, settings_dir.name)

    app = QApplication(["Rosida"])
    app.setOrganizationDomain("kroesch.ch")
    app.setApplicationName("Rosida")

    from config.i18n import install_translators, set_language_setting

    set_language_setting(args.lang)
    install_translators(app)

    from app import RosidaApp, load_application_fonts

    load_application_fonts()

    def wait(ms: int = 150):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    failures = []

    def shot(widget, name: str, rect=None):
        wait()
        path = out / f"{name}.png"
        # Ausschnitt nur, wenn er gültig ist und im Widget liegt
        if rect is not None:
            rect = rect.intersected(widget.rect())
        image = widget.grab(rect) if rect is not None and not rect.isEmpty() else widget.grab()
        if image.isNull() or not image.save(str(path)):
            failures.append(name)
            print(f"  FEHLER: {name} konnte nicht aufgenommen werden")
            return
        print(f"  {path.relative_to(REPO) if path.is_relative_to(REPO) else path}")

    document = args.document.resolve()
    print(f"Lade {document}")
    # Pfad schon beim Start setzen: Relative Bilder werden beim Laden gerendert
    win = RosidaApp(initial_filepath=str(document))
    width, height = (int(v) for v in args.size.lower().split("x"))
    win.resize(width, height)
    win.show()
    wait(300)

    # 1) Alle Zellen berechnen und warten, bis der Kernel fertig ist
    doc = win.doc
    win.act_run_all.trigger()
    deadline = time.monotonic() + args.timeout
    while doc.kernel.is_busy():
        if time.monotonic() > deadline:
            sys.exit(f"Abbruch: Zellen nach {args.timeout} s noch nicht fertig berechnet")
        wait(100)
    wait(500)
    print("Screenshots:")

    # 2) Hauptanwendung
    scroll = win.scroll.verticalScrollBar()
    scroll.setValue(0)
    shot(win, "01_main")

    # 3) Dokumenteigenschaften (Frontmatter-Editor) aufgeklappt
    doc.frontmatter_cell.expand()
    win.scroll.ensureWidgetVisible(doc.frontmatter_cell)
    shot(win, "02_properties")
    doc.frontmatter_cell.collapse()  # ohne die Eigenschaften neu zu übernehmen

    # 4) Ende des Dokuments
    scroll.setValue(scroll.maximum())
    shot(win, "03_end")

    # 5) Editor der letzten nichtleeren Zelle
    filled = [c for c in doc.cells if c.editor.toPlainText().strip()]
    if filled:
        cell = filled[-1]
        cell.switch_to_edit()
        wait()
        # Anfang der Zelle zeigen, auch wenn sie höher als das Fenster ist
        scroll.setValue(cell.mapTo(doc, QPoint(0, 0)).y() - 40)
        shot(win, "04_editor")
        shot(cell, "04_editor_cell")
        cell.cancel_edit()

    # 6) Docks, Toolbar, Menü- und Statusleiste einzeln
    for dock in win.findChildren(QDockWidget):
        dock.show()
        dock.raise_()  # falls als Tab gestapelt
        shot(dock, f"dock_{dock.objectName() or type(dock).__name__}")
    for index, toolbar in enumerate(win.findChildren(QToolBar)):
        # Auf die Knöpfe zuschneiden statt der ganzen Fensterbreite
        crop = toolbar.childrenRect().adjusted(-6, -4, 6, 4)
        shot(toolbar, f"toolbar_{toolbar.objectName() or index}", crop)
    menubar = win.menuBar()
    # Menüeinträge sind keine Kind-Widgets: Ausschnitt aus ihren Positionen
    entries = [menubar.actionGeometry(a) for a in menubar.actions()]
    crop = entries[0].united(entries[-1]).adjusted(-4, 0, 8, 0) if entries else None
    shot(menubar, "menubar", crop)
    shot(win.statusBar(), "statusbar")

    doc.set_modified(False)  # kein "Änderungen speichern?"-Dialog
    win.close()
    settings_dir.cleanup()
    print(f"Fertig: {out}")
    if failures:
        sys.exit(f"{len(failures)} Aufnahme(n) fehlgeschlagen: {', '.join(failures)}")


if __name__ == "__main__":
    main()
