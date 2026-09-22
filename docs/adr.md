# Architecture_Decisions.md

## ADR 0001: Natives Markdown (`.md`) als Persistenzformat

* **Status:** Akzeptiert
* **Datum:** 2026-09
* **Kontext:**
Klassische Notebook-Formate (wie Jupyter `.ipynb`) basieren auf monolithischem JSON. Dies führt zu unlesbaren Git-Diffs, Merge-Konflikten und erfordert spezialisierte Parser für einfache Textanalysen.
* **Entscheidung:**
Rosida nutzt standardkonformes Markdown als primäres Speicherformat. Python-Zellen werden als Fenced Code Blocks (`python ... `) persistiert. Horizontale Trennlinien (`---`) trennen aufeinanderfolgende Markdown-Zellen.
* **Konsequenzen:**
* Saubere Diffs in Versionskontrollsystemen (Git).
* Vollständige Interoperabilität mit CLI-Tools (`pandoc`, `grep`, `bat`, `marimo`).
* Verlustfreie Rekonstruktion des Zellenaufbaus beim Laden.

---

## ADR 0002: MathText-Rendering via Matplotlib (In-Memory)

* **Status:** Akzeptiert
* **Datum:** 2026-09
* **Kontext:**
Web-basierte Math-Renderer (MathJax/KaTeX in `QWebEngineView`) erfordern schwere Chromium-Abhängigkeiten und verursachen spürbaren Overhead beim Layout-Reflow. Reine TeX-Installationen (`pdflatex`) sind als Systemabhängigkeit zu schwergewichtig.
* **Entscheidung:**
Mathematische Formeln ($...$ und 
$$...$$


) werden über Matplotlibs integrierte `mathtext`-Engine gerendert, in hochauflösende Raster- bzw. Vektorgrafiken konvertiert und via `QTextDocument.addResource` direkt im nativen Textfluss verankert.
* **Konsequenzen:**
* Keine Web-Engine oder externe Browser-Prozesse notwendig.
* Geringer Speicher-Footprint und scharfe HiDPI-Darstellung.
* Einschränkung auf den von `mathtext` unterstützten LaTeX-Befehlssatz (reicht für CAS-Anwendungen vollständig aus).

---

## ADR 0003: Prozessmodell & Ausführungsarchitektur (Execution Model)

* **Status:** In Evaluierung (Zweistufige Migration)
* **Datum:** 2026-09
* **Kontext:**
Aktuell führt Rosida Python-Code via `exec()` direkt im Hauptprozess der Qt-Anwendung aus. Die Zellen teilen sich ein globales Namespace-Dictionary.
> *„Für flüssiges Arbeiten bei schwereren Rechnungen reicht es oft schon, die Ausführung mittelfristig in einen QThread (oder einen schlanken Subprozess via multiprocessing) auszulagern, damit die Qt-Oberfläche jederzeit responsiv bleibt.“*


* **Problemanalyse des Status quo (In-Process):**
* **Vorteile:** Zero-Copy-Datenaustausch (0 ms Overhead), direkter Zugriff auf Live-Objekte, minimaler Codeaufwand, kein IPC-Setup.
* **Risiken:**
1. *Blocking Event Loop:* Rechenintensive Aufgaben (z. B. symbolische Integration in SymPy, Optimierungsschleifen) blockieren den GUI-Thread; macOS zeigt den Beachball.
2. *Crash Vulnerability:* Segfaults in C-Extensions (NumPy/SciPy) reißen die gesamte Anwendung inklusive Editor ab.
3. *Namespace Pollution:* Manipulationen an `sys.modules` oder globalen Builtins können die Qt-Laufzeit destabilisieren.


### Architektur-Optionen im Vergleich

| Kriterium | Option A: In-Process (Aktuell) | Option B: Worker-Thread (`QThread`) | Option C: Subprozess (`multiprocessing` / IPC) |
| --- | --- | --- | --- |
| **UI-Responsivität** | Blockiert bei Berechnung | Vollständig responsiv | Vollständig responsiv |
| **Crash-Isolation** | Keine (App stürzt ab) | Keine (Thread reißt Prozess mit) | Vollständig isoliert |
| **Datenaustausch** | Direkt im RAM (Pointer) | Direkt im RAM (GIL-Beachtung) | Serialisierung (IPC / Shared Memory) |
| **Abbrechen (`Interrupt`)** | Nicht möglich ohne Kill | Schwer/unsicher in Python | Trivial via `SIGINT` / `terminate()` |
| **Komplexität** | Sehr gering | Gering | Mittel bis hoch |

### Beschlossener Evolutionspfad

1. **Phase 1 (Gegenwart): In-Process mit `KernelSession`-Abstraktion**
Die Ausführungslogik wird vollständig aus `InPlaceCell` in eine separate Klasse `KernelSession` verlagert, damit die Zellen keinen direkten `exec()`-Aufruf mehr enthalten.
2. **Phase 2 (Kurzfristig): Entkopplung via `QThread**`
Rechenjobs werden über Qt-Signals/Slots an einen Hintergrund-Thread übergeben. Die GUI bleibt bedienbar (Spinner/Statusbalken), und `stdout`/Plots werden asynchron zurückgemeldet.
3. **Phase 3 (Bedarfsgetrieben): Isolierter Kernel-Worker**
Falls instabile C-Bibliotheken oder echte Interrupts (Zellenausführung sofort abbrechen) zwingend werden, wandert `KernelSession` in einen separaten Subprozess (z. B. via Unix Domain Sockets oder `multiprocessing.Pipe`).

---

## ADR 0004: Native macOS-Integration & Bundle-Struktur

* **Status:** Akzeptiert
* **Datum:** 2026-09
* **Kontext:**
Unter macOS gestartete Python-Skripte zeigen generische Namen („python“, „app.py“) im Application-Menü und fehlen im Dock/App-Switcher als eigenständige Entität.
* **Entscheidung:**
Rosida wird als minimales, deklaratives `.app`-Bundle mit `Info.plist`, eigenständigem Launch-Skript und standardkonformem `AppIcon.icns` (Rhodonea-Kurve) verpackt. Qt-Metadaten (`QCoreApplication.setApplicationName("Rosida")`) und `sys.argv[0]` werden vor der Instanziierung von `QApplication` initialisiert.
* **Konsequenzen:**
* Konsistentes natives Look & Feel ohne schwere Installer/Packer.
* Portabel und mit lokaler Entwicklungsumgebung (`uv` / Standalone-`venv`) direkt verknüpfbar.
