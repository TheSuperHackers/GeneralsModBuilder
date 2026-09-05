import os

from generalsmodbuilder.data.buildfiles import MakeBuildFilesFromJsons


def test_build_file_paths_are_normalized(MakeJsonFile, MakeFile):
    MakeFile("Sub/Included.json", "{}")
    jsonFile = MakeJsonFile({"build": {"version": 1, "files": ["Sub/../Sub/Included.json"]}})
    buildFiles = MakeBuildFilesFromJsons([jsonFile])
    assert buildFiles.absFiles == [os.path.normpath(buildFiles.absFiles[0])]
    assert ".." not in buildFiles.absFiles[0]
