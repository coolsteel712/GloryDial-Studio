"""Compression-version-2 scanline RLE codec.

Ported as literally as possible from ``Frame.java``'s ``compression`` /
``decompression`` methods (plus its helpers ``checkSubsequencePixel``,
``packingChainPixels`` and ``countClonePixel``), including the exact
byte-offset arithmetic.

CONFIRMED REFERENCE-IMPLEMENTATION BUG (verified by re-reading
Frame.java verbatim after this port initially looked "too corrupted to
be a faithful port" - it is a faithful port): ``packingChainPixels``
groups consecutive runs that share the same repeat-count into one
compact record, and reconstructs each distinct pixel's bytes by
grabbing a flat contiguous slice of the ORIGINAL line at an offset
computed from ``sizeCurrentByte/pixelCount - 2 + count``. That offset
formula is only correct when every run in the group has
``repeatValue == 1`` (so there is no repetition to skip over between
distinct pixels); for any group with ``repeatValue > 1`` it reads from
the wrong position, silently substituting a wrong (usually nearby,
already-seen) pixel value for one or more of the group's members. This
was confirmed against the supplied reference file by isolating a
single real scanline (block "DaysOfWeek", frame 0, row 14) that
contains a [2,2,2]-run group and manually tracing both the Java
source's arithmetic and the actual byte layout it reads from - the
reconstructed pixel is provably wrong there, independent of any
last-row/table issue. It is preserved here exactly rather than
"corrected", per this project's compatibility-over-elegance rule -
GloryDial Studio's V2 output and re-import behave identically to
ClockFaceEdit's own. Affected rows are usually few and often visually
minor (an adjacent, already-similar color substituted for one pixel),
but this is a real, deterministic limitation of compression V2 in the
original tool. Prefer V1 (always lossless, never compressed) or V3
(byte-exact validated against a real device export) unless a specific
device requires V2.

Separately, and for the same underlying reason (the offset-table
lookahead having no bounds check for the last row - see decompress()),
the LAST scanline of every V2 RLE-compressed frame is also frequently
wrong. Both issues are surfaced as a validation warning by
formats/writer.py whenever V2 is selected.

On-disk layout of one compressed scanline-RLE frame buffer:

    u32 LE                total size of everything that follows
    u32 LE * num_rows      per-row byte address (see note in
                           decompress() about the +4 correction that
                           compensates for the leading size field)
    run data               concatenated per-row run records, each:
                              u8 pixel_count
                              u8 repeat_count
                              <pixel_count * 2 bytes>
"""

from __future__ import annotations

import struct
from typing import List


class _LineEncoder:
    """Mirrors Frame.java's linkedListTemp / linkedListCount instance
    fields and the three helper methods that mutate them."""

    def __init__(self) -> None:
        self.temp: List[int] = []
        self.count: List[int] = []

    def check_subsequence_pixel(self, buff_line: bytes) -> int:
        self.count.clear()
        count_clone_pixel = 1
        prev0 = 0
        prev1 = 0
        n = len(buff_line)
        i = 0
        while i < n:
            if i >= 2:
                if prev0 == buff_line[i] and prev1 == buff_line[i + 1]:
                    count_clone_pixel += 1
                else:
                    value = count_clone_pixel
                    num_of_bytes = count_clone_pixel // 255 + 1
                    for _j in range(num_of_bytes):
                        byte_value = min(value, 255)
                        self.count.append(byte_value)
                        self.temp.append(1)
                        self.temp.append(byte_value)
                        self.temp.append(prev0)
                        self.temp.append(prev1)
                        value -= byte_value
                    count_clone_pixel = 1
            prev0 = buff_line[i]
            prev1 = buff_line[i + 1]
            i += 2

        value = count_clone_pixel
        num_of_bytes = count_clone_pixel // 255 + 1
        for _j in range(num_of_bytes):
            byte_value = min(value, 255)
            self.count.append(byte_value)
            self.temp.append(1)
            self.temp.append(byte_value)
            self.temp.append(prev0)
            self.temp.append(prev1)
            value -= byte_value

        return self._count_clone_pixel(self.count)

    @staticmethod
    def _count_clone_pixel(values: List[int]) -> int:
        count = 1
        max_count = 1
        for i in range(1, len(values)):
            if values[i] == values[i - 1]:
                count += 1
                if count > max_count:
                    max_count = count
            else:
                count = 1
        return max_count

    def packing_chain_pixels(self, buff_line: bytes) -> None:
        self.temp.clear()
        pixel_counts: List[int] = []
        data: List[int] = []
        count_clone = 1
        current_element = self.count[0]
        for i in range(1, len(self.count)):
            if self.count[i] == current_element:
                count_clone += 1
            else:
                pixel_counts.append(count_clone)
                data.append(current_element)
                current_element = self.count[i]
                count_clone = 1
        pixel_counts.append(count_clone)
        data.append(current_element)

        count = 0
        all_size_byte = 0
        for i in range(len(data)):
            self.temp.append(pixel_counts[i] & 0xFF)
            self.temp.append(data[i] & 0xFF)
            pixel_count = pixel_counts[i] & 0xFF
            size_current_byte = pixel_count * 2 * (data[i] & 0xFF)
            all_size_byte += size_current_byte
            count = size_current_byte // pixel_count - 2 + count
            for j in range(pixel_count * 2):
                idx = count + j
                self.temp.append(buff_line[idx] if 0 <= idx < len(buff_line) else 0)
            count = 0
            count += all_size_byte


