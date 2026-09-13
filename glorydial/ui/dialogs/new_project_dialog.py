"""New Project dialog - pick a device profile (or a custom size) and
the compression version to author for."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
)

from ...model.device import Device, DeviceDatabase


class NewProjectDialog(QDialog):
    def __init__(self, db: DeviceDatabase, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Clock Face")
        self.resize(360, 220)
        self.db = db
        self.result_device: Optional[Device] = None
        self.result_version: int = 3

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.device_combo = QComboBox()
        self.devices = db.list_devices()
        for dev in self.devices:
            self.device_combo.addItem(f"{dev.name} ({dev.size_text})")
        self.device_combo.addItem("Custom size...")
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        form.addRow("Device", self.device_combo)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(16, 4096)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(16, 4096)
        form.addRow("Width", self.width_spin)
        form.addRow("Height", self.height_spin)

        self.version_combo = QComboBox()
        self.version_combo.addItems(["1 - no compression", "2 - scanline RLE", "3 - LZ4"])
        self.version_combo.setCurrentIndex(2)
        form.addRow("Compression version", self.version_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if self.devices:
            self._on_device_changed(0)

    def _on_device_changed(self, index: int) -> None:
        if 0 <= index < len(self.devices):
            dev = self.devices[index]
            self.width_spin.setValue(dev.width)
            self.height_spin.setValue(dev.height)
            self.width_spin.setEnabled(False)
            self.height_spin.setEnabled(False)
        else:
            self.width_spin.setEnabled(True)
            self.height_spin.setEnabled(True)

    def accept(self) -> None:
        idx = self.device_combo.currentIndex()
        if 0 <= idx < len(self.devices):
            self.result_device = self.devices[idx]
        else:
            self.result_device = Device(name="Custom", width=self.width_spin.value(), height=self.height_spin.value())
        self.result_version = self.version_combo.currentIndex() + 1
        super().accept()
