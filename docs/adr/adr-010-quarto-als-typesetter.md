---
adr: 10
title: "Quarto als reiner Typesetter (Statischer Export)"
status: Akzeptiert
date: 2026-09-27
author: Karsten Kroesch
implemented:
aliases:
  - ADR 010
tags:
  - adr
---

# ADR 010: Quarto als reiner Typesetter (Statischer Export)

**Kontext:**
Rosida verarbeitet und berechnet Code-Zellen interaktiv und hält den Session-State im lokalen Speicher. Für den hochwertigen Dokumenten-Export (PDF via Typst oder LaTeX) wird Quarto verwendet. Standardmäßig interpretiert Quarto Blöcke mit der Syntax ````{python}` als interaktive Zellen und startet eine eigene Jupyter-Engine, um den Code erneut auszuführen. Dies führt zu redundanten Berechnungen, zwingt Quarto in die Rolle einer Ausführungsumgebung und verlangsamt den finalen Rendering-Prozess enorm.

**Entscheidung:**
Die Zuständigkeiten werden strikt getrennt (Separation of Concerns): Rosida ist die exklusive Ausführungsumgebung, Quarto fungiert ausschließlich als nachgelagerter Setzer (Typesetter).

1. **Syntax-Anpassung:** Im exportierten `.qmd`-Dokument werden Code-Zellen als statischer Text mit Highlighting formatiert (`python` anstelle von `{python}`).
2. **Ergebnis-Einfrierung:** Rosida exportiert die bereits lokal berechneten Resultate (Konsolenausgaben, Tabellen, Matplotlib-Grafiken) direkt als statisches Markdown unter den jeweiligen Codeblock.
3. **Globale Sperre:** Im YAML-Frontmatter des generierten Dokuments wird die Ausführung als zusätzliche Sicherheitsmaßnahme global deaktiviert (`execute: eval: false`).

**Konsequenzen:**

* **Positiv:** Mechanische Sympathie. Der Quarto-Build-Prozess wird pfeilschnell und deterministisch, da keine versteckten Python-Prozesse oder Kernel-Starts im Hintergrund ablaufen.
* **Positiv:** Die exportierten `.qmd`-Dateien sind "eingefroren" und dokumentieren exakt den Zustand zum Zeitpunkt des Exports (hohe Reproduzierbarkeit für die Wissenschaft).
* **Positiv:** Die Architektur bleibt simpel. Es müssen keine komplexen Jupyter-State-Synchronisationen zwischen Rosida und Quarto gebaut werden.
* **Negativ/Trade-off:** Das erstellte `.qmd`-Dokument ist in anderen Umgebungen (wie Positron oder Jupyter) nicht mehr als "Live-Notebook" nutzbar. Da Rosida aber die Single Source of Truth für die Interaktion ist, ist dies ein explizit gewünschtes Verhalten.
