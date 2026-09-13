import os

import numpy as np
from PIL import Image

from glorydial.formats import reader, writer
from glorydial.model.block import Frame

SAMPLE = os.path.join(os.path.dirname(__file__), "sample_double_circle.bin")


def test_open_then_immediately_save_stays_structurally_valid(tmp_path):
    project, report = reader.read_bin(SAMPLE)
    assert not report.errors
    out = str(tmp_path / "immediate_save.bin")
    writer.write_bin(project, out, version=project.compression_version)

    project2, report2 = reader.read_bin(out)
    assert not report2.errors
    assert project2.screen_width == project.screen_width
    assert project2.screen_height == project.screen_height
    assert project2.compression_version == project.compression_version
    assert set(project2.blocks) == set(project.blocks)


def test_double_save_cycle_is_stable(tmp_path):
    """open -> save -> open -> save -> open, expecting pixel-exact
    stability by the second cycle (V3 is fully lossless per-cycle)."""
    project, _ = reader.read_bin(SAMPLE)
    path1 = str(tmp_path / "cycle1.bin")
    writer.write_bin(project, path1, version=3)

    project2, report2 = reader.read_bin(path1)
    assert not report2.errors
    path2 = str(tmp_path / "cycle2.bin")
    writer.write_bin(project2, path2, version=3)

    project3, report3 = reader.read_bin(path2)
    assert not report3.errors

    for tid in project2.blocks:
        for f2, f3 in zip(project2.blocks[tid].frames, project3.blocks[tid].frames):
            assert np.array_equal(np.asarray(f2.image), np.asarray(f3.image))


def test_editing_blocks_between_saves_still_produces_valid_file(tmp_path):
    project, _ = reader.read_bin(SAMPLE)

    # Move a block, toggle transparency, delete a block, add a new one.
    project.blocks[1].x += 10
    project.blocks[1].y -= 5
    project.blocks[4].black_is_transparent = not project.blocks[4].black_is_transparent
    project.remove_block(71)
    new_block = project.add_block(48)  # KmMiText, previously absent
    new_block.frames.append(Frame(Image.new("RGBA", (10, 10), (255, 255, 255, 255))))

    out = str(tmp_path / "edited.bin")
    writer.write_bin(project, out, version=3)

    project2, report2 = reader.read_bin(out)
    assert not report2.errors
    assert 71 not in project2.blocks
    assert 48 in project2.blocks
    assert project2.blocks[1].x == project.blocks[1].x
    assert project2.blocks[1].y == project.blocks[1].y
    assert project2.blocks[4].black_is_transparent == project.blocks[4].black_is_transparent


def test_all_three_versions_produce_openable_files(tmp_path):
    project, _ = reader.read_bin(SAMPLE)
    for version in (1, 2, 3):
        out = str(tmp_path / f"v{version}.bin")
        writer.write_bin(project, out, version=version)
        project2, report2 = reader.read_bin(out)
        assert not report2.errors, f"version {version} produced unreadable output"
        assert len(project2.blocks) == len(project.blocks)
