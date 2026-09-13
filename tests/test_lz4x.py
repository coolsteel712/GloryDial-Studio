import os

from glorydial.formats import lz4x

SAMPLE = os.path.join(os.path.dirname(__file__), "sample_double_circle.bin")


def test_decode_real_rgb565_frame_from_sample():
    with open(SAMPLE, "rb") as fh:
        data = fh.read()
    raw, meta, consumed = lz4x.decode_frame(data, 79672)  # Background block
    assert meta.width == 410 and meta.height == 502
    assert meta.flag == 0 and meta.method == lz4x.METHOD_RGB565
    assert len(raw) == 410 * 502 * 2
    assert consumed == lz4x.METADATA_SIZE + meta.compressed_size


def test_decode_real_argb6666_frame_from_sample():
    with open(SAMPLE, "rb") as fh:
        data = fh.read()
    raw, meta, consumed = lz4x.decode_frame(data, 362)  # HoursHand
    assert meta.flag == 1 and meta.method == lz4x.METHOD_ARGB6666
    assert len(raw) == meta.width * meta.height * 3


def test_encode_matches_source_byte_layout_for_both_methods():
    # RGB565 branch: metaData[8]=0; metaData[9]=2
    frame = lz4x.encode_frame(0, 4, 4, lz4x.METHOD_RGB565, b"\x00" * 32)
    assert frame[8] == 0 and frame[9] == 2
    # ARGB6666 branch: metaData[8]=1; metaData[9]=3
    frame = lz4x.encode_frame(0, 4, 4, lz4x.METHOD_ARGB6666, b"\x00" * 48)
    assert frame[8] == 1 and frame[9] == 3
    assert frame[16] == 2 and frame[17] == 1
    assert frame[18] == 0xCC and frame[19] == 0xCC


def test_encode_decode_round_trip():
    raw_in = bytes(range(256)) * 4  # 1024 bytes, e.g. a 16x16 RGB565-ish buffer? just needs to round trip
    frame = lz4x.encode_frame(100, 8, 16, lz4x.METHOD_RGB565, raw_in[: 8 * 16 * 2])
    raw_out, meta, consumed = lz4x.decode_frame(frame, 0)
    assert raw_out == raw_in[: 8 * 16 * 2]
    assert meta.start_address == 100


def test_rejects_unsupported_method():
    try:
        lz4x.encode_frame(0, 2, 2, 99, b"\x00" * 8)
        assert False, "expected ValueError"
    except ValueError:
        pass
