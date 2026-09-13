"""Block type schema.

Ported directly from ``EnumBlockName.java`` in the ClockFaceEdit source.
The numeric IDs are exactly the values ClockFaceEdit uses in the 24-byte
block descriptors of a compiled .bin file, and must never be renumbered.

Note the deliberate gap at id 50 (there is no block type 50 in the
original enum - it jumps from ``Dots(49)`` to ``Animation(51)``) and the
catch-all ``unknown(73)`` entry used by ClockFaceEdit's ``getValue()``
helper when a block id can't be matched to a name. Both are preserved
here for format fidelity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"
_DEFAULTS_PATH = _RESOURCES_DIR / "block_defaults.json"

# --------------------------------------------------------------------------
# EnumBlockName.java  (id -> name)
# --------------------------------------------------------------------------
BLOCK_NAME_BY_ID: Dict[int, str] = {
    1: "HoursHand",
    2: "MinutesHand",
    3: "SecondsHand",
    4: "HoursDigits",
    5: "MinutesDigits",
    6: "SecondsDigits",
    7: "TimeDelimiter",
    8: "BatteryImages",
    9: "ConnectionImages",
    10: "Preview",
    11: "MonthsDigits",
    12: "MonthsNames",
    13: "DayDigits",
    14: "DateDelimiter",
    15: "DaysOfWeek",
    16: "AmPmText",
    17: "Background",
    18: "PulseImages",
    19: "PulseDigits",
    20: "WeatherImages",
    21: "TemperatureDigits",
    22: "CelsiusFahrenheitText",
    23: "BpmText",
    24: "StepsIcon",
    25: "StepsDigits",
    26: "StepsText",
    27: "FullYearDigits",
    28: "YearDelimiter",
    29: "CaloriesImages",
    30: "CaloriesDigits",
    31: "CaloriesText",
    32: "StepsImages",
    33: "BatteryChargeDigits",
    34: "Percent",
    35: "PulseHundredsDigits",
    36: "PulseTensDigits",
    37: "PulseOnesDigits",
    38: "StepsTenThousandsDigits",
    39: "StepsThousandsDigits",
    40: "StepsHundredsDigits",
    41: "StepsTensDigits",
    42: "StepsOnesDigits",
    43: "CaloriesThousandsDigits",
    44: "CaloriesHundredsDigits",
    45: "CaloriesTensDigits",
    46: "CaloriesOnesDigits",
    47: "KilometresDigits",
    48: "KmMiText",
    49: "Dots",
    # NOTE: 50 intentionally does not exist in ClockFaceEdit's EnumBlockName.
    51: "Animation",
    52: "KilometresTensDigits",
    53: "KilometresOnesDigits",
    54: "KilometresDelimiter",
    55: "KilometresTenthsDigits",
    56: "KilometresHundredsDigits",
    57: "HoursTensDigits",
    58: "HoursOnesDigits",
    59: "MinutesTensDigits",
    60: "MinutesOnesDigits",
    61: "SecondsTensDigits",
    62: "SecondsOnesDigits",
    63: "MonthTensDigits",
    64: "MonthOnesDigits",
    65: "DayTensDigits",
    66: "DayOnesDigits",
    67: "YearThousandsDigits",
    68: "YearHundredsDigits",
    69: "YearTensDigits",
    70: "YearOnesDigits",
    71: "CaloriesImages2",
    72: "KilometresImages",
    73: "unknown",
}

BLOCK_ID_BY_NAME: Dict[str, int] = {name: id_ for id_, name in BLOCK_NAME_BY_ID.items()}

# Block ids that are "hands" (ReadBinFile.java: addressBlock == 1 || 2 || 3).
# These are the only blocks that carry meaningful ArrowInfo, and the only
# blocks exempt from V1/V2 scanline compression (Frame.java / CreateBinFile.java).
HAND_IDS = (1, 2, 3)
HOURS_HAND_ID, MINUTES_HAND_ID, SECONDS_HAND_ID = HAND_IDS

# Blocks that CanvasImage.java special-cases out of the normal render loop:
# Background(17) is blitted full-canvas *before* the loop runs, and
# Preview(10) is a gallery-thumbnail resource that is never drawn on the
# live face at all.
BACKGROUND_ID = 17
PREVIEW_ID = 10
RENDER_SKIP_IDS = (BACKGROUND_ID, PREVIEW_ID)

# Suffixes used by CreateBinFile.java (via utilities.getTaxValue /
# EnumZeroNumberBlock) to decide, ONLY for compression version 2, whether a
# non-hand block's frames are stored raw instead of scanline-RLE-compressed.
# This exemption is NOT mirrored by the V2 reader (ReadBinFile.java always
# assumes non-hand blocks are compressed under v2) - that inconsistency is a
# real quirk of the original tool and is intentionally reproduced by
# formats/writer.py and formats/reader.py rather than "fixed".
DIGIT_SUFFIX_WORDS = (
    "OnesDigits",
    "TensDigits",
    "HundredsDigits",
    "ThousandsDigits",
    "TenThousandsDigits",
    "TenthsDigits",
    "Delimiter",
)

# CONFIRMED against EnumZeroNumberBlock.java (the "value" field on each
# enum constant) and its actual consumer, utilities.getTaxValue(), whose
# second return value is read as `count` by CanvasImage.java /
# CanvasImageFull.java and used to drive a side-by-side compositing loop:
#
#     for (int i = 0; i < count; i++) {
#         ... pick imageName ...
#         removeBackgroundImage(..., x, y, ...);
#         x += Width;   // advance by one glyph's width for the next digit
#     }
#
# This proves these block names are NOT "one frame per possible value"
# blocks - they are COMPOUND blocks: a shared pool of single-digit glyph
# images (typically 0-9, sometimes a couple of extras) rendered as
# `count` digits side by side, most-significant digit first. This is a
# real, source-confirmed semantic, not an assumption - see the block
# comment in rendering/simulation.py for how it's used.
#
# Values below are exactly EnumZeroNumberBlock's per-constant int:
# HoursDigits(2), MinutesDigits(2), SecondsDigits(2), MonthsDigits(2),
# DayDigits(2), PulseDigits(3), TemperatureDigits(3), StepsDigits(5),
# FullYearDigits(4), CaloriesDigits(4), BatteryChargeDigits(3),
# KilometresDigits(5). Every other *Digits block name (HoursTensDigits,
# HoursOnesDigits, PulseHundredsDigits, ...) has value 1 in the enum,
# confirming those are already-split single-digit blocks needing no
# compositing - which is also how they were already handled here.
COMPOUND_DIGIT_COUNTS = {
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


def is_hand(block_id: int) -> bool:
    return block_id in HAND_IDS


def block_name_is_digit_suffixed(name: str) -> bool:
    return any(word in name for word in DIGIT_SUFFIX_WORDS)


def compound_digit_count(name: str) -> "int | None":
    """Number of side-by-side single-digit glyphs this block name
    represents, or None if it is not a compound digit-group block (a
    normal single-frame-per-value block, or an already-split
    single-digit block like HoursTensDigits)."""
    return COMPOUND_DIGIT_COUNTS.get(name)


def block_name(block_id: int) -> str:
    return BLOCK_NAME_BY_ID.get(block_id, "unknown")


def block_id(name: str) -> int:
    if name not in BLOCK_ID_BY_NAME:
        raise KeyError(f"Unknown block name '{name}'. Not part of the ClockFaceEdit block schema.")
    return BLOCK_ID_BY_NAME[name]


def all_block_names() -> List[str]:
    return [BLOCK_NAME_BY_ID[i] for i in sorted(BLOCK_NAME_BY_ID)]


# --------------------------------------------------------------------------
# Default property values, ported from jsonfullorig.json (the template
# ClockFaceEdit ships at ./jre/jsonParsing/jsonfullorig.json and reads via
# WriteReadJsonFile.readBlockJsonFile(name, true) whenever a brand new block
# is added in the editor).
# --------------------------------------------------------------------------
@dataclass
class BlockDefaults:
    x: int = 0
    y: int = 0
    animation_speed: int = 0
    image_index: int = 0
    images_count: int = 0
    black_is_transparent: bool = True
    arrow_full_length: int = 0
    arrow_length_to_center: int = 0
    arrow_width: int = 0


def _load_defaults() -> Dict[str, BlockDefaults]:
    result: Dict[str, BlockDefaults] = {}
    try:
        with open(_DEFAULTS_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        raw = {}
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        arrow = entry.get("ArrowInfo", {}) or {}
        result[name] = BlockDefaults(
            x=int(entry.get("X", 0)),
            y=int(entry.get("Y", 0)),
            animation_speed=int(entry.get("AnimationSpeed", 0)),
            image_index=int(entry.get("ImageIndex", 0)),
            images_count=int(entry.get("ImagesCount", 0)),
            black_is_transparent=bool(entry.get("BlackIsTransparent", True)),
            arrow_full_length=int(arrow.get("ArrowFullLength", 0)),
            arrow_length_to_center=int(arrow.get("ArrowLengthToCenter", 0)),
            arrow_width=int(arrow.get("ArrowWidth", 0)),
        )
    # Make sure every known block name has *some* default, even if the
    # template json was missing an entry (defensive - keeps the app usable).
    for name in BLOCK_ID_BY_NAME:
        result.setdefault(name, BlockDefaults())
    return result


BLOCK_DEFAULTS: Dict[str, BlockDefaults] = _load_defaults()


def default_for(name: str) -> BlockDefaults:
    return BLOCK_DEFAULTS.get(name, BlockDefaults())
