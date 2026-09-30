"""Reihenfolgetreue Ausführung von Zellen außerhalb des GUI-Threads."""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from worker.worker import CellWorker


@dataclass
class CellOutcome:
    """Ergebnis eines Laufs; error ist der Traceback oder leer."""

    value: object = None
    stdout: str = ""
    error: str = ""


class Kernel(QObject):
    """Führt Python-Code nacheinander in CellWorker-Threads aus.

    Alle Zellen teilen sich einen Namensraum und bauen aufeinander auf,
    deshalb läuft immer nur ein Job. GUI-Jobs (run_call, z.B. Textzellen mit
    {{ ... }}-Ausdrücken) reihen sich in dieselbe Warteschlange ein, damit sie
    die Ergebnisse vorheriger Python-Zellen sehen.
    """

    busy_changed = Signal(bool)

    def __init__(self, namespace: dict, parent=None):
        super().__init__(parent)
        self.namespace = namespace
        self._queue: deque = deque()
        self._worker: CellWorker | None = None
        self._outcome: CellOutcome | None = None
        self._on_done: Callable[[CellOutcome], None] | None = None
        self._busy = False

    def is_busy(self) -> bool:
        return self._worker is not None or bool(self._queue)

    def is_computing(self) -> bool:
        """True while Python code runs in a worker thread."""
        return self._worker is not None

    def run_code(self, code: str, on_done: Callable[[CellOutcome], None]) -> None:
        """Runs code in a worker thread; on_done is called in the GUI thread."""
        self._queue.append((code, on_done))
        self._pump()

    def run_call(self, fn: Callable[[], None]) -> None:
        """Runs fn in the GUI thread once all earlier jobs are done (at once if idle)."""
        self._queue.append((fn, None))
        self._pump()

    def _pump(self) -> None:
        while self._worker is None and self._queue:
            job, on_done = self._queue.popleft()
            if on_done is None:
                job()
                continue
            self._outcome = CellOutcome()
            self._on_done = on_done
            self._worker = CellWorker(job, self.namespace)
            # Gebundene Methoden: Die Signale kommen aus dem Worker-Thread und
            # werden so als Queued Connection im GUI-Thread zugestellt.
            self._worker.result_ready.connect(self._on_result)
            self._worker.error_occurred.connect(self._on_error)
            self._worker.finished.connect(self._on_finished)
            self._worker.start()
        self._set_busy(self.is_busy())

    def _on_result(self, value, stdout: str) -> None:
        self._outcome = CellOutcome(value=value, stdout=stdout)

    def _on_error(self, error: str, stdout: str) -> None:
        self._outcome = CellOutcome(stdout=stdout, error=error)

    def _on_finished(self) -> None:
        worker, outcome, on_done = self._worker, self._outcome, self._on_done
        self._worker = self._outcome = self._on_done = None
        worker.deleteLater()
        try:
            on_done(outcome)
        finally:
            self._pump()

    def _set_busy(self, busy: bool) -> None:
        if busy != self._busy:
            self._busy = busy
            self.busy_changed.emit(busy)
