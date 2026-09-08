import pytest

from generalsmodbuilder.data.runner import SplitGameExeArgs


@pytest.mark.parametrize("text, expected", [
    ("-win -quickstart", ["-win", "-quickstart"]),
    ("-win", ["-win"]),
    ("", []),
    ("   ", []),
    ("-win  -quickstart", ["-win", "-quickstart"]),
    ("-xres 1024 -yres 768", ["-xres", "1024", "-yres", "768"]),
])
def test_a_command_line_splits_into_its_arguments(text, expected):
    assert SplitGameExeArgs(text) == expected


def test_an_unquoted_windows_path_keeps_its_backslashes():
    # Posix splitting reads a backslash as an escape and would give 'C:Gamesx.big'.
    assert SplitGameExeArgs(r"-mod C:\Games\x.big") == ["-mod", r"C:\Games\x.big"]


def test_a_quoted_path_with_a_space_is_one_argument_without_its_quotes():
    assert SplitGameExeArgs(r'-mod "C:\My Mod\x.big" -xres 1024') == [
        "-mod", r"C:\My Mod\x.big", "-xres", "1024"]
