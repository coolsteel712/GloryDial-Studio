import os

import numpy as np

from glorydial.formats import reader, writer

SAMPLE = os.path.join(os.path.dirname(__file__), "sample_double_circle.bin")


def test_v1_round_trip_lossless_after_first_quantization(tmp_path):
    project, _ = reader.read_bin(SAMPLE)
    out = str(tmp_path / "v1.bin")
    writer.write_bin(project, out, version=1)

    project2, report2 = reader.read_bin(out)
    assert not report2.errors
    assert len(project2.blocks) == len(project.blocks)

    for tid, block in project.blocks.items():
        block2 = project2.blocks[tid]
        assert block2.images_count == block.images_count
        for f1, f2 in zip(block.frames, block2.frames):
            a1 = np.asarray(f1.image.convert("RGB")).astype(int)
            a2 = np.asarray(f2.image.convert("RGB")).astype(int)
            assert a1.shape == a2.shape

    # V1 is never compressed: re-compiling the already-quantized project
    # a second time must produce byte-identical pixel data (no further
    # drift), which is the real lossless guarantee V1 offers.
    out2 = str(tmp_path / "v1_again.bin")
    writer.write_bin(project2, out2, version=1)
    project3, report3 = reader.read_bin(out2)
    assert not report3.errors
    for tid, block2 in project2.blocks.items():
        block3 = project3.blocks[tid]
        for f2, f3 in zip(block2.frames, block3.frames):
            assert np.array_equal(np.asarray(f2.image), np.asarray(f3.image))


def test_v1_header_fields():
    project, _ = reader.read_bin(SAMPLE)
    data = writer.compile_bin(project, version=1)
    assert data[19] == 1
    assert data[20] == 0xFF  # block count only meaningful for v>=3


def test_v1_recompiled_file_is_fully_readable():
    project, _ = reader.read_bin(SAMPLE)
    data = writer.compile_bin(project, version=1)
    project2, report2 = reader.read_bin_bytes(data)
    assert not report2.errors
    assert len(project2.blocks) == len(project.blocks)
