"""24-byte file header.

Verified field-by-field against a real device export (the supplied
"Double Circle.bin") during development - see the worked example in
this module's tests. Layout:

    bytes 0-3    opaque_id        preserved verbatim, never interpreted
                                   (see model.block.ProjectHeader)
    bytes 4-7    u32 LE           payload size = total file length - 24
    bytes 8-11   u32 LE           CRC32 (zlib/standard poly) of bytes[24:]
    bytes 12-13  u16 LE           screen width
    bytes 14-15  u16 LE           screen height
    byte 16      0x00             reserved (CreateBinFile literal)
    byte 17      0x01             reserved (CreateBinFile literal)
    byte 18      0xFF             reserved (CreateBinFile literal)
    byte 19      u8               compression version: 1, 2, or 3
    byte 20      u8               block count (only meaningful for v>=3,
                                   0xFF otherwise)
    bytes 21-23  0xFF 0xFF 0xFF   padding

This was cross-checked against Double_Circle.bin: bytes[12:16] decoded
to width=410/height=502, byte[19]=3, byte[20]=14 (block count), and
bytes[8:12] as a little-endian u32 matched zlib.crc32(data[24:])
exactly.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

HEADER_SIZE = 24


@dataclass
class BinHeader:
    opaque_id: bytes
    payload_size: int
    crc32: int
    width: int
    height: int
    version: int
    block_count: int  # 0xFF ("unknown"/unused) for v1/v2


def parse_header(data: bytes) -> BinHeader:
    if len(data) < HEADER_SIZE:
        raise ValueError(
            f"File is only {len(data)} bytes long; a valid clock-face .bin "
            f"needs at least {HEADER_SIZE} bytes for its header."
        )
    opaque_id = data[0:4]
    payload_size = struct.unpack_from("<I", data, 4)[0]
    crc32 = struct.unpack_from("<I", data, 8)[0]
    width, height = struct.unpack_from("<HH", data, 12)
    version_raw = data[19]
    version = 1 if version_raw == 0xFF else version_raw
    if version not in (1, 2, 3):
        raise ValueError(
            f"Unrecognized compression version byte 0x{version_raw:02X} at "
            f"offset 19. Expected 1, 2, 3 (or 0xFF as an alias for 1)."
        )
    block_count = data[20]
    return BinHeader(
        opaque_id=opaque_id,
        payload_size=payload_size,
        crc32=crc32,
        width=width,
        height=height,
        version=version,
        block_count=block_count,
    )


def verify_crc(data: bytes, header: BinHeader) -> bool:
    return (zlib.crc32(data[HEADER_SIZE:]) & 0xFFFFFFFF) == header.crc32


def build_header(
    opaque_id: bytes,
    width: int,
    height: int,
    version: int,
    block_count: int,
    payload: bytes,
) -> bytes:
    """Builds the 24-byte header for a payload that will be written
    immediately after it. ``payload`` is everything in the file after
    the header (block descriptors + terminator + image data), and is
    only used here to compute size/CRC - the caller is responsible for
    concatenating header + payload."""
    if len(opaque_id) != 4:
        raise ValueError("opaque_id must be exactly 4 bytes.")
    if not (0 <= width <= 0xFFFF) or not (0 <= height <= 0xFFFF):
        raise ValueError(f"Screen dimensions {width}x{height} do not fit in the format's 16-bit fields.")
    header = bytearray(HEADER_SIZE)
    header[0:4] = opaque_id
    struct.pack_into("<I", header, 4, len(payload) & 0xFFFFFFFF)
    struct.pack_into("<I", header, 8, zlib.crc32(payload) & 0xFFFFFFFF)
    struct.pack_into("<HH", header, 12, width, height)
    header[16] = 0x00
    header[17] = 0x01
    header[18] = 0xFF
    header[19] = version & 0xFF
    header[20] = (block_count & 0xFF) if version >= 3 else 0xFF
    header[21] = 0xFF
    header[22] = 0xFF
    header[23] = 0xFF
    return bytes(header)
