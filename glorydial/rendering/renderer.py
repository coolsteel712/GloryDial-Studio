"""Composites a Project + SimState into a single rendered frame.

Paint order is ported from CanvasImage.java's drawImageCanvas():
Background(17) is blitted full-canvas first (outside the main loop,
and only if it exists and is visible), Preview(10) is never drawn on
the live face at all, then every other visible block is painted in
ascending type-id order, and finally the three hands are painted last
(on top of everything else) - see model.block.Project.render_order_blocks().

BlackIsTransparent is applied per-pixel at render time (pure black ->
fully transparent), exactly mirroring CanvasImage.removeBackgroundImage:
``if (BlackIsTransparent && color.equals(Color.BLACK)) color = TRANSPARENT;``
It is never baked into stored/edited pixel data.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from PIL import Image

from ..model import block_schema
from ..model.block import Block, Project
from . import hands as hands_mod
from .simulation import SimState, resolve_display_frame_indices, resolve_frame_index


def _apply_black_is_transparent(image: Image.Image) -> Image.Image:
    arr = np.array(image.convert("RGBA"))
    black_mask = (arr[:, :, 0] == 0) & (arr[:, :, 1] == 0) & (arr[:, :, 2] == 0)
    arr[black_mask, 3] = 0
    return Image.fromarray(arr, "RGBA")


def _maybe_strip_black(block: Block, image: Image.Image) -> Image.Image:
    return _apply_black_is_transparent(image) if block.black_is_transparent else image


def _frame_image(block: Block, sim: SimState) -> Optional[Image.Image]:
    """Single-frame lookup, used for Background and for hands (which
    always show exactly one frame - compound digit compositing does not
    apply to them)."""
    if not block.frames:
        return None
    idx = resolve_frame_index(block, sim)
    idx = max(0, min(idx, len(block.frames) - 1))
    return _maybe_strip_black(block, block.frames[idx].image)


def _display_images(block: Block, sim: SimState) -> List[Image.Image]:
    """General entry point for non-hand, non-background blocks: returns
    one or more images to draw side-by-side (see
    rendering/simulation.py's resolve_display_frame_indices for why
    compound digit-group blocks like HoursDigits need more than one)."""
    if not block.frames:
        return []
    indices = resolve_display_frame_indices(block, sim)
    out = []
    for idx in indices:
        idx = max(0, min(idx, len(block.frames) - 1))
        out.append(_maybe_strip_black(block, block.frames[idx].image))
    return out


def render(project: Project, sim: SimState) -> Image.Image:
    canvas = Image.new("RGBA", (project.screen_width, project.screen_height), (0, 0, 0, 255))

    bg = project.background_block()
    if bg is not None and bg.visible and bg.frames:
        bg_image = _frame_image(bg, sim)
        if bg_image is not None:
            if bg_image.size != canvas.size:
                bg_image = bg_image.resize(canvas.size, Image.NEAREST)
            canvas.paste(bg_image, (0, 0), bg_image)

    for block in project.render_order_blocks():
        if not block.visible or not block.frames:
            continue

        if block.is_hand:
            image = _frame_image(block, sim)
            if image is None:
                continue
            transform = hands_mod.transform_for(block, sim)
            # Rotate around the pivot: PIL rotates around the image's own
            # center, so we pad/expand into a canvas-sized layer with the
            # (unrotated) hand image placed at its back-computed top-left
            # anchor (X - ArrowWidth/2, Y - ArrowLengthToCenter), then
            # rotate that layer around the true pivot (X, Y) - see
            # rendering/hands.py for the confirmed source derivation.
            layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            layer.paste(image, (round(transform.anchor_x), round(transform.anchor_y)), image)
            rotated = layer.rotate(
                -transform.angle_degrees,  # PIL rotates counter-clockwise for +angle
                resample=Image.BICUBIC,
                center=(transform.pivot_x, transform.pivot_y),
            )
            canvas.alpha_composite(rotated)
        else:
            images = _display_images(block, sim)
            x = block.x
            for image in images:
                canvas.alpha_composite(image, (x, block.y))
                x += image.width  # CanvasImage.java: x += Width (one glyph width per digit)

    return canvas
