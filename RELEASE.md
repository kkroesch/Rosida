# Release Notes: Rosida v0.3.0

Alle Änderungen seit v0.2.0.

## Highlights

* **Formelsatz wie in LaTeX:** Formeln werden jetzt mit ziamath in Latin Modern Math gesetzt, passend
  zu den CMU-Schriften, und bleiben im PDF Vektorgrafik. Matrizen, `aligned` und `cases` funktionieren.
* **Rechnen im Hintergrund:** Python-Zellen laufen in einem eigenen Thread, die Oberfläche bleibt
  bedienbar. Eine Zelle zeigt während der Berechnung einen Warteindikator.
* **HTML-Export** mit KaTeX, eingebetteten Schriften und Plots, Syntax-Hervorhebung und Kopier-Knopf.
* **Zitate und Literaturverzeichnis:** `[@key]` wird im PDF- und HTML-Export aufgelöst, die zitierten
  Werke erscheinen unter „Quellen“. Die Literaturdatei kommt aus `bibliography:` in den
  Dokumenteigenschaften.
* **Englische Oberfläche:** Rosida ist jetzt zweisprachig (Deutsch/Englisch), mit Systemsprache als
  Standard und Auswahl in den Einstellungen.

## Formelsatz & Typografie

* **ziamath statt Matplotlib-Mathtext** (ADR 014): Formeln werden als Vektor-Textobjekte gesetzt und
  sitzen auf der Grundlinie des Textes. Mathtext bleibt als Fallback für Ausdrücke, die ziamath nicht
  versteht. Die Formelschrift ist über die Einstellung `render/math_font` wählbar.
* SymPy-Matrizen werden als Formel dargestellt, in der Zelle und in allen Exporten.
* **CMU-Schriften (Computer Modern)** und zugehörige Einstellungen wurden integriert, diverse
  typografische Probleme sind behoben. Die mitgelieferten Schriften werden jetzt tatsächlich aus
  `assets/fonts` geladen und in alle App-Pakete eingebaut.
* Das Stylesheet der Textzellen liegt in den Einstellungen (`render/markdown_css`). Zeilen mit hohen
  Formeln werden nicht mehr gestreckt.

## Markdown & Quarto

* Textzellen werden mit python-markdown gerendert: Tabellen, verschachtelte Listen, Codeblöcke und
  Überschriften-IDs funktionieren jetzt; die alte handgeschriebene Fallunterscheidung ist entfallen.
* **Figures und Callouts** werden als eigene Widgets dargestellt (ADR 008). Callouts
  (`::: {.callout-note}` usw.) und Abbildungen mit `{#fig-…}` funktionieren auch innerhalb von
  Fließtext.
* Erste Quarto-Experimente und ein dediziertes `.qmd`-Beispieldokument liegen bei.

## Rechnen

* **Worker-Thread** (ADR 003, Stufe 1): Zellen werden der Reihe nach im Hintergrund berechnet;
  Textzellen mit `{{ … }}` warten auf die Python-Zellen davor.
* Warteindikator „Wird berechnet …“ bzw. „Wartet …“ in der Zelle; die Statusleiste zeigt, ob der
  Kernel rechnet.
* `print()`-Ausgaben bleiben auch bei einem Fehler sichtbar; der vollständige Traceback steht im
  Tooltip der Fehlermeldung.
* Beim Öffnen berechnete Zellen markieren das Dokument nicht mehr als geändert.

## Export

* **HTML-Export** (`Ctrl+Shift+H`): eine eigenständige Datei. KaTeX setzt die Formeln (per CDN mit
  SRI-Prüfung, ohne Netz bleibt der LaTeX-Quelltext lesbar), CMU-Schriften, Bilder und Plots (SVG)
  sind eingebettet, Codeblöcke haben Syntax-Hervorhebung (Pygments) und einen Kopier-Knopf. Titel,
  Autoren, Datum und Zusammenfassung kommen aus den Dokumenteigenschaften.
* **PDF-Export:** Formeln als Vektorgrafik. Behoben: Bei mehreren Zellen konnten falsche Formeln im
  PDF landen, weil sich gleichnamige Bildressourcen überschrieben.
* **Zitate** in Quarto-Schreibweise (`[@key]`, `[vgl. @a, S. 5; @b]`, `[-@key]`, `@key`) werden im
  PDF- und HTML-Export aufgelöst; die zitierten Werke folgen unter „Quellen“, mit URL bzw. DOI und
  Abrufdatum. Unbekannte Schlüssel werden rot markiert.
* **Quarto-Export:** übernimmt jetzt die Dokumenteigenschaften statt einer festen Frontmatter und
  passt den Pfad zur Literaturdatei an, sodass Quarto sein eigenes Literaturverzeichnis erzeugt.
* Exporte folgen der Dokumentsprache (`lang:` in den Eigenschaften): „Quellen“/„References“,
  Datumsformat, Anführungszeichen.

## Literatur

* **Literatur-Dock** für die Verwaltung von Referenzen; ein Doppelklick fügt `[@key]` ein.
* Die Literaturdatei wird aus `bibliography:` in den Dokumenteigenschaften geladen. Ohne Angabe
  schreibt die Dateiauswahl sie relativ zum Dokument in die Eigenschaften; fehlt die Datei, nennt das
  Dock ihren Namen.
