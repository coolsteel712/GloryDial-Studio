"""Compression-version-3 per-frame LZ4 container.

Ported from ``Frame.decompressionLZ4`` (read) and the V3 branch of
``CreateBinFile.addressStartImage`` (write). Every frame - hands
included, unlike V1/V2 - is stored as:

    u32 LE   start_address   (absolute byte offset of this frame in the
                              file; informational/legacy, re-derived on
                              write, preserved on read)
    u16 LE   width
    u16 LE   height
    u8       flag            (CreateBinFile.java writes this as an
                              independent literal: 0 for the RGB565
                              branch, 1 for the ARGB6666 branch)
    u8       method          (also an independent literal: 2 for
                              RGB565, 3 for ARGB6666)
    u16 LE   reserved         (always 0)
    u32 LE   compressed_size (length of the LZ4 block that follows)
    u16 LE   trailer_marker1 (0x0002 observed / written as bytes 2,1 -
                              see note below)
    u8       0xCC
    u8       0xCC
    <compressed_size bytes of raw LZ4 block data>

Verified directly against CreateBinFile.java, lines 303-311:

    // RGB565 branch:      // ARGB6666 branch:
    metaData[8] = 0;       metaData[8] = 1;
    metaData[9] = 2;       metaData[9] = 3;
    metaData[10] = 0;      metaData[10] = 0;
    metaData[11] = 0;      metaData[11] = 0;

``flag`` and ``method`` are each written as their own single-byte
literal by the two independent branches above - the source never
constructs or reads a combined 4-byte "pixel format" integer, even
though bytes 8-11 happen to read back as 0x00000200 / 0x00000301 when
viewed as one little-endian u32 (a byte-pattern side effect of flag
sitting in the low byte and method in the next one, not something the
Java code itself does). Both fields are modeled and preserved
separately here to stay faithful to the actual write statements.

CreateBinFile writes bytes 16/17 as the literal values 2 and 1
(``metaData[16]=2; metaData[17]=1;``) and bytes 18/19 as 0xCC 0xCC
(``metaData[18]=-52; metaData[19]=-52;`` i.e. -52 as a signed byte ==
0xCC unsigned). Nothing in the available source explains what these
four bytes mean beyond "always these constants" - they are preserved
verbatim rather than reinterpreted.

The LZ4 payload itself is a raw (headerless) LZ4 block, decompressed
with an upper-bound target size of ``width*height*3`` regardless of
the actual pixel format - this is safe (not a bug) because LZ4's raw
block format has no fixed original-size field; both Java's
LZ4SafeDecompressor and Python's lz4.block.decompress stop as soon as
the compressed input is exhausted, so passing an oversized upper bound
just avoids a second, tighter allocation. This was confirmed against
the supplied reference file (Double Circle.bin) during development:
the actual decompressed length for a method=2 (RGB565) frame came back
as exactly width*height*2, not width*height*3, confirming the
decompressor trims to the real payload rather than the upper bound.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from lz4.block import compress as _lz4_compress
from lz4.block import decompress as _lz4_decompress

METHOD_RGB565 = 2
METHOD_ARGB6666 = 3

METADATA_SIZE = 20


@dataclass
class Lz4FrameMeta:
    start_address: int
    width: int
    height: int
    flag: int
    method: int
    compressed_size: int


def parse_meta(buf: bytes, offset: int) -> Lz4FrameMeta:
    start_address, width, height = struct.unpack_from("<IHH", buf, offset)
    flag = buf[offset + 8]
    method = buf[offset + 9]
    compressed_size = struct.unpack_from("<I", buf, offset + 12)[0]
    return Lz4FrameMeta(start_address, width, height, flag, method, compressed_size)


def raw_pixel_size(meta: "Lz4FrameMeta") -> int:
    """Exact expected size of the decompressed pixel buffer for this
    frame, per CreateBinFile.java's own packing: 2 bytes/pixel for
    RGB565 (method 2), 3 bytes/pixel for ARGB6666 (method 3)."""
    bytes_per_pixel = 2 if meta.method == METHOD_RGB565 else 3
    return meta.width * meta.height * bytes_per_pixel


def decode_frame(buf: bytes, offset: int) -> "tuple[bytes, Lz4FrameMeta, int]":
    """Returns (raw_pixel_bytes, meta, total_bytes_consumed)."""
    meta = parse_meta(buf, offset)
    payload = buf[offset + METADATA_SIZE: offset + METADATA_SIZE + meta.compressed_size]
    exact_size = raw_pixel_size(meta)
    raw = _lz4_decompress(payload, uncompressed_size=exact_size)
    return raw, meta, METADATA_SIZE + meta.compressed_size


def encode_frame(start_address: int, width: int, height: int, method: int, raw_pixels: bytes) -> bytes:
    if method not in (METHOD_RGB565, METHOD_ARGB6666):
        raise ValueError(f"Unsupported V3 pixel method {method!r}; expected {METHOD_RGB565} (RGB565) or {METHOD_ARGB6666} (ARGB6666).")
    compressed = bytes(_lz4_compress(raw_pixels, mode="fast", store_size=False))
    meta = bytearray(METADATA_SIZE)
    struct.pack_into("<IHH", meta, 0, start_address & 0xFFFFFFFF, width, height)
    # CreateBinFile.java, lines 303-311: two independent per-branch byte
    # literals, NOT a derived combined value -
    #   RGB565:   metaData[8]=0; metaData[9]=2;
    #   ARGB6666: metaData[8]=1; metaData[9]=3;
    meta[8] = 0 if method == METHOD_RGB565 else 1
    meta[9] = method & 0xFF
    meta[10] = 0
    meta[11] = 0
    struct.pack_into("<I", meta, 12, len(compressed))
    meta[16] = 2
    meta[17] = 1
    meta[18] = 0xCC
    meta[19] = 0xCC
    return bytes(meta) + compressed
