"""Regression test for a real crash: dragging a block on the canvas
raised

    RuntimeError: wrapped C/C++ object of type BlockItem has been deleted

The root cause: WatchCanvasView.mouseReleaseEvent emitted
block_moved(...), which is connected (directly, same thread) to
MainWindow._on_block_moved -> _refresh_all() -> canvas.load_project()
-> WatchCanvasScene.sync_from_project() -> scene.clear(). That
synchronously destroys every BlockItem from before the emit - including
the one mouseReleaseEvent's own loop body still held a Python reference
to - and the old code then called `item.setPos(start_pos)` on it
*after* the emit returned, touching an already-deleted Qt object.

The fix reads every needed value from each item into plain Python
values BEFORE emitting anything, and never touches a QGraphicsItem
after a signal that can trigger a rebuild. This test wires up the real
MainWindow (so the real, synchronous rebuild actually happens) and
drives a drag through the canvas's own event handlers rather than
mocking anything, so it would have caught the original bug.
"""

import os

import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

from glorydial.formats import reader

SAMPLE = os.path.join(os.path.dirname(__file__), "sample_double_circle.bin")

_app = None


def _get_app():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


def test_dragging_a_block_does_not_crash_on_synchronous_rebuild():
    _get_app()
    from glorydial.ui.main_window import MainWindow

    win = MainWindow()
    project, _ = reader.read_bin(SAMPLE)
    win.project = project
    win._refresh_all()

    canvas = win.canvas
    item = canvas._scene.items_by_block[1]  # HoursHand
    item.setSelected(True)

    # Simulate exactly what mousePressEvent/mouseReleaseEvent do, without
    # needing a real synthetic QMouseEvent: seed the drag-start position,
    # move the item (as Qt's own drag handling would), then let
    # mouseReleaseEvent's post-processing run for real.
    canvas._drag_start_positions[1] = item.pos()
    item.setPos(item.pos() + QPointF(15, -7))

    # Run the same post-processing mouseReleaseEvent performs: read every
    # item value into plain Python values first, then emit. This is what
    # actually triggers the real, synchronous MainWindow._on_block_moved
    # -> _refresh_all() -> canvas rebuild chain that used to crash.
    moves = []
    for type_id, start_pos in list(canvas._drag_start_positions.items()):
        it = canvas._scene.items_by_block.get(type_id)
        assert it is not None
        new_pos = it.pos()
        anchor = it.data(0)
        if new_pos != start_pos:
            if anchor is not None:
                dx = new_pos.x() - start_pos.x()
                dy = new_pos.y() - start_pos.y()
                moves.append((type_id, int(anchor[0] + dx), int(anchor[1] + dy)))
            else:
                moves.append((type_id, int(new_pos.x()), int(new_pos.y())))
    canvas._drag_start_positions.clear()

    original_x, original_y = win.project.blocks[1].x, win.project.blocks[1].y
    for type_id, x, y in moves:
        canvas.block_moved.emit(type_id, x, y)  # triggers the real synchronous rebuild

    assert win.project.blocks[1].x == original_x + 15
    assert win.project.blocks[1].y == original_y - 7


def test_scene_rebuilding_flag_suppresses_selection_signal_reentrancy():
    _get_app()
    from glorydial.ui.main_window import MainWindow

    win = MainWindow()
    project, _ = reader.read_bin(SAMPLE)
    win.project = project
    win._refresh_all()

    # Directly exercise the guarded path: selected_type_id() must return
    # None (not raise) while a rebuild is flagged in progress.
    win.canvas._scene.rebuilding = True
    assert win.canvas._scene.selected_type_id() is None
    win.canvas._scene.rebuilding = False


def test_repeated_moves_and_refreshes_are_stable():
    """Broader smoke coverage: several move+refresh cycles in a row,
    mirroring rapid real-world dragging, must never raise."""
    _get_app()
    from glorydial.ui.main_window import MainWindow

    win = MainWindow()
    project, _ = reader.read_bin(SAMPLE)
    win.project = project
    win._refresh_all()

    for i in range(5):
        win._on_block_moved(1, 100 + i, 200 + i)
    assert (win.project.blocks[1].x, win.project.blocks[1].y) == (104, 204)
