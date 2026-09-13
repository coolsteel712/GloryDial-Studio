"""Property inspector - editable fields mirror ListViewEdit.java exactly:
X, Y, AnimationSpeed, BlackIsTransparent, and (hands only) ArrowFullLength /
ArrowLengthToCenter / ArrowWidth.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..model.block import Block
from ..model import block_schema


class PropertiesPanel(QWidget):
    property_changed = pyqtSignal(int, str, object)  # type_id, field name, value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._type_id: Optional[int] = None
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.title = QLabel("No block selected")
        self.title.setStyleSheet("font-weight: 600; font-size: 15px;")
        layout.addWidget(self.title)

        self.subtitle = QLabel("")
        self.subtitle.setStyleSheet("color: #9a9ba3;")
        layout.addWidget(self.subtitle)

        general_box = QGroupBox("Position && Timing")
        form = QFormLayout(general_box)
        self.x_spin = self._make_spin(-20000, 20000)
        self.y_spin = self._make_spin(-20000, 20000)
        self.anim_spin = self._make_spin(0, 65535)
        form.addRow("X", self.x_spin)
        form.addRow("Y", self.y_spin)
        form.addRow("Animation Speed", self.anim_spin)
        layout.addWidget(general_box)

        appearance_box = QGroupBox("Appearance")
        form2 = QFormLayout(appearance_box)
        self.black_transparent_check = QCheckBox("Black is transparent")
        self.black_transparent_check.stateChanged.connect(
            lambda v: self._emit("black_is_transparent", bool(v))
        )
        form2.addRow(self.black_transparent_check)
        layout.addWidget(appearance_box)

        self.arrow_box = QGroupBox("Hand geometry (ArrowInfo)")
        form3 = QFormLayout(self.arrow_box)
        self.arrow_full_spin = self._make_spin(0, 255)
        self.arrow_center_spin = self._make_spin(0, 255)
        self.arrow_width_spin = self._make_spin(0, 255)
        form3.addRow("Arrow Full Length", self.arrow_full_spin)
        form3.addRow("Arrow Length To Center", self.arrow_center_spin)
        form3.addRow("Arrow Width", self.arrow_width_spin)
        layout.addWidget(self.arrow_box)

        self.digit_box = QGroupBox("Digit glyph pool (preview only)")
        form4 = QFormLayout(self.digit_box)
        self.digit_offset_spin = self._make_spin(-255, 255)
        form4.addRow("Digit '0' is at frame", self.digit_offset_spin)
        digit_hint = QLabel(
            "The file format doesn't record where '0' sits in this\n"
            "block's shared glyph pool - compare against the Frames\n"
            "strip below and adjust if digits look wrong. This only\n"
            "affects the live preview, never the saved .bin."
        )
        digit_hint.setStyleSheet("color: #9a9ba3; font-size: 11px;")
        digit_hint.setWordWrap(True)
        form4.addRow(digit_hint)
        layout.addWidget(self.digit_box)

        layout.addStretch(1)
        self.setEnabled(False)

    def _make_spin(self, lo: int, hi: int) -> QSpinBox:
        s = QSpinBox()
        s.setRange(lo, hi)
        s.valueChanged.connect(self._on_spin_changed)
        return s

    def _emit(self, field: str, value) -> None:
        if self._updating or self._type_id is None:
            return
        self.property_changed.emit(self._type_id, field, value)

    def _on_spin_changed(self, _value: int) -> None:
        if self._updating or self._type_id is None:
            return
        sender = self.sender()
        mapping = {
            self.x_spin: "x",
            self.y_spin: "y",
            self.anim_spin: "animation_speed",
            self.arrow_full_spin: "arrow_full_length",
            self.arrow_center_spin: "arrow_length_to_center",
            self.arrow_width_spin: "arrow_width",
            self.digit_offset_spin: "digit_glyph_offset",
        }
        field = mapping.get(sender)
        if field:
            self.property_changed.emit(self._type_id, field, sender.value())

    def show_block(self, block: Optional[Block]) -> None:
        self._updating = True
        try:
            if block is None:
                self._type_id = None
                self.title.setText("No block selected")
                self.subtitle.setText("")
                self.setEnabled(False)
                return
            self.setEnabled(True)
            self._type_id = block.type_id
            self.title.setText(block.name)
            self.subtitle.setText(
                f"Type ID {block.type_id} · {block.images_count} frame(s) · "
                f"{block.width}x{block.height}"
            )
            self.x_spin.setValue(block.x)
            self.y_spin.setValue(block.y)
            self.anim_spin.setValue(block.animation_speed)
            self.black_transparent_check.setChecked(block.black_is_transparent)
            self.arrow_box.setVisible(block.is_hand)
            if block.is_hand:
                self.arrow_full_spin.setValue(block.arrow_full_length)
                self.arrow_center_spin.setValue(block.arrow_length_to_center)
                self.arrow_width_spin.setValue(block.arrow_width)

            is_compound = block_schema.compound_digit_count(block.name) is not None
            self.digit_box.setVisible(is_compound)
            if is_compound:
                self.digit_offset_spin.setValue(block.digit_glyph_offset)
        finally:
            self._updating = False
