# Metriken-Erklärung

## 1. Größenmetriken (SLOC / LOC / Kommentarzeilen)

- **SLOC** (Source Lines of Code): Zeilen mit echtem Code – Leerzeilen und reine Kommentarzeilen zählen nicht mit.
- **LOC**: alle Zeilen der Datei (inkl. Leerzeilen/Kommentare).
- **Kommentarzeilen**: separat ausgewiesen.

Bei uns: **2191 SLOC** über 21 Dateien, **34 Kommentarzeilen** – das ist bewusst wenig, weil euer Stil explizit auf Kommentare verzichtet außer bei nicht-offensichtlichem WHY. Das ist also kein Makel, sondern Konvention.

**Größte Datei mit Abstand:** `document.py` mit 577 SLOC – mehr als doppelt so groß wie die nächstgrößere (`app.py`, 268). Das ist der Schlüssel zum Verständnis der MI-Ausreißer weiter unten.

## 2. Klassen / Funktionen

Simple `ast`-Zählung – 38 Klassen, 155 Funktionen/Methoden insgesamt. Keine Bewertung, nur Strukturüberblick.

## 3. Zyklomatische Komplexität (McCabe)

**Was:** Zählt unabhängige Pfade durch eine Funktion – jedes `if`, `elif`, `for`, `while`, `except`, `and`/`or` etc. erhöht den Wert um 1 (Startwert 1). Faustregel: hohe Zahl = viele Fallunterscheidungen = schwerer zu testen/verstehen.

**Notenskala** (radon): A=1–5, B=6–10, C=11–20, D=21–30, E=31–40, F=41+.

**Bei uns:** Ø 2.58 → Note **A**, sehr überschaubar im Schnitt. Die Top-10-Ausreißer im Report zeigen, wo es konzentrierter ist:

| Funktion | Wert | Warum vermutlich |
|---|---|---|
| `render_markdown_with_math` | 19 (C) | Markdown-Parser: viele `if/elif` für H1/H2/H3/Zitat, plus Regex-Callback-Funktionen für Block-/Inline-Mathe |
| `InPlaceCell._detect_effective_mode` | 12 (C) | Die Auto-Modus-Erkennung – rät anhand vieler Bedingungen zwischen Python/Markdown |
| `InPlaceCell._render_python_mode` | 11 (C) | Output-Typ-Verzweigung: SymPy/Figure/DataFrame/Sonstiges + Exception-Handling |
| `DocumentCanvas.load_from_markdown` | 11 (C) | Regex-Matching-Schleife beim Datei-Import |

Keine davon ist "gefährlich" (erst ab D/21+ würde ich mir Sorgen machen) – das sind einfach die Stellen mit den meisten Fallunterscheidungen, gute Kandidaten falls ihr mal aufräumen wollt, aber kein akuter Handlungsbedarf.

## 4. Wartbarkeitsindex (MI)

**Was:** Komposit-Formel aus Halstead-Volumen (Vokabular-/Operanden-Komplexität), zyklomatischer Komplexität, LOC und Kommentaranteil – ein grober "wie überschaubar ist diese Datei als Ganzes"-Wert pro Modul.

**Wichtig, wie letztes Mal erklärt:** Trotz 0–100-Darstellung **kein Prozentwert** – Note A beginnt schon bei ~20. Ein MI von 61.9 im Schnitt ist also richtig gut, nicht "60%".

**Bei uns:** Ø 61.9 (A). Genau **eine** Datei fällt aus dem A-Raster: `document.py` mit MI 10.4 (**B**) – nachvollziehbar, weil sie mit 577 SLOC die größte Datei ist und 4 der 10 komplexesten Funktionen enthält (Größe + Komplexität sind die zwei Haupttreiber der Formel). Kein Grund zur Panik, aber falls ihr `document.py` nochmal aufteilen wollt, wäre das der naheliegende Kandidat.

## 5. Ruff-Findings (Lint)

**Was:** `ruff check` mit Default-Regelsatz – schnelle statische Analyse (Stil, Bugs, Sicherheit, Imports).

**Bei uns:** 35 Findings, größtenteils zwei Muster:
- **`BLE001` (13×)** – "blind except" (`except Exception:`) – bewusst so gebaut in euren Actions für robustes Error-Handling bei Dialogen, aber Ruff mahnt zurecht an, dass man besser spezifischer fängt oder loggt.
- **`I001` (10×)** – unsortierte Imports (unser Metrik-Skript selbst hat übrigens auch eins davon, siehe `actions/file.py`).
- Rest sind Einzelfälle (`exec`-Nutzung in der Zellausführung – das ist architekturbedingt notwendig, kein echter Fehler; `QModelIndex()` als Default-Arg; ein `try/except/pass`).

**Notenskala hier ist meine eigene Heuristik** (keine offizielle Norm): Funde pro 1000 SLOC, 35/2191 ≈ 16 → Note **C**. Das ist der einzige nicht auf einem etablierten Standard basierende Wert im Report – bewusst so im Report vermerkt.

## 6. Vulture (toter Code)

**Was:** Findet vermutlich unbenutzten Code (Funktionen/Importe/Methoden ohne erkennbaren Aufrufer), mit Konfidenzwert.

**Bei uns:** 8 Funde, Note A (niedrige Dichte). Aber Vorsicht – **7 von 8 sind vermutlich falsch-positiv**: Qt ruft `paintEvent`, `mouseMoveEvent`, `rowCount`/`columnCount`/`headerData` selbst aus dem Framework auf, Vulture sieht diese Aufrufe aber nicht (steht auch so als Warnhinweis im Report). Der einzige wirklich prüfenswerte Fund: `export_to_qmd` in `exporters/qmd.py:86` – eine Hilfsfunktion, die wahrscheinlich seit dem Umbau auf die `QmdRenderer`-Klasse nicht mehr direkt aufgerufen wird.

Möchtest du, dass ich `export_to_qmd` genauer prüfe und ggf. entferne?
