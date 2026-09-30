import json
import re

import yaml

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QStackedWidget
from PySide6.QtCore import Qt, Signal

from .inline_editor import InlineEditor


def parse_yaml_properties(yaml_text: str) -> dict:
    """Parses the bare YAML of the properties editor (without --- markers)."""
    try:
        data = yaml.safe_load(yaml_text) if yaml_text.strip() else {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _yaml_scalar(value: str) -> str:
    """Plain YAML scalar if unambiguous, otherwise double-quoted (JSON is valid YAML)."""
    return value if re.fullmatch(r"[\w./-]+", value) else json.dumps(value)


def set_yaml_property(yaml_text: str, key: str, value: str | list[str]) -> str:
    """Sets a top-level key line by line, keeping order, quoting and comments.

    An existing value (including an indented block such as a list) is
    replaced; otherwise the key is appended.
    """
    lines = yaml_text.splitlines()
    if isinstance(value, list):
        rendered = "[" + ", ".join(_yaml_scalar(v) for v in value) + "]"
    else:
        rendered = _yaml_scalar(value)
    new_line = f"{key}: {rendered}"
    for i, line in enumerate(lines):
        if re.match(rf"{re.escape(key)}\s*:", line):
            end = i + 1
            while end < len(lines) and (
                lines[end].startswith((" ", "\t", "-")) or not lines[end].strip()
            ):
                end += 1
            # Leerzeilen am Blockende gehören nicht zum Wert
            while end > i + 1 and not lines[end - 1].strip():
                end -= 1
            lines[i:end] = [new_line]
            break
    else:
        lines.append(new_line)
    return "\n".join(lines)


class FrontmatterCell(QWidget):
    # Geparste Dokumenteigenschaften nach jeder Übernahme (z.B. für das BibTeX-Dock)
    frontmatter_updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        # Zustand 0: Eingeklappt (Kompakter Button)
        self.btn_collapsed = QPushButton(self.tr("⏵ Document properties"))
        self.btn_collapsed.setStyleSheet("text-align: left; color: gray; border: none;")
        self.btn_collapsed.clicked.connect(self.expand)

        self.editor = InlineEditor()
        self.editor.run_requested.connect(self.commit_and_collapse)
        self.stack.addWidget(self.btn_collapsed)
        self.stack.addWidget(self.editor)

        # Standardmäßig ausgeklappt starten
        self.stack.setCurrentIndex(1)

    def metadata(self) -> dict:
        return parse_yaml_properties(self.editor.toPlainText())

    def commit_and_collapse(self):
        metadata = self.metadata()

        # Text im Button anpassen (z.B. Titel anzeigen)
        title = metadata.get("title") or self.tr("Document properties")
        self.btn_collapsed.setText(f"⏵ {title}")

        # Zelle einklappen
        self.stack.setCurrentIndex(0)
        self.frontmatter_updated.emit(metadata)

    def set_property(self, key: str, value: str):
        """Writes one top-level property into the YAML and commits it."""
        self.editor.setPlainText(
            set_yaml_property(self.editor.toPlainText(), key, value)
        )
        self.commit_and_collapse()

    def expand(self):
        self.stack.setCurrentIndex(1)
        self.editor.setFocus()
