---
title: Architecture Decision Records
tags:
  - adr
---

# Architecture Decision Records

<!-- Generiert von scripts/adr_report.py (just adr-report), nicht von Hand bearbeiten. -->

12 Entscheidungen – Akzeptiert: 5, Implementiert: 6, Nicht verfolgen: 1.

| ADR | Titel | Status | Implementiert | Datum | Autor | Siehe auch |
|---|---|---|---|---|---|---|
| [001](adr-001-markdown-als-speicherformat.md) | Natives Markdown (.md) als Persistenzformat | Implementiert | v0.2.0 | 2026-09-25 | Karsten Kroesch | – |
| [002](adr-002-mathtext-rendering.md) | MathText-Rendering via Matplotlib (In-Memory) | Implementiert | v0.3.0 | 2026-09-25 | Karsten Kroesch | – |
| [003](adr-003-ausfuehrungsmodell.md) | Prozessmodell & Ausführungsarchitektur (Execution Model) | Implementiert | v0.3.0 | 2026-09-22 | Karsten Kroesch | [005](adr-005-qprocess-kernel.md) |
| [004](adr-004-macos-app-bundle.md) | Native macOS-Integration & Bundle-Struktur | Implementiert | v0.2.0 | 2026-09-25 | Karsten Kroesch | – |
| [005](adr-005-qprocess-kernel.md) | Isolierte Code-Ausführung via persistenten QProcess und dynamische Toolbar-Steuerung | Akzeptiert | – | 2026-09-25 | Karsten Kroesch | – |
| [006](adr-006-nicht-modale-fehlerbehandlung.md) | Nicht-modales Fehler-Handling via Inline-Akkordeon und System-Log-Drawer | Akzeptiert | – | 2026-09-25 | Karsten Kroesch | – |
| [007](adr-007-fluechtige-prompt-zellen.md) | Flüchtige Prompt-Zellen zur KI-gestützten Inhalts- und Code-Generierung | Nicht verfolgen | – | 2026-09-25 | Karsten Kroesch | [013](adr-013-prompt-zellen.md) |
| [008](adr-008-qt-widgets-fuer-quarto-bloecke.md) | Native Qt-Widgets für Quarto-Blocksemantik (Figures & Callouts) | Implementiert | v0.2.0 | 2026-09-26 | Karsten Kroesch | – |
| [009](adr-009-zotero-bibliografie.md) | Zotero-Integration über dateibasierte Bibliografie (.bib) | Implementiert | v0.2.0 | 2026-09-27 | Karsten Kroesch | – |
| [010](adr-010-quarto-als-typesetter.md) | Quarto als reiner Typesetter (Statischer Export) | Akzeptiert | – | 2026-09-27 | Karsten Kroesch | – |
| [012](adr-012-denkbrett-post-its.md) | Visuelle Organisation von Literatur-Notizen (Denkbrett / Post-it UI) | Akzeptiert | – | 2026-09-27 | Karsten Kroesch | – |
| [013](adr-013-prompt-zellen.md) | KI-Integration via deterministischer Prompt-Zellen | Akzeptiert | – | 2026-09-27 | Karsten Kroesch | [007](adr-007-fluechtige-prompt-zellen.md) |

## Hinweise

- Nicht vergebene Nummern: 011
