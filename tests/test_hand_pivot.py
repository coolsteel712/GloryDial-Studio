"""Regression tests for hand placement/rotation.

Pinned down directly against CanvasImageFull.java (the native-resolution
"full size" editor canvas, which is free of CanvasImage.java's unrelated
editor-widget-fitting scale hacks and makes the real semantics
unambiguous):

    x = X - ArrowWidth / 2.0
    y = Y - ArrowLengthToCenter
    ...
    Rotate(angle, x + ArrowWidth/2, y + ArrowLengthToCenter)   // == Rotate(angle, X, Y)

i.e. the block's own (X, Y) IS the rotation pivot; the hand image's
top-left drawing position is back-computed from it. An earlier version
of this module had this backwards (adding ArrowInfo offsets to (X, Y)
to get the pivot, and drawing the image directly at (X, Y)) after
mis-reading only the scaled CanvasImage.java preview-canvas variant.
That bug caused hands to render displaced far from their intended
position - see the real Double Circle.bin numbers exercised below.
"""

from datetime import datetime

from glorydial.model.block import Block
from glorydial.rendering import hands
from glorydial.rendering.simulation import SimState

# Real values read from the supplied Double Circle.bin (K72, 410x502, V3) -
# confirmed directly against the actual block descriptors, not assumed.
REAL_HANDS = {
    1: dict(x=205, y=251, width=38, height=151, arrow_width=38, arrow_length_to_center=145, arrow_full_length=151),
    2: dict(x=205, y=251, width=36, height=173, arrow_width=36, arrow_length_to_center=167, arrow_full_length=173),
    3: dict(x=205, y=251, width=48, height=255, arrow_width=48, arrow_length_to_center=201, arrow_full_length=255),
}


def _make_hand(type_id: int) -> Block:
    v = REAL_HANDS[type_id]
    return Block(
        type_id=type_id,
        x=v["x"],
        y=v["y"],
        arrow_width=v["arrow_width"],
        arrow_length_to_center=v["arrow_length_to_center"],
        arrow_full_length=v["arrow_full_length"],
    )


def test_pivot_is_exactly_block_xy_not_offset():
    """The pivot must be exactly (X, Y) - NOT (X + ArrowWidth/2,
    Y + ArrowLengthToCenter). This is the core of the reported bug."""
    for type_id in (1, 2, 3):
        block = _make_hand(type_id)
        px, py = hands.pivot_for(block)
        assert (px, py) == (float(block.x), float(block.y))


def test_image_anchor_is_pivot_minus_half_arrow_info():
    for type_id, v in REAL_HANDS.items():
        block = _make_hand(type_id)
        ax, ay = hands.image_anchor_for(block)
        assert ax == v["x"] - v["arrow_width"] / 2.0
        assert ay == v["y"] - v["arrow_length_to_center"]


def test_anchor_plus_half_arrow_info_recovers_pivot_for_arbitrary_values():
    """General property (not just the sample's specific numbers): for
    ANY ArrowInfo values, anchor + (ArrowWidth/2, ArrowLengthToCenter)
    must land back exactly on (X, Y)."""
    for x, y, aw, alc in [(0, 0, 0, 0), (100, 200, 50, 80), (17, 999, 3, 1), (500, 5, 255, 255)]:
        block = Block(type_id=1, x=x, y=y, arrow_width=aw, arrow_length_to_center=alc)
        ax, ay = hands.image_anchor_for(block)
        px, py = hands.pivot_for(block)
        assert ax + aw / 2.0 == px
        assert ay + alc == py


def test_zero_arrow_info_places_image_top_left_at_pivot():
    block = Block(type_id=1, x=50, y=60, arrow_width=0, arrow_length_to_center=0)
    ax, ay = hands.image_anchor_for(block)
    assert (ax, ay) == (50.0, 60)


def test_transform_for_bundles_pivot_and_anchor_consistently():
    block = _make_hand(1)
    sim = SimState(dt=datetime(2026, 1, 1, 3, 0, 0))
    t = hands.transform_for(block, sim)
    assert (t.pivot_x, t.pivot_y) == (205.0, 251)
    assert t.anchor_x == 205 - 38 / 2.0
    assert t.anchor_y == 251 - 145


def test_live_angles_at_specific_clock_times():
    """Covers the exact times requested for manual verification:
    12:00:00, 03:00:00, 06:30:00, 09:45:00, 16:04:18, 23:59:59."""
    hour_block = _make_hand(1)
    minute_block = _make_hand(2)
    second_block = _make_hand(3)

    cases = [
        # (h, m, s) -> (expected hour angle, expected minute angle, expected second angle)
        ((12, 0, 0), (0.0, 0.0, 0.0)),
        ((3, 0, 0), (90.0, 0.0, 0.0)),
        ((6, 30, 0), (195.0, 180.0, 0.0)),
        ((9, 45, 0), (292.5, 270.0, 0.0)),
        ((16, 4, 18), (122.0, 25.8, 108.0)),
        ((23, 59, 59), (359.5, 359.9, 354.0)),
    ]
    for (h, m, s), (eh, em, es) in cases:
        sim = SimState(dt=datetime(2026, 1, 1, h, m, s))
        assert abs(hands.live_angle_for(hour_block, sim) - eh) < 0.01
        assert abs(hands.live_angle_for(minute_block, sim) - em) < 0.01
        assert abs(hands.live_angle_for(second_block, sim) - es) < 0.01


def test_pivot_and_anchor_are_stable_across_all_requested_times():
    """No matter the simulated time, the PIVOT must always stay pinned
    exactly at the block's (X, Y) - only the angle should change."""
    block = _make_hand(1)
    for h, m, s in [(12, 0, 0), (3, 0, 0), (6, 30, 0), (9, 45, 0), (16, 4, 18), (23, 59, 59)]:
        sim = SimState(dt=datetime(2026, 1, 1, h, m, s))
        t = hands.transform_for(block, sim)
        assert (t.pivot_x, t.pivot_y) == (205.0, 251)


def test_reference_demo_angles_preserved_for_compatibility_reference():
    assert hands.REFERENCE_DEMO_ANGLES == {1: 300.0, 2: 48.0, 3: 216.0}
