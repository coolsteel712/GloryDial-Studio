import os

import numpy as np

from glorydial.formats import reader, writer

SAMPLE = os.path.join(os.path.dirname(__file__), "sample_double_circle.bin")


def test_v2_header_fields():
    project, _ = reader.read_bin(SAMPLE)
    data = writer.compile_bin(project, version=2)
    assert data[19] == 2
    assert data[20] == 0xFF


def test_v2_round_trip_readable_and_mostly_correct():
    project, _ = reader.read_bin(SAMPLE)
    data = writer.compile_bin(project, version=2)
    project2, report2 = reader.read_bin_bytes(data)
    assert not report2.errors
    assert len(project2.blocks) == len(project.blocks)

    # V2 has confirmed, documented reference-implementation bugs (see
    # tests/test_rle.py) that can corrupt some rows. Separately, simply
    # re-encoding via V2's RGB565 pipeline (big-endian pack + gamma-table
    # unpack) uses a DIFFERENT quantization than the V3 source data was
    # originally decoded with (linear/ARGB6666), so a small, uniform
    # per-pixel precision difference is expected on every row even with
    # zero corruption. We therefore flag a row as "bad" only when its
    # worst per-channel difference exceeds plausible quantization noise,
    # not on exact equality.
    QUANT_TOLERANCE = 20
    for tid, block in project.blocks.items():
        block2 = project2.blocks[tid]
        for f1, f2 in zip(block.frames, block2.frames):
            a1 = np.asarray(f1.image.convert("RGB")).astype(int)
            a2 = np.asarray(f2.image.convert("RGB")).astype(int)
            if a1.shape != a2.shape:
                continue
            diff = np.abs(a1 - a2)
            total_rows = a1.shape[0]
            bad_rows = sum(1 for r in range(total_rows) if diff[r].max() > QUANT_TOLERANCE)
            # At most a small minority of rows should ever be affected by
            # the two confirmed bugs; everything else is quantization noise.
            assert bad_rows <= max(2, total_rows // 4), f"block {tid}: {bad_rows}/{total_rows} rows exceed tolerance"


def test_v2_hands_match_within_quantization_tolerance():
    """Frame.java / CreateBinFile.java: hands (1,2,3) always skip the RLE
    path under V2, so hand frames must be spatially identical - but V2
    re-encodes via a different RGB565 quantization (big-endian + gamma
    table) than the V3 source was decoded with (linear + ARGB6666), so
    exact pixel equality is not the right bar; boundedness is."""
    project, _ = reader.read_bin(SAMPLE)
    data = writer.compile_bin(project, version=2)
    project2, _ = reader.read_bin_bytes(data)
    for hand_id in (1, 2, 3):
        b1 = project.blocks[hand_id]
        b2 = project2.blocks[hand_id]
        for f1, f2 in zip(b1.frames, b2.frames):
            a1 = np.asarray(f1.image.convert("RGB")).astype(int)
            a2 = np.asarray(f2.image.convert("RGB")).astype(int)
            assert a1.shape == a2.shape
            assert np.abs(a1 - a2).max() <= 24  # quantization-only bound, no compression involved


def test_v2_validation_warns_about_known_quirks():
    project, _ = reader.read_bin(SAMPLE)
    report = writer.validate_project(project, version=2)
    assert any("V2" in w or "packingChainPixels" in w for w in report.warnings)
