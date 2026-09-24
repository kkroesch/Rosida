import polars as pl
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QTableView, QHeaderView, QMenu
)


class PolarsTableModel(QAbstractTableModel):
    def __init__(self, df: pl.DataFrame):
        super().__init__()
        self._df = df

    def rowCount(self, parent=QModelIndex()):
        return self._df.height

    def columnCount(self, parent=QModelIndex()):
        return self._df.width

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            val = self._df[index.row(), index.column()]
            return "" if val is None else str(val)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._df.columns[section]
            return str(section + 1)
        return None


class PolarsTableWidget(QWidget):
    def __init__(self, df: pl.DataFrame, parent=None):
        super().__init__(parent)
        self.df = df

        self.source_model = PolarsTableModel(df)
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterKeyColumn(-1)

        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)

        header = self.table_view.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._open_header_menu)
        header.setStretchLastSection(True)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Polars DataFrame durchsuchen...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.proxy_model.setFilterFixedString)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.search_input)
        layout.addWidget(self.table_view)

    def _open_header_menu(self, pos):
        menu = QMenu(self)
        header = self.table_view.horizontalHeader()

        for col_idx, col_name in enumerate(self.df.columns):
            action = menu.addAction(col_name)
            action.setCheckable(True)
            action.setChecked(not self.table_view.isColumnHidden(col_idx))
            action.toggled.connect(
                lambda checked, idx=col_idx: self.table_view.setColumnHidden(idx, not checked)
            )

        menu.exec(header.mapToGlobal(pos))
