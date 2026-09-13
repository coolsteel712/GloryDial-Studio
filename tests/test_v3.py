import os

import numpy as np

from glorydial.formats import header as header_mod
from glorydial.formats import reader, writer

SAMPLE = os.path.join(os.path.dirname(__file__), "sample_double_circle.bin")


def test_read_real_sample_matches_known_structure():
    project, report = reader.read_bin(SAMPLE)
    assert not report.errors
    assert not report.warnings
    assert project.screen_width == 410
    assert project.screen_height == 502
    assert project.compression_version == 3
    assert len(project.blocks) == 14
    assert set(project.blocks) == {1, 2, 3, 4, 5, 10, 11, 13, 15, 17, 25, 30, 32, 71}


def test_hand_geometry_matches_known_sample_values():
    project, _ = reader.read_bin(SAMPLE)
    hour = project.blocks[1]
    assert (hour.width, hour.height) == (38, 151)
    assert (hour.x, hour.y) == (205, 251)


def test_v3_round_trip_is_pixel_exact():
    project, _ = reader.read_bin(SAMPLE)
    data = writer.compile_bin(project, version=3)
    project2, report2 = reader.read_bin_bytes(data)
    assert not report2.errors
    assert len(project2.blocks) == len(project.blocks)

    for tid, block in project.blocks.items():
        block2 = project2.blocks[tid]
        assert block2.images_count == block.images_count
        for f1, f2 in zip(block.frames, block2.frames):
            a1 = np.asarray(f1.image)
            a2 = np.asarray(f2.image)
            assert np.array_equal(a1, a2), f"pixel mismatch in block {tid}"


def test_v3_resource_sharing_preserved_on_recompile():
    """The real sample shares resources between HoursDigits/MinutesDigits,
    MonthsDigits/DayDigits, StepsDigits/CaloriesDigits, and
    StepsImages/CaloriesImages2 - verify the dedup survives a rewrite."""
    project, _ = reader.read_bin(SAMPLE)
    data = writer.compile_bin(project, version=3)

    offset = header_mod.HEADER_SIZE
    block_count = data[20]
    addresses = {}
    for _ in range(block_count):
        import struct
        type_id = struct.unpack_from("<H", data, offset)[0]
        start_addr = struct.unpack_from("<I", data, offset + 4)[0]
        addresses[type_id] = start_addr
        offset += 24

    for a, b in [(4, 5), (11, 13), (25, 30), (32, 71)]:
        assert addresses[a] == addresses[b], f"expected block {a} and {b} to share a resource"


def test_v3_even_width_validation():
    project, _ = reader.read_bin(SAMPLE)
    # Force an odd-width frame to trigger the documented V3 validation rule.
    from PIL import Image

    from glorydial.model.block import Frame
    project.blocks[17].frames[0] = Frame(Image.new("RGBA", (11, 502)))
    report = writer.validate_project(project, version=3)
    assert any("even" in e for e in report.errors)


def test_v3_header_block_count_written():
    project, _ = reader.read_bin(SAMPLE)
    data = writer.compile_bin(project, version=3)
    assert data[19] == 3
    assert data[20] == len(project.blocks)
