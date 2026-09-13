"""Simulated runtime values driving the live preview.

ClockFaceEdit's own editor preview does NOT simulate time/date/sensor
values at all - CanvasImage.java always shows a single fixed,
illustrative frame per block (picked by a hard-coded per-block-name
heuristic) and rotates hands to three constant demo angles
(300/48/216 degrees). That's a static mock-up, not a simulation.

GloryDial Studio replaces that with a genuine simulation: every block
gets one or more frame indices (or a rotation angle, for hands)
computed from an explicit, user-editable SimState. This is an
intentional, additive improvement the task calls for; it does not
change anything about the compiled file format - only what the
live-editing preview shows.

IMPORTANT, SOURCE-CONFIRMED CORRECTION: an earlier version of this
module assumed blocks like "HoursDigits" have one frame per possible
value (e.g. frame 14 for 2 PM). That is wrong. EnumZeroNumberBlock.java
assigns these names a "value" (2 for HoursDigits, 5 for StepsDigits,
etc.) that CanvasImage.java/CanvasImageFull.java read back via
utilities.getTaxValue() as `count`, and use to drive a real
side-by-side compositing loop:

    for (int i = 0; i < count; i++) {
        ... pick which single-digit glyph to show ...
        removeBackgroundImage(..., x, y, ...);
        x += Width;   // advance for the next digit
    }

So "HoursDigits" is a compound block: a shared pool of single-digit
glyph images (0-9, sometimes with a couple of extras), rendered as
`count` digits side-by-side, most-significant first - see
model/block_schema.py's COMPOUND_DIGIT_COUNTS (values taken directly
from EnumZeroNumberBlock.java) and resolve_display_frame_indices()
below. The already-separately-split single-digit blocks
(HoursTensDigits, HoursOnesDigits, PulseHundredsDigits, ...) have
value 1 in that same enum, confirming they were already being handled
correctly as ordinary single-frame blocks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from ..model import block_schema
from ..model.block import Block


@dataclass
class SimState:
    dt: datetime = field(default_factory=datetime.now)
    battery_percent: int = 78
    connected: bool = True
    charging: bool = False
    heart_rate_bpm: int = 72
    steps: int = 6421
    calories: int = 312
    distance_km: float = 4.7
    temperature: int = 21
    use_celsius: bool = True
    use_12_hour: bool = False

    def clone(self) -> "SimState":
        return SimState(**self.__dict__)


def _digit(value: int, place: int) -> int:
    """place=0 -> ones, 1 -> tens, 2 -> hundreds, ..."""
    return (abs(value) // (10 ** place)) % 10


def _digits_of(value: int, count: int) -> List[int]:
    """Most-significant-digit-first list of exactly `count` decimal
    digits of abs(value), left-padded/truncated as needed - used for
    compound multi-digit blocks (see COMPOUND_DIGIT_COUNTS)."""
    return [_digit(value, p) for p in range(count - 1, -1, -1)]


def _clamp_index(value: int, images_count: int) -> int:
    if images_count <= 0:
        return 0
    return max(0, min(value, images_count - 1))


def _hours_24(sim: SimState) -> int:
    return sim.dt.hour


def _hours_12(sim: SimState) -> int:
    h = sim.dt.hour % 12
    return 12 if h == 0 else h


def _hours_value(sim: SimState) -> int:
    return _hours_12(sim) if sim.use_12_hour else _hours_24(sim)


# --------------------------------------------------------------------
# Single-frame blocks: name -> function (block, sim) -> ONE frame index
# (or, for already-split single-digit blocks, one digit 0-9).
# Anything not listed falls back to frame 0 in resolve_frame_index().
# --------------------------------------------------------------------
_RESOLVERS = {
    "HoursTensDigits": lambda b, s: _digit(_hours_value(s), 1),
    "HoursOnesDigits": lambda b, s: _digit(_hours_value(s), 0),
    "MinutesTensDigits": lambda b, s: _digit(s.dt.minute, 1),
    "MinutesOnesDigits": lambda b, s: _digit(s.dt.minute, 0),
    "SecondsTensDigits": lambda b, s: _digit(s.dt.second, 1),
    "SecondsOnesDigits": lambda b, s: _digit(s.dt.second, 0),
    "MonthsNames": lambda b, s: s.dt.month - 1,
    "MonthTensDigits": lambda b, s: _digit(s.dt.month, 1),
    "MonthOnesDigits": lambda b, s: _digit(s.dt.month, 0),
    "DayTensDigits": lambda b, s: _digit(s.dt.day, 1),
    "DayOnesDigits": lambda b, s: _digit(s.dt.day, 0),
    "DaysOfWeek": lambda b, s: s.dt.weekday(),
    "YearThousandsDigits": lambda b, s: _digit(s.dt.year, 3),
    "YearHundredsDigits": lambda b, s: _digit(s.dt.year, 2),
    "YearTensDigits": lambda b, s: _digit(s.dt.year, 1),
    "YearOnesDigits": lambda b, s: _digit(s.dt.year, 0),
    "AmPmText": lambda b, s: 0 if s.dt.hour < 12 else 1,
    "BatteryImages": lambda b, s: _battery_frame(b, s),
    "ConnectionImages": lambda b, s: 0 if s.connected else (1 if b.images_count > 1 else 0),
    "PulseImages": lambda b, s: 0,
    "PulseHundredsDigits": lambda b, s: _digit(s.heart_rate_bpm, 2),
    "PulseTensDigits": lambda b, s: _digit(s.heart_rate_bpm, 1),
    "PulseOnesDigits": lambda b, s: _digit(s.heart_rate_bpm, 0),
    "StepsTenThousandsDigits": lambda b, s: _digit(s.steps, 4),
    "StepsThousandsDigits": lambda b, s: _digit(s.steps, 3),
    "StepsHundredsDigits": lambda b, s: _digit(s.steps, 2),
    "StepsTensDigits": lambda b, s: _digit(s.steps, 1),
    "StepsOnesDigits": lambda b, s: _digit(s.steps, 0),
    "CaloriesThousandsDigits": lambda b, s: _digit(s.calories, 3),
    "CaloriesHundredsDigits": lambda b, s: _digit(s.calories, 2),
    "CaloriesTensDigits": lambda b, s: _digit(s.calories, 1),
    "CaloriesOnesDigits": lambda b, s: _digit(s.calories, 0),
    "KilometresTensDigits": lambda b, s: _digit(int(s.distance_km), 1),
    "KilometresOnesDigits": lambda b, s: _digit(int(s.distance_km), 0),
    "KilometresTenthsDigits": lambda b, s: int(round(s.distance_km * 10)) % 10,
    "KilometresHundredsDigits": lambda b, s: int(round(s.distance_km * 100)) % 10,
    "CelsiusFahrenheitText": lambda b, s: 0 if s.use_celsius else 1,
    "WeatherImages": lambda b, s: 0,
    "StepsIcon": lambda b, s: 0,
    "StepsImages": lambda b, s: 0,
    "CaloriesImages": lambda b, s: 0,
    "CaloriesImages2": lambda b, s: 0,
    "KilometresImages": lambda b, s: 0,
}


# --------------------------------------------------------------------
# Compound multi-digit blocks: name -> function (block, sim) -> the RAW
# INTEGER VALUE to split into block_schema.compound_digit_count(name)
# side-by-side digit glyphs, most-significant first.
#
# Decimal placement for KilometresDigits and sign handling for
# TemperatureDigits are not specified anywhere in the available
# ClockFaceEdit source (it only tells us "N glyphs side by side", not
# which represent a fractional part or a sign) - the choices below
# (hundredths-of-a-km for distance, absolute value for temperature) are
# GloryDial Studio's own reasonable, clearly-documented interpretation,
# not something read from the reference implementation.
# --------------------------------------------------------------------
_COMPOUND_VALUE_RESOLVERS = {
    "HoursDigits": lambda b, s: _hours_value(s),
    "MinutesDigits": lambda b, s: s.dt.minute,
    "SecondsDigits": lambda b, s: s.dt.second,
    "MonthsDigits": lambda b, s: s.dt.month,
    "DayDigits": lambda b, s: s.dt.day,
    "PulseDigits": lambda b, s: s.heart_rate_bpm,
    "TemperatureDigits": lambda b, s: s.temperature,
    "StepsDigits": lambda b, s: s.steps,
    "FullYearDigits": lambda b, s: s.dt.year,
    "CaloriesDigits": lambda b, s: s.calories,
    "BatteryChargeDigits": lambda b, s: s.battery_percent,
    "KilometresDigits": lambda b, s: int(round(s.distance_km * 100)),
}


def _battery_frame(block: Block, sim: SimState) -> int:
    if block.images_count <= 1:
        return 0
    idx = int(sim.battery_percent / 100.0 * (block.images_count - 1))
    return idx


def resolve_frame_index(block: Block, sim: SimState) -> int:
    """Returns which SINGLE frame (0-based) of ``block`` should be shown.
    Only meaningful for non-compound blocks - see
    resolve_display_frame_indices() for the general entry point that
    also handles compound multi-digit blocks correctly."""
    if block.images_count == 0:
        return 0
    resolver = _RESOLVERS.get(block.name)
    if resolver is None:
        return 0
    try:
        raw = resolver(block, sim)
    except Exception:
        raw = 0
    return _clamp_index(int(raw), block.images_count)


def resolve_display_frame_indices(block: Block, sim: SimState) -> List[int]:
    """General entry point for rendering: returns the ordered list of
    frame indices to draw side-by-side, left to right, starting at the
    block's own (X, Y) and advancing by one frame-width per subsequent
    entry (matching CanvasImage.java's `x += Width` loop). Length is 1
    for every ordinary block, and block_schema.compound_digit_count(name)
    for compound digit-group blocks like HoursDigits.

    Each digit value has ``block.digit_glyph_offset`` added before
    clamping into the available frame range - see Block.digit_glyph_offset
    for why that offset exists and is not always 0."""
    if block.images_count == 0:
        return [0]
    n = block_schema.compound_digit_count(block.name)
    if n is None:
        return [resolve_frame_index(block, sim)]
    resolver = _COMPOUND_VALUE_RESOLVERS.get(block.name)
    try:
        value = int(resolver(block, sim)) if resolver else 0
    except Exception:
        value = 0
    return [_clamp_index(d + block.digit_glyph_offset, block.images_count) for d in _digits_of(value, n)]
