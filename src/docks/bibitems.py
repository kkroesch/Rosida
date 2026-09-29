from pathlib import Path
import re

from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QStackedWidget,
    QFileDialog,
)
from PySide6.QtCore import Signal, Qt


class BibItemWidget(QWidget):
    """Fehlertolerantes UI-Element für einen einzelnen Zettelkasten-Eintrag."""

    def __init__(self, key, author="", title="", parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)

        # Fallbacks für unsaubere BibTeX-Daten
        display_author = author if author else "Unbekannter Autor"
        display_title = title if title else "Kein Titel"

        layout.addWidget(QLabel(f"<b>[{key}]</b>"))
        layout.addWidget(QLabel(f"<i>{display_author}</i>"))

        lbl_title = QLabel(display_title)
        lbl_title.setWordWrap(True)
        layout.addWidget(lbl_title)


class BibDock(QDockWidget):
    """Dock-Widget mit integriertem Stack für nahtloses Umschalten zwischen Button und Liste."""

    # Sendet ausschließlich den fertigen Quarto-String nach außen (z.B. "[@Asimov1956]")
    citation_selected = Signal(str)
    # Vom Benutzer gewählte .bib-Datei (absoluter Pfad); das Hauptfenster
    # trägt sie als bibliography in die Frontmatter ein.
    bib_file_chosen = Signal(str)

    def __init__(self, parent=None):
        super().__init__("References", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.stack = QStackedWidget()
        self.setWidget(self.stack)

        # Seite 0: Initialer Lade-Button
        self.btn_load = QPushButton("Load References (.bib)")
        self.btn_load.clicked.connect(self.choose_bib_file)
        self.lbl_hint = QLabel()
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet("color: #64748b; font-size: 11px;")

        page_load = QWidget()
        page_load_layout = QVBoxLayout(page_load)
        page_load_layout.addWidget(self.btn_load)
        page_load_layout.addWidget(self.lbl_hint)
        page_load_layout.addStretch()

        # Seite 1: Die scrollbare Literatur-Liste mit Dateiname und Wechsel-Button
        self.lbl_source = QLabel()
        self.lbl_source.setStyleSheet("color: #64748b; font-size: 11px;")
        btn_change = QPushButton("Ändern …")
        btn_change.setToolTip("Andere Literaturdatei wählen")
        btn_change.clicked.connect(self.choose_bib_file)
        header = QHBoxLayout()
        header.setContentsMargins(4, 4, 4, 0)
        header.addWidget(self.lbl_source, 1)
        header.addWidget(btn_change)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        page_list = QWidget()
        page_list_layout = QVBoxLayout(page_list)
        page_list_layout.setContentsMargins(0, 0, 0, 0)
        page_list_layout.addLayout(header)
        page_list_layout.addWidget(self.list_widget)

        self.stack.addWidget(page_load)
        self.stack.addWidget(page_list)
        self._start_dir = ""

    def choose_bib_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "BibTeX-Datei wählen",
            self._start_dir,
            "BibTeX (*.bib);;Alle Dateien (*)",
        )
        if file_path:
            self.bib_file_chosen.emit(file_path)

    def show_bibliography(self, files: list[Path], start_dir: str = ""):
        """Loads the given .bib files, or shows the load button if there are none.

        Missing files are named in a hint below the button.
        """
        self._start_dir = start_dir
        existing = [f for f in files if f.is_file()]
        missing = [f.name for f in files if not f.is_file()]

        entries = []
        for f in existing:
            entries.extend(self._parse_bibtex_lightweight(f))
        self.populate_list(entries)

        if existing:
            self.lbl_source.setText(", ".join(f.name for f in existing))
            self.lbl_source.setToolTip("\n".join(str(f) for f in existing))
            self.stack.setCurrentIndex(1)
        else:
            self.lbl_hint.setText(
                f"Nicht gefunden: {', '.join(missing)}" if missing else ""
            )
            self.stack.setCurrentIndex(0)

    def _parse_bibtex_lightweight(self, file_path):
        """Minimalistischer Parser, der fehlertolerant über die Datei iteriert."""
        entries = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return []

        # Teile bei jedem '@' auf, ignoriere den Datei-Header vor dem ersten Eintrag
        for block in content.split("@")[1:]:
            lines = block.strip().split("\n")
            if not lines:
                continue

            # Erste Zeile enthält Typ und Key, z.B. "article{Asimov1956,"
            first_line = lines[0]
            if "{" not in first_line:
                continue

            # Key extrahieren
            key = first_line.split("{")[1].split(",")[0].strip()
            entry = {"key": key, "author": "", "title": ""}

            # Rohen Text des Blocks für non-greedy Regex zusammenfassen
            block_text = " ".join(lines)

            # Sucht nach author/title = {...} oder = "...", ignoriert Zeilenumbrüche
            author_match = re.search(
                r'\bauthor\s*=\s*[\{"](.*?)(?:[\}"]\s*,|[\}"]\s*$)',
                block_text,
                re.IGNORECASE,
            )
            if author_match:
                entry["author"] = author_match.group(1).strip()

            title_match = re.search(
                r'\btitle\s*=\s*[\{"](.*?)(?:[\}"]\s*,|[\}"]\s*$)',
                block_text,
                re.IGNORECASE,
            )
            if title_match:
                entry["title"] = title_match.group(1).strip()

            # Bereinigt typische LaTeX-Schutzklammern (z.B. {B}austeine -> Bausteine)
            entry["title"] = entry["title"].replace("{", "").replace("}", "")
            entry["author"] = entry["author"].replace("{", "").replace("}", "")

            entries.append(entry)

        return entries

    def populate_list(self, entries):
        self.list_widget.clear()

        for entry in entries:
            item = QListWidgetItem(self.list_widget)

            # Widget mit Fallbacks initialisieren
            custom_widget = BibItemWidget(
                key=entry.get("key", "Unknown"),
                author=entry.get("author", ""),
                title=entry.get("title", ""),
            )

            # Größe anpassen und den Key unsichtbar im Item hinterlegen
            item.setSizeHint(custom_widget.sizeHint())
            item.setData(Qt.UserRole, entry.get("key", ""))

            self.list_widget.setItemWidget(item, custom_widget)

    def on_item_double_clicked(self, item):
        bib_key = item.data(Qt.UserRole)
        if bib_key:
            self.citation_selected.emit(f"[@{bib_key}]")
