"""24-byte block descriptor, repeated once per block after the header.

Verified against the supplied reference file: parsing all 14
descriptors of "Double Circle.bin" reproduced exactly the block types,
sizes, positions and (for the three hands) ArrowInfo values expected
for a 410x502 "Double Circle" K72 face, including several
resource-sharing pairs (e.g. HoursDigits/MinutesDigits sharing one
start address) confirmed by cross-referencing FolderImageComparison.java.

Layout (ReadBinFile.java's per-block read loop / CreateBinFile.java's
per-folder write loop):

    u16 LE   type_id            (matches EnumBlockName's numeric value)
    u16 LE   width               (of frame 0 - all frames in a block
                                   must share dimensions, see validation)
    u32 LE   start_address       absolute byte offset of frame 0's data
    u16 LE   height
    u16 LE   x
    u16 LE   y
    u16 LE   animation_speed
    u8       images_count        (frame count)
    u8       black_is_transparent_raw   0 => True, 1 => False (INVERTED -
                                   see note below)
    u8*3     reserved            always 0
    u8       arrow_full_length   (hands only, else 0)
    u8       arrow_length_to_center (hands only, else 0)
    u8       arrow_width         (hands only, else 0)

BlackIsTransparent inversion is intentional and verified on both sides
of ClockFaceEdit: ReadBinFile.java does
``blackIsTransparent = (buffByte[i+17] == 0)`` and CreateBinFile.java's
writer does the exact mirror (writes 0 for true, 1 for false) - this
is reproduced exactly rather than "corrected" to a natural boolean byte.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

DESCRIPTOR_SIZE = 24
TERMINATOR = b"\x00\x00"


@dataclass
class BlockDescriptor:
    type_id: int
    width: int
    start_address: int
    height: int
    x: int
    y: int
    animation_speed: int
    images_count: int
    black_is_transparent: bool
    arrow_full_length: int
    arrow_length_to_center: int
    arrow_width: int


def parse_descriptor(data: bytes, offset: int) -> BlockDescriptor:
    type_id, width = struct.unpack_from("<HH", data, offset)
    start_address = struct.unpack_from("<I", data, offset + 4)[0]
    height, x, y, anim = struct.unpack_from("<HHHH", data, offset + 8)
    images_count = data[offset + 16]
    black_is_transparent_raw = data[offset + 17]
    arrow_full_length = data[offset + 21]
    arrow_length_to_center = data[offset + 22]
    arrow_width = data[offset + 23]
    return BlockDescriptor(
        type_id=type_id,
        width=width,
        start_address=start_address,
        height=height,
        x=x,
        y=y,
        animation_speed=anim,
        images_count=images_count,
        black_is_transparent=(black_is_transparent_raw == 0),
        arrow_full_length=arrow_full_length,
        arrow_length_to_center=arrow_length_to_center,
        arrow_width=arrow_width,
    )


def build_descriptor(desc: BlockDescriptor) -> bytes:
    if not (0 <= desc.images_count <= 0xFF):
        raise ValueError(
            f"Block '{desc.type_id}' has {desc.images_count} frames; the format's "
            f"ImagesCount field is a single byte, so it must be between 0 and 255."
        )
    for name, val in (
        ("ArrowFullLength", desc.arrow_full_length),
        ("ArrowLengthToCenter", desc.arrow_length_to_center),
        ("ArrowWidth", desc.arrow_width),
    ):
        if not (0 <= val <= 0xFF):
            raise ValueError(f"{name} value {val} does not fit in this format's single byte field (0-255).")
    out = bytearray(DESCRIPTOR_SIZE)
    struct.pack_into("<HH", out, 0, desc.type_id & 0xFFFF, desc.width & 0xFFFF)
    struct.pack_into("<I", out, 4, desc.start_address & 0xFFFFFFFF)
    struct.pack_into("<HHHH", out, 8, desc.height & 0xFFFF, desc.x & 0xFFFF, desc.y & 0xFFFF, desc.animation_speed & 0xFFFF)
    out[16] = desc.images_count & 0xFF
    out[17] = 0 if desc.black_is_transparent else 1
    out[18] = 0
    out[19] = 0
    out[20] = 0
    out[21] = desc.arrow_full_length & 0xFF
    out[22] = desc.arrow_length_to_center & 0xFF
    out[23] = desc.arrow_width & 0xFF
    return bytes(out)
