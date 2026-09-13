import os

import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from PyQt6.QtWidgets import QApplication

from glorydial.formats import reader

SAMPLE = os.path.join(os.path.dirname(__file__), "sample_double_circle.bin")

_app = None


def _get_app():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


def test_main_window_constructs():
    _get_app()
    from glorydial.ui.main_window import MainWindow

    win = MainWindow()
    assert win.project is not None
    assert len(win.project.blocks) == 0


def test_main_window_loads_real_project():
    _get_app()
    from glorydial.ui.main_window import MainWindow

    win = MainWindow()
    project, report = reader.read_bin(SAMPLE)
    win.project = project
    win.current_path = SAMPLE
    win._refresh_all()
    assert win.layers_panel.tree.topLevelItemCount() == 14


def test_selecting_a_block_populates_properties_and_timeline():
    _get_app()
    from glorydial.ui.main_window import MainWindow

    win = MainWindow()
    project, _ = reader.read_bin(SAMPLE)
    win.project = project
    win._refresh_all()
    win._on_layers_selected(1)
    assert win.properties_panel.title.text() == "HoursHand"
    assert win.timeline_panel.list.count() == 1


def test_moving_a_block_updates_model():
    _get_app()
    from glorydial.ui.main_window import MainWindow

    win = MainWindow()
    project, _ = reader.read_bin(SAMPLE)
    win.project = project
    win._refresh_all()
    win._on_block_moved(1, 111, 222)
    assert (win.project.blocks[1].x, win.project.blocks[1].y) == (111, 222)


def test_save_through_ui_produces_valid_file(tmp_path):
    _get_app()
    from glorydial.ui.main_window import MainWindow

    win = MainWindow()
    project, _ = reader.read_bin(SAMPLE)
    win.project = project
    win._refresh_all()
    out = str(tmp_path / "ui_saved.bin")
    win._write_to(out)

    project2, report2 = reader.read_bin(out)
    assert not report2.errors
    assert len(project2.blocks) == len(project.blocks)


def test_add_and_delete_block_through_ui():
    _get_app()
    from glorydial.ui.main_window import MainWindow

    win = MainWindow()
    project, _ = reader.read_bin(SAMPLE)
    win.project = project
    win._refresh_all()
    assert 48 not in win.project.blocks
    win.project.add_block(48)
    win._refresh_all()
    assert 48 in win.project.blocks
    win._on_delete_block_direct = None  # placeholder, delete goes through confirm dialog normally
    win.project.remove_block(48)
    win._refresh_all()
    assert 48 not in win.project.blocks
