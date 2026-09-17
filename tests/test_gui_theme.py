import re

import pytest
from ttkbootstrap.themes.standard import STANDARD_THEMES

from generalsmodbuilder.gui import theme


PALETTE = {
    "AMBER": theme.AMBER,
    "KHAKI": theme.KHAKI,
    "SAND": theme.SAND,
    "TEAL": theme.TEAL,
    "EMBER": theme.EMBER,
}


def Channel(value: float) -> float:
    value /= 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def Luminance(color: str) -> float:
    color = color.lstrip("#")
    red, green, blue = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * Channel(red) + 0.7152 * Channel(green) + 0.0722 * Channel(blue)


def ContrastRatio(first: str, second: str) -> float:
    lit, dim = sorted((Luminance(first), Luminance(second)), reverse=True)
    return (lit + 0.05) / (dim + 0.05)


@pytest.mark.parametrize("name, color", sorted(PALETTE.items()))
def test_a_palette_colour_is_legible_on_the_background(name, color):
    # The gui is dark only because these colours fail this on a light background. A colour
    # tweak that drops below the threshold is a legibility bug, not a matter of taste.
    assert ContrastRatio(color, theme.BACKGROUND) >= 4.5


@pytest.mark.parametrize("color", [theme.FOREGROUND, theme.MUTED])
def test_the_text_colours_are_legible_on_the_background(color):
    assert ContrastRatio(color, theme.BACKGROUND) >= 4.5


def test_the_border_is_visible_against_the_background():
    # A border only separates two surfaces, so it is held to the lower boundary threshold.
    assert ContrastRatio(theme.BORDER, theme.BACKGROUND) < 4.5
    assert Luminance(theme.BORDER) > Luminance(theme.BACKGROUND)


def test_the_theme_fills_every_colour_slot_ttkbootstrap_expects():
    expected = set(STANDARD_THEMES["darkly"]["colors"].keys())
    assert set(theme.THEME_COLORS.keys()) == expected


@pytest.mark.parametrize("key, color", sorted(theme.THEME_COLORS.items()))
def test_every_theme_colour_is_a_six_digit_hex_value(key, color):
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", color), key


def test_the_palette_colours_are_distinct():
    assert len(set(PALETTE.values())) == len(PALETTE)


def test_the_buttons_that_run_something_share_one_amber_outline_style():
    assert theme.ACTION_STYLE == "warning-outline"
    assert theme.THEME_COLORS["warning"] == theme.AMBER


def test_the_quiet_buttons_do_not_compete_with_the_amber_ones():
    # Refresh, Clear, Copy and Browse are not actions, so they stay khaki.
    assert theme.QUIET_STYLE == "secondary-outline"
    assert theme.THEME_COLORS["secondary"] == theme.KHAKI
