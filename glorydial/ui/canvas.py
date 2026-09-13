"""Interactive design canvas.

Each visible block is its own QGraphicsPixmapItem (not one flattened
bitmap), so blocks can be individually selected, dragged, and nudged
with arrow keys, with a live selection outline - the "real design
canvas" behavior the task calls for. Z-order and the Background/Preview
special-casing mirror model.block.Project.render_order_blocks() /
rendering/renderer.py. Hands are rendered pre-rotated (their pixmap is
regenerated whenever the simulated time changes) since QGraphicsItem
rotation pivots don't map cleanly onto ArrowInfo's pivot semantics for
per-pixel BlackIsTransparent handling; dragging a hand still moves its
(X, Y) anchor like any other block.
"""

from __future__ import annotations

from typing import Dict, Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

from ..model.block import Block, Project
from ..rendering import hands as hands_mod
from ..rendering import renderer as renderer_mod
from ..rendering.simulation import SimState, resolve_display_frame_indices, resolve_frame_index


def pil_to_qpixmap(image) -> QPixmap:
    image = image.convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimg = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


class BlockItem(QGraphicsPixmapItem):
    def __init__(self, type_id: int, movable: bool = True):
        super().__init__()
        self.type_id = type_id
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, movable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)


class WatchCanvasScene(QGraphicsScene):
    block_moved = pyqtSignal(int, int, int)  # type_id, x, y

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items_by_block: Dict[int, BlockItem] = {}
        self._suppress_move_signal = False
        self.rebuilding = False

    def sync_from_project(self, project: Project, sim: SimState) -> None:
        # Guards re-entrant callers (see WatchCanvasView._on_selection_changed)
        # against touching QGraphicsItems mid-teardown: self.clear() below
        # destroys every item and can itself emit selectionChanged
        # synchronously as items are removed, which would otherwise try to
        # read a half-destroyed item's data.
        self.rebuilding = True
        try:
            self.clear()
            self.items_by_block.clear()
            self.setSceneRect(0, 0, project.screen_width, project.screen_height)

            # Checkerboard so transparency is visible even with no Background.
            self._draw_checker(project.screen_width, project.screen_height)

            bg = project.background_block()
            if bg is not None and bg.visible and bg.frames:
                image = bg.frames[resolve_frame_index(bg, sim)].image
                if bg.black_is_transparent:
                    image = renderer_mod._apply_black_is_transparent(image)
                item = BlockItem(bg.type_id, movable=False)
                item.setPixmap(pil_to_qpixmap(image))
                item.setZValue(-1)
                item.setPos(0, 0)
                self.addItem(item)
                self.items_by_block[bg.type_id] = item

            z = 0
            for block in project.render_order_blocks():
                if not block.visible or not block.frames:
                    continue

                item = BlockItem(block.type_id)
                if block.is_hand:
                    idx = resolve_frame_index(block, sim)
                    image = block.frames[idx].image
                    if block.black_is_transparent:
                        image = renderer_mod._apply_black_is_transparent(image)
                    transform = hands_mod.transform_for(block, sim)
                    layer = renderer_mod.Image.new("RGBA", (project.screen_width, project.screen_height), (0, 0, 0, 0))
                    layer.paste(image, (round(transform.anchor_x), round(transform.anchor_y)), image)
                    rotated = layer.rotate(
                        -transform.angle_degrees,
                        resample=renderer_mod.Image.BICUBIC,
                        center=(transform.pivot_x, transform.pivot_y),
                    )
                    item.setPixmap(pil_to_qpixmap(rotated))
                    item.setPos(0, 0)
                    item.setData(0, (block.x, block.y))  # anchor for drag math (pivot, not top-left)
                else:
                    composite = self._composite_display_images(block, sim)
                    if composite is None:
                        continue
                    item.setPixmap(pil_to_qpixmap(composite))
                    item.setPos(block.x, block.y)
                item.setZValue(z)
                z += 1
                self.addItem(item)
                self.items_by_block[block.type_id] = item
        finally:
            self.rebuilding = False

    def _composite_display_images(self, block: Block, sim: SimState):
        """Builds one image for the block's current display state,
        placing compound multi-digit blocks (e.g. HoursDigits) as
        side-by-side glyphs exactly like rendering/renderer.py does -
        see rendering/simulation.py's resolve_display_frame_indices for
        why some blocks need more than one glyph."""
        images = []
        for idx in resolve_display_frame_indices(block, sim):
            idx = max(0, min(idx, len(block.frames) - 1))
            image = block.frames[idx].image
            if block.black_is_transparent:
                image = renderer_mod._apply_black_is_transparent(image)
            images.append(image)
        if not images:
            return None
        if len(images) == 1:
            return images[0]
        total_width = sum(im.width for im in images)
        height = max(im.height for im in images)
        composite = renderer_mod.Image.new("RGBA", (total_width, height), (0, 0, 0, 0))
        x = 0
        for im in images:
            composite.alpha_composite(im, (x, 0))
            x += im.width
        return composite

    def _draw_checker(self, w: int, h: int, size: int = 12) -> None:
        rect = QGraphicsRectItem(0, 0, w, h)
        rect.setBrush(QBrush(QColor(30, 31, 36)))
        rect.setPen(QPen(Qt.PenStyle.NoPen))
        rect.setZValue(-100)
        self.addItem(rect)

    def selected_type_id(self) -> Optional[int]:
        if self.rebuilding:
            return None
        try:
            for item in self.selectedItems():
                if isinstance(item, BlockItem):
                    return item.type_id
        except RuntimeError:
            # Items were destroyed mid-teardown (e.g. a rebuild triggered
            # re-entrantly by a signal handler) - nothing to select.
            return None
        return None