* Neuer BibTeX-Leser: versteht verschachtelte Klammern, `@string`, Monatsmakros und LaTeX-Umlaute,
  wie sie Zotero und JabRef exportieren. Titel erscheinen im Dock ohne LaTeX-Befehle.

## Editor & Bedienung

* **Syntax-Hervorhebung** im Editor.
* Der Editor wächst mit dem Inhalt und zeigt immer alle Zeilen, ohne eigene Scrollbar. Der
  Größengriff legt eine Mindesthöhe fest, ein Doppelklick setzt sie zurück.
* **Zellen verschieben** mit `Ctrl+Shift+Up`/`Ctrl+Shift+Down` (auch per Toolbar), rückgängig
  machbar. **Zelle einfügen** (`Ctrl+Shift+A`) setzt die neue Zelle vor die aktive.
* `Escape` und `Shift+Enter` behalten die Scrollposition des Dokuments.
* **Dokumenteigenschaften (Frontmatter):** neues Widget mit Import und Export; eingeklappt zeigt es
  den Titel des Dokuments.
* **Variablen-Inspektor** als Dock; ein Doppelklick fügt den Variablennamen ein.
* Polars-Unterstützung mit interaktivem Tabellen-Widget.
* Import von Jupyter-Notebooks (`.ipynb`).
* Warnung beim Schließen ungespeicherter Dokumente; Event-Debugger für die Entwicklung.

## Sprache

* Oberfläche auf Englisch und Deutsch (Qt Linguist, `assets/i18n`); auch Qts eigene Dialoge und
  Tastenkürzel („Strg+N“) werden übersetzt.
* **Einstellungen** (`Ctrl+,`): Wahl der Sprache (Systemsprache, English, Deutsch), wirksam nach einem
  Neustart.
* Handbuch-Dialog in der Sprache der Oberfläche (`docs/quickstart.md`, `docs/quickstart.en.md`).

## Fehlerbehebungen

* „Zelle einfügen“ landete eine Position zu weit oben, bei der zweiten Zelle ganz am Dokumentanfang.
* Große Lücke über dem Dokument: Die eingeklappten Dokumenteigenschaften waren so hoch wie ihr
  Editor.
* „Neues Dokument“ übernahm Titel und Literaturdatei des vorherigen Dokuments.
* Die eingeklappten Dokumenteigenschaften zeigten nie den Titel.
* Formeln im PDF wurden durch eine zusätzliche Kontur fett dargestellt.
* Kleinere Korrekturen an Beschriftungen („Dokcument Properties“, halb englisches Literatur-Dock,
  verschlucktes „&“ im Titel der LaTeX-Palette).

## Dokumentation

* **Handbuch** `docs/manual_de.md` mit Screenshots aller Bereiche; bindet die Kurzanleitung ein.
* Englische Kurzanleitung `docs/quickstart.en.md`.
* **Architekturentscheidungen** (`docs/adr`): einheitliche Dateinamen und Frontmatter (Status,
  Umsetzungsversion) für Obsidian, generierte Übersicht `docs/adr/README.md`; neue ADRs 014–017.

## Tooling & Architektur

* **Reproduzierbare Builds:** `uv.lock` für konsistente Builds auf allen Plattformen.
* **Automatisierte Tests:** GUI-Testsuite mit `pytest-qt`, inzwischen rund 70 Tests; `just test`
  (headless) oder `just test-watch` (mit sichtbarem Fenster).
* **Code-Qualität:** Metrik-Report (Komplexität, Maintainability Index, Ruff- und Vulture-Findings)
  über `just metrics`; `just format` formatiert den Quelltext.
* Neue Rezepte: `just i18n` (Übersetzungen aktualisieren), `just screenshots` (Screenshots aller
  Komponenten, isoliert und offscreen), `just adr-report` (ADR-Übersicht).
* `InPlaceCell` liegt jetzt in `src/widgets/inplace.py`; die Ausführung übernimmt `src/worker/`.
* Neue Abhängigkeiten: `markdown`, `ziamath`, `pygments`.

## Builds & Deployment

* Native Installer für Windows und Linux.
* macOS: Code Signing der App korrigiert und abgeschlossen.
* Schriften, Übersetzungen und Handbücher werden in alle Pakete eingebaut (Linux und Windows hatten
  bisher kein Handbuch).
* Eigene App-Icons und Hilfesystem; Refactoring von Layout und QTAwesome-Actions.

## Hinweise zum Update

* **Tastenkürzel:** `Ctrl+Shift+A` fügt jetzt vor der aktiven Zelle ein; „Zelle darunter einfügen“
  (`Ctrl+Shift+B`) entfällt, dafür verschieben `Ctrl+Shift+Up`/`Down` die aktive Zelle.
* **Sprache:** Auf einem englisch eingestellten System startet Rosida jetzt auf Englisch; Deutsch
  lässt sich in den Einstellungen wählen.
* **Stylesheet:** Wer bereits ein eigenes Stylesheet in den Einstellungen gespeichert hat, bekommt
  die neuen Regeln (Zitate, Zeilenabstand) nicht automatisch.
* **Bekannt:** `F3` und `F4` sind doppelt belegt (Dokumentstruktur/Variablen bzw.
  LaTeX-Palette/Literatur) und lösen deshalb nichts aus; die Docks sind über das Menü **Ansicht**
  erreichbar. Laufende Berechnungen lassen sich noch nicht abbrechen.
