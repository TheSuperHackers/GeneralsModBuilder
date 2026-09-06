"""
Covers the image helpers of copy.py. The images are made here rather than committed, so
that these run without any binary fixture.
"""
import os

import PIL.Image
import pytest

from generalsmodbuilder.build.copy import BuildFileType, HasAlphaChannel, ResizeImageWithParams


def MakeImage(mode: str = "RGB", size=(64, 32)):
    return PIL.Image.new(mode, size, 255 if mode == "L" else None)


def test_no_param_leaves_the_size_alone():
    img = MakeImage(size=(64, 32))
    assert ResizeImageWithParams(img, {}).size == (64, 32)
    assert ResizeImageWithParams(img, None).size == (64, 32)


def test_resize_names_the_size():
    img = MakeImage(size=(64, 32))
    assert ResizeImageWithParams(img, {"resize": 128}).size == (128, 128)
    assert ResizeImageWithParams(img, {"resize": [128]}).size == (128, 128)
    assert ResizeImageWithParams(img, {"resize": [128, 16]}).size == (128, 16)


def test_rescale_multiplies_the_size():
    img = MakeImage(size=(64, 32))
    assert ResizeImageWithParams(img, {"rescale": 0.5}).size == (32, 16)
    assert ResizeImageWithParams(img, {"rescale": [2]}).size == (128, 64)
    assert ResizeImageWithParams(img, {"rescale": [2, 0.5]}).size == (128, 16)


def test_rescale_applies_to_the_result_of_resize():
    img = MakeImage(size=(64, 32))
    assert ResizeImageWithParams(img, {"resize": [100, 100], "rescale": 0.5}).size == (50, 50)


def test_a_resampling_mode_is_named_in_any_case():
    img = MakeImage(size=(64, 32))
    # An unknown name falls back to the default rather than failing, and either way the
    # image comes out in the size that was asked for.
    for name in ["BICUBIC", "bicubic", "Lanczos", "NEAREST", "not-a-mode"]:
        assert ResizeImageWithParams(img, {"resize": 16, "resampling": name}).size == (16, 16)


def test_an_image_with_alpha_keeps_its_channels_on_resize():
    img = PIL.Image.new("RGBA", (64, 32), (10, 20, 30, 0))
    resized = ResizeImageWithParams(img, {"resize": [16, 16]})
    assert resized.mode == "RGBA"
    assert resized.size == (16, 16)
    # The colour must survive a fully transparent image, which is why the channels are
    # resized one by one.
    assert resized.getpixel((0, 0)) == (10, 20, 30, 0)


def WriteImage(tmp_path, name: str, mode: str) -> str:
    path = str(tmp_path / name)
    PIL.Image.new(mode, (8, 8), None).save(path)
    return path


@pytest.mark.parametrize("mode,expected", [("RGB", False), ("RGBA", True)])
def test_an_alpha_channel_is_read_from_a_tga(tmp_path, mode, expected):
    source = WriteImage(tmp_path, "Texture.tga", mode)
    assert HasAlphaChannel(source, BuildFileType.tga) == expected


def test_reading_the_alpha_channel_does_not_hold_the_file_open(tmp_path):
    # The file is read while a build is writing beside it, so it must not stay open.
    source = WriteImage(tmp_path, "Texture.tga", "RGBA")
    assert HasAlphaChannel(source, BuildFileType.tga)
    os.remove(source)
    assert not os.path.isfile(source)


def test_an_unknown_file_type_has_no_alpha_channel(tmp_path):
    source = WriteImage(tmp_path, "Texture.bmp", "RGB")
    assert not HasAlphaChannel(source, BuildFileType.Any)
