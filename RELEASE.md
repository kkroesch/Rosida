# Rosida 0.3.0

Version 0.3.0 macht Rosida zu einer vollwertigen, typografisch sauberen Arbeitsumgebung für wissenschaftliche Notizen und Berechnungen. Der Fokus dieses Releases liegt auf exzellenter Text- und Formeldarstellung im Computer-Modern-Satz, nativer Quarto-Semantik, dynamischem Zell-Editing sowie einer durchgehenden Härtung von Build-System und Testabdeckung.

---

### Highlights

* **Computer Modern Unicode (CMU) Typografie:** Vollständige Integration der CMU-Schriftfamilie (CMU Serif für Fließtext, CMU Sans Serif für Überschriften, CMU Concrete für Zitate und CMU Typewriter Text für Code).


* **Dynamische Inline-Editoren:** Der Editor passt seine Höhe beim Aktivieren einer Zelle und beim Tippen automatisch exakt an die Zeilenanzahl an – ohne störende interne Scrollbalken.


* **Quarto Semantik:** Native Rendering-Unterstützung für Quarto-Figuren (`FigureWidget` mit Badges und Captions) sowie Callout-Blöcke (`note`, `tip`, `warning`, `caution`).


* **Variable Inspector:** Neues Dock-Widget zur interaktiven Inspektion des aktiven Python-Zellzustands.


* **Deterministische Builds & GUI-Tests:** Umstellung des Paket- und Build-Managements auf `uv.lock` sowie Einführung einer vollständigen `pytest-qt`-Testsuite.



---

### Neuerungen & Verbesserungen im Detail

#### Typografie & Markdown-Rendering

* **Wissenschaftlicher Schriftsatz:** Registrierung der CMU-Schriften beim App-Start und sauberes Dokument-Styling über getrennte CSS-Selektoren statt fehleranfälliger Inline-Schriftgrößen.


* **Formel-Harmonisierung:** Formelsatz über Matplotlibs TeX-Engine (`mathtext.fontset = 'cm'`) mit transparenter PNG-Ausgabe und korrigierter vertikaler Ausrichtung im Fließtext.
* **Saubere Variablenauflösung:** Expressions in doppelten geschweiften Klammern (`{{expr}}`) werden vor dem Rendern zuverlässig gegen den Notebook-Namespace aufgelöst.

#### Editor & Benutzeroberfläche

* **Auto-Height für `InlineEditor`:** Automatische Neuberechnung der Widget-Höhe basierend auf Zeilenanzahl, Zeilenabstand (`lineSpacing`) und Dokument-Margins.


* **Variable Inspector Dock:** Integriertes Dock-Widget zur Echtzeit-Anzeige definierter Variablen, Typen und Werte in der aktuellen Session.


* **Quarto-Widgets:** Native Widgets für Abbildungen und Callout-Boxen inklusive Icon-Integration über `qtawesome`.


* **Sicherheit im Workflow:** Warnung vor Datenverlust beim Schließen ungespeicherter Dokumente sowie integrierter Event-Debugger.



#### Dateiformate & I/O

* **Zellentrennung:** Symmetrisches Parsen und Serialisieren von Markdown/QMD-Zellen über standardkonforme `---`-Trenner verhindert das ungewollte Verschmelzen von Blöcken.


* **IPython-Notebooks:** Direkter Import von `.ipynb`-Dateien.


* **Bereinigte Export-Pipeline:** Migration auf zellbasiertes Rendering via `DocumentCanvas.export_qmd()`.



#### Infrastruktur, Tests & Qualitätssicherung

* **Reproduzierbarkeit via `uv.lock`:** Einheitliche `pyproject.toml` mit gepinntem Lockfile für plattformübergreifend identische Abhängigkeiten unter Linux, macOS und Windows.


* **Headless GUI-Tests:** Automatisierte Testsuite mit `pytest-qt` via `just test` sowie visueller `just test-watch`-Modus zur interaktiven Fehleranalyse.


* **Code-Metriken:** Integrierter Qualitätsreport via `just metrics` zur Überwachung von Komplexität (McCabe), Wartbarkeit (Radon), Linting (Ruff) und totem Code (Vulture).


* **Architektur-Dokumentation:** Einführung von Architecture Decision Records (ADRs) zur Nachvollziehbarkeit technischer Entwurfsentscheidungen.
