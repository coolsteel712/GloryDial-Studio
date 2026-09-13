"""Top-level .bin file reader.

Ported from ``ReadBinFile.java``. The header is parsed first (24
bytes), then block descriptors are read sequentially in 24-byte
strides starting at offset 24. Rather than trusting the header's block
count byte (which is only meaningful for V3 - ReadBinFile.java itself
never actually uses it either), descriptors are read until the two
bytes immediately following a descriptor are both zero - the same
end-of-descriptors terminator ClockFaceEdit's own streaming byte-loop
detects via ``allBytes[i+1]==0 && allBytes[i+2]==0``. This is safe
because no valid block type id is ever 0, so a genuine next descriptor
can never be mistaken for the terminator.

Frame data for each block is then read by directly indexing into the
file at each descriptor's ``start_address``, exactly as
ReadBinFile.java does (it does NOT walk the outer byte-loop for this -
it randomly accesses ``allBytes`` using the address fields), advancing
a local cursor by each frame's actual on-disk size as frames are
decoded sequentially.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ..image_codec import argb6666, rgb565
from ..model.block import Block, Frame, Project, ProjectHeader
from ..model import block_schema
from . import descriptor as desc_mod
from . import header as header_mod
from . import lz4x, rle
from .errors import ValidationReport


def _is_compressed_frame(header: header_mod.BinHeader, type_id: int) -> bool:
    """ReadBinFile.java's flagCompressedFrame decision, verified line
    for line against the source:

        if (addressBlock != 1 && != 2 && != 3) {
            flagCompressedFrame = (version==2) || (version==3);
        } else {
            flagCompressedFrame = (versionCompress == 3);
        }
    """
    if block_schema.is_hand(type_id):
        return header.version == 3
    return header.version in (2, 3)


def _read_descriptors(data: bytes, header: header_mod.BinHeader) -> Tuple[List[desc_mod.BlockDescriptor], int]:
    descriptors: List[desc_mod.BlockDescriptor] = []
    offset = header_mod.HEADER_SIZE
    max_possible = (len(data) - header_mod.HEADER_SIZE) // desc_mod.DESCRIPTOR_SIZE
    for _ in range(max(max_possible, 0)):
        if offset + desc_mod.DESCRIPTOR_SIZE > len(data):
            break
        d = desc_mod.parse_descriptor(data, offset)
        descriptors.append(d)
        offset += desc_mod.DESCRIPTOR_SIZE
        # End-of-descriptors terminator check (see module docstring).
        if offset + 2 <= len(data) and data[offset] == 0 and data[offset + 1] == 0:
            offset += 2
            break
    return descriptors, offset


def _decode_v1_v2_frame(data: bytes, addr: int, width: int, height: int, compressed: bool, report: ValidationReport, block_name: str) -> Tuple["object", int]:
    if compressed:
        if addr + 4 > len(data):
            report.warn(f"'{block_name}': truncated compressed frame at offset {addr}; treating remaining frames as raw.")
            compressed = False
        else:
            temp_size = int.from_bytes(data[addr:addr + 4], "little", signed=False) + 4
            if not (8 < temp_size < len(data)):
                # Mirrors ReadBinFile.java's own sanity fallback: an
                # implausible size means "actually not compressed".
                compressed = False
    if compressed:
        size = int.from_bytes(data[addr:addr + 4], "little", signed=False) + 4
        buf = data[addr:addr + size]
        raw = rle.decompress(buf, width, height)
        image = rgb565.unpack_big_endian_gamma(raw, width, height)
        return image, addr + size
    size = width * height * 2
    buf = data[addr:addr + size]
    if len(buf) < size:
        raise ValueError(
            f"'{block_name}': not enough data to read a {width}x{height} raw RGB565 frame "
            f"at offset {addr} (needed {size} bytes, only {len(buf)} available)."
        )
    image = rgb565.unpack_big_endian_gamma(buf, width, height)
    return image, addr + size


def _decode_v3_frame(data: bytes, addr: int, block_name: str):
    raw, meta, consumed = lz4x.decode_frame(data, addr)
    if meta.method == lz4x.METHOD_ARGB6666:
        image = argb6666.unpack(raw, meta.width, meta.height)
    else:
        image = rgb565.unpack_little_endian_linear(raw, meta.width, meta.height)
    return image, addr + consumed


def _default_digit_glyph_offset(block_name: str, images_count: int) -> int:
    """Best-effort default for Block.digit_glyph_offset - see that
    field's docstring for why this can't be known for certain from the
    file format alone. The only case with real evidence behind it is
    exactly 14 frames, matching the contiguous ASCII strip
    '-./0123456789:' confirmed by inspecting the supplied reference
    file's HoursDigits/MinutesDigits glyph pool (digit '0' at index 3).
    Any other frame count falls back to a naive direct mapping (digit
    value == frame index), which the user can correct in the
    Properties panel by comparing against the Frames strip."""
    if block_schema.compound_digit_count(block_name) is None:
        return 0
    if images_count == 14:
        return 3
    return 0


def read_bin(path: str) -> Tuple[Project, ValidationReport]:
    with open(path, "rb") as fh:
        data = fh.read()
    project, report = read_bin_bytes(data)
    project.source_path = path
    return project, report


def read_bin_bytes(data: bytes) -> Tuple[Project, ValidationReport]:
    report = ValidationReport()
    header = header_mod.parse_header(data)
    if not header_mod.verify_crc(data, header):
        report.warn(
            "The file's CRC32 checksum does not match its contents. The file "
            "may have been edited by another tool or partially corrupted; "
            "GloryDial Studio will still try to load it."
        )

    descriptors, image_area_start = _read_descriptors(data, header)

    project = Project(
        header=ProjectHeader(opaque_id=header.opaque_id),
        screen_width=header.width,
        screen_height=header.height,
        compression_version=header.version,
        source_path=None,
    )

    for d in descriptors:
        compressed = _is_compressed_frame(header, d.type_id)
        block_name = block_schema.block_name(d.type_id)
        addr = d.start_address
        frames: List[Frame] = []
        try:
            for _ in range(d.images_count):
                if header.version == 3:
                    image, addr = _decode_v3_frame(data, addr, block_name)
                else:
                    image, addr = _decode_v1_v2_frame(data, addr, d.width, d.height, compressed, report, block_name)
                frames.append(Frame(image))
        except Exception as exc:  # noqa: BLE001 - surfaced as a readable report entry
            report.error(f"Could not decode frame(s) for block '{block_name}' (type {d.type_id}): {exc}")
            continue

        block = Block(
            type_id=d.type_id,
            x=d.x,
            y=d.y,
            animation_speed=d.animation_speed,
            black_is_transparent=d.black_is_transparent,
            arrow_full_length=d.arrow_full_length,
            arrow_length_to_center=d.arrow_length_to_center,
            arrow_width=d.arrow_width,
            frames=frames,
            digit_glyph_offset=_default_digit_glyph_offset(block_name, d.images_count),
        )
        if d.type_id in project.blocks:
            report.warn(f"Duplicate block type id {d.type_id} ('{block_name}') found in file; keeping the last one.")
        project.blocks[d.type_id] = block

    return project, report
