from PIL import Image

from glorydial.formats import dedup
from glorydial.model.block import Block, Frame, Project


def _solid_block(type_id, color, w=4, h=4):
    return Block(type_id=type_id, frames=[Frame(Image.new("RGBA", (w, h), color))])


def test_identical_frame_sets_are_grouped():
    b1 = _solid_block(4, (255, 0, 0, 255))
    b2 = _solid_block(5, (255, 0, 0, 255))  # identical content, different block
    b3 = _solid_block(6, (0, 255, 0, 255))  # different content
    rep = dedup.group_shared_resources([b1, b2, b3])
    assert rep[4] == 4  # first occurrence is its own representative
    assert rep[5] == 4  # second occurrence shares with the first
    assert rep[6] == 6  # unique content is its own representative


def test_different_frame_counts_are_not_grouped():
    b1 = _solid_block(4, (1, 2, 3, 255))
    b2 = Block(type_id=5, frames=[Frame(Image.new("RGBA", (4, 4), (1, 2, 3, 255))), Frame(Image.new("RGBA", (4, 4), (4, 5, 6, 255)))])
    rep = dedup.group_shared_resources([b1, b2])
    assert rep[4] == 4
    assert rep[5] == 5


def test_compile_order_is_plain_ascending_numeric_no_hand_special_case():
    project = Project()
    for tid in (17, 3, 1, 4, 2, 10):
        project.add_block(tid)
        for f in project.blocks[tid].frames if False else []:
            pass
    order = [b.type_id for b in project.ordered_blocks_for_compile()]
    assert order == sorted(order) == [1, 2, 3, 4, 10, 17]


def test_render_order_puts_hands_last_and_skips_background_preview():
    project = Project()
    for tid in (17, 10, 4, 1, 2, 3, 5):
        project.add_block(tid)
    order = [b.type_id for b in project.render_order_blocks()]
    assert 17 not in order  # Background excluded (drawn separately)
    assert 10 not in order  # Preview excluded (never drawn)
    assert order == [4, 5, 1, 2, 3]  # non-hands ascending, then hands ascending
