import os

import pytest

from generalsmodbuilder.data.buildfiles import MakeBuildFilesFromJsons


def test_build_file_paths_are_normalized(MakeJsonFile, MakeFile):
    MakeFile("Sub/Included.json", "{}")
    jsonFile = MakeJsonFile({"build": {"version": 1, "files": ["Sub/../Sub/Included.json"]}})
    buildFiles = MakeBuildFilesFromJsons([jsonFile])
    assert buildFiles.absFiles == [os.path.normpath(buildFiles.absFiles[0])]
    assert ".." not in buildFiles.absFiles[0]


def test_a_file_entry_of_the_wrong_type_names_the_file_and_the_index(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeBuildFilesFromJsons([MakeJsonFile({"build": {"files": ["Ok.json", 2]}})])
    assert str(error.value).endswith("build.files[1] is type:int but should be type:str")


def test_a_missing_file_is_reported_by_its_path(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeBuildFilesFromJsons([MakeJsonFile({"build": {"files": ["Absent.json"]}})])
    assert "build.files" in str(error.value)
    assert "is not a valid file" in str(error.value)


def test_no_build_section_yields_no_files(MakeJsonFile):
    assert MakeBuildFilesFromJsons([MakeJsonFile({})]).absFiles == []
