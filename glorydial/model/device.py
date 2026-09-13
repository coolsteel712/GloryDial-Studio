"""Device profiles and device database.

Ported from DbSqliteConnection.java / ControllerSettingDevice.java: the
original tool keeps a SQLite table ``data(id, name, sizescreen,
combobox)`` at ``jre/DB/device.sqlite`` mapping a device name to a
"WxH" screen-size string. GloryDial Studio reproduces that with a
cleaner schema that also records which compression version(s) a device
is known to support (information ClockFaceEdit did not track
explicitly, but which the task requires a Device Manager to capture -
this is a deliberate, additive enhancement, not a format change: it
only affects the *editor's* device list, never the compiled .bin
bytes).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Device:
    name: str
    width: int
    height: int
    supported_versions: str = "1,2,3"  # comma separated, e.g. "3" for K72-only
    notes: str = ""

    @property
    def size_text(self) -> str:
        return f"{self.width}x{self.height}"

    @property
    def version_list(self) -> List[int]:
        out = []
        for chunk in self.supported_versions.split(","):
            chunk = chunk.strip()
            if chunk.isdigit():
                out.append(int(chunk))
        return out or [1, 2, 3]


DEFAULT_DB_PATH = Path.home() / ".glorydial" / "devices.sqlite"


class DeviceDatabase:
    """Thin SQLite wrapper. Safe to construct repeatedly; it creates the
    table and seeds built-in devices on first use."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else DEFAULT_DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                sizescreen TEXT NOT NULL,
                combobox TEXT,
                notes TEXT DEFAULT ''
            )
            """
        )
        self._conn.commit()
        if self.count() == 0:
            from ..devices.seed import BUILTIN_DEVICES

            for dev in BUILTIN_DEVICES:
                try:
                    self.add(dev)
                except ValueError:
                    pass

    def count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM data")
        return cur.fetchone()[0]

    def list_devices(self) -> List[Device]:
        cur = self._conn.execute("SELECT name, sizescreen, combobox, notes FROM data ORDER BY name")
        devices = []
        for row in cur.fetchall():
            w, h = (int(v) for v in row["sizescreen"].split("x"))
            devices.append(
                Device(
                    name=row["name"],
                    width=w,
                    height=h,
                    supported_versions=row["combobox"] or "1,2,3",
                    notes=row["notes"] or "",
                )
            )
        return devices

    def get(self, name: str) -> Optional[Device]:
        for dev in self.list_devices():
            if dev.name.lower() == name.lower():
                return dev
        return None

    def add(self, device: Device) -> None:
        if self.get(device.name) is not None:
            raise ValueError(f"A device named '{device.name}' already exists.")
        if "x" not in device.size_text:
            raise ValueError("Screen size must be formatted as WIDTHxHEIGHT, e.g. 360x360.")
        self._conn.execute(
            "INSERT INTO data(name, sizescreen, combobox, notes) VALUES (?, ?, ?, ?)",
            (device.name, device.size_text, device.supported_versions, device.notes),
        )
        self._conn.commit()

    def update(self, name: str, device: Device) -> None:
        self._conn.execute(
            "UPDATE data SET name=?, sizescreen=?, combobox=?, notes=? WHERE name=?",
            (device.name, device.size_text, device.supported_versions, device.notes, name),
        )
        self._conn.commit()

    def delete(self, name: str) -> None:
        self._conn.execute("DELETE FROM data WHERE name=?", (name,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
