"""GloryDial Studio - a modern editor for smartwatch clock-face .bin files.

This package is a clean-room Python/PyQt6 re-implementation of the
behavior of the ClockFaceEdit Java application. Where the original
source establishes specific, sometimes unusual, binary-format or
rendering behavior, that behavior is treated as authoritative and is
reproduced here even where it looks inconsistent, because compatibility
with real watch firmware depends on it. Every place where this is done
intentionally is called out in a comment referencing the ClockFaceEdit
source file/class it was derived from.
"""

__version__ = "1.0.0"
