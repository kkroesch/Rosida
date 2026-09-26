from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class VariableInspectorDock(QDockWidget):

  def __init__(self, parent=None):
    super().__init__("Variablen", parent)
    self.setObjectName("DockVariableInspector")
    self.setAllowedAreas(
        Qt.DockWidgetArea.LeftDockWidgetArea
        | Qt.DockWidgetArea.RightDockWidgetArea
    )

    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    self.table = QTableWidget(0, 3)
    self.table.setHorizontalHeaderLabels(["Name", "Typ", "Wert"])
    self.table.verticalHeader().setVisible(False)
    self.table.setAlternatingRowColors(True)
    self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    # Spaltenanpassung: Name & Typ eng, Wert nimmt den Rest
    header = self.table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

    layout.addWidget(self.table)
    self.setWidget(container)

  def update_variables(self, variables: list[dict]):
    self.table.setRowCount(len(variables))
    for row, item in enumerate(variables):
      name_item = QTableWidgetItem(item["name"])
      type_item = QTableWidgetItem(item["type"])
      val_item = QTableWidgetItem(item["value"])

      # Dezentere Farbe für den Typen
      type_item.setForeground(Qt.GlobalColor.darkGray)

      self.table.setItem(row, 0, name_item)
      self.table.setItem(row, 1, type_item)
      self.table.setItem(row, 2, val_item)
