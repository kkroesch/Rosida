---
adr: 16
title: "Gemeinsames Ausgabemodell für Vorschau und Exporte"
status: Vorgeschlagen
date: 2026-09-30
author: Claude Code
implemented:
aliases:
  - ADR 016
related:
  - "[[ADR 010]]"
tags:
  - adr
---

# ADR 016: Gemeinsames Ausgabemodell für Vorschau und Exporte

## Kontext

Wie das Ergebnis einer Python-Zelle dargestellt wird (SymPy-Formel, Matplotlib-Figur,
Polars-Tabelle, Text, Fehler, `print`-Ausgabe), entscheidet Rosida derzeit an **vier Stellen**
unabhängig voneinander:

| Ort | Datei |
|---|---|
| Vorschau in der App | `widgets/inplace.py` |
| PDF-Export | `exporters/pdf.py` |
| HTML-Export | `exporters/html.py` |
| Quarto-Export | `exporters/qmd.py` / `document.py` |

Die Stellen laufen bereits auseinander: Im **PDF** erscheint ein Polars-`DataFrame` nur als
Text-`repr` (App und HTML zeigen eine Tabelle), und der Wert wird dort unmaskiert in HTML
eingesetzt, sodass ein `<` im Ergebnis das Layout stört. Fehler werden im PDF anders erkannt als im
HTML-Export (Präfix `Error:` in `last_stdout`). Jede neue Ausgabeart (z. B. Einheiten, Plotly,
Bilder) müsste viermal implementiert werden.

Für Textzellen ist das Problem bereits gelöst: Vorschau, PDF und HTML teilen sich die
Markdown-Pipeline (`markdown_to_html`) und unterscheiden sich nur im Formel-Renderer.

## Entscheidung

1. Nach der Ausführung übersetzt Rosida das Ergebnis **einmal** in eine Liste von
   `CellOutput`-Objekten mit Art und Nutzlast, z. B.
   `stdout(text)`, `math(latex)`, `figure(svg, png)`, `table(dataframe)`, `text(str)`,
   `error(message, traceback)`.
2. Die Zelle speichert diese Liste statt `last_val`/`last_stdout`.
3. Jedes Ziel hat einen **Renderer**, der nur noch die Ausgabearten abbildet: Qt-Widgets (Vorschau),
   Qt-Rich-Text (PDF), HTML, Quarto-Markdown. Unbekannte Arten fallen einheitlich auf `text` zurück.
4. Die Übersetzung vom Python-Wert zur Ausgabeart ist eine Registry (`isinstance`-Regeln), damit
   neue Typen an einer Stelle ergänzt werden.

## Alternativen

* **Bei vier Stellen bleiben** und sie synchron halten: bisherige Praxis, führt zu den beschriebenen
  Abweichungen.
* **Alles über HTML** (Vorschau als HTML-Widget): scheitert am eingeschränkten Qt-Rich-Text und an
  interaktiven Widgets (DataFrame-Tabelle, Matplotlib-Canvas).

## Konsequenzen

* **Positiv:** Gleiche Darstellung in Vorschau und allen Exporten; neue Ausgabearten (Einheiten,
  Bilder, weitere Plot-Bibliotheken) an einer Stelle.
* **Positiv:** Die Ausgaben sind reine Daten und lassen sich ohne Qt testen.
* **Positiv:** Grundlage für ADR 010 (eingefrorene Ergebnisse im Quarto-Export) und für einen
  späteren Ergebnis-Cache.
* **Negativ:** Umbau der Zellen und aller Exporter; Figuren müssen beim Übersetzen einmal als SVG/PNG
  gerendert werden (heute teils erst beim Export).
