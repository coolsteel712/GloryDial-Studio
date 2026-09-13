"""Device Manager: select / add / edit / delete device profiles.

Ported behaviorally from ControllerSettingDevice.java's SQLite-backed
device list (see model/device.py for the DB layer itself).
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...model.device import Device, DeviceDatabase


class DeviceManagerDialog(QDialog):
    def __init__(self, db: DeviceDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.selected_device: Optional[Device] = None
        self.setWindowTitle("Device Manager")
        self.resize(560, 420)

        root = QHBoxLayout(self)

        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.itemSelectionChanged.connect(self._on_select)
        left.addWidget(self.list)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 4096)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 4096)
        self.versions_edit = QLineEdit()
        self.versions_edit.setPlaceholderText("e.g. 1,2,3 or just 3")
        self.notes_edit = QLineEdit()
        form.addRow("Name", self.name_edit)
        form.addRow("Width", self.width_spin)
        form.addRow("Height", self.height_spin)
        form.addRow("Supported versions", self.versions_edit)
        form.addRow("Notes", self.notes_edit)
        right.addLayout(form)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add New")
        add_btn.clicked.connect(self._on_add)
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self._on_save)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(delete_btn)
        right.addLayout(btn_row)
        right.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        right.addWidget(buttons)

        root.addLayout(right, 1)
        self._refresh_list()

    def _refresh_list(self, select_name: Optional[str] = None) -> None:
        self.list.clear()
        for dev in self.db.list_devices():
            item = QListWidgetItem(f"{dev.name}  ({dev.size_text})")
            item.setData(1000, dev.name)
            self.list.addItem(item)
            if select_name and dev.name == select_name:
                item.setSelected(True)

    def _on_select(self) -> None:
        items = self.list.selectedItems()
        if not items:
            return
        name = items[0].data(1000)
        dev = self.db.get(name)
        if dev is None:
            return
        self.name_edit.setText(dev.name)
        self.width_spin.setValue(dev.width)
        self.height_spin.setValue(dev.height)
        self.versions_edit.setText(dev.supported_versions)
        self.notes_edit.setText(dev.notes)

    def _current_form_device(self) -> Optional[Device]:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please enter a device name.")
            return None
        return Device(
            name=name,
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            supported_versions=self.versions_edit.text().strip() or "1,2,3",
            notes=self.notes_edit.text().strip(),
        )

    def _on_add(self) -> None:
        dev = self._current_form_device()
        if dev is None:
            return
        try:
            self.db.add(dev)
        except ValueError as e:
            QMessageBox.warning(self, "Could not add device", str(e))
            return
        self._refresh_list(select_name=dev.name)

    def _on_save(self) -> None:
        items = self.list.selectedItems()
        if not items:
            QMessageBox.information(self, "No selection", "Select a device to update, or use Add New.")
            return
        original_name = items[0].data(1000)
        dev = self._current_form_device()
        if dev is None:
            return
        self.db.update(original_name, dev)
        self._refresh_list(select_name=dev.name)

    def _on_delete(self) -> None:
        items = self.list.selectedItems()
        if not items:
            return
        name = items[0].data(1000)
        if QMessageBox.question(self, "Delete device", f"Delete device '{name}'?") == QMessageBox.StandardButton.Yes:
            self.db.delete(name)
            self._refresh_list()

    def _on_accept(self) -> None:
        items = self.list.selectedItems()
        if items:
            self.selected_device = self.db.get(items[0].data(1000))
        self.accept()
