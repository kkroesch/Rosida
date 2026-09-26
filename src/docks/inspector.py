from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class VariableInspectorDock(QDockWidget):
  # Signal meldet den Variablennamen als String
  variable_double_clicked = Signal(str)

  def __init__(self, parent=None):
    super().__init__("Variablen", parent)
    self.setObjectName("DockVariableInspector")

    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    self.table = QTableWidget(0, 3)
    self.table.setHorizontalHeaderLabels(["Name", "Typ", "Wert"])
    self.table.verticalHeader().setVisible(False)
    self.table.setAlternatingRowColors(True)
    self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    # Doppelklick auf Tabellenzeile abfangen
    self.table.cellDoubleClicked.connect(self._on_row_double_clicked)

    header = self.table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

    layout.addWidget(self.table)
    self.setWidget(container)

  def _on_row_double_clicked(self, row: int, _column: int):
    # Name steht immer in Spalte 0
    name_item = self.table.item(row, 0)
    if name_item:
      self.variable_double_clicked.emit(name_item.text())

  def update_variables(self, variables: list[dict]):
    self.table.setRowCount(len(variables))
    for row, item in enumerate(variables):
      name_item = QTableWidgetItem(item["name"])
      type_item = QTableWidgetItem(item["type"])
      val_item = QTableWidgetItem(item["value"])

      type_item.setForeground(Qt.GlobalColor.darkGray)

      self.table.setItem(row, 0, name_item)
      self.table.setItem(row, 1, type_item)
      self.table.setItem(row, 2, val_item)
