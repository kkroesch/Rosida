import ast
import traceback
from PySide6.QtCore import QThread, Signal


class CellWorker(QThread):
    # Signale für die sichere Kommunikation zurück zum Main-Thread
    result_ready = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, code_text, local_namespace, parent=None):
        super().__init__(parent)
        self.code_text = code_text
        self.local_namespace = local_namespace

    def run(self):
        """Wird asynchron ausgeführt, sobald .start() aufgerufen wird."""
        try:
            tree = ast.parse(self.code_text)
            if not tree.body:
                self.result_ready.emit(None)
                return

            last_node = tree.body[-1]
            result = None

            if isinstance(last_node, ast.Expr):
                # Alles außer der letzten Zeile ausführen
                exec_tree = ast.Module(body=tree.body[:-1], type_ignores=[])
                exec_code = compile(exec_tree, filename="<ast>", mode="exec")
                exec(exec_code, self.local_namespace)

                # Letzte Zeile evaluieren
                eval_tree = ast.Expression(body=last_node.value)
                eval_code = compile(eval_tree, filename="<ast>", mode="eval")
                result = eval(eval_code, self.local_namespace)
            else:
                exec(self.code_text, self.local_namespace)

            # Ergebnis an die GUI funken
            self.result_ready.emit(result)

        except Exception as e:
            # Bei einem Fehler den genauen Traceback in die GUI schicken
            self.error_occurred.emit(traceback.format_exc())
