"""Gemeinsame Fixtures für die GUI-Tests (pytest-qt).

Zum Zusehen wie bei Playwrights headed/slowMo-Modus:

    ROSIDA_TEST_SLOWMO=300 QT_QPA_PLATFORM= just test

`QT_QPA_PLATFORM=` (leer) erzwingt die echte Fensterplattform statt des
Offscreen-Renderers, `ROSIDA_TEST_SLOWMO` fügt nach jeder simulierten
Interaktion eine Pause in Millisekunden ein, damit man den Klicks/Eingaben
tatsächlich folgen kann.
"""

import os
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
  sys.path.insert(0, str(SRC_DIR))

SLOWMO_MS = int(os.environ.get("ROSIDA_TEST_SLOWMO", "0"))


@pytest.fixture
def slow_step(qtbot):
  """Wie Playwrights slowMo: nach einer Interaktion kurz warten, wenn ROSIDA_TEST_SLOWMO gesetzt ist."""

  def _wait(ms: int | None = None):
    qtbot.wait(ms if ms is not None else SLOWMO_MS)

  return _wait


@pytest.fixture
def rosida_win(qtbot):
  """Eine frische RosidaApp-Instanz mit einer leeren Startzelle, sichtbar für den Watch-Modus."""
  from app import RosidaApp

  win = RosidaApp()
  qtbot.addWidget(win)
  win.show()
  qtbot.waitExposed(win)
  return win
