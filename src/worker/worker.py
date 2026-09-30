import ast
from io import StringIO
import sys
import threading
import traceback

from PySide6.QtCore import QThread, Signal


class _ThreadLocalStdout:
    """sys.stdout-Ersatz, der pro Thread in einen eigenen Puffer umleiten kann.

    contextlib.redirect_stdout tauscht sys.stdout prozessweit; während eine
    Zelle im Worker läuft, landeten sonst auch print()-Ausgaben des
    GUI-Threads in der Zellausgabe.
    """

    def __init__(self, fallback):
        self._fallback = fallback
        self._local = threading.local()

    def capture(self, buffer: StringIO | None):
        self._local.buffer = buffer

    def _target(self):
        return getattr(self._local, "buffer", None) or self._fallback

    def write(self, text):
        return self._target().write(text)

    def flush(self):
        self._target().flush()

    def __getattr__(self, name):
        return getattr(self._target(), name)


def _stdout_proxy() -> _ThreadLocalStdout:
    if not isinstance(sys.stdout, _ThreadLocalStdout):
        sys.stdout = _ThreadLocalStdout(sys.stdout)
    return sys.stdout


class CellWorker(QThread):
    # Signale für die sichere Kommunikation zurück zum Main-Thread
    result_ready = Signal(object, str)  # Wert der letzten Zeile, stdout
    error_occurred = Signal(str, str)  # Traceback, stdout

    def __init__(self, code_text, local_namespace, parent=None):
        super().__init__(parent)
        self.code_text = code_text
        self.local_namespace = local_namespace

    def run(self):
        """Wird asynchron ausgeführt, sobald .start() aufgerufen wird."""
        stdout = _stdout_proxy()
        buffer = StringIO()
        stdout.capture(buffer)
        try:
            result = self._execute()
            self.result_ready.emit(result, buffer.getvalue())
        except Exception:
            # Bei einem Fehler den genauen Traceback in die GUI schicken
            self.error_occurred.emit(traceback.format_exc(), buffer.getvalue())
        finally:
            stdout.capture(None)

    def _execute(self):
        tree = ast.parse(self.code_text, filename="<cell>")
        if not tree.body:
            return None

        last_node = tree.body[-1]
        if not isinstance(last_node, ast.Expr):
            exec(compile(tree, "<cell>", "exec"), self.local_namespace)
            return None

        # Alles außer der letzten Zeile ausführen
        exec_tree = ast.Module(body=tree.body[:-1], type_ignores=[])
        exec(compile(exec_tree, "<cell>", "exec"), self.local_namespace)

        # Letzte Zeile evaluieren
        eval_tree = ast.Expression(body=last_node.value)
        return eval(compile(eval_tree, "<cell>", "eval"), self.local_namespace)
