"""Dialog to add a new block type to the project - lists every block
name from the ClockFaceEdit schema not already used in this project."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QListWidgetItem, QVBoxLayout

from ...model import block_schema
from ...model.block import Project


class AddBlockDialog(QDialog):
    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Block")
        self.resize(320, 420)
        self.chosen_type_id: Optional[int] = None

        layout = QVBoxLayout(self)
        self.list = QListWidget()
        for type_id in sorted(block_schema.BLOCK_NAME_BY_ID):
            if type_id in project.blocks:
                continue
            name = block_schema.block_name(type_id)
            item = QListWidgetItem(f"{name}  (id {type_id})")
            item.setData(1000, type_id)
            self.list.addItem(item)
        self.list.itemDoubleClicked.connect(lambda _: self.accept())
        layout.addWidget(self.list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        items = self.list.selectedItems()
        if items:
            self.chosen_type_id = items[0].data(1000)
        super().accept()
