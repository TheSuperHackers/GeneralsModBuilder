import os

import pytest

from generalsmodbuilder.main import MakeArgumentParser, MakeUserRunnerFromArgs


def MakeUserRunner(*argv):
    return MakeUserRunnerFromArgs(MakeArgumentParser().parse_args(list(argv)))


def test_no_game_option_sets_nothing():
    userRunner = MakeUserRunner("--run")
    assert userRunner.absGameInstallDir == ""
    assert userRunner.relGameExeFile == ""
    assert userRunner.gameExeArgs == None


def test_the_install_path_is_made_absolute():
    userRunner = MakeUserRunner("--game-install-path", "Game")
    assert userRunner.absGameInstallDir == os.path.abspath("Game")


def test_an_absolute_install_path_is_kept():
    userRunner = MakeUserRunner("--game-install-path", os.path.abspath(os.sep + "Games"))
    assert userRunner.absGameInstallDir == os.path.abspath(os.sep + "Games")


def test_the_exe_file_is_taken_as_written():
    assert MakeUserRunner("--game-exe-file", "generalszh.exe").relGameExeFile == "generalszh.exe"


def test_exe_args_are_split_into_the_argument_list():
    assert MakeUserRunner("--game-exe-args", "-win -quickstart").gameExeArgs == ["-win", "-quickstart"]


def test_empty_exe_args_mean_no_arguments_rather_than_the_configured_ones():
    assert MakeUserRunner("--game-exe-args", "").gameExeArgs == []


@pytest.mark.parametrize("argv", [
    ["--game-exe-args=-win"],
    ["--game-exe-args=-win -quickstart"],
    ["--game-exe-args", "-win -quickstart"],
])
def test_a_leading_dash_argument_value_is_accepted(argv):
    # A value that argparse could read as an option is passed with '=', and a value
    # holding a space is not read as an option either.
    assert MakeUserRunner(*argv).gameExeArgs[0] == "-win"


def test_a_single_leading_dash_value_without_the_equals_sign_is_rejected():
    with pytest.raises(SystemExit):
        MakeUserRunner("--game-exe-args", "-win")
