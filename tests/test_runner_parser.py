import os

import pytest

from generalsmodbuilder.data.runner import (
    UserRunner, MakeJsonRunnerFromJsons, MakeRunner)


def MakeRunnerJson(**overrides) -> dict:
    jRunner = {"version": 1, "gameExeFile": "generals.exe", "gameInstallPath": "Game"}
    jRunner.update(overrides)
    return {"runner": jRunner}


def MakeRunnerFromJsons(jsonFiles, userRunner: UserRunner = None):
    return MakeRunner(MakeJsonRunnerFromJsons(jsonFiles), userRunner)


@pytest.fixture
def GameDir(MakeFile):
    """
    An installation directory holding the game executable, next to the json file.
    """
    MakeFile("Game/generals.exe")
    return "Game"


def test_the_install_dir_is_found_by_the_executable_in_it(MakeJsonFile, GameDir, tmp_path):
    runner = MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson())])
    assert runner.absGameInstallDir == os.path.join(str(tmp_path), "Game")
    assert runner.AbsGameExeFile() == os.path.join(str(tmp_path), "Game", "generals.exe")


def test_game_data_files_are_joined_to_the_install_dir_and_normalized(MakeJsonFile, GameDir, MakeFile, tmp_path):
    MakeFile("Game/Data/INI/Weapon.ini")
    runner = MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson(
        regularGameDataFiles=["Data/../Data/INI/Weapon.ini"]))])
    assert runner.absRegularGameDataFiles == [os.path.join(str(tmp_path), "Game", "Data", "INI", "Weapon.ini")]


def test_a_game_data_file_that_is_absent_is_kept(MakeJsonFile, GameDir, tmp_path):
    # The list says which files are allowed to be present, not which are required. Every
    # language that is not installed is listed here and matches nothing.
    runner = MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson(
        regularGameDataFiles=["AudioKorean.big"]))])
    assert runner.absRegularGameDataFiles == [os.path.join(str(tmp_path), "Game", "AudioKorean.big")]


def test_a_game_data_wildcard_resolves_to_its_matches(MakeJsonFile, GameDir, MakeFile, tmp_path):
    MakeFile("Game/Data/A.bik")
    MakeFile("Game/Data/B.bik")
    runner = MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson(
        regularGameDataFiles=["Data/**/*.bik"]))])
    assert sorted(os.path.basename(f) for f in runner.absRegularGameDataFiles) == ["A.bik", "B.bik"]


def test_a_game_data_wildcard_that_matches_nothing_is_not_reported(MakeJsonFile, GameDir, capsys):
    runner = MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson(
        regularGameDataFiles=["Data/**/*.nothing"]))])
    assert runner.absRegularGameDataFiles == []
    assert "matches nothing" not in capsys.readouterr().out


def test_a_bad_file_type_entry_names_the_file_the_key_and_the_index(MakeJsonFile, GameDir):
    with pytest.raises(AssertionError) as error:
        MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson(relevantGameDataFileTypes=["big", 2]))])
    assert str(error.value).endswith("runner.relevantGameDataFileTypes[1] is type:int but should be type:str")


def test_a_bad_exe_arg_value_is_reported(MakeJsonFile, GameDir):
    with pytest.raises(AssertionError) as error:
        MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson(gameExeArgs={"-win": {"nested": 1}}))])
    assert "runner.gameExeArgs.value" in str(error.value)


def test_a_later_json_wins_over_an_earlier_one(MakeJsonFile, MakeFile, tmp_path):
    MakeFile("A/Game/generals.exe")
    MakeFile("B/Game/generals.exe")
    first = MakeJsonFile(MakeRunnerJson(), "A/First.json")
    second = MakeJsonFile(MakeRunnerJson(), "B/Second.json")
    runner = MakeRunnerFromJsons([first, second])
    assert runner.absGameInstallDir == os.path.join(str(tmp_path), "B", "Game")


def test_a_missing_game_installation_names_where_it_looked(MakeJsonFile, tmp_path):
    # An empty install dir used to be normalized into the current directory, which
    # passes isdir, so the failure blamed the executable path instead.
    with pytest.raises(AssertionError) as error:
        MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson())])
    message = str(error.value)
    assert "game installation directory containing 'generals.exe' was not found" in message
    assert os.path.join(str(tmp_path), "Game") in message


def test_a_missing_game_exe_file_is_reported_as_such(MakeJsonFile, GameDir):
    jRunner = MakeRunnerJson()
    del jRunner["runner"]["gameExeFile"]
    with pytest.raises(AssertionError) as error:
        MakeRunnerFromJsons([MakeJsonFile(jRunner)])
    assert str(error.value).startswith("runner.gameExeFile is not set by any configuration file")


