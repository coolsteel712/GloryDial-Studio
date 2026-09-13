"""Built-in device profiles seeded into a fresh device database.

K72 (410x502, compression v3) is the device the supplied reference
BIN ("Double Circle.bin") targets, confirmed by parsing its header.
The rest are common round/square smartwatch resolutions provided as a
starting point; none of them are hardcoded elsewhere in the
application - the whole app is device/profile driven and works with
any width/height/version combination entered through the Device
Manager.
"""

from __future__ import annotations

from ..model.device import Device

BUILTIN_DEVICES = [
    Device(name="K72", width=410, height=502, supported_versions="3", notes="Confirmed via sample Double Circle.bin"),
    Device(name="MK68", width=466, height=466, supported_versions="1,2,3", notes="Special-cased TemperatureDigits width in ClockFaceEdit (utilities.getTaxValue)"),
    Device(name="Generic 360x360", width=360, height=360, supported_versions="1,2,3"),
    Device(name="Generic 240x240", width=240, height=240, supported_versions="1,2,3"),
    Device(name="Generic 466x466", width=466, height=466, supported_versions="1,2,3"),
    Device(name="Generic 320x385", width=320, height=385, supported_versions="1,2,3"),
]
