# Rosida

Rosida ist eine leichtgewichtige, native mathematische Notizbuch-Umgebung für macOS und Linux, entwickelt mit Python und PySide6 (Qt6).

Statt schwerfällige Web-Engines (Chromium/Electron) oder unlesbare proprietäre JSON-Formate (`.ipynb`) zu nutzen, setzt Rosida auf **reines Markdown (`.md`) als natives Speicherformat**, eine direkte In-Memory-Berechnung via SymPy/NumPy/Polars und eine ruhige, reaktionsschnelle Benutzeroberfläche im Papier-Stil.

Eine ausführlichere Einführung mit Beispielen (Python, NumPy, Matplotlib, SymPy, Polars) findest du in [docs/quickstart.md](docs/quickstart.md).

---

## Kernmerkmale

* **Natives Markdown als Dokumentenformat:** Notizbücher werden als reguläre `.md`-Dateien gespeichert. Code-Zellen sind gewöhnliche Fenced Code Blocks (` ```python ... ``` `), mehrere Text-Zellen werden durch `---` getrennt. Vollständige Git-Diff-Kompatibilität ohne Merge-Konflikte.
* **Keine Web-Engine:** Formeln (`$...$` und `$$...$$`) werden direkt über Matplotlibs interne `mathtext`-Engine in hochauflösende Vektoren bzw. HiDPI-Grafiken übersetzt und nativ in Qt gerendert.
* **In-Place Cell Editing:** Nahtloses Umschalten zwischen editierbarem Quelltext und formatierter Ausgabe ohne störende Layout-Sprünge. Zellen ohne sichtbare Ausgabe (reine Imports/Zuweisungen) kollabieren auf ein kompaktes Klick-Icon statt Platz zu verschwenden.
* **Symbolik & Numerik:** Automatisches Auswerten von SymPy-Ausdrücken (inklusive gerenderter Formelausgabe), NumPy-Berechnungen, Einbetten nativer Matplotlib-Canvas-Plots sowie interaktiver Polars-`DataFrame`-Tabellen.
* **`{{ ausdruck }}`-Live-Templating:** In Text-Zellen wird `{{ ... }}` im gemeinsamen Zellen-Namespace ausgewertet – SymPy-Ergebnisse werden automatisch zu LaTeX, alles andere zu Text.
* **Gleitende Modus-Erkennung:** Automatische Unterscheidung zwischen Markdown-Text und ausführbarem Python-Code je Zelle (Auto/Python/Text, umschaltbar).
* **LaTeX- & Quarto-Kürzelpalette:** Einklappbare Akkordeon-Seitenleiste mit mathematischen Operatoren, griechischen Buchstaben, Kalkül- und Matrix-Kürzeln sowie Quarto-Callouts, Fußnoten- und Cross-Reference-Bausteinen für den schnellen Einschub.
* **Dokumentstruktur-Übersicht:** Einklappbare Gliederungs-Seitenleiste aus den Überschriften und Zellen des Dokuments, Klick springt direkt zur Zelle.
* **Export:** Verlustfreier Vektor-PDF-Druck sowie Export als Quarto-Dokument (`.qmd`, inkl. ausgewerteter `{{ }}`-Ausdrücke, Tabellen und Grafiken) direkt aus dem Dokument.

---

## Dateiformat-Spezifikation

Rosida-Notizbücher sind standardkonformes CommonMark:

````markdown
# Harmonischer Oszillator

Untersuchung der gedämpften Schwingung für $f(t) = e^{-\gamma t} \cos(\omega t)$.

---

```python
import sympy as sp

t, gamma, omega = sp.symbols('t gamma omega', positive=True)
f = sp.exp(-gamma * t) * sp.cos(omega * t)
sp.diff(f, t)
```
````

---

## Installation & Start

### Voraussetzungen

