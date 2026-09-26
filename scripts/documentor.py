"""Erzeugt UML Dokumentation.

"""

import ast
from pathlib import Path


class CodeModelVisitor(ast.NodeVisitor):

  def __init__(self):
    self.classes = {}  # {ClassName: {"bases": [...], "signals": [...], "methods": [...]}}
    self.connections = []  # [(sender_expr, signal_name, slot_expr)]
    self.current_class = None

  def visit_ClassDef(self, node: ast.ClassDef):
    bases = [ast.unparse(b) for b in node.bases]
    self.classes[node.name] = {"bases": bases, "signals": [], "methods": []}
    prev_class = self.current_class
    self.current_class = node.name

    for item in node.body:
      # 1. Signale finden: signal_name = Signal(...)
      if isinstance(item, ast.Assign):
        for target in item.targets:
          if isinstance(target, ast.Name):
            val_str = ast.unparse(item.value)
            if "Signal(" in val_str:
              # Typ-Argumente aus Signal(...) extrahieren
              args = val_str[val_str.find("(") + 1 : val_str.rfind(")")]
              self.classes[node.name]["signals"].append(
                  (target.id, args or "void")
              )

      # 2. Methoden sammeln (ohne private Dunder, außer __init__)
      elif isinstance(item, ast.FunctionDef):
        if not item.name.startswith("__") or item.name == "__init__":
          args = [
              a.arg for a in item.args.args if a.arg not in ("self", "cls")
          ]
          self.classes[node.name]["methods"].append(
              f"{item.name}({', '.join(args)})"
          )

    self.generic_visit(node)
    self.current_class = prev_class

  def visit_Call(self, node: ast.Call):
    # 3. Verbindungen aufspüren: <emitter>.<signal>.connect(<slot>)
    if isinstance(node.func, ast.Attribute) and node.func.attr == "connect":
      signal_expr = node.func.value
      slot_expr = ast.unparse(node.args[0]) if node.args else "???"

      if isinstance(signal_expr, ast.Attribute):
        signal_name = signal_expr.attr
        emitter_expr = ast.unparse(signal_expr.value)
        self.connections.append((emitter_expr, signal_name, slot_expr))

    self.generic_visit(node)


def generate_plantuml(source_dir: Path, out_dir: Path):
  visitor = CodeModelVisitor()

  for py_file in source_dir.rglob("*.py"):
    try:
      tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
      visitor.visit(tree)
    except SyntaxError:
      continue

  out_dir.mkdir(parents=True, exist_ok=True)

  # --- 1. Klassendiagramm ---
  class_lines = [
      "@startuml",
      "skinparam classAttributeIconSize 0",
      "skinparam monochrome true",
      "hide empty members",
  ]

  for cls, data in visitor.classes.items():
    class_lines.append(f"class {cls} {{")
    for sig, sig_type in data["signals"]:
      class_lines.append(f"  {{field}} ⚡ +{sig} : Signal({sig_type})")
    for m in data["methods"][:8]:  # Fokus auf die ersten 8 Methoden
      class_lines.append(f"  +{m}")
    if len(data["methods"]) > 8:
      class_lines.append("  +...")
    class_lines.append("}")

    for base in data["bases"]:
      # Nur erben lassen, wenn die Basisklasse im Scope ist oder ein bekanntes Qt-Widget
      clean_base = base.split(".")[-1]
      class_lines.append(f"{clean_base} <|-- {cls}")

  class_lines.append("@enduml\n")
  (out_dir / "classes.puml").write_text("\n".join(class_lines), encoding="utf-8")

  # --- 2. Signal-Flow-Diagramm ---
  wire_lines = [
      "@startuml",
      "skinparam componentStyle rectangle",
      "skinparam arrowThickness 1.2",
      'title Rosida Signal-Slot Verkabelung (Runtime Connections)',
  ]

  for emitter, sig, slot in visitor.connections:
    # Bereinigung: self.doc -> DocumentCanvas o.ä.
    src = emitter.replace("self.", "")
    dst = slot.replace("self.", "")
    wire_lines.append(f'[{src}] --> [{dst}] : <<{sig}>>')

  wire_lines.append("@enduml\n")
  (out_dir / "signals.puml").write_text("\n".join(wire_lines), encoding="utf-8")


if __name__ == "__main__":
  generate_plantuml(Path("."), Path("docs/diagrams"))