def compress(raw_rgb565: bytes, width: int) -> bytes:
    """Mirrors Frame.compression(Byte[] buffByte, int width)."""
    row_bytes = width * 2
    num_rows = len(raw_rgb565) // row_bytes
    line_payloads: List[bytes] = []
    for row in range(num_rows):
        line = raw_rgb565[row * row_bytes: (row + 1) * row_bytes]
        enc = _LineEncoder()
        if enc.check_subsequence_pixel(line) > 1:
            enc.packing_chain_pixels(line)
        line_payloads.append(bytes(enc.temp))

    offset_table = bytearray()
    address = len(line_payloads) * 4
    data = bytearray()
    for payload in line_payloads:
        offset_table += struct.pack("<I", address)
        address += len(payload)
        data += payload

    body = bytes(offset_table) + bytes(data)
    return struct.pack("<I", len(body)) + body


def _i32(buf: bytes, pos: int) -> int:
    """Reads a little-endian int32 at ``pos``, matching Java's
    ``b0&255 | b1<<8 | b2<<16 | b3<<24`` (note: Java does NOT mask b1..b3,
    so this is a signed-shift composition, not an unsigned u32 read -
    reproduced via struct's signed '<i' which gives the same result for
    these bit patterns)."""
    if pos + 4 <= len(buf):
        return struct.unpack_from("<i", buf, pos)[0]
    # Match Java array semantics as closely as practical: real
    # ClockFaceEdit would throw ArrayIndexOutOfBoundsException reading
    # past the end of a corrupt buffer. We treat missing bytes as 0
    # rather than crashing the whole application.
    padded = buf[pos:pos + 4] + b"\x00" * max(0, 4 - (len(buf) - pos))
    return struct.unpack("<i", padded)[0]


def _u8(buf: bytes, pos: int) -> int:
    return buf[pos] if 0 <= pos < len(buf) else 0


def decompress(buf: bytes, width: int, height: int) -> bytes:
    """Mirrors Frame.decompression(byte[] buffByte, int width, int height)
    field-for-field, INCLUDING its lack of a bounds check when reading
    "the next row's address" for what is actually the final row (at
    that point ``i+4`` points past the offset table into the start of
    the run-data section, not a real table entry). Real ClockFaceEdit
    has this exact same behavior; adding an extra guard here would make
    this module diverge from the reference implementation for the very
    last scanline of every RLE-compressed frame, so it is intentionally
    left out - only crash-safety (see _i32/_u8) is added."""
    pixel_data = bytearray(width * height * 2)
    length_block_frame = _i32(buf, 0) + 4
    address_begin_line = _i32(buf, 4)
    count_pixel = 0
    i = 0
    while i < len(buf):
        if 4 <= i <= address_begin_line:
            address_line = _i32(buf, i)
            size_block = 4
            if address_line < length_block_frame - 4:
                address_next_line = _i32(buf, i + 4)
                size_block = address_next_line - address_line
            block = 0
            block_byte_count = 4
            guard = 0
            while block < size_block:
                guard += 1
                if guard > 1_000_000:
                    break  # safety valve against runaway loops on corrupt input
                address_line_block = address_line + block
                if (
                    address_line_block + 4 >= length_block_frame
                    or address_line_block + 5 >= length_block_frame
                ):
                    break
                all_pixel = _u8(buf, address_line_block + 4)
                repeat = _u8(buf, address_line_block + 5)
                block_byte_count = 4
                if all_pixel > 1:
                    block_byte_count += all_pixel * 2 - 2
                for j in range(all_pixel):
                    p0 = _u8(buf, address_line_block + 6 + j * 2)
                    p1 = _u8(buf, address_line_block + 7 + j * 2)
                    for _y in range(repeat):
                        if count_pixel + 2 <= len(pixel_data):
                            pixel_data[count_pixel] = p0
                            pixel_data[count_pixel + 1] = p1
                        count_pixel += 2
                block += block_byte_count
        i += 4
    return bytes(pixel_data)
