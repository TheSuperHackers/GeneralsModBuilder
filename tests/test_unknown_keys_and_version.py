import pytest

from generalsmodbuilder.data.buildfiles import MakeBuildFilesFromJsons
from generalsmodbuilder.data.bundles import MakeBundlesFromJsons
from generalsmodbuilder.data.changeconfig import MakeChangeConfigFromJsons
from generalsmodbuilder.data.folders import MakeFoldersFromJsons
from generalsmodbuilder.data.runner import MakeJsonRunnerFromJsons
from generalsmodbuilder.data.tools import MakeToolsFromJsons


def MakeTools(jsonFile, tmp_path):
    return MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path))


# Each case is a section with one key that the format does not define.
SECTIONS = {
    "folders": ({"folders": {"releaseDir": "R", "buildDir": "B", "releasDir": "R"}},
                "folders.releasDir", MakeFoldersFromJsons),
    "runner": ({"runner": {"gameExeFile": "generals.exe", "gameExeFil": "x"}},
               "runner.gameExeFil", MakeJsonRunnerFromJsons),
    "build": ({"build": {"files": [], "file": []}},
              "build.file", MakeBuildFilesFromJsons),
    "changelog": ({"changelog": {"records": [], "record": []}},
                  "changelog.record", MakeChangeConfigFromJsons),
    "bundles": ({"bundles": {"items": [], "item": []}},
                "bundles.item", MakeBundlesFromJsons),
}


@pytest.mark.parametrize("section", sorted(SECTIONS))
def test_an_unknown_key_is_rejected(MakeJsonFile, section):
    data, expectedKey, Parse = SECTIONS[section]
    with pytest.raises(AssertionError) as error:
        Parse([MakeJsonFile(data)])
    message = str(error.value)
    assert f"{expectedKey} is not a known key" in message
    assert "Known keys here are" in message


def test_an_unknown_tools_key_is_rejected(MakeJsonFile, tmp_path):
    with pytest.raises(AssertionError) as error:
        MakeTools(MakeJsonFile({"tools": {"lst": []}}), tmp_path)
    assert "tools.lst is not a known key" in str(error.value)


def test_the_info_key_of_a_tool_is_accepted(MakeJsonFile, tmp_path):
    # It is not consumed, but it describes a tool for whoever reads the configuration.
    tools = MakeTools(MakeJsonFile({"tools": {"list": [
        {"name": "sample", "info": "Does a thing", "files": [{"target": "s.exe", "runnable": True}]}]}}), tmp_path)
    assert "sample" in tools


def test_an_unknown_bundle_item_key_is_rejected(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile({"bundles": {"items": [{"name": "A", "bigg": True}]}})])
    assert "bundles.items[0] 'A'.bigg is not a known key" in str(error.value)


def test_a_misspelled_event_name_is_rejected(MakeJsonFile):
    # It used to be ignored, so the script simply never ran.
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile({"bundles": {"items": [
            {"name": "A", "onPrebuild": {"script": "x.py"}}]}})])
    assert "bundles.items[0] 'A'.onPrebuild is not a known key" in str(error.value)


def test_a_correctly_spelled_event_name_is_accepted(MakeJsonFile, MakeFile):
    MakeFile("x.py")
    bundles = MakeBundlesFromJsons([MakeJsonFile({"bundles": {"items": [
        {"name": "A", "onPreBuild": {"script": "x.py"}}]}})])
    assert len(bundles.items[0].events) == 1


@pytest.mark.parametrize("section,data", [
    ("folders", {"folders": {"releaseDir": "R", "buildDir": "B"}}),
    ("bundles", {"bundles": {"items": []}}),
    ("changelog", {"changelog": {"records": []}}),
    ("build", {"build": {"files": []}}),
])
def test_a_version_newer_than_this_build_is_rejected(MakeJsonFile, section, data):
    data[section]["version"] = 99
    Parse = {"folders": MakeFoldersFromJsons, "bundles": MakeBundlesFromJsons,
             "changelog": MakeChangeConfigFromJsons, "build": MakeBuildFilesFromJsons}[section]
    with pytest.raises(AssertionError) as error:
        Parse([MakeJsonFile(data)])
    assert f"{section}.version is 99, but this build knows the format only up to version 1" in str(error.value)


def test_a_tools_version_newer_than_this_build_is_rejected(MakeJsonFile, tmp_path):
    with pytest.raises(AssertionError) as error:
        MakeTools(MakeJsonFile({"tools": {"version": 99, "list": []}}), tmp_path)
    assert "tools.version is 99, but this build knows the format only up to version 2" in str(error.value)


def test_a_version_below_one_is_rejected(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeFoldersFromJsons([MakeJsonFile({"folders": {"version": 0, "releaseDir": "R", "buildDir": "B"}})])
    assert "folders.version is 0, but a format version starts at 1" in str(error.value)


def test_a_section_without_a_version_is_read_as_the_current_one(MakeJsonFile, tmp_path):
    folders = MakeFoldersFromJsons([MakeJsonFile({"folders": {"releaseDir": "R", "buildDir": "B"}})])
    assert folders.absReleaseDir.endswith("R")
