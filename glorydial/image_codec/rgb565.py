"""RGB565 pixel packing/unpacking.

ClockFaceEdit actually contains TWO different RGB565 codecs with
DIFFERENT byte orders, verified directly against PackerImage.java /
UnpackerImage.java - this is easy to miss (the variable names "byteH"/
"byteL" are misleading in one of them) so both are spelled out here
with the exact source lines they were checked against:

V1 & V2 ("packToBytesImage" / "unpackImage") - BIG ENDIAN:
    PackerImage.packToBytesImage():
        OutputImageArray[numByte]   = byteH;   // high byte first
        OutputImageArray[numByte+1] = byteL;   // low byte second
    UnpackerImage.unpackImage():
        byte byteH = rawImage[numByte];
        byte byteL = rawImage[numByte + 1];
        curPixel = byteH << 8 | (byteL & 255);   // high byte first, confirmed
    Channel expansion uses the Table5/Table6 lookup tables (a
    non-linear, gamma-like re-expansion).

V3 method 2 ("packImageV3Method2" / "unpackImageV3Method2") - LITTLE ENDIAN:
    PackerImage.packImageV3Method2():
        rawImage[numByte]   = rgb565 & 255;         // low byte first
        rawImage[numByte+1] = rgb565 >> 8 & 255;    // high byte second
    UnpackerImage.unpackImageV3Method2():
        rgb565 = (byteH & 255) | (byteL & 255) << 8;  // despite the
                                                        // variable names,
                                                        // this reads the
                                                        // FIRST byte as
                                                        // the LOW byte -
                                                        // i.e. little
                                                        // endian.
    Channel expansion uses plain integer division (component*255/max),
    NOT the Table5/Table6 tables.

Getting this byte order wrong would silently corrupt every V1/V2 image
on write and produce visibly wrong colors on read, so both paths are
implemented and named separately rather than sharing one "pack()"/
"unpack()" pair that would have to guess the caller's intent.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

# UnpackerImage.java Table5 / Table6 - 5-bit and 6-bit -> 8-bit expansion,
# used only by the V1/V2 (big-endian) codec.
TABLE5 = [0, 8, 16, 25, 33, 41, 49, 58, 66, 74, 82, 90, 99, 107, 115, 123,
          132, 140, 148, 156, 165, 173, 181, 189, 197, 206, 214, 222, 230,
          239, 247, 255]
TABLE6 = [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 45, 49, 53, 57, 61, 65,
          69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109, 113, 117, 121, 125,
          130, 134, 138, 142, 146, 150, 154, 158, 162, 166, 170, 174, 178,
          182, 186, 190, 194, 198, 202, 206, 210, 215, 219, 223, 227, 231,
          235, 239, 243, 247, 251, 255]

_T5 = np.array(TABLE5, dtype=np.uint16)
_T6 = np.array(TABLE6, dtype=np.uint16)


def _quantize(image: Image.Image):
    """Shared rounding step: Math.round(component*scale/255.0) for both
    PackerImage methods is numerically identical to their
    (int)(component*scale/255+0.5f) sibling for these ranges - only
    byte order differs between the two callers below."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.float64)
    r = np.round(rgb[:, :, 0] * 31.0 / 255.0).astype(np.uint16)
    g = np.round(rgb[:, :, 1] * 63.0 / 255.0).astype(np.uint16)
    b = np.round(rgb[:, :, 2] * 31.0 / 255.0).astype(np.uint16)
    return r, g, b


def pack_big_endian(image: Image.Image) -> bytes:
    """PackerImage.packToBytesImage - used for compression V1 and V2."""
    r, g, b = _quantize(image)
    val = (r << 11) | (g << 5) | b
    return val.astype(">u2").tobytes()


def pack_little_endian(image: Image.Image) -> bytes:
    """PackerImage.packImageV3Method2 - used for compression V3, method 2."""
    r, g, b = _quantize(image)
    val = (r << 11) | (g << 5) | b
    return val.astype("<u2").tobytes()


def _unpack_common(raw: bytes, width: int, height: int, dtype: str):
    expected = width * height * 2
    if len(raw) < expected:
        raise ValueError(
            f"RGB565 buffer too short: expected {expected} bytes for "
            f"{width}x{height}, got {len(raw)}."
        )
    val = np.frombuffer(raw[:expected], dtype=dtype).reshape((height, width))
    r = (val >> 11) & 0x1F
    g = (val >> 5) & 0x3F
    b = val & 0x1F
    return r, g, b


def unpack_big_endian_gamma(raw: bytes, width: int, height: int) -> Image.Image:
    """UnpackerImage.unpackImage - used for V1/V2 frames."""
    r, g, b = _unpack_common(raw, width, height, ">u2")
    out = np.empty((height, width, 4), dtype=np.uint8)
    out[:, :, 0] = _T5[r]
    out[:, :, 1] = _T6[g]
    out[:, :, 2] = _T5[b]
    out[:, :, 3] = 255
    return Image.fromarray(out, "RGBA")


def unpack_little_endian_linear(raw: bytes, width: int, height: int) -> Image.Image:
    """UnpackerImage.unpackImageV3Method2 - used for V3 method==2 frames."""
    r, g, b = _unpack_common(raw, width, height, "<u2")
    out = np.empty((height, width, 4), dtype=np.uint8)
    out[:, :, 0] = (r.astype(np.uint32) * 255 // 31).astype(np.uint8)
    out[:, :, 1] = (g.astype(np.uint32) * 255 // 63).astype(np.uint8)
    out[:, :, 2] = (b.astype(np.uint32) * 255 // 31).astype(np.uint8)
    out[:, :, 3] = 255
    return Image.fromarray(out, "RGBA")
