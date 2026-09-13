"""Layers / block tree panel."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..model.block import Project
from ..model import block_schema

COL_NAME, COL_ID, COL_FRAMES, COL_VISIBLE = range(4)


class LayersPanel(QWidget):
    block_selected = pyqtSignal(int)
    visibility_toggled = pyqtSignal(int, bool)
    delete_requested = pyqtSignal(int)
    duplicate_requested = pyqtSignal(int)
    add_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Block", "ID", "Frames", "Visible"])
        self.tree.header().setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.tree)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Block")
        add_btn.clicked.connect(self.add_requested.emit)
        btn_row.addWidget(add_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self._updating = False

    def refresh(self, project: Project, selected_id: Optional[int] = None) -> None:
        self._updating = True
        self.tree.clear()
        for block in project.ordered_blocks_for_compile():
            item = QTreeWidgetItem([block.name, str(block.type_id), str(block.images_count), ""])
            item.setData(0, Qt.ItemDataRole.UserRole, block.type_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(COL_VISIBLE, Qt.CheckState.Checked if block.visible else Qt.CheckState.Unchecked)
            if block.is_hand:
                item.setForeground(0, self.palette().highlight())
            self.tree.addTopLevelItem(item)
            if selected_id is not None and block.type_id == selected_id:
                item.setSelected(True)
        self._updating = False

    def _on_selection_changed(self) -> None:
        if self._updating:
            return
        items = self.tree.selectedItems()
        if items:
            self.block_selected.emit(items[0].data(0, Qt.ItemDataRole.UserRole))

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._updating or column != COL_VISIBLE:
            return
        type_id = item.data(0, Qt.ItemDataRole.UserRole)
        self.visibility_toggled.emit(type_id, item.checkState(COL_VISIBLE) == Qt.CheckState.Checked)

    def _on_context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if item is None:
            return
        type_id = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        dup_action = menu.addAction("Duplicate frames from...")
        del_action = menu.addAction("Delete block")
        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if chosen == dup_action:
            self.duplicate_requested.emit(type_id)
        elif chosen == del_action:
            self.delete_requested.emit(type_id)
