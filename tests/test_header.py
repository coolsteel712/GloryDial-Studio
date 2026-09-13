import os
import struct
import zlib

from glorydial.formats import header

SAMPLE = os.path.join(os.path.dirname(__file__), "sample_double_circle.bin")


def test_parse_header_matches_known_sample_values():
    with open(SAMPLE, "rb") as fh:
        data = fh.read()
    h = header.parse_header(data)
    assert h.width == 410
    assert h.height == 502
    assert h.version == 3
    assert h.block_count == 14
    assert header.verify_crc(data, h)


def test_build_header_round_trips_size_and_crc():
    payload = b"some fake payload bytes" * 10
    h_bytes = header.build_header(b".BIN", 240, 240, 3, 5, payload)
    assert len(h_bytes) == header.HEADER_SIZE
    parsed = header.parse_header(h_bytes + payload)
    assert parsed.width == 240
    assert parsed.height == 240
    assert parsed.version == 3
    assert parsed.block_count == 5
    assert parsed.payload_size == len(payload)
    assert (zlib.crc32(payload) & 0xFFFFFFFF) == parsed.crc32
    assert header.verify_crc(h_bytes + payload, parsed)


def test_opaque_id_preserved_verbatim():
    payload = b"xyz"
    h_bytes = header.build_header(b"\x61\x32\xEF\x00", 10, 10, 1, 0, payload)
    parsed = header.parse_header(h_bytes + payload)
    assert parsed.opaque_id == b"\x61\x32\xEF\x00"


def test_version_ff_is_alias_for_1():
    payload = b"abc"
    h_bytes = bytearray(header.build_header(b".BIN", 10, 10, 1, 0, payload))
    h_bytes[19] = 0xFF
    parsed = header.parse_header(bytes(h_bytes) + payload)
    assert parsed.version == 1


def test_rejects_unknown_version_byte():
    payload = b"abc"
    h_bytes = bytearray(header.build_header(b".BIN", 10, 10, 1, 0, payload))
    h_bytes[19] = 0x07
    try:
        header.parse_header(bytes(h_bytes) + payload)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_rejects_too_short_file():
    try:
        header.parse_header(b"short")
        assert False, "expected ValueError"
    except ValueError:
        pass
