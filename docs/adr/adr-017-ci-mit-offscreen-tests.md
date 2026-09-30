---
adr: 17
title: "Continuous Integration mit Offscreen-GUI-Tests"
status: Vorgeschlagen
date: 2026-09-30
author: Claude Code
implemented:
aliases:
  - ADR 017
related:
  - "[[ADR 004]]"
tags:
  - adr
---

# ADR 017: Continuous Integration mit Offscreen-GUI-Tests

## Kontext

Rosida hat eine Testsuite mit rund 70 Tests (pytest-qt), die offscreen ohne Bildschirm in etwa
zehn Sekunden läuft, ein Screenshot-Skript, eine Übersetzungsprüfung und einen ADR-Report. Nichts
davon läuft automatisch: Ob ein Commit etwas kaputt macht, zeigt sich erst beim nächsten lokalen
Testlauf.

Der vorhandene Release-Workflow `macos-app.yaml` liegt in `.github/workflow/`. GitHub Actions liest
aber nur `.github/workflows/`, der Workflow wird daher nie ausgeführt.

## Entscheidung

1. Ein Workflow `.github/workflows/ci.yaml` läuft bei jedem Push und Pull Request auf
   `ubuntu-latest`:
   * `astral-sh/setup-uv`, dann die Tests offscreen (`QT_QPA_PLATFORM=offscreen`, wie `just test`).
   * Systembibliotheken, die Qt auch offscreen braucht: `libegl1`, `libgl1`, `libxkbcommon0`,
     `libfontconfig1`, `libdbus-1-3`.
   * `ruff check` (zunächst nur die Regelgruppe `F`, damit die vorhandenen Altlasten den Lauf nicht
     blockieren).
   * Prüfen, dass `just i18n` und `just adr-report` keine Änderungen erzeugen (Übersetzungen und
     ADR-Übersicht sind aktuell).
2. Bei Pull Requests erzeugt der Workflow zusätzlich die Screenshots (`just screenshots`) und hängt
   sie als Artefakt an, damit Oberflächenänderungen im Review sichtbar sind.
3. Der Release-Workflow zieht nach `.github/workflows/` um und läuft wie vorgesehen bei `v*`-Tags.

## Alternativen

* **Nur lokal testen:** bisherige Praxis; Fehler fallen spät auf.
* **Tests mit echtem X-Server (Xvfb):** näher an der Wirklichkeit, aber langsamer und für die
  vorhandenen Tests nicht nötig.

## Konsequenzen

* **Positiv:** Jeder Push wird geprüft; Übersetzungen und ADR-Übersicht können nicht unbemerkt
  veralten.
* **Positiv:** Screenshots im Pull Request machen UI-Änderungen reviewbar.
* **Negativ:** Offscreen-Tests sehen keine plattformspezifischen Effekte (macOS-Menüleiste,
  Tastenkürzel mit `Cmd`); dafür bleiben der Release-Build und manuelle Tests.
* **Hinweis:** Mit dem Umzug des Release-Workflows baut jeder `v*`-Tag automatisch ein DMG.
