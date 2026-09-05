import os

import pytest

from generalsmodbuilder.data.folders import MakeFoldersFromJsons


def test_directories_are_resolved_against_the_json_directory(MakeJsonFile, tmp_path):
    jsonFile = MakeJsonFile({"folders": {"version": 1, "releaseDir": "Release", "buildDir": "Build"}})
    folders = MakeFoldersFromJsons([jsonFile])
    assert folders.absReleaseDir == os.path.join(str(tmp_path), "Release")
    assert folders.absBuildDir == os.path.join(str(tmp_path), "Build")


def test_a_later_json_overrides_an_earlier_one(MakeJsonFile, tmp_path):
    first = MakeJsonFile({"folders": {"releaseDir": "Release", "buildDir": "Build"}}, "A/First.json")
    second = MakeJsonFile({"folders": {"buildDir": "Other"}}, "B/Second.json")
    folders = MakeFoldersFromJsons([first, second])
    assert folders.absReleaseDir == os.path.join(str(tmp_path), "A", "Release")
    assert folders.absBuildDir == os.path.join(str(tmp_path), "B", "Other")


@pytest.mark.parametrize("missing", ["releaseDir", "buildDir"])
def test_a_missing_directory_names_the_json_key(MakeJsonFile, missing):
    jFolders = {"releaseDir": "Release", "buildDir": "Build"}
    del jFolders[missing]
    with pytest.raises(AssertionError) as error:
        MakeFoldersFromJsons([MakeJsonFile({"folders": jFolders})])
    assert str(error.value) == f"folders.{missing} is not set by any configuration file"


def test_a_directory_of_the_wrong_type_names_the_file_and_the_key(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeFoldersFromJsons([MakeJsonFile({"folders": {"releaseDir": 1, "buildDir": "Build"}})])
    message = str(error.value)
    assert message.endswith("folders.releaseDir is type:int but should be type:str")
    assert "Test.json" in message


def test_a_section_of_the_wrong_type_is_reported(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeFoldersFromJsons([MakeJsonFile({"folders": ["Release"]})])
    assert str(error.value).endswith("folders is type:list but should be type:dict")


def test_the_same_directory_for_build_and_release_is_rejected(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeFoldersFromJsons([MakeJsonFile({"folders": {"releaseDir": "Out", "buildDir": "Out"}})])
    assert "folders.releaseDir and folders.buildDir are both" in str(error.value)


def test_directories_that_differ_in_case_only_are_rejected(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeFoldersFromJsons([MakeJsonFile({"folders": {"releaseDir": "Out", "buildDir": "out"}})])
    assert "folders.releaseDir and folders.buildDir are both" in str(error.value)
