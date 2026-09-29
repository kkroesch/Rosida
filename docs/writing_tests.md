# Tests schreiben

Das Schreiben von GUI-Tests mit `pytest-qt` folgt im Grunde immer denselben drei Mustern. 

**1. Sichtbarkeit und UI-Zustand prüfen (z. B. Frontmatter-Toggle)**
Du nutzt den `qtbot`, um echte Mausklicks zu simulieren, und prüfst danach direkt die Qt-Properties.

```python
from PySide6.QtCore import Qt

def test_frontmatter_expand_shows_editor(qtbot, main_window):
    cell = main_window.frontmatter_cell
    
    # 1. Klick auf den "Eingeklappt"-Button simulieren
    qtbot.mouseClick(cell.btn_collapsed, Qt.MouseButton.LeftButton)
    
    # 2. Prüfen, ob der Editor jetzt sichtbar ist
    assert cell.editor.isVisible()
    assert not cell.btn_collapsed.isVisible()

```

**2. Dateidialoge mocken (z. B. Bibitem-Dock Datei-Import)**
Genau wie bei der `QMessageBox` darf der Test niemals einen echten Dateidialog öffnen. Du patchst `QFileDialog.getOpenFileName`, sodass es sofort einen Dummy-Pfad zurückwirft.

```python
def test_bibdock_loads_file_and_switches_stack(qtbot, main_window, monkeypatch):
    dock = main_window.bib_dock
    
    # Den Dateidialog abfangen und einen fixen Test-Pfad zurückgeben
    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: ("tests/fixtures/dummy.bib", "BibTeX (*.bib)")
    )
    
    # Klick auf den Lade-Button simulieren
    qtbot.mouseClick(dock.btn_load, Qt.MouseButton.LeftButton)
    
    # Prüfen, ob das StackedWidget auf die Liste (Index 1) umgeschaltet hat
    assert dock.stack.currentIndex() == 1

```

**3. Eigene Signale abwarten (z. B. Shift+Enter in Python-Zellen)**
Wenn eine Aktion asynchron ist oder ein Signal abfeuert (wie dein neues `execute_requested`), nutzt du den Context-Manager `waitSignal`. Schlägt das Signal nicht innerhalb des Timeouts fehl, crasht der Test.

```python
def test_shift_enter_emits_execute_signal(qtbot, python_cell):
    # Test blockiert hier maximal 500ms und wartet exakt auf dieses Signal
    with qtbot.waitSignal(python_cell.editor.execute_requested, timeout=500):
        
        # Tastendruck Shift + Enter direkt in den Editor feuern
        qtbot.keyClick(
            python_cell.editor, 
            Qt.Key.Key_Return, 
            modifier=Qt.KeyboardModifier.ShiftModifier
        )

```
