from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDockWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from document import InPlaceCell


class StructureOutlineDock(QDockWidget):
    """Collapsible dock displaying the outline hierarchy of the notebook."""

    item_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__("Dokumentstruktur", parent)
        self.setObjectName("DocumentStructureDock")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 8, 6, 6)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background-color: #ffffff;
                font-size: 12px;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 5px 6px;
                border-radius: 4px;
                color: #334155;
            }
            QTreeWidget::item:hover {
                background-color: #f1f5f9;
            }
            QTreeWidget::item:selected {
                background-color: #e0f2fe;
                color: #0369a1;
                font-weight: 600;
            }
        """)
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

        self.setWidget(container)
        self.setMinimumWidth(220)

    def _on_item_clicked(self, item: QTreeWidgetItem):
        idx = item.data(0, Qt.ItemDataRole.UserRole)
        if idx is not None:
            self.item_selected.emit(idx)

    def update_outline(self, cells: list[InPlaceCell]):
        """Parses cell content into hierarchical outline headings."""
        self.tree.clear()
        for idx, cell in enumerate(cells):
            text = cell.editor.toPlainText().strip()
            if not text:
                continue

            effective = cell._detect_effective_mode(text)
            if effective == "markdown":
                for line in text.split("\n"):
                    line = line.strip()
                    if line.startswith("# "):
                        item = QTreeWidgetItem([f"H1  {line[2:].strip()}"])
                        item.setData(0, Qt.ItemDataRole.UserRole, idx)
                        self.tree.addTopLevelItem(item)
                    elif line.startswith("## "):
                        item = QTreeWidgetItem([f"  H2  {line[3:].strip()}"])
                        item.setData(0, Qt.ItemDataRole.UserRole, idx)
                        self.tree.addTopLevelItem(item)
                    elif line.startswith("### "):
                        item = QTreeWidgetItem([f"    H3  {line[4:].strip()}"])
                        item.setData(0, Qt.ItemDataRole.UserRole, idx)
                        self.tree.addTopLevelItem(item)
            else:
                first_line = text.split("\n")[0][:28]
                item = QTreeWidgetItem([f"⚡ {first_line}..."])
                item.setData(0, Qt.ItemDataRole.UserRole, idx)
                self.tree.addTopLevelItem(item)