class WatchCanvasView(QGraphicsView):
    block_selected = pyqtSignal(object)  # Optional[int]
    block_moved = pyqtSignal(int, int, int)  # type_id, new_x, new_y

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = WatchCanvasScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor(24, 25, 29)))
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._drag_start_positions: Dict[int, QPointF] = {}
        self.scene().selectionChanged.connect(self._on_selection_changed)

    def load_project(self, project: Project, sim: SimState) -> None:
        self._scene.sync_from_project(project, sim)
        self.fit_to_view()

    def fit_to_view(self) -> None:
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_to_view()

    def _on_selection_changed(self) -> None:
        if self._scene.rebuilding:
            return
        self.block_selected.emit(self._scene.selected_type_id())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        try:
            for item in self._scene.items_by_block.values():
                if item.isSelected():
                    self._drag_start_positions[item.type_id] = item.pos()
        except RuntimeError:
            self._drag_start_positions.clear()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # IMPORTANT: read every needed value from each QGraphicsItem into
        # plain Python values FIRST, and only emit block_moved afterward.
        # block_moved is connected (directly, same thread) to
        # MainWindow._on_block_moved, which calls _refresh_all() ->
        # canvas.load_project() -> scene.sync_from_project() -> a full
        # scene.clear() - so by the time emit() returns, every BlockItem
        # from before this call has been destroyed on the Qt side. Touching
        # `item` again after emitting (this code used to call
        # `item.setPos(start_pos)` right after emit) raises "wrapped C/C++
        # object of type BlockItem has been deleted". Resetting the item's
        # position is unnecessary anyway: the rebuild the emit triggers
        # already replaces it with a freshly-positioned item.
        moves = []
        for type_id, start_pos in self._drag_start_positions.items():
            item = self._scene.items_by_block.get(type_id)
            if item is None:
                continue
            try:
                new_pos = item.pos()
                anchor = item.data(0)  # hands store their true (x,y) anchor separately
            except RuntimeError:
                continue
            if new_pos == start_pos:
                continue
            if anchor is not None:
                dx = new_pos.x() - start_pos.x()
                dy = new_pos.y() - start_pos.y()
                moves.append((type_id, int(anchor[0] + dx), int(anchor[1] + dy)))
            else:
                moves.append((type_id, int(new_pos.x()), int(new_pos.y())))
        self._drag_start_positions.clear()
        for type_id, x, y in moves:
            self.block_moved.emit(type_id, x, y)

    def keyPressEvent(self, event):
        step = 5 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1
        type_id = self._scene.selected_type_id()
        if type_id is not None and event.key() in (
            Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down,
        ):
            item = self._scene.items_by_block[type_id]
            anchor = item.data(0)
            base_x, base_y = anchor if anchor is not None else (item.pos().x(), item.pos().y())
            dx = -step if event.key() == Qt.Key.Key_Left else (step if event.key() == Qt.Key.Key_Right else 0)
            dy = -step if event.key() == Qt.Key.Key_Up else (step if event.key() == Qt.Key.Key_Down else 0)
            # Nothing touches `item` after this point - safe even though
            # the emit below can trigger a synchronous scene rebuild.
            self.block_moved.emit(type_id, int(base_x + dx), int(base_y + dy))
            event.accept()
            return
        super().keyPressEvent(event)
