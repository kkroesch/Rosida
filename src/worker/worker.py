import traceback
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

# 1. Signale für die Kommunikation Worker -> UI
# QRunnable selbst kann keine Signale senden, daher dieser QObject-Wrapper.
class WorkerSignals(QObject):
    started = Signal(str)                  # cell_id
    finished = Signal(str, str)            # cell_id, result_text
    error = Signal(str, str)               # cell_id, error_traceback

# 2. Der generische Worker für ALLE Zelltypen (Python, Prompt, etc.)
class CellWorker(QRunnable):
    def __init__(self, cell_id, execution_function, *args, **kwargs):
        super().__init__()
        self.cell_id = cell_id
        self.execution_function = execution_function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        self.signals.started.emit(self.cell_id)
        try:
            # Hier läuft die blockierende Arbeit im Hintergrund-Thread
            result = self.execution_function(*self.args, **self.kwargs)
            self.signals.finished.emit(self.cell_id, str(result))
        except Exception:
            # Fängt Abstürze im Python-Code oder Netzwerk-Timeouts ab
            self.signals.error.emit(self.cell_id, traceback.format_exc())

# 3. Die spezifischen Executors (die eigentliche Logik)
class PromptExecutor:
    def execute_blocking(self, prompt_text, model="jev"):
        # Simuliert Netzwerk-Latenz oder lokales LLM
        import time
        time.sleep(2)
        return f"**Relevanz:** Hoch (simuliert für '{prompt_text}')"

class PythonExecutor:
    def execute_blocking(self, code_text):
        # Simuliert Datenverarbeitung
        import time
        time.sleep(3)
        return "Polars DataFrame Output..."

# 4. Integration in den Rosida Main-Thread (UI)
class RosidaEngine:
    def __init__(self):
        self.thread_pool = QThreadPool.globalInstance()
        self.prompt_exec = PromptExecutor()

    def run_cell(self, cell_id, content, cell_type="prompt"):
        if cell_type == "prompt":
            worker = CellWorker(cell_id, self.prompt_exec.execute_blocking, content)
        else:
            return

        # Signale mit der UI verknüpfen
        worker.signals.started.connect(self.on_cell_started)
        worker.signals.finished.connect(self.on_cell_finished)
        worker.signals.error.connect(self.on_cell_error)

        # Ab in den Hintergrund damit!
        self.thread_pool.start(worker)

    @Slot(str)
    def on_cell_started(self, cell_id):
        print(f"UI Update: Zelle {cell_id} lädt (Spinner anzeigen...)")

    @Slot(str, str)
    def on_cell_finished(self, cell_id, result):
        print(f"UI Update: Zelle {cell_id} fertig. Füge Text ein:\n{result}")

    @Slot(str, str)
    def on_cell_error(self, cell_id, error_msg):
        print(f"UI Update: Fehler in Zelle {cell_id}:\n{error_msg}")
