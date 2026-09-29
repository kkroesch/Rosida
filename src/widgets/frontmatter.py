import yaml

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QStackedWidget
from PySide6.QtCore import Qt

from .inline_editor import InlineEditor


def parse_frontmatter(document_text):
    """
    Trennt das YAML-Frontmatter vom Rest des Dokuments.
    Gibt ein Dictionary mit den Metadaten zurück.
    """
    # Prüfen, ob das Dokument strikt mit --- beginnt
    if not document_text.startswith("---"):
        return {}

    # Den Text an den '---' Markern aufsplitten (maxsplit=2)
    parts = document_text.split("---", 2)

    if len(parts) >= 3:
        yaml_content = parts[1]
        try:
            # safe_load ist wichtig, damit keine schadhaften Python-Objekte ausgeführt werden
            metadata = yaml.safe_load(yaml_content)
            return metadata if metadata else {}
        except yaml.YAMLError as e:
            print(f"Fehler beim Parsen des Frontmatters: {e}")
            return {}

    return {}


class FrontmatterCell(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        # Zustand 0: Eingeklappt (Kompakter Button)
        self.btn_collapsed = QPushButton("⏵ Dokcument Properties")
        self.btn_collapsed.setStyleSheet("text-align: left; color: gray; border: none;")
        self.btn_collapsed.clicked.connect(self.expand)

        self.editor = InlineEditor()
        self.editor.run_requested.connect(self.commit_and_collapse)
        self.stack.addWidget(self.btn_collapsed)
        self.stack.addWidget(self.editor)

        # Standardmäßig ausgeklappt starten
        self.stack.setCurrentIndex(1)

    def commit_and_collapse(self):
        text = self.editor.toPlainText()
        metadata = parse_frontmatter(text)

        # TODO: Hier Signal feuern, um Docks (wie BibTeX) zu aktualisieren
        # self.frontmatter_updated.emit(metadata)

        # Text im Button anpassen (z.B. Titel anzeigen)
        title = metadata.get("title", "Properties")
        self.btn_collapsed.setText(f"⏵ {title}")

        # Zelle einklappen
        self.stack.setCurrentIndex(0)

    def expand(self):
        self.stack.setCurrentIndex(1)
        self.editor.setFocus()
