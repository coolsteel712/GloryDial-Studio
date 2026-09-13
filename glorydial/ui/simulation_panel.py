"""Controls for the simulated time/date/sensor values the live preview
renders against - see rendering/simulation.py."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import QDate, QDateTime, QTime, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDateTimeEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..rendering.simulation import SimState


class SimulationPanel(QWidget):
    changed = pyqtSignal(SimState)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = SimState()
        self._updating = False
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(1000)
        self._live_timer.timeout.connect(self._tick_live)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        time_box = QGroupBox("Time && Date")
        tform = QFormLayout(time_box)
        self.datetime_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.datetime_edit.dateTimeChanged.connect(self._on_datetime_changed)
        tform.addRow("Date/Time", self.datetime_edit)

        self.live_check = QCheckBox("Use system time (live)")
        self.live_check.stateChanged.connect(self._on_live_toggled)
        tform.addRow(self.live_check)

        self.hour12_check = QCheckBox("12-hour format")
        self.hour12_check.stateChanged.connect(lambda v: self._update_field("use_12_hour", bool(v)))
        tform.addRow(self.hour12_check)
        layout.addWidget(time_box)

        sensors_box = QGroupBox("Sensors && Activity")
        sform = QFormLayout(sensors_box)
        self.battery_slider = self._make_slider(0, 100, self.state.battery_percent)
        self.battery_slider.valueChanged.connect(lambda v: self._update_field("battery_percent", v))
        sform.addRow("Battery %", self.battery_slider)

        self.connected_check = QCheckBox("Connected")
        self.connected_check.setChecked(self.state.connected)
        self.connected_check.stateChanged.connect(lambda v: self._update_field("connected", bool(v)))
        sform.addRow(self.connected_check)

        self.hr_spin = self._make_spin(30, 220, self.state.heart_rate_bpm)
        self.hr_spin.valueChanged.connect(lambda v: self._update_field("heart_rate_bpm", v))
        sform.addRow("Heart rate (bpm)", self.hr_spin)

        self.steps_spin = self._make_spin(0, 99999, self.state.steps)
        self.steps_spin.valueChanged.connect(lambda v: self._update_field("steps", v))
        sform.addRow("Steps", self.steps_spin)

        self.calories_spin = self._make_spin(0, 9999, self.state.calories)
        self.calories_spin.valueChanged.connect(lambda v: self._update_field("calories", v))
        sform.addRow("Calories", self.calories_spin)

        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(0, 999)
        self.distance_spin.setSuffix(" (x0.1 km)")
        self.distance_spin.setValue(int(self.state.distance_km * 10))
        self.distance_spin.valueChanged.connect(lambda v: self._update_field("distance_km", v / 10.0))
        sform.addRow("Distance", self.distance_spin)

        self.temp_spin = self._make_spin(-40, 60, self.state.temperature)
        self.temp_spin.valueChanged.connect(lambda v: self._update_field("temperature", v))
        sform.addRow("Temperature", self.temp_spin)

        self.celsius_check = QCheckBox("Celsius (unchecked = Fahrenheit)")
        self.celsius_check.setChecked(self.state.use_celsius)
        self.celsius_check.stateChanged.connect(lambda v: self._update_field("use_celsius", bool(v)))
        sform.addRow(self.celsius_check)
        layout.addWidget(sensors_box)

        layout.addStretch(1)

    def _make_slider(self, lo, hi, val) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    def _make_spin(self, lo, hi, val) -> QSpinBox:
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    def _update_field(self, field: str, value) -> None:
        if self._updating:
            return
        setattr(self.state, field, value)
        self.changed.emit(self.state)

    def _on_datetime_changed(self, qdt: QDateTime) -> None:
        if self._updating:
            return
        py_dt = qdt.toPyDateTime()
        self.state.dt = py_dt
        self.changed.emit(self.state)

    def _on_live_toggled(self, checked) -> None:
        if checked:
            self._live_timer.start()
            self.datetime_edit.setEnabled(False)
        else:
            self._live_timer.stop()
            self.datetime_edit.setEnabled(True)

    def _tick_live(self) -> None:
        self.state.dt = datetime.now()
        self._updating = True
        self.datetime_edit.setDateTime(QDateTime.currentDateTime())
        self._updating = False
        self.changed.emit(self.state)