def test_game_data_files_are_not_resolved_against_the_working_directory(MakeJsonFile):
    # They used to be joined to ".", which made them resolve wherever the build ran.
    with pytest.raises(AssertionError):
        MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson(regularGameDataFiles=["Data/**/*.big"]))])


def test_the_json_runner_keeps_the_game_data_files_relative(MakeJsonFile, GameDir):
    jsonRunner = MakeJsonRunnerFromJsons([MakeJsonFile(MakeRunnerJson(
        regularGameDataFiles=["Data/INI/Weapon.ini"]))])
    assert jsonRunner.relRegularGameDataFiles == ["Data/INI/Weapon.ini"]


def test_the_configured_exe_args_become_the_argument_list(MakeJsonFile, GameDir):
    runner = MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson(
        gameExeArgs={"-win": "", "-xres": 1024}))])
    assert runner.gameExeArgs == ["-win", "-xres", "1024"]


def test_a_user_runner_that_sets_nothing_changes_nothing(MakeJsonFile, GameDir, tmp_path):
    runner = MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson(gameExeArgs={"-win": ""}))], UserRunner())
    assert runner.absGameInstallDir == os.path.join(str(tmp_path), "Game")
    assert runner.relGameExeFile == "generals.exe"
    assert runner.gameExeArgs == ["-win"]


def test_a_user_exe_file_wins_over_the_configured_one(MakeJsonFile, GameDir, MakeFile, tmp_path):
    MakeFile("Game/generalszh.exe")
    runner = MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson())],
                                 UserRunner(relGameExeFile="generalszh.exe"))
    assert runner.relGameExeFile == "generalszh.exe"
    assert runner.AbsGameExeFile() == os.path.join(str(tmp_path), "Game", "generalszh.exe")


def test_user_exe_args_replace_the_configured_ones(MakeJsonFile, GameDir):
    runner = MakeRunnerFromJsons(
        [MakeJsonFile(MakeRunnerJson(gameExeArgs={"-win": "", "-quickstart": ""}))],
        UserRunner(gameExeArgs=["-xres", "1024"]))
    assert runner.gameExeArgs == ["-xres", "1024"]


def test_an_empty_user_exe_arg_list_launches_the_game_without_arguments(MakeJsonFile, GameDir):
    runner = MakeRunnerFromJsons(
        [MakeJsonFile(MakeRunnerJson(gameExeArgs={"-win": "", "-quickstart": ""}))],
        UserRunner(gameExeArgs=[]))
    assert runner.gameExeArgs == []


def test_a_user_install_dir_is_the_only_one_searched(MakeJsonFile, GameDir, MakeFile, tmp_path):
    # The configured directory holds the executable too, so only exclusivity decides this.
    MakeFile("Custom/generals.exe")
    custom = os.path.join(str(tmp_path), "Custom")
    runner = MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson())],
                                 UserRunner(absGameInstallDir=custom))
    assert runner.absGameInstallDir == custom


def test_a_user_install_dir_without_the_executable_names_that_path(MakeJsonFile, GameDir, tmp_path):
    custom = os.path.join(str(tmp_path), "Custom")
    os.makedirs(custom)
    with pytest.raises(AssertionError) as error:
        MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson())], UserRunner(absGameInstallDir=custom))
    message = str(error.value)
    assert custom in message
    assert os.path.join(str(tmp_path), "Game") not in message


def test_game_data_files_join_onto_the_user_install_dir(MakeJsonFile, GameDir, MakeFile, tmp_path):
    MakeFile("Custom/generals.exe")
    custom = os.path.join(str(tmp_path), "Custom")
    runner = MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson(regularGameDataFiles=["INIZH.big"]))],
                                 UserRunner(absGameInstallDir=custom))
    assert runner.absRegularGameDataFiles == [os.path.join(custom, "INIZH.big")]


def test_a_user_install_dir_is_normalized(MakeJsonFile, GameDir, MakeFile, tmp_path):
    MakeFile("Custom/generals.exe")
    userRunner = UserRunner(absGameInstallDir=os.path.join(str(tmp_path), "Data", "..", "Custom"))
    runner = MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson())], userRunner)
    assert runner.absGameInstallDir == os.path.join(str(tmp_path), "Custom")


def test_a_bad_user_exe_arg_is_reported(MakeJsonFile, GameDir):
    with pytest.raises(AssertionError) as error:
        MakeRunnerFromJsons([MakeJsonFile(MakeRunnerJson())], UserRunner(gameExeArgs=["-xres", 1024]))
    assert str(error.value).endswith("\"userRunner.gameExeArgs[1]\" is type:int but should be type:str")
