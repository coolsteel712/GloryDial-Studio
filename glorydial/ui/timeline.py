"""Frame strip for the currently selected block: import, replace,
duplicate, delete, reorder, export frames."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QWidget,
)

from ..model.block import Block


def _pil_to_icon(image, max_size: int = 64) -> QPixmap:
    image = image.convert("RGBA")
    image.thumbnail((max_size, max_size))
    data = image.tobytes("raw", "RGBA")
    qimg = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


class TimelinePanel(QWidget):
    frame_selected = pyqtSignal(int)
    import_requested = pyqtSignal(str)  # file path -> append as new frame
    replace_requested = pyqtSignal(int, str)  # index, file path
    duplicate_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    move_requested = pyqtSignal(int, int)  # src, dst
    export_requested = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._block: Optional[Block] = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(QSize(64, 64))
        self.list.setFixedHeight(100)
        self.list.setFlow(QListWidget.Flow.LeftToRight)
        self.list.setMovement(QListWidget.Movement.Snap)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.itemSelectionChanged.connect(self._on_selection_changed)
        self.list.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self.list, 1)

        btns = QHBoxLayout()
        for label, handler in [
            ("Import...", self._on_import),
            ("Replace...", self._on_replace),
            ("Duplicate", self._on_duplicate),
            ("Delete", self._on_delete),
            ("Export...", self._on_export),
        ]:
            b = QPushButton(label)
            b.clicked.connect(handler)
            btns.addWidget(b)
        layout.addLayout(btns)

    def show_block(self, block: Optional[Block]) -> None:
        self._block = block
        self.list.clear()
        if block is None:
            return
        for i, frame in enumerate(block.frames):
            item = QListWidgetItem(QIcon(_pil_to_icon(frame.image)), str(i))
            self.list.addItem(item)

    def _current_index(self) -> Optional[int]:
        items = self.list.selectedItems()
        if not items:
            return None
        return self.list.row(items[0])

    def _on_selection_changed(self) -> None:
        idx = self._current_index()
        if idx is not None:
            self.frame_selected.emit(idx)

    def _on_rows_moved(self, parent, start, end, dest, row) -> None:
        dst = row if row < start else row - 1
        self.move_requested.emit(start, dst)

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import frame image", "", "Images (*.png *.bmp *.jpg *.jpeg *.gif)")
        if path:
            self.import_requested.emit(path)

    def _on_replace(self) -> None:
        idx = self._current_index()
        if idx is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Replace frame image", "", "Images (*.png *.bmp *.jpg *.jpeg *.gif)")
        if path:
            self.replace_requested.emit(idx, path)

    def _on_duplicate(self) -> None:
        idx = self._current_index()
        if idx is not None:
            self.duplicate_requested.emit(idx)

    def _on_delete(self) -> None:
        idx = self._current_index()
        if idx is not None:
            self.delete_requested.emit(idx)

    def _on_export(self) -> None:
        idx = self._current_index()
        if idx is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export frame image", f"frame_{idx}.png", "PNG (*.png)")
        if path:
            self.export_requested.emit(idx, path)
