import os

from glorydial.formats import reader

SAMPLE = os.path.join(os.path.dirname(__file__), "sample_double_circle.bin")


def test_crc_mismatch_produces_warning_not_failure(tmp_path):
    with open(SAMPLE, "rb") as fh:
        data = bytearray(fh.read())
    data[8] ^= 0xFF  # corrupt one CRC byte
    corrupted = tmp_path / "corrupted_crc.bin"
    corrupted.write_bytes(bytes(data))

    project, report = reader.read_bin(str(corrupted))
    assert any("CRC32" in w for w in report.warnings)
    assert len(project.blocks) == 14  # still loads


def test_terminator_detection_stops_at_correct_block_count():
    project, report = reader.read_bin(SAMPLE)
    assert not report.errors
    assert len(project.blocks) == 14


def test_is_hand_compression_rule_matches_source():
    from glorydial.formats.reader import _is_compressed_frame
    from glorydial.formats.header import BinHeader

    h1 = BinHeader(b".BIN", 0, 0, 100, 100, 1, 0xFF)
    h2 = BinHeader(b".BIN", 0, 0, 100, 100, 2, 0xFF)
    h3 = BinHeader(b".BIN", 0, 0, 100, 100, 3, 5)

    # Hands: only compressed under v3.
    assert not _is_compressed_frame(h1, 1)
    assert not _is_compressed_frame(h2, 1)
    assert _is_compressed_frame(h3, 1)

    # Non-hands: compressed under v2 or v3, not v1.
    assert not _is_compressed_frame(h1, 17)
    assert _is_compressed_frame(h2, 17)
    assert _is_compressed_frame(h3, 17)
