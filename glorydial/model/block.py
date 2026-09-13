"""Core in-memory data model for a clock-face project.

This is the "internal model" the whole app operates on: it is rich
enough to represent everything a .bin file can contain (so opening a
file and immediately saving it again round-trips structurally), while
staying independent of any particular compression version so the same
model can be re-compiled to V1, V2 or V3.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from PIL import Image

from . import block_schema


@dataclass
class Frame:
    """A single decoded image frame belonging to a block.

    ``image`` is always kept as an RGBA Pillow Image in memory - internal
    representation is deliberately format/version independent. Pixel
    format conversion (RGB565 / ARGB6666) only happens at load/compile
    time in glorydial.formats.
    """

    image: Image.Image  # RGBA

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    def content_hash(self) -> str:
        """Stable hash of pixel content, used for resource de-duplication
        (mirrors FolderImageComparison.java's SHA-256-of-file-bytes
        approach, but hashes decoded pixels so it is robust to
        incidental PNG re-encoding)."""
        return hashlib.sha256(self.image.tobytes()).hexdigest()


@dataclass
class Block:
    """One block/layer of the watch face.

    Field names intentionally mirror the 24-byte on-disk descriptor and
    the property names ClockFaceEdit exposes in its block editor: X, Y,
    AnimationSpeed, ImageIndex, ImagesCount, BlackIsTransparent, and (for
    hands only) ArrowFullLength / ArrowLengthToCenter / ArrowWidth.
    """

    type_id: int
    x: int = 0
    y: int = 0
    animation_speed: int = 0
    image_index: int = 0
    black_is_transparent: bool = True
    arrow_full_length: int = 0
    arrow_length_to_center: int = 0
    arrow_width: int = 0
    frames: List[Frame] = field(default_factory=list)

    # Editor-only convenience state (never written to the .bin):
    visible: bool = True  # ClockFaceEdit's "isLookImage" show/hide toggle
    digit_glyph_offset: int = 0
    """Only meaningful for compound multi-digit blocks (see
    model.block_schema.compound_digit_count and
    rendering/simulation.py). Neither ReadBinFile.java nor
    CreateBinFile.java declare where within a digit-glyph pool the '0'
    glyph lives - that is a property of each face's own asset content,
    not something the file format specifies. Confirmed by directly
    inspecting the supplied Double Circle.bin: its 14-frame HoursDigits/
    MinutesDigits pool is a contiguous ASCII strip '-./0123456789:',
    putting '0' at frame index 3, not 0. formats/reader.py sets a
    best-effort default for this (3 when a compound block has exactly
    14 frames, matching that observed convention; 0 otherwise), and it
    is user-editable in the Properties panel so it can be corrected by
    eye against the Frames strip for any face that uses a different
    layout. This is a live-preview-only convenience: it is never read
    from or written to the compiled .bin."""

    @property
    def name(self) -> str:
        return block_schema.block_name(self.type_id)

    @property
    def is_hand(self) -> bool:
        return block_schema.is_hand(self.type_id)

    @property
    def images_count(self) -> int:
        return len(self.frames)

    @property
    def width(self) -> int:
        return self.frames[0].width if self.frames else 0

    @property
    def height(self) -> int:
        return self.frames[0].height if self.frames else 0

    def frame_hash_set(self) -> frozenset:
        """Set of content hashes for this block's frames - used to detect
        resources that are byte-identical to another block's resources
        (see formats/writer.py ``deduplicate_resources``, ported from
        FolderImageComparison.java)."""
        return frozenset(f.content_hash() for f in self.frames)

    def clone_frame(self, index: int) -> None:
        if 0 <= index < len(self.frames):
            self.frames.insert(index + 1, Frame(self.frames[index].image.copy()))

    def delete_frame(self, index: int) -> None:
        if 0 <= index < len(self.frames):
            del self.frames[index]

    def move_frame(self, src: int, dst: int) -> None:
        if 0 <= src < len(self.frames) and 0 <= dst < len(self.frames):
            f = self.frames.pop(src)
            self.frames.insert(dst, f)


@dataclass
class ProjectHeader:
    """Raw header metadata preserved across read/write.

    ``opaque_id`` is the 4 mystery bytes at offset 0-3 of every .bin
    file. ClockFaceEdit's own generic writer (CreateBinFile.writeZeroBlockBinFile)
    always emits the literal ASCII ".BIN" there and never touches it
    again, yet real device-exported faces (e.g. the supplied
    "Double Circle.bin") contain other, non-ASCII, values. Nothing in the
    available ClockFaceEdit source reads or interprets these bytes beyond
    displaying them as a raw string in the "bin info" dialog, so their
    true meaning is unknown. We preserve them byte-for-byte on round trip
    rather than guessing at semantics.
    """

    opaque_id: bytes = b".BIN"


@dataclass
class Project:
    header: ProjectHeader = field(default_factory=ProjectHeader)
    device_name: Optional[str] = None
    screen_width: int = 410
    screen_height: int = 502
    compression_version: int = 3
    blocks: Dict[int, Block] = field(default_factory=dict)
    source_path: Optional[str] = None

    def add_block(self, type_id: int) -> Block:
        if type_id in self.blocks:
            raise ValueError(f"Block '{block_schema.block_name(type_id)}' already exists in this project.")
        defaults = block_schema.default_for(block_schema.block_name(type_id))
        blk = Block(
            type_id=type_id,
            x=defaults.x,
            y=defaults.y,
            animation_speed=defaults.animation_speed,
            image_index=defaults.image_index,
            black_is_transparent=defaults.black_is_transparent,
            arrow_full_length=defaults.arrow_full_length,
            arrow_length_to_center=defaults.arrow_length_to_center,
            arrow_width=defaults.arrow_width,
        )
        self.blocks[type_id] = blk
        return blk

    def remove_block(self, type_id: int) -> None:
        self.blocks.pop(type_id, None)

    def ordered_blocks_for_compile(self) -> List[Block]:
        """Order blocks the way CreateBinFile.java's write loop does:
        plain ascending numeric type id, NO special-casing of hands.
        (Verified directly against CreateBinFile.java's Arrays.sort
        comparator, and cross-checked against the real block descriptor
        order found in the supplied Double Circle.bin: [1,2,3,4,5,10,
        11,13,15,17,25,30,32,71] - already plain ascending.)

        This is deliberately DIFFERENT from render_order_blocks() below:
        CanvasImage.java uses a *different*, hands-last comparator only
        for on-screen paint order, never for the compiled file's
        descriptor order. Conflating the two was an early mistake
        during development, corrected after re-checking both source
        files side by side."""
        return sorted(self.blocks.values(), key=lambda b: b.type_id)

    def render_order_blocks(self) -> List[Block]:
        """Paint order used by the live preview, ported from
        CanvasImage.java's custom Comparator<File>: non-hand blocks
        ascending by type id, then the three hands ascending by type id
        last (so hands are always drawn on top). Background/Preview are
        excluded here since CanvasImage.java draws Background separately
        up front and never draws Preview at all - see renderer.py."""
        non_hands = sorted((b for b in self.blocks.values() if not b.is_hand and b.type_id not in block_schema.RENDER_SKIP_IDS), key=lambda b: b.type_id)
        hands = sorted((b for b in self.blocks.values() if b.is_hand), key=lambda b: b.type_id)
        return non_hands + hands

    def background_block(self) -> Optional[Block]:
        return self.blocks.get(block_schema.BACKGROUND_ID)
