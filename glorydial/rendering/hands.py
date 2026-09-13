"""Hand rotation: pivot point and angle.

CONFIRMED (and corrected) against ClockFaceEdit source: an earlier
version of this module got this backwards by reading only
CanvasImage.java, whose preview-canvas variant entangles the true
geometry with unrelated editor-widget-fitting scale factors (`rati`,
`/2.4`, a hardcoded `240`) used to fit an arbitrary screen size into a
fixed-size preview widget. CanvasImageFull.java - the "full size" /
native-resolution editor window opened on double-click - has the same
logic without that scaling noise and makes the real semantics
unambiguous (lines ~174-178):

    double centerArrowWidth = ArrowWidth / 2.0;
    ScaleCenterArrowWidth = centerArrowWidth / W * W;      // == ArrowWidth/2
    ScaleArrowLengthToCenter = ArrowLengthToCenter / H * W; // == ArrowLengthToCenter for a square screen
    x = X - ArrowWidth / 2.0;
    y = Y - ArrowLengthToCenter;
    ...
    gc.transform(new Affine(new Rotate(angle, x + ScaleCenterArrowWidth, y + ScaleArrowLengthToCenter)));
    gc.drawImage(wImage, x, y, ...);

i.e. **the block's (X, Y) IS the rotation pivot/anchor itself**, not the
image's top-left corner:

    image_top_left = (X - ArrowWidth / 2, Y - ArrowLengthToCenter)
    pivot = (X, Y)

(For a non-square screen, ClockFaceEdit's own `ScaleArrowLengthToCenter`
multiplies by `sizeScreenWeight/sizeScreenHeight` where it should
cancel to a plain `ArrowLengthToCenter` the same way
`ScaleCenterArrowWidth` does - almost certainly an unintentional
aspect-ratio-dependent skew/typo in the reference implementation rather
than deliberate design, since it has no analogous justification and
breaks the otherwise-exact pivot-at-(X,Y) identity. GloryDial Studio
uses the clean, resolution-independent form: pivot is always exactly
(X, Y), which is also what a 1:1 native-resolution renderer should
do - CanvasImage.java's own scaling hacks exist only because it draws
into a fixed-size preview widget, which does not apply here.)

``ArrowFullLength`` is still not used in any rotation/pivot calculation
anywhere in the available ClockFaceEdit source - it is preserved as
project data (round-tripped faithfully) but no rendering meaning is
invented for it here.

The ANGLE itself is where GloryDial Studio intentionally diverges from
ClockFaceEdit: the reference editor always shows each hand at one
fixed illustrative angle (Hour=300 deg, Minute=48 deg, Second=216 deg -
CanvasImage.removeBackgroundImage's literal Rotate(...) calls), which
is a static mock-up pose, not a working clock. Since the task calls
for a real, live, time-driven preview, angles here are computed from
the current SimState instead.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..model.block import Block
from .simulation import SimState

# ClockFaceEdit's own fixed demo angles (CanvasImage.removeBackgroundImage),
# kept available for anyone who wants to reproduce the reference editor's
# static preview pose exactly (e.g. for side-by-side comparison/testing).
REFERENCE_DEMO_ANGLES = {1: 300.0, 2: 48.0, 3: 216.0}


@dataclass
class HandTransform:
    pivot_x: float
    pivot_y: float
    anchor_x: float
    anchor_y: float
    angle_degrees: float


def pivot_for(block: Block) -> "tuple[float, float]":
    """The block's own (X, Y) IS the rotation pivot - see module
    docstring. Do NOT add ArrowWidth/2 or ArrowLengthToCenter here."""
    return (float(block.x), float(block.y))


def image_anchor_for(block: Block) -> "tuple[float, float]":
    """Top-left position at which to draw the (unrotated) hand image,
    back-computed from the pivot per CanvasImageFull.java:
    image_top_left = (X - ArrowWidth/2, Y - ArrowLengthToCenter)."""
    return (block.x - block.arrow_width / 2.0, block.y - block.arrow_length_to_center)


def live_angle_for(block: Block, sim: SimState) -> float:
    """Degrees clockwise, matching JavaFX's Rotate (clockwise-positive
    for screen coordinates), 0 degrees = hand pointing straight up."""
    if block.type_id == 1:  # HoursHand
        h = sim.dt.hour % 12
        return (h + sim.dt.minute / 60.0) * 30.0
    if block.type_id == 2:  # MinutesHand
        return (sim.dt.minute + sim.dt.second / 60.0) * 6.0
    if block.type_id == 3:  # SecondsHand
        return sim.dt.second * 6.0
    return 0.0


def transform_for(block: Block, sim: SimState) -> HandTransform:
    px, py = pivot_for(block)
    ax, ay = image_anchor_for(block)
    return HandTransform(pivot_x=px, pivot_y=py, anchor_x=ax, anchor_y=ay, angle_degrees=live_angle_for(block, sim))
