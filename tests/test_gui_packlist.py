import pytest

from generalsmodbuilder.gui.packlist import CHECK_SIZE, DrawCheckImage, MatchPackSelection
from generalsmodbuilder.gui.theme import AMBER


def HexToRgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


@pytest.mark.parametrize("allNames, wantedNames, expected", [
    (["A", "B", "C"], ["A", "C"], [0, 2]),
    (["A", "B", "C"], [], []),
    (["A", "B", "C"], ["B"], [1]),
    (["A", "B", "C"], ["A", "B", "C"], [0, 1, 2]),
    ([], ["A"], []),
])
def test_the_wanted_packs_decide_which_rows_start_ticked(allNames, wantedNames, expected):
    assert MatchPackSelection(allNames, wantedNames) == expected


def test_a_wanted_pack_that_the_configuration_does_not_have_is_ignored():
    # The command line may name a pack that this configuration does not define.
    assert MatchPackSelection(["A", "B"], ["B", "Missing"]) == [1]


def test_a_repeated_wanted_pack_ticks_its_row_once():
    # --install and --build-pack can both name the same pack.
    assert MatchPackSelection(["A", "B"], ["A", "A"]) == [0]


def test_the_rows_come_back_in_list_order_not_in_the_order_asked_for():
    assert MatchPackSelection(["A", "B", "C"], ["C", "A"]) == [0, 2]


@pytest.mark.parametrize("checked", [True, False])
def test_a_check_mark_is_drawn_at_the_size_asked_for(checked):
    image = DrawCheckImage(CHECK_SIZE, checked)
    assert image.size == (CHECK_SIZE, CHECK_SIZE)
    assert image.mode == "RGBA"


def test_a_ticked_mark_is_filled_with_the_palette_amber():
    image = DrawCheckImage(CHECK_SIZE, True)
    amber = HexToRgb(AMBER)
    pixels = image.load()
    filled = 0
    for x in range(CHECK_SIZE):
        for y in range(CHECK_SIZE):
            pixel = pixels[x, y]
            if pixel[3] > 200 and max(abs(a - b) for a, b in zip(pixel[:3], amber)) <= 6:
                filled += 1
    # The rest of the box is the check mark, and the corners are rounded and antialiased.
    assert filled > CHECK_SIZE * CHECK_SIZE * 0.4


def test_an_unticked_mark_is_hollow():
    image = DrawCheckImage(CHECK_SIZE, False)
    middle = CHECK_SIZE // 2
    assert image.getpixel((middle, middle))[3] == 0


def test_the_two_marks_differ():
    assert DrawCheckImage(CHECK_SIZE, True).tobytes() != DrawCheckImage(CHECK_SIZE, False).tobytes()
