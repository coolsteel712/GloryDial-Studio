from glorydial.formats import descriptor as desc_mod


def test_descriptor_round_trip():
    d = desc_mod.BlockDescriptor(
        type_id=4,
        width=28,
        start_address=12345,
        height=34,
        x=50,
        y=233,
        animation_speed=0,
        images_count=14,
        black_is_transparent=True,
        arrow_full_length=0,
        arrow_length_to_center=0,
        arrow_width=0,
    )
    raw = desc_mod.build_descriptor(d)
    assert len(raw) == desc_mod.DESCRIPTOR_SIZE
    parsed = desc_mod.parse_descriptor(raw, 0)
    assert parsed == d


def test_black_is_transparent_inverted_byte():
    d_true = desc_mod.BlockDescriptor(1, 1, 0, 1, 0, 0, 0, 1, True, 0, 0, 0)
    d_false = desc_mod.BlockDescriptor(1, 1, 0, 1, 0, 0, 0, 1, False, 0, 0, 0)
    raw_true = desc_mod.build_descriptor(d_true)
    raw_false = desc_mod.build_descriptor(d_false)
    assert raw_true[17] == 0  # True -> stored 0
    assert raw_false[17] == 1  # False -> stored 1


def test_hand_arrow_fields_round_trip():
    d = desc_mod.BlockDescriptor(1, 38, 362, 151, 205, 251, 0, 1, True, 50, 130, 12)
    raw = desc_mod.build_descriptor(d)
    parsed = desc_mod.parse_descriptor(raw, 0)
    assert parsed.arrow_full_length == 50
    assert parsed.arrow_length_to_center == 130
    assert parsed.arrow_width == 12


def test_images_count_out_of_range_rejected():
    d = desc_mod.BlockDescriptor(1, 1, 0, 1, 0, 0, 0, 300, True, 0, 0, 0)
    try:
        desc_mod.build_descriptor(d)
        assert False, "expected ValueError"
    except ValueError:
        pass
