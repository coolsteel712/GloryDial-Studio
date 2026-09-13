import random

from PIL import Image

from glorydial.image_codec import argb6666, rgb565


def _random_image(w, h, alpha=True, seed=0):
    random.seed(seed)
    img = Image.new("RGBA" if alpha else "RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            if alpha:
                px[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            else:
                px[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    return img


def test_rgb565_big_endian_round_trip_is_stable_after_first_quantization():
    img = _random_image(9, 5, alpha=False, seed=1)
    raw = rgb565.pack_big_endian(img)
    decoded = rgb565.unpack_big_endian_gamma(raw, 9, 5)
    # Re-encoding an already-quantized image must not drift further.
    raw2 = rgb565.pack_big_endian(decoded)
    decoded2 = rgb565.unpack_big_endian_gamma(raw2, 9, 5)
    import numpy as np
    assert np.array_equal(
        np.asarray(decoded.convert("RGB")),
        np.asarray(decoded2.convert("RGB")),
    )


def test_rgb565_little_endian_round_trip_is_stable():
    img = _random_image(11, 6, alpha=False, seed=2)
    raw = rgb565.pack_little_endian(img)
    decoded = rgb565.unpack_little_endian_linear(raw, 11, 6)
    raw2 = rgb565.pack_little_endian(decoded)
    decoded2 = rgb565.unpack_little_endian_linear(raw2, 11, 6)
    import numpy as np
    assert np.array_equal(
        np.asarray(decoded.convert("RGB")),
        np.asarray(decoded2.convert("RGB")),
    )


def test_rgb565_byte_order_differs_between_v1v2_and_v3():
    img = Image.new("RGB", (1, 1), (0, 255, 0))  # pure green -> distinct hi/lo bytes
    be = rgb565.pack_big_endian(img)
    le = rgb565.pack_little_endian(img)
    assert be == bytes([le[1], le[0]])


def test_argb6666_round_trip_stable():
    img = _random_image(8, 8, alpha=True, seed=3)
    raw = argb6666.pack(img)
    decoded = argb6666.unpack(raw, 8, 8)
    raw2 = argb6666.pack(decoded)
    decoded2 = argb6666.unpack(raw2, 8, 8)
    import numpy as np
    assert np.array_equal(np.asarray(decoded), np.asarray(decoded2))


def test_argb6666_full_opaque_and_transparent_extremes():
    img = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
    img.putpixel((1, 0), (255, 255, 255, 255))
    raw = argb6666.pack(img)
    decoded = argb6666.unpack(raw, 2, 1)
    assert decoded.getpixel((0, 0))[3] == 0
    assert decoded.getpixel((1, 0)) == (255, 255, 255, 255)


def test_unpack_rejects_short_buffer():
    try:
        rgb565.unpack_big_endian_gamma(b"\x00\x00", 4, 4)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        argb6666.unpack(b"\x00\x00\x00", 4, 4)
        assert False, "expected ValueError"
    except ValueError:
        pass
