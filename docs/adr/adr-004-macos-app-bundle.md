---
adr: 4
title: "Native macOS-Integration & Bundle-Struktur"
status: Implementiert
date: 2026-09-25
author: Karsten Kroesch
implemented: v0.2.0
aliases:
  - ADR 004
tags:
  - adr
---

# ADR 004: Native macOS-Integration & Bundle-Struktur

* **Kontext:**
Unter macOS gestartete Python-Skripte zeigen generische Namen („python“, „app.py“) im Application-Menü und fehlen im Dock/App-Switcher als eigenständige Entität.
* **Entscheidung:**
Rosida wird als minimales, deklaratives `.app`-Bundle mit `Info.plist`, eigenständigem Launch-Skript und standardkonformem `AppIcon.icns` (Rhodonea-Kurve) verpackt. Qt-Metadaten (`QCoreApplication.setApplicationName("Rosida")`) und `sys.argv[0]` werden vor der Instanziierung von `QApplication` initialisiert.
* **Konsequenzen:**
* Konsistentes natives Look & Feel ohne schwere Installer/Packer.
* Portabel und mit lokaler Entwicklungsumgebung (`uv` / Standalone-`venv`) direkt verknüpfbar.
