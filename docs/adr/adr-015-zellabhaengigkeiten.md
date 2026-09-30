---
adr: 15
title: "Zellabhängigkeiten erkennen und veraltete Ergebnisse markieren"
status: Vorgeschlagen
date: 2026-09-30
author: Claude Code
implemented:
aliases:
  - ADR 015
related:
  - "[[ADR 003]]"
tags:
  - adr
---

# ADR 015: Zellabhängigkeiten erkennen und veraltete Ergebnisse markieren

## Kontext

Alle Zellen teilen sich einen Namensraum (ADR 003). Ändert man eine Zelle, die eine Variable
definiert (`g = 9.81`), zeigen alle späteren Zellen, die `g` verwenden, weiterhin ihre alten
Ergebnisse, ohne Hinweis. Man muss selbst wissen, was neu zu berechnen ist, oder „Alle ausführen“
wählen, was bei rechenintensiven Dokumenten teuer ist.

Maple und reaktive Notebooks (Pluto.jl, marimo) lösen das über einen Abhängigkeitsgraphen. Für
Rosida, das sich an Maple orientiert, ist das ein naheliegender nächster Schritt; der Worker-Thread
und die geordnete Ausführungswarteschlange (ADR 003, Stufe 1) sind bereits vorhanden.

## Entscheidung

1. **Statische Analyse:** Für jede Python-Zelle ermittelt Rosida per `ast` die Namen, die sie
   *definiert* (Zuweisungen, `import`, `def`, `class`, `for`-Ziele) und die sie *liest*.
   Textzellen lesen die Namen in ihren `{{ … }}`-Ausdrücken.
2. **Abhängigkeitsgraph:** Zelle B hängt von Zelle A ab, wenn B einen Namen liest, den A als letzte
   Zelle vor B definiert.
3. **Veraltet-Markierung:** Wird eine Zelle ausgeführt oder geändert, erhalten alle direkt und
   indirekt abhängigen Zellen eine dezente Markierung („veraltet“) am Rand. „Abhängige neu
   berechnen“ führt genau diese Zellen in Dokumentreihenfolge aus.
4. **Kein Automatismus als Standard:** Automatisches Neuberechnen ist eine Einstellung, weil
   Berechnungen lange dauern können (Rosida kann sie nicht abbrechen, siehe ADR 005).
5. **Hinweise:** Liest eine Zelle einen Namen, den keine vorherige Zelle definiert, zeigt Rosida
   das vor der Ausführung an („`x` wird erst in Zelle 7 definiert“).

## Alternativen

* **Vollständig reaktiv wie marimo:** jede Änderung rechnet sofort alles Abhängige neu. Passt nicht
  zu langen Berechnungen ohne Abbruchmöglichkeit.
* **Laufzeit-Tracing** der Namenszugriffe: genauer bei dynamischem Code, aber aufwendig und langsam.
* **Nichts tun:** einfach, aber veraltete Ergebnisse bleiben eine stille Fehlerquelle, besonders in
  exportierten Dokumenten.

## Konsequenzen

* **Positiv:** Sichtbar, welche Ergebnisse nicht mehr zum Code passen; gezieltes Neuberechnen statt
  „Alle ausführen“.
* **Positiv:** Die Analyse ist billig (Millisekunden) und läuft ohne Ausführung.
* **Negativ:** Statische Analyse erkennt keine Mutationen (`werte.append(1)`), kein `exec` und keine
  dynamischen Zugriffe (`globals()["x"]`). Sie ist deshalb nur ein Hinweis; im Zweifel bleibt
  „Alle ausführen“.
* **Folgearbeit:** Exporte könnten warnen, wenn veraltete Zellen enthalten sind.
