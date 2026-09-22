# Rosida

Rosida ist eine leichtgewichtige, native mathematische Notizbuch-Umgebung für macOS und Linux, entwickelt mit Python und PySide6 (Qt6).

Statt schwerfällige Web-Engines (Chromium/Electron) oder unlesbare proprietäre JSON-Formate (`.ipynb`) zu nutzen, setzt Rosida auf **reines Markdown (`.md`) als natives Speicherformat**, eine direkte In-Memory-Berechnung via SymPy/NumPy und eine ruhige, reaktionsschnelle Benutzeroberfläche im Papier-Stil.

---

## Kernmerkmale

* **Natives Markdown als Dokumentenformat:** Notizbücher werden als reguläre `.md`-Dateien gespeichert. Code-Zellen sind gewöhnliche Fenced Code Blocks (`python ... `), getrennt durch standardisierte Markdown-Trennlinien (`---`). Vollständige Git-Diff-Kompatibilität ohne Merge-Konflikte.
* **Keine Web-Engine:** Formeln (`$...$` und `$$...$$`) werden direkt über Matplotlibs interne `mathtext`-Engine in hochauflösende Vektoren bzw. HiDPI-Grafiken übersetzt und nativ in Qt gerendert.
* **In-Place Cell Editing:** Nahtloses Umschalten zwischen editierbarem Quelltext und formatierter Ausgabe ohne störende Layout-Sprünge.
* **Symbolik & Numerik:** Automatisches Auswerten von SymPy-Ausdrücken (inklusive gerenderter Formelausgabe), NumPy-Berechnungen und Einbetten nativer Matplotlib-Canvas-Plots.
* **Gleitende Modus-Erkennung:** Automatische Unterscheidung zwischen Markdown-Text und ausführbarem Python-Code.
* **LaTeX-Formelpalette:** Einklappbare Akkordeon-Seitenleiste mit mathematischen Operatoren, griechischen Buchstaben, Kalkül- und Matrix-Kürzeln für den schnellen Einschub in Formeln.
* **Export:** Verlustfreier Vektor-PDF-Druck und HTML-Export direkt aus dem Dokument.

---

## Dateiformat-Spezifikation

Rosida-Notizbücher sind standardkonformes CommonMark:

```markdown
# Harmonischer Oszillator

Untersuchung der gedämpften Schwingung für $f(t) = e^{-\gamma t} \cos(\omega t)$.

---

```python
import sympy as sp

t, gamma, omega = sp.symbols('t gamma omega', positive=True)
f = sp.exp(-gamma * t) * sp.cos(omega * t)
sp.diff(f, t)
```

```

---

## Installation & Start

### Voraussetzungen

* Python 3.11+
* Paketmanager [`uv`](https://github.com/astral-sh/uv?utm_source=gemini) (empfohlen) oder `pip`

### Entwicklungsumgebung starten

Repository klonen und Rosida direkt im isolierten Environment ausführen:

```bash
git clone https://github.com/dein-user/rosida.git
cd rosida

# Ausführung via uv
uv run --with pyside6 --with sympy --with matplotlib --with numpy python rosida_app.py

```

Optional kann eine Datei direkt übergeben werden:

```bash
uv run --with pyside6 --with sympy --with matplotlib --with numpy python rosida_app.py beispiel.md

```

---

## Plattform-Builds

### macOS App-Bundle (`Rosida.app`)

Rosida kann als in sich geschlossenes macOS-Bundle mit nativer Menüleiste und Rhodonea-Icon ausgeführt werden:

```bash
# Start über das lokale Launch-Skript
./Rosida.app/Contents/MacOS/launch

# Oder direkt per open
open Rosida.app

```

### Linux Flatpak

Das Manifest `ch.kroesch.rosida.yaml` baut ein Flatpak auf Basis der KDE-Plattform (Qt 6):

```bash
# Flatpak bauen und installieren
flatpak-builder --user --install --force-clean build-dir ch.kroesch.rosida.yaml

# Ausführen
flatpak run ch.kroesch.rosida

```

---

## Architektur

Die Architektur folgt modularen Prinzipien zur klaren Trennung von Darstellung, Persistenz und Ausführung:

* **`rosida_app.py`:** Orchestrierung des Desktop-Fensters (Menüs, Symbolleiste, Docks, Statusleiste).
* **`document.py`:** Dokument-Aggregat (`DocumentCanvas`), In-Place-Zell-Controller (`InPlaceCell`) und Markdown-Serializer.
* **`actions/`:** Wiederverwendbare, selbstverwaltende `QAction`-Klassen für Menüs, Toolbars und In-Document-Buttons.
* **`latex_palette.py`:** Einklappbares Werkzeugdock für Formelkürzel.
* **`Architecture_Decisions.md`:** Dokumentation aller architektonischen Richtungsentscheidungen (ADRs).

---

## Lizenz

MIT License. Frei für akademische, private und kommerzielle Nutzung.
