import os

import pytest

from generalsmodbuilder.data.runner import UserRunner, MakeUserRunnerFromJson
from generalsmodbuilder.usersettings import (
    GetUserSettingsFile, LoadUserRunner, MergeUserRunners, SaveUserRunner)


@pytest.fixture
def SettingsFile(tmp_path):
    return str(tmp_path / "Settings" / "UserSettings.json")


def test_a_save_round_trips_through_a_load(SettingsFile):
    SaveUserRunner(SettingsFile, r"D:\MyGame", "generalszh.exe", "-win -quickstart")
    userRunner = LoadUserRunner(SettingsFile)
    assert userRunner.absGameInstallDir == r"D:\MyGame"
    assert userRunner.relGameExeFile == "generalszh.exe"
    assert userRunner.gameExeArgs == ["-win", "-quickstart"]


def test_saving_creates_the_directory(SettingsFile):
    assert not os.path.isdir(os.path.dirname(SettingsFile))
    SaveUserRunner(SettingsFile, "", "", "")
    assert os.path.isfile(SettingsFile)


def test_a_saved_empty_setting_changes_nothing(SettingsFile):
    SaveUserRunner(SettingsFile, "", "", "")
    userRunner = LoadUserRunner(SettingsFile)
    assert userRunner.absGameInstallDir == ""
    assert userRunner.relGameExeFile == ""
    assert userRunner.gameExeArgs == []


def test_a_missing_file_changes_nothing(SettingsFile):
    userRunner = LoadUserRunner(SettingsFile)
    assert userRunner.absGameInstallDir == ""
    assert userRunner.relGameExeFile == ""
    assert userRunner.gameExeArgs == None


def test_a_file_that_is_not_json_is_reported_and_changes_nothing(SettingsFile, capsys):
    os.makedirs(os.path.dirname(SettingsFile))
    with open(SettingsFile, "w", encoding="utf-8") as file:
        file.write("{ not json")
    userRunner = LoadUserRunner(SettingsFile)
    assert userRunner.gameExeArgs == None
    assert "are not read" in capsys.readouterr().out


def test_an_absent_section_changes_nothing(MakeJsonFile):
    userRunner = MakeUserRunnerFromJson(MakeJsonFile({}))
    assert userRunner.absGameInstallDir == ""
    assert userRunner.gameExeArgs == None


def test_an_unknown_key_names_the_file_the_section_and_the_key(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeUserRunnerFromJson(MakeJsonFile({"userRunner": {"gameInstallPat": "D:/MyGame"}}))
    message = str(error.value)
    assert "userRunner.gameInstallPat is not a known key" in message
    assert "Test.json" in message


def test_a_version_the_build_does_not_know_is_rejected(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeUserRunnerFromJson(MakeJsonFile({"userRunner": {"version": 2}}))
    assert "this build knows the format only up to version 1" in str(error.value)


def test_a_bad_value_type_is_reported(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeUserRunnerFromJson(MakeJsonFile({"userRunner": {"gameExeArgs": ["-win"]}}))
    assert "userRunner.gameExeArgs" in str(error.value)


def test_the_settings_file_lives_under_the_user_config_dir():
    path = GetUserSettingsFile()
    assert os.path.basename(path) == "UserSettings.json"
    assert "GeneralsModBuilder" in path


def test_a_command_line_setting_wins_over_a_saved_one():
    fromArgs = UserRunner(absGameInstallDir=r"D:\FromArgs", relGameExeFile="fromargs.exe",
                          gameExeArgs=["-fromargs"])
    fromFile = UserRunner(absGameInstallDir=r"D:\FromFile", relGameExeFile="fromfile.exe",
                          gameExeArgs=["-fromfile"])
    merged = MergeUserRunners(fromArgs, fromFile)
    assert merged.absGameInstallDir == r"D:\FromArgs"
    assert merged.relGameExeFile == "fromargs.exe"
    assert merged.gameExeArgs == ["-fromargs"]


def test_a_saved_setting_is_used_where_the_command_line_gave_none():
    fromFile = UserRunner(absGameInstallDir=r"D:\FromFile", relGameExeFile="fromfile.exe",
                          gameExeArgs=["-fromfile"])
    merged = MergeUserRunners(UserRunner(), fromFile)
    assert merged.absGameInstallDir == r"D:\FromFile"
    assert merged.relGameExeFile == "fromfile.exe"
    assert merged.gameExeArgs == ["-fromfile"]


def test_the_fields_are_merged_one_by_one():
    merged = MergeUserRunners(UserRunner(absGameInstallDir=r"D:\FromArgs"),
                              UserRunner(relGameExeFile="fromfile.exe"))
    assert merged.absGameInstallDir == r"D:\FromArgs"
    assert merged.relGameExeFile == "fromfile.exe"


def test_an_empty_saved_setting_leaves_the_field_unset():
    merged = MergeUserRunners(UserRunner(), UserRunner(absGameInstallDir="", gameExeArgs=None))
    assert merged.absGameInstallDir == ""
    assert merged.gameExeArgs == None


def test_a_command_line_arg_list_of_no_tokens_still_wins():
    merged = MergeUserRunners(UserRunner(gameExeArgs=[]), UserRunner(gameExeArgs=["-fromfile"]))
    assert merged.gameExeArgs == []
