import os

import pytest

from generalsmodbuilder.data.runner import MakeUserRunnerFromJson
from generalsmodbuilder.usersettings import GetUserSettingsFile, LoadUserRunner, SaveUserRunner


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
