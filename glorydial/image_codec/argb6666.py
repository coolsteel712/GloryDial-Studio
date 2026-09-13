"""ARGB6666 pixel packing/unpacking.

Ported from ``PackerImage.packImageARGB6666`` (pack) and
``UnpackerImage.unpackImageARGB6666`` with ``versionMethod == 3``
(unpack) in ClockFaceEdit. Only used for compression version 3, and
only for source images that have an alpha channel (CreateBinFile.java
picks ARGB6666 vs. RGB565-method-2 based on
``image.getColorModel().hasAlpha()``).

Each pixel is packed into 3 bytes as a little-endian 24-bit value
``A6 R6 G6 B6`` (6 bits per channel, MSB-first within the 24-bit word):
byte0 = bits 0-7, byte1 = bits 8-15, byte2 = bits 16-23.
"""

from __future__ import annotations

import numpy as np
from PIL import Image


def pack(image: Image.Image) -> bytes:
    rgba = np.asarray(image.convert("RGBA"), dtype=np.float64)
    # Java does (component*63+127)/255 using INTEGER division - replicate
    # that exactly rather than float rounding, to avoid off-by-one drift.
    a = ((np.asarray(rgba[:, :, 3], dtype=np.int64) * 63 + 127) // 255).astype(np.uint32)
    r = ((np.asarray(rgba[:, :, 0], dtype=np.int64) * 63 + 127) // 255).astype(np.uint32)
    g = ((np.asarray(rgba[:, :, 1], dtype=np.int64) * 63 + 127) // 255).astype(np.uint32)
    b = ((np.asarray(rgba[:, :, 2], dtype=np.int64) * 63 + 127) // 255).astype(np.uint32)
    packed = (a << 18) | (r << 12) | (g << 6) | b
    byte1 = (packed & 0xFF).astype(np.uint8)
    byte2 = ((packed >> 8) & 0xFF).astype(np.uint8)
    byte3 = ((packed >> 16) & 0xFF).astype(np.uint8)
    height, width = byte1.shape
    out = np.empty((height, width, 3), dtype=np.uint8)
    out[:, :, 0] = byte1
    out[:, :, 1] = byte2
    out[:, :, 2] = byte3
    return out.tobytes()


def unpack(raw: bytes, width: int, height: int) -> Image.Image:
    expected = width * height * 3
    if len(raw) < expected:
        raise ValueError(
            f"ARGB6666 buffer too short: expected {expected} bytes for "
            f"{width}x{height}, got {len(raw)}."
        )
    arr = np.frombuffer(raw[:expected], dtype=np.uint8).reshape((height, width, 3)).astype(np.uint32)
    byte1, byte2, byte3 = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    inverted = (byte3 << 16) | (byte2 << 8) | byte1
    a6 = (inverted >> 18) & 0x3F
    r6 = (inverted >> 12) & 0x3F
    g6 = (inverted >> 6) & 0x3F
    b6 = inverted & 0x3F
    out = np.empty((height, width, 4), dtype=np.uint8)
    out[:, :, 0] = ((r6 * 255 + 31) // 63).astype(np.uint8)
    out[:, :, 1] = ((g6 * 255 + 31) // 63).astype(np.uint8)
    out[:, :, 2] = ((b6 * 255 + 31) // 63).astype(np.uint8)
    out[:, :, 3] = ((a6 * 255 + 31) // 63).astype(np.uint8)
    return Image.fromarray(out, "RGBA")
