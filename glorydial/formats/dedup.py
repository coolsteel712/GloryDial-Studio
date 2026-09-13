"""Shared-resource detection at compile time.

Ported from ``BinFile/CheckDuplicate/FolderImageComparison.java``: two
blocks whose *entire* set of frame images are byte-identical (as a
set, not an ordered sequence - ``Set<String>`` equality in the Java
source) get grouped, and only the first one's resource bytes are
actually written; every other block in the group points its
``start_address`` at that first block's address instead.

The original hashes raw PNG file bytes on disk; we hash decoded pixel
content instead (frame.content_hash(), SHA-256 of the RGBA buffer) so
grouping is robust to how a frame happened to be produced or
re-encoded, which is strictly a superset of what byte-identical PNGs
would already match.
"""

from __future__ import annotations

from typing import Dict, List

from ..model.block import Block


def group_shared_resources(blocks: List[Block]) -> Dict[int, int]:
    """Returns a mapping of {type_id: representative_type_id} for every
    block whose frame content is identical to an earlier block's (in
    the given order). A block not present as a key shares with no one
    and owns its own resource."""
    seen: Dict[frozenset, int] = {}
    representative_of: Dict[int, int] = {}
    for block in blocks:
        if not block.frames:
            continue
        key = block.frame_hash_set()
        if key in seen:
            representative_of[block.type_id] = seen[key]
        else:
            seen[key] = block.type_id
            representative_of[block.type_id] = block.type_id
    return representative_of
