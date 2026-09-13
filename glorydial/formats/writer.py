"""Top-level .bin file writer.

Ported from ``CreateBinFile.java``. See model.block.Project.
ordered_blocks_for_compile() for the exact (hands-included-in-place)
ascending numeric ordering this uses for the on-disk descriptor list -
verified against CreateBinFile.java's Arrays.sort comparator and
cross-checked against the real descriptor order found in the supplied
"Double Circle.bin".

Compilation proceeds in three passes:

1. Validate (dimensions consistent per block, V3 even-width rule,
   field ranges, final size <= 1 MiB - all ported from CheckImage.java
   / utilities.allImagesSameSize / the inline checks in
   CreateBinFile.addressStartImage).
2. Detect shared resources (formats/dedup.py, ported from
   FolderImageComparison.java) so identical frame-sets are written
   once and pointed at by every block that shares them - exactly
   mirroring CreateBinFile.checkDuplicateBlock's behavior of returning
   -1 for the first ("representative") block of a group and the
   representative's address for every later member.
3. Pack every representative block's frames with the version-specific
   codec, assemble descriptors + terminator + resource bytes, then
   build the 24-byte header (size + CRC32) over the assembled payload.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from ..image_codec import argb6666, rgb565
from ..model import block_schema
from ..model.block import Block, Project
from . import descriptor as desc_mod
from . import dedup
from . import header as header_mod
from . import lz4x, rle
from .errors import ValidationError, ValidationReport

MAX_FILE_SIZE = 1024 * 1024  # CreateBinFile.java: finalBytesArr.length/1024 <= 1024


def validate_project(project: Project, version: int) -> ValidationReport:
    report = ValidationReport()
    if version not in (1, 2, 3):
        report.error(f"Unsupported compression version {version!r}; must be 1, 2 or 3.")
        return report
    if not (0 <= project.screen_width <= 0xFFFF) or not (0 <= project.screen_height <= 0xFFFF):
        report.error(f"Screen size {project.screen_width}x{project.screen_height} does not fit this format's 16-bit fields.")

    if version == 2:
        report.warn(
            "Compression V2 reproduces two confirmed data-corruption bugs present "
            "in ClockFaceEdit's own reference implementation (Frame.java): (1) the "
            "last scanline of every RLE-compressed frame is often decoded "
            "incorrectly on re-import, and (2) any run of pixels that gets grouped "
            "by its 'packingChainPixels' optimization with a repeat-count greater "
            "than 1 can substitute the wrong pixel value. Both were confirmed "
            "against real image data during development - see formats/rle.py for "
            "the full analysis. GloryDial Studio reproduces this exactly for "
            "compatibility rather than silently 'fixing' the format. Prefer V1 "
            "(always lossless) or V3 (validated byte-exact against a real device "
            "export) unless a specific device requires V2."
        )

    for block in project.blocks.values():
        if not block.frames:
            continue
        w0, h0 = block.frames[0].width, block.frames[0].height
        for i, frame in enumerate(block.frames):
            if frame.width != w0 or frame.height != h0:
                report.error(
                    f"Block '{block.name}' contains images of different sizes: "
                    f"frame 0 is {w0}x{h0} but frame {i} is {frame.width}x{frame.height}. "
                    f"All frames in a block must share the same dimensions."
                )
                break
        if version == 3 and w0 % 2 != 0:
            report.error(
                f"'{block.name}' frame 0 is {w0} pixels wide. Compression version 3 "
                f"requires an even image width."
            )
        if not (0 <= block.images_count <= 0xFF):
            report.error(f"'{block.name}' has {block.images_count} frames; the maximum supported is 255.")
        if block.is_hand:
            for label, val in (
                ("ArrowFullLength", block.arrow_full_length),
                ("ArrowLengthToCenter", block.arrow_length_to_center),
                ("ArrowWidth", block.arrow_width),
            ):
                if not (0 <= val <= 0xFF):
                    report.error(f"'{block.name}'.{label} = {val} is out of range (0-255).")
    return report


def _pack_v1_or_v2_frame(image, block: Block, version: int) -> bytes:
    raw = rgb565.pack_big_endian(image)
    if version == 1:
        return raw
    # V2: hands are never compressed (Frame.java / CreateBinFile.java);
    # non-hand blocks are compressed UNLESS their name contains one of
    # the digit-suffix words (utilities.getTaxValue) - see
    # model/block_schema.py's DIGIT_SUFFIX_WORDS for the exact list and
    # the caveat that the V2 reader does not mirror this exemption.
    if block.is_hand:
        return raw
    if block_schema.block_name_is_digit_suffixed(block.name):
        return raw
    return rle.compress(raw, image.width)


def _frame_has_meaningful_alpha(image) -> bool:
    """CreateBinFile.java picks ARGB6666 vs RGB565-method-2 based on
    ``image.getColorModel().hasAlpha()`` - i.e. whether the SOURCE FILE
    was saved with an alpha channel at all, regardless of its actual
    values. Our internal model always stores frames as RGBA (see
    model.block.Frame), so that literal distinction isn't available to
    us. We use the closest meaningful equivalent instead: whether any
    pixel's alpha is not fully opaque. This produces smaller, equally
    correct V3 output (RGB565 for anything that is really opaque)
    rather than needlessly tripling storage for every frame just
    because it happens to be internally represented as RGBA - a
    deliberate, documented improvement over blindly mirroring the
    Java property, which cannot regress correctness since a fully
    opaque alpha channel carries no visual information to lose."""
    arr = np.asarray(image.convert("RGBA"))
    return bool((arr[:, :, 3] < 255).any())


def _pack_v3_frame(image, start_address: int) -> bytes:
    if _frame_has_meaningful_alpha(image):
        raw = argb6666.pack(image)
        method = lz4x.METHOD_ARGB6666
    else:
        raw = rgb565.pack_little_endian(image)
        method = lz4x.METHOD_RGB565
    return lz4x.encode_frame(start_address, image.width, image.height, method, raw)


def compile_bin(project: Project, version: int) -> bytes:
    """Returns the full compiled .bin file bytes. Raises ValidationError
    if the project can't be compiled; call validate_project() first if
    you want to show all problems at once instead of stopping at the
    first one."""
    report = validate_project(project, version)
    report.raise_if_errors()

    ordered = project.ordered_blocks_for_compile()
    representative_of = dedup.group_shared_resources(ordered)

    descriptor_bytes: List[bytes] = []
    resource_bytes = bytearray()
    resolved_address: Dict[int, int] = {}

    header_and_descriptors_size = header_mod.HEADER_SIZE + len(ordered) * desc_mod.DESCRIPTOR_SIZE + len(desc_mod.TERMINATOR)
    cursor = header_and_descriptors_size

    for block in ordered:
        resolved_address[block.type_id] = cursor
        representative_id = representative_of.get(block.type_id, block.type_id)
        is_representative = representative_id == block.type_id

        if not is_representative:
            start_address = resolved_address[representative_id]
        else:
            start_address = cursor
            for frame in block.frames:
                if version == 3:
                    frame_bytes = _pack_v3_frame(frame.image, cursor)
                else:
                    frame_bytes = _pack_v1_or_v2_frame(frame.image, block, version)
                resource_bytes += frame_bytes
                cursor += len(frame_bytes)

        desc = desc_mod.BlockDescriptor(
            type_id=block.type_id,
            width=block.width,
            start_address=start_address,
            height=block.height,
            x=block.x,
            y=block.y,
            animation_speed=block.animation_speed,
            images_count=block.images_count,
            black_is_transparent=block.black_is_transparent,
            arrow_full_length=block.arrow_full_length if block.is_hand else 0,
            arrow_length_to_center=block.arrow_length_to_center if block.is_hand else 0,
            arrow_width=block.arrow_width if block.is_hand else 0,
        )
        descriptor_bytes.append(desc_mod.build_descriptor(desc))

    payload = b"".join(descriptor_bytes) + desc_mod.TERMINATOR + bytes(resource_bytes)
    header_bytes = header_mod.build_header(
        opaque_id=project.header.opaque_id,
        width=project.screen_width,
        height=project.screen_height,
        version=version,
        block_count=len(ordered),
        payload=payload,
    )
    result = header_bytes + payload

    if len(result) > MAX_FILE_SIZE:
        raise ValidationError(
            f"Cannot proceed - 1 problem(s) found:\n"
            f"  - The compiled file is {len(result) / 1024:.1f} KB, which exceeds the "
            f"format's 1024 KB (1 MiB) limit. Reduce image sizes or frame counts."
        )
    return result


def write_bin(project: Project, path: str, version: int) -> None:
    data = compile_bin(project, version)
    with open(path, "wb") as fh:
        fh.write(data)