* Python 3.11+
* Paketmanager [`uv`](https://github.com/astral-sh/uv) (empfohlen)

### Entwicklungsumgebung starten

Repository klonen und Rosida direkt im isolierten Environment ausführen:

```bash
git clone https://github.com/dein-user/rosida.git
cd rosida

just run
```

`just run` startet `src/app.py` via `uv run` mit allen benötigten Paketen (PySide6, SymPy, NumPy, Matplotlib, Polars, qtawesome) – ohne manuelle venv-Verwaltung. Äquivalent von Hand:

```bash
uv run --with pyside6 --with polars --with sympy --with matplotlib --with numpy --with qtawesome \
  src/app.py
```

Optional kann eine Datei direkt übergeben werden:

```bash
uv run --with pyside6 --with polars --with sympy --with matplotlib --with numpy --with qtawesome \
  src/app.py beispiel.md
```

---

## Plattform-Builds

### macOS App-Bundle (`Rosida.app`)

`build/macos/Justfile` baut ein in sich geschlossenes, signiertes macOS-Bundle mit eigener Python-Runtime und Rhodonea-Icon. Wegen eines Pfadauflösungs-Problems bei `justfile_directory()` in Just-Modulen **muss der Build aktuell aus dem `build/macos`-Verzeichnis heraus** gestartet werden (nicht über `just macos ...` vom Repo-Root aus):

```bash
cd build/macos

# Nur das App-Bundle bauen (unsigniert, ohne DMG)
just macapp

# Vollständiger Release-Build: Bundle + Runtime + Signierung + DMG + Notarisierung
just build
```

Das fertige Bundle liegt danach unter `build/macos/dist/Rosida.app`:

```bash
open build/macos/dist/Rosida.app
```

### Linux Flatpak

Ein Flatpak-Manifest liegt unter `build/linux/flatpak/net.kroesch.rosida.yaml` (App-ID `ch.kroesch.rosida`, KDE-Plattform/Qt 6):

```bash
# Flatpak bauen und installieren
flatpak-builder --user --install --force-clean build-dir build/linux/flatpak/net.kroesch.rosida.yaml

# Ausführen
flatpak run ch.kroesch.rosida
```

> **Hinweis:** Das Manifest installiert aktuell nur den historischen Flat-Layout-Stand (`rosida_app.py`, `document.py`, ohne Polars/qtawesome) und muss vor dem nächsten Release noch an die aktuelle `src/`-Paketstruktur und die vollständige Abhängigkeitsliste angepasst werden.

---

## Architektur

Die Architektur folgt modularen Prinzipien zur klaren Trennung von Darstellung, Persistenz und Ausführung (alles unter `src/`):

* **`app.py`:** Orchestrierung des Desktop-Fensters (Menüs, Symbolleiste, Docks, Statusleiste) – `RosidaApp`.
* **`document.py`:** Dokument-Aggregat (`DocumentCanvas`) und In-Place-Zell-Controller (`InPlaceCell`) inkl. Markdown-Serialisierung.
* **`actions/`:** Selbstverwaltende `QAction`-Kommandos für Menüs und Toolbar, gruppiert nach Domäne (`file.py`, `edit.py`, `cell.py`, `view.py`) sowie die `QUndoCommand`-Klassen für Zellen-Einfügen/-Löschen.
* **`docks/`:** Einklappbare Seitenleisten-Widgets – `latex.py` (LaTeX-/Quarto-Kürzelpalette) und `structure_outline.py` (Dokumentstruktur).
* **`widgets/`:** Eigenständige UI-Bausteine der Zelle (`inline_editor.py`, `resize_grip.py`, `clickable_frame.py`, `math_text.py` für Formel-Rendering & `{{ }}`-Templating) sowie `data.py` (Polars-Tabellen-Widget).
* **`exporters/`:** Reine Export-Funktionen, entkoppelt von der UI – `pdf.py` (Vektor-PDF) und `qmd.py` (Quarto-Renderer).
* **`docs/adr.md`:** Dokumentation aller architektonischen Richtungsentscheidungen (ADRs).
* **`docs/quickstart.md`:** Kurzanleitung mit Beispielen für Einsteiger.

---

## Lizenz

MIT License. Frei für akademische, private und kommerzielle Nutzung.
