import random

from glorydial.formats import rle


def test_rle_round_trips_random_data_except_known_edge_cases():
    random.seed(42)
    width, height = 20, 5
    row_bytes = width * 2
    data = bytearray()
    for _ in range(height):
        row = bytearray()
        while len(row) < row_bytes:
            run_len = random.choice([1, 1, 2, 3, 5, 10])
            b0, b1 = random.randint(0, 255), random.randint(0, 255)
            for _ in range(run_len):
                if len(row) + 2 <= row_bytes:
                    row += bytes([b0, b1])
        data += row[:row_bytes]
    data = bytes(data)
    comp = rle.compress(data, width)
    decomp = rle.decompress(comp, width, height)
    assert decomp == data


def test_rle_constant_color_last_row_quirk_is_isolated():
    """Documents (and pins down) the confirmed ClockFaceEdit V2 bug:
    the offset-table lookahead has no bounds check for the LAST row, so
    it reads into the start of the data section instead of a real table
    entry. For a simple (ungrouped) per-row encoding this manifests as
    exactly one wrong row - the last one - and nothing else."""
    w, h = 28, 34
    data = bytes([0xAB, 0xCD] * (w * h))
    comp = rle.compress(data, w)
    decomp = rle.decompress(comp, w, h)
    row_bytes = w * 2
    mismatched_rows = [
        r for r in range(h)
        if data[r * row_bytes:(r + 1) * row_bytes] != decomp[r * row_bytes:(r + 1) * row_bytes]
    ]
    assert mismatched_rows == [h - 1]


def test_rle_grouped_runs_with_repeat_gt_1_can_misplace_a_pixel():
    """Documents the second confirmed bug: packingChainPixels groups
    consecutive equal-repeat-count runs and reconstructs pixel values
    from a flat contiguous slice of the original line, which is only
    correct when repeat==1 for the group. This test pins down a
    concrete repeat=2 case (three back-to-back 2-pixel runs) and
    asserts the OUTPUT actually differs from the input for at least one
    of the group's pixels - i.e. it documents the bug rather than
    hiding it."""
    # Row: [P]*6, then 7 distinct singles, then [Q]*5, then three runs
    # of length 2 with DIFFERENT pixel values (this specific shape is
    # what triggers the group-of-3/repeat=2 offset bug).
    def px(n):
        return bytes([n, 255 - n])

    row = px(0) * 6
    for i in range(1, 8):
        row += px(i * 10)
    row += px(200) * 5
    row += px(74) * 2 + px(0) * 2 + px(74) * 2  # the problematic [2,2,2] group
    row += px(9) * 8
    row += px(41) * 1  # pad to reach 54 pixels like the real-world case
    row += px(7) * 7
    row = row[:54 * 2]  # exactly 54 pixels, matching the documented real case

    comp = rle.compress(row, 54)
    decomp = rle.decompress(comp, 54, 1)
    # The bug is real and reproducible: the group's third distinct pixel
    # gets substituted with the second one's value instead of its own.
    assert decomp != row
