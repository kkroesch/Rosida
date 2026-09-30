---
adr: 1
title: "Natives Markdown (.md) als Persistenzformat"
status: Implementiert
date: 2026-09-25
author: Karsten Kroesch
implemented: v0.2.0
aliases:
  - ADR 001
tags:
  - adr
---

# ADR 001: Natives Markdown (`.md`) als Persistenzformat

* **Kontext:**
Klassische Notebook-Formate (wie Jupyter `.ipynb`) basieren auf monolithischem JSON. Dies führt zu unlesbaren Git-Diffs, Merge-Konflikten und erfordert spezialisierte Parser für einfache Textanalysen.
* **Entscheidung:**
Rosida nutzt standardkonformes Markdown als primäres Speicherformat. Python-Zellen werden als Fenced Code Blocks (`python ... `) persistiert. Horizontale Trennlinien (`---`) trennen aufeinanderfolgende Markdown-Zellen.
* **Konsequenzen:**
* Saubere Diffs in Versionskontrollsystemen (Git).
* Vollständige Interoperabilität mit CLI-Tools (`pandoc`, `grep`, `bat`, `marimo`).
* Verlustfreie Rekonstruktion des Zellenaufbaus beim Laden.

---
