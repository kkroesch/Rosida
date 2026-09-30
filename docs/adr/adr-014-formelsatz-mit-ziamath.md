---
adr: 14
title: "Formelsatz mit ziamath als Vektor-Textobjekt"
status: Implementiert
date: 2026-09-29
author: Claude Code
implemented: v0.3.0
aliases:
  - ADR 014
related:
  - "[[ADR 002]]"
tags:
  - adr
---

# ADR 014: Formelsatz mit ziamath als Vektor-Textobjekt

> **Siehe auch:** [ADR 002: MathText-Rendering via Matplotlib](adr-002-mathtext-rendering.md)
> beschreibt den vorherigen Ansatz, den diese Entscheidung ablöst.

## Kontext

ADR 002 setzte Formeln mit Matplotlibs `mathtext` und bettete sie als Rasterbilder ein. In der
Praxis zeigten sich drei Schwächen:

* **Befehlsumfang:** `mathtext` kennt weder Matrizen noch `aligned` oder `cases`. SymPy liefert
  Matrizen als `\begin{matrix}`, solche Ergebnisse erschienen als Fehler.
* **Typografie:** Die Formeln wirkten neben dem CMU-Fließtext fremd (DejaVu-Stil, schwankende
  Grundlinie, Ausrichtung nur „ungefähr mittig“).
* **PDF-Export:** Rasterbilder werden beim Zoomen unscharf; außerdem überschrieben sich gleichnamige
  Bildressourcen mehrerer Zellen im zusammengeführten Exportdokument.

Eine Web-Engine (KaTeX/MathJax in `QWebEngineView`) bleibt aus den Gründen von ADR 002 ausgeschlossen.

## Entscheidung

1. **ziamath** (reines Python: LaTeX → MathML → SVG) setzt die Formeln, standardmäßig in
   **Latin Modern Math**, passend zu den CMU-Schriften. Die Schrift ist über `render/math_font`
   einstellbar; ohne Angabe nutzt ziamath STIX Two Math.
2. Formeln werden als **eigenes Textobjekt** (`QTextObjectInterface`) in das `QTextDocument`
   eingefügt, nicht als Bild. Es zeichnet die Glyphen-Pfade direkt mit dem `QPainter`, dadurch bleiben
   sie im PDF Vektorgrafik und sitzen über ascent/descent aus der SVG-`viewBox` auf der Grundlinie.
3. Das SVG wird **nicht mit `QSvgRenderer`** gezeichnet: Dessen voreingestellter (unsichtbarer) Stift
   wird von Qts PDF-Engine als Kontur ausgegeben, jede Glyphe erscheint dadurch fett. Die wenigen
   Elemente, die ziamath erzeugt (`path` mit M/L/Q/C/Z, `rect`), übersetzt Rosida selbst in
   `QPainterPath`s.
4. `mathtext` bleibt als **Fallback** für Ausdrücke, die ziamath ablehnt.
5. Im **HTML-Export** setzt KaTeX die Formeln im Browser; dort ist die Web-Engine ohnehin vorhanden.

## Alternativen

* **KaTeX/MathJax in der App:** erfordert QtWebEngine (Chromium), siehe ADR 002.
* **LaTeX + dvisvgm:** beste Typografie, aber eine TeX-Installation als Systemabhängigkeit.
* **`QSvgRenderer` für das SVG:** getestet, verworfen wegen der fetten Glyphen im PDF (siehe oben).

## Konsequenzen

* **Positiv:** Matrizen, `aligned`, `cases` und SymPy-Ergebnisse werden gesetzt; Vorschau und PDF
  sehen aus wie LaTeX und bleiben bei jedem Zoom scharf.
* **Positiv:** Keine neue schwere Abhängigkeit (ziamath und latex2mathml sind reines Python).
* **Negativ:** ziamath deckt nicht jeden LaTeX-Befehl ab; unbekannte Befehle erscheinen als Text
  statt als Fehler, Spalten in `cases`/Matrizen sind eng gesetzt.
* **Negativ:** Der eigene SVG-Pfad-Übersetzer muss erweitert werden, falls ziamath künftig weitere
  SVG-Elemente erzeugt (ein Test deckt TrueType- und CFF-Umrisse ab).
