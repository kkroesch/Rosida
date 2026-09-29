# Release Notes: Rosida v0.3.0

## Neue Features & UI

* **Document Properties & Frontmatter:** Neues Widget für die Dokumenteigenschaften (Frontmatter) inklusive vollständiger Import- und Export-Logik.


* **Literaturverwaltung:** Das Bibitem-Dock für die Verwaltung von Referenzen wurde integriert.


* **Editor-Upgrades:** Syntax-Highlighting für den Editor ist jetzt aktiv. Ein Fix für die automatische Höhenanpassung des Editors wurde implementiert.


* **Daten & Analyse:** Ein Variable Inspector Dock steht nun zur Verfügung. Polars-Support sowie ein interaktives Tabellen-Widget wurden als Beispiel hinzugefügt.


* **Kompatibilität:** Native Import-Funktion für `.ipynb` (Jupyter Notebooks) eingebaut.


* **Sicherheit & Debugging:** Ein Event-Debugger sowie eine Warnung beim Schließen ungespeicherter Dokumente schützen jetzt vor Datenverlust.



## Typografie & Quarto

* **Gestaltung:** CMU-Schriftarten (Computer Modern) und zugehörige Einstellungen wurden integriert, diverse typografische Probleme sind behoben.


* **Layout-Elemente:** Unterstützung für Figures (Abbildungen) und Callouts wurde hinzugefügt.


* **Quarto:** Erste Quarto-Experimente und ein dediziertes `.qmd`-Beispieldokument liegen bei.



## Tooling & Architektur

* **Reproduzierbare Builds:** Einführung von `uv.lock` für konsistente, reproduzierbare Builds über alle unterstützten Plattformen hinweg.


* **Automatisierte Tests:** Eine vollständige GUI-Testsuite via `pytest-qt` wurde etabliert. Diese lässt sich über `just test` (headless) oder `just test-watch` (mit UI-Verzögerung) ausführen.


* **Code-Qualität:** Ein Report für Code-Metriken (Komplexität, Maintainability Index, Ruff- und Vulture-Findings) inklusive farbiger Fortschrittsbalken ist nun via `just metrics` abrufbar. Unbenutzter Code (`export_to_qmd`) wurde in diesem Zuge entfernt.



## Builds & Deployment

* **Installer:** Native Installer für Windows und Linux wurden zum Build-Prozess hinzugefügt.


* **macOS:** Der Apple-Signierungsprozess (Code Signing) für die Mac-App wurde korrigiert und abgeschlossen.


* **UX & Design:** Eigene App-Icons sowie ein grundlegendes Hilfesystem (Help System) wurden implementiert. Layout und QTAwesome-Actions wurden einem Refactoring unterzogen.
