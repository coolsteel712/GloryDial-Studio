"""Regression tests for compound multi-digit block resolution.

Confirmed against EnumZeroNumberBlock.java (the per-block-name "value")
and its real consumer, utilities.getTaxValue() -> CanvasImage.java /
CanvasImageFull.java's `for (i=0;i<count;i++) { ...; x += Width; }`
side-by-side compositing loop. An earlier version of this module
treated blocks like "HoursDigits" as one-frame-per-value blocks, which
this test suite would have caught: for the real Double Circle.bin,
HoursDigits/MinutesDigits share a 14-frame resource, and 24 (a valid
hour-as-single-index in that wrong scheme) doesn't even fit in that
range while a correct 2-digit split always does.
"""

from datetime import datetime

from glorydial.model import block_schema
from glorydial.model.block import Block, Frame
from glorydial.rendering.simulation import SimState, resolve_display_frame_indices
from PIL import Image


def _digit_pool_block(type_id: int, n_frames: int = 14) -> Block:
    b = Block(type_id=type_id)
    for _ in range(n_frames):
        b.frames.append(Frame(Image.new("RGBA", (10, 10))))
    return b


def test_compound_digit_counts_match_enum_zero_number_block():
    # Verified verbatim against EnumZeroNumberBlock.java's per-constant value.
    assert block_schema.COMPOUND_DIGIT_COUNTS == {
        "HoursDigits": 2,
        "MinutesDigits": 2,
        "SecondsDigits": 2,
        "MonthsDigits": 2,
        "DayDigits": 2,
        "PulseDigits": 3,
        "TemperatureDigits": 3,
        "StepsDigits": 5,
        "FullYearDigits": 4,
        "CaloriesDigits": 4,
        "BatteryChargeDigits": 3,
        "KilometresDigits": 5,
    }


def test_already_split_single_digit_blocks_are_not_compound():
    for name in ("HoursTensDigits", "HoursOnesDigits", "PulseHundredsDigits", "YearOnesDigits"):
        assert block_schema.compound_digit_count(name) is None


def test_hours_digits_returns_two_glyphs_not_one_frame_per_hour():
    block = _digit_pool_block(block_schema.block_id("HoursDigits"))
    sim = SimState(dt=datetime(2026, 1, 1, 14, 0, 0), use_12_hour=False)  # 2 PM = 14
    indices = resolve_display_frame_indices(block, sim)
    assert len(indices) == 2
    assert indices == [1, 4]  # tens=1, ones=4 -> "14"


def test_minutes_digits_two_glyphs():
    block = _digit_pool_block(block_schema.block_id("MinutesDigits"))
    sim = SimState(dt=datetime(2026, 1, 1, 0, 4, 0))
    assert resolve_display_frame_indices(block, sim) == [0, 4]  # "04"


def test_steps_digits_five_glyphs():
    block = _digit_pool_block(block_schema.block_id("StepsDigits"))
    sim = SimState(steps=6421)
    assert resolve_display_frame_indices(block, sim) == [0, 6, 4, 2, 1]  # "06421"


def test_full_year_digits_four_glyphs():
    block = _digit_pool_block(block_schema.block_id("FullYearDigits"))
    sim = SimState(dt=datetime(2026, 1, 1))
    assert resolve_display_frame_indices(block, sim) == [2, 0, 2, 6]


def test_non_compound_block_still_returns_single_index():
    block = _digit_pool_block(block_schema.block_id("HoursTensDigits"))
    sim = SimState(dt=datetime(2026, 1, 1, 14, 0, 0))
    indices = resolve_display_frame_indices(block, sim)
    assert indices == [1]  # tens digit of 14


def test_digit_indices_are_clamped_to_available_frames():
    block = _digit_pool_block(block_schema.block_id("StepsDigits"), n_frames=5)  # only 0-4 available
    sim = SimState(steps=99999)
    indices = resolve_display_frame_indices(block, sim)
    assert all(0 <= i <= 4 for i in indices)


def test_renderer_places_digit_glyphs_side_by_side():
    from glorydial.model.block import Project
    from glorydial.rendering.renderer import render

    project = Project(screen_width=100, screen_height=50)
    block = project.add_block(block_schema.block_id("HoursDigits"))
    block.x, block.y = 10, 10
    block.black_is_transparent = False
    red = Image.new("RGBA", (8, 12), (255, 0, 0, 255))
    blue = Image.new("RGBA", (8, 12), (0, 0, 255, 255))
    for i in range(10):
        block.frames.append(Frame(red.copy() if i != 4 else blue.copy()))
    for _ in range(4):  # pad up toward a 14-frame pool like the real sample
        block.frames.append(Frame(Image.new("RGBA", (8, 12))))

    sim = SimState(dt=datetime(2026, 1, 1, 4, 0, 0), use_12_hour=False)  # hour "04" -> tens=0(red), ones=4(blue)
    img = render(project, sim)
    # tens digit (frame 0, red) drawn at x=10; ones digit (frame 4, blue) at x=18
    assert img.getpixel((12, 15))[:3] == (255, 0, 0)
    assert img.getpixel((20, 15))[:3] == (0, 0, 255)
