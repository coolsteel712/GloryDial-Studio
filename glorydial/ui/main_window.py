"""GloryDial Studio main window."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QToolBar,
    QWidget,
)

from ..formats import reader, writer
from ..formats.errors import ValidationError
from ..model import block_schema
from ..model.block import Block, Frame, Project, ProjectHeader
from ..model.device import Device, DeviceDatabase
from ..rendering.simulation import SimState
from .canvas import WatchCanvasView
from .dialogs.add_block_dialog import AddBlockDialog
from .dialogs.device_manager import DeviceManagerDialog
from .dialogs.new_project_dialog import NewProjectDialog
from .layers import LayersPanel
from .properties import PropertiesPanel
from .simulation_panel import SimulationPanel
from .style import DARK_QSS
from .timeline import TimelinePanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GloryDial Studio")
        self.resize(1440, 900)

        self.device_db = DeviceDatabase()
        self.project = self._make_blank_project()
        self.current_path: Optional[str] = None
        self._selected_type_id: Optional[int] = None

        self._build_ui()
        self._refresh_all()

    # ------------------------------------------------------------------
    def _make_blank_project(self) -> Project:
        return Project(header=ProjectHeader(), screen_width=410, screen_height=502, compression_version=3)

    def _build_ui(self) -> None:
        self.canvas = WatchCanvasView()
        self.setCentralWidget(self.canvas)
        self.canvas.block_selected.connect(self._on_canvas_selected)
        self.canvas.block_moved.connect(self._on_block_moved)

        self.layers_panel = LayersPanel()
        self.layers_panel.block_selected.connect(self._on_layers_selected)
        self.layers_panel.visibility_toggled.connect(self._on_visibility_toggled)
        self.layers_panel.delete_requested.connect(self._on_delete_block)
        self.layers_panel.add_requested.connect(self._on_add_block)
        layers_dock = QDockWidget("Layers", self)
        layers_dock.setWidget(self.layers_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, layers_dock)

        self.properties_panel = PropertiesPanel()
        self.properties_panel.property_changed.connect(self._on_property_changed)
        properties_dock = QDockWidget("Properties", self)
        properties_dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, properties_dock)

        self.simulation_panel = SimulationPanel()
        self.simulation_panel.changed.connect(self._on_sim_changed)
        sim_dock = QDockWidget("Simulation", self)
        sim_dock.setWidget(self.simulation_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, sim_dock)

        self.timeline_panel = TimelinePanel()
        self.timeline_panel.import_requested.connect(self._on_frame_import)
        self.timeline_panel.replace_requested.connect(self._on_frame_replace)
        self.timeline_panel.duplicate_requested.connect(self._on_frame_duplicate)
        self.timeline_panel.delete_requested.connect(self._on_frame_delete)
        self.timeline_panel.move_requested.connect(self._on_frame_move)
        self.timeline_panel.export_requested.connect(self._on_frame_export)
        timeline_dock = QDockWidget("Frames", self)
        timeline_dock.setWidget(self.timeline_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, timeline_dock)

        self._build_menu_and_toolbar()

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel()
        self.status.addPermanentWidget(self.status_label)

    def _build_menu_and_toolbar(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        self._add_action(file_menu, "&New...", self._on_new, QKeySequence.StandardKey.New)
        self._add_action(file_menu, "&Open BIN...", self._on_open, QKeySequence.StandardKey.Open)
        self._add_action(file_menu, "&Save", self._on_save, QKeySequence.StandardKey.Save)
        self._add_action(file_menu, "Save &As...", self._on_save_as, QKeySequence.StandardKey.SaveAs)
        file_menu.addSeparator()
        self._add_action(file_menu, "Export Preview as PNG...", self._on_export_preview)
        file_menu.addSeparator()
        self._add_action(file_menu, "E&xit", self.close)

        device_menu = menu.addMenu("&Device")
        self._add_action(device_menu, "Device &Manager...", self._on_device_manager)

        view_menu = menu.addMenu("&View")
        self._add_action(view_menu, "Fit Canvas", self.canvas.fit_to_view)

        help_menu = menu.addMenu("&Help")
        self._add_action(help_menu, "&About", self._on_about)

        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.addAction("New", self._on_new)
        toolbar.addAction("Open", self._on_open)
        toolbar.addAction("Save", self._on_save)
        toolbar.addSeparator()
        toolbar.addAction("Add Block", self._on_add_block)
        toolbar.addSeparator()
        toolbar.addAction("Devices", self._on_device_manager)

    def _add_action(self, menu, text, handler, shortcut=None) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(handler)
        if shortcut:
            action.setShortcut(shortcut)
        menu.addAction(action)
        return action

    # ------------------------------------------------------------------
    def _refresh_all(self, keep_selection: bool = True) -> None:
        sel = self._selected_type_id if keep_selection else None
        self.layers_panel.refresh(self.project, sel)
        self.canvas.load_project(self.project, self.simulation_panel.state)
        self._show_selected_block()
        self.status_label.setText(
            f"{self.project.screen_width}x{self.project.screen_height} · "
            f"Compression V{self.project.compression_version} · "
            f"{len(self.project.blocks)} block(s)"
        )

    def _show_selected_block(self) -> None:
        block = self.project.blocks.get(self._selected_type_id) if self._selected_type_id else None
        self.properties_panel.show_block(block)
        self.timeline_panel.show_block(block)

    # ---- selection sync ------------------------------------------------
    def _on_canvas_selected(self, type_id) -> None:
        self._selected_type_id = type_id
        self.layers_panel.refresh(self.project, type_id)
        self._show_selected_block()

    def _on_layers_selected(self, type_id: int) -> None:
        self._selected_type_id = type_id
        self._show_selected_block()

    # ---- block editing ---------------------------------------------------
    def _on_block_moved(self, type_id: int, x: int, y: int) -> None:
        block = self.project.blocks.get(type_id)
        if block is None:
            return
        block.x, block.y = x, y
        self._refresh_all()

    def _on_property_changed(self, type_id: int, field: str, value) -> None:
        block = self.project.blocks.get(type_id)
        if block is None:
            return
        setattr(block, field, value)
        self._refresh_all()

    def _on_visibility_toggled(self, type_id: int, visible: bool) -> None:
        block = self.project.blocks.get(type_id)
        if block is None:
            return
        block.visible = visible
        self._refresh_all()

    def _on_delete_block(self, type_id: int) -> None:
        name = block_schema.block_name(type_id)
        if QMessageBox.question(self, "Delete block", f"Delete block '{name}'?") != QMessageBox.StandardButton.Yes:
            return
        self.project.remove_block(type_id)
        if self._selected_type_id == type_id:
            self._selected_type_id = None
        self._refresh_all()

    def _on_add_block(self) -> None:
        dlg = AddBlockDialog(self.project, self)
        if dlg.exec() and dlg.chosen_type_id is not None:
            self.project.add_block(dlg.chosen_type_id)
            self._selected_type_id = dlg.chosen_type_id
            self._refresh_all()

    # ---- frame editing ---------------------------------------------------
    def _current_block(self) -> Optional[Block]:
        return self.project.blocks.get(self._selected_type_id) if self._selected_type_id else None

    def _on_frame_import(self, path: str) -> None:
        block = self._current_block()
        if block is None:
            return
        try:
            image = Image.open(path).convert("RGBA")
        except Exception as e:
            QMessageBox.warning(self, "Could not open image", str(e))
            return
        block.frames.append(Frame(image))
        self._refresh_all()

    def _on_frame_replace(self, index: int, path: str) -> None:
        block = self._current_block()
        if block is None:
            return
        try:
            image = Image.open(path).convert("RGBA")
        except Exception as e:
            QMessageBox.warning(self, "Could not open image", str(e))
            return
        if 0 <= index < len(block.frames):
            block.frames[index] = Frame(image)
        self._refresh_all()

    def _on_frame_duplicate(self, index: int) -> None:
        block = self._current_block()
        if block is not None:
            block.clone_frame(index)
            self._refresh_all()

    def _on_frame_delete(self, index: int) -> None:
        block = self._current_block()
        if block is not None:
            block.delete_frame(index)
            self._refresh_all()

    def _on_frame_move(self, src: int, dst: int) -> None:
        block = self._current_block()
        if block is not None:
            block.move_frame(src, dst)
            self._refresh_all()

    def _on_frame_export(self, index: int, path: str) -> None:
        block = self._current_block()
        if block is None or not (0 <= index < len(block.frames)):
            return
        block.frames[index].image.save(path)

    # ---- simulation -------------------------------------------------------
    def _on_sim_changed(self, sim: SimState) -> None:
        self.canvas.load_project(self.project, sim)

    # ---- file operations ----------------------------------------------------
    def _on_new(self) -> None:
        dlg = NewProjectDialog(self.device_db, self)
        if not dlg.exec():
            return
        device = dlg.result_device
        self.project = Project(
            header=ProjectHeader(),
            device_name=device.name,
            screen_width=device.width,
            screen_height=device.height,
            compression_version=dlg.result_version,
        )
        self.current_path = None
        self._selected_type_id = None
        self._refresh_all()

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Clock Face", "", "UTE Watch Face (*.bin)")
        if not path:
            return
        try:
            project, report = reader.read_bin(path)
        except Exception as e:
            QMessageBox.critical(self, "Could not open file", str(e))
            return
        if report.errors:
            QMessageBox.critical(self, "File has problems", "\n".join(report.errors))
        if report.warnings:
            QMessageBox.warning(self, "Opened with warnings", "\n".join(report.warnings))
        self.project = project
        self.current_path = path
        self._selected_type_id = None
        self._refresh_all()

    def _on_save(self) -> None:
        if self.current_path is None:
            self._on_save_as()
            return
        self._write_to(self.current_path)

    def _on_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Clock Face", self.current_path or "clockface.bin", "UTE Watch Face (*.bin)")
        if not path:
            return
        self._write_to(path)

    def _write_to(self, path: str) -> None:
        try:
            writer.write_bin(self.project, path, self.project.compression_version)
        except ValidationError as e:
            QMessageBox.critical(self, "Cannot save", str(e))
            return
        self.current_path = path
        self.status.showMessage(f"Saved {path}", 4000)

    def _on_export_preview(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Preview", "preview.png", "PNG (*.png)")
        if not path:
            return
        from ..rendering.renderer import render

        image = render(self.project, self.simulation_panel.state)
        image.save(path)

    def _on_device_manager(self) -> None:
        dlg = DeviceManagerDialog(self.device_db, self)
        dlg.exec()

    def _on_about(self) -> None:
        QMessageBox.information(
            self,
            "About GloryDial Studio",
            "GloryDial Studio\n\n"
            "Open-source watch face editor for UTE/GloryFit-compatible .bin watch faces, with support for multiple devices and compression versions. "
            "Supported Compression Versions: 1, 2, 3.",
        )


def apply_theme(app) -> None:
    app.setStyleSheet(DARK_QSS)
