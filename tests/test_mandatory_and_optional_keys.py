"""
The mandatory and optional contract of every section, as executable cases.

For the sections that several json files merge into one result, mandatory means present
in at least one of them, not in every one, which is why those keys are read as optional
and are required only once the files have been merged.
"""
import pytest

from generalsmodbuilder.data.bundles import MakeBundlesFromJsons
from generalsmodbuilder.data.changeconfig import MakeChangeConfigFromJsons
from generalsmodbuilder.data.folders import MakeFoldersFromJsons
from generalsmodbuilder.data.tools import MakeToolsFromJsons


# ---------------------------------------------------------------- tools

def MakeToolJson(**fileOverrides) -> dict:
    jFile = {"target": "sample.exe", "runnable": True}
    jFile.update(fileOverrides)
    return {"tools": {"list": [{"name": "sample", "files": [jFile]}]}}


def test_tool_optional_keys_have_their_documented_defaults(MakeJsonFile, tmp_path):
    tools = MakeToolsFromJsons([MakeJsonFile(MakeToolJson())], rootDir=str(tmp_path))
    tool = tools["sample"]
    file = tool.files[0]
    assert tool.versionStr == ""
    assert file.url == ""
    assert file.md5 == "" and file.sha256 == ""
    assert file.size == -1
    assert file.absExtractDir == ""
    assert file.autoDeleteAfterInstall is False
    assert file.skipIfRunnableExists is False
    assert file.callInstructions == []


def test_a_tool_file_without_any_integrity_key_is_accepted(MakeJsonFile, tmp_path):
    # It is then only checked for existence, which SETTINGS.md states.
    tools = MakeToolsFromJsons([MakeJsonFile(MakeToolJson())], rootDir=str(tmp_path))
    file = tools["sample"].files[0]
    assert file.md5 == "" and file.sha256 == "" and file.size == -1


# ---------------------------------------------------------------- bundles

def test_bundle_item_optional_keys_have_their_documented_defaults(MakeJsonFile, MakeFile):
    MakeFile("Src/A.ini")
    bundles = MakeBundlesFromJsons([MakeJsonFile({"bundles": {"items": [
        {"name": "Item", "files": [{"sourceParent": "Src", "sourceList": ["A.ini"]}]}]}})])
    item = bundles.items[0]
    assert item.isBig is True
    assert item.namePrefix == "" and item.nameSuffix == "" and item.bigSuffix == ""
    assert item.setGameLanguageOnInstall == ""
    assert item.events == {}


def test_bundle_pack_optional_keys_have_their_documented_defaults(MakeJsonFile):
    bundles = MakeBundlesFromJsons([MakeJsonFile({"bundles": {"packs": [
        {"name": "Pack", "itemNames": []}]}})])
    pack = bundles.packs[0]
    assert pack.allowBuild is False and pack.allowInstall is False
    assert pack.namePrefix == "" and pack.nameSuffix == ""


def test_a_bundle_file_defaults_its_source_parent_to_the_json_directory(MakeJsonFile, MakeFile, tmp_path):
    MakeFile("A.ini")
    bundles = MakeBundlesFromJsons([MakeJsonFile({"bundles": {"items": [
        {"name": "Item", "files": [{"sourceList": ["A.ini"]}]}]}})])
    assert bundles.items[0].files[0].absSourceParent == str(tmp_path)


def test_a_bundle_file_accepts_the_legacy_parent_key(MakeJsonFile, MakeFile, tmp_path):
    MakeFile("Src/A.ini")
    bundles = MakeBundlesFromJsons([MakeJsonFile({"bundles": {"items": [
        {"name": "Item", "files": [{"parent": "Src", "sourceList": ["A.ini"]}]}]}})])
    assert bundles.items[0].files[0].absSourceParent.endswith("Src")


def test_a_source_target_element_defaults_its_target_to_its_source(MakeJsonFile, MakeFile):
    # SETTINGS.md called target mandatory here, but it has always defaulted.
    MakeFile("Src/A.ini")
    bundles = MakeBundlesFromJsons([MakeJsonFile({"bundles": {"items": [
        {"name": "Item", "files": [{"sourceParent": "Src", "sourceTargetList": [{"source": "A.ini"}]}]}]}})])
    assert bundles.items[0].files[0].relTargetFile == "A.ini"


def test_an_event_defaults_its_function_name(MakeJsonFile, MakeFile):
    MakeFile("Event.py")
    bundles = MakeBundlesFromJsons([MakeJsonFile({"bundles": {"items": [
        {"name": "Item", "onPreBuild": {"script": "Event.py"}}]}})])
    assert list(bundles.items[0].events.values())[0].funcName == "OnEvent"
    assert list(bundles.items[0].events.values())[0].kwargs == {}


# ---------------------------------------------------------------- changelog

def test_changelog_record_optional_keys_have_their_documented_defaults(MakeJsonFile, MakeFile):
    MakeFile("Log.yaml")
    config = MakeChangeConfigFromJsons([MakeJsonFile({"changelog": {"records": [
        {"sourceList": ["Log.yaml"], "targetList": ["Out.md"]}]}})])
    record = config.records[0]
    assert record.sortDefinitions == []
    assert record.includeLabels == [] and record.excludeLabels == []


# ---------------------------------------------------------------- merged sections

def test_folders_may_be_split_across_two_json_files(MakeJsonFile):
    # Each key is optional per file and required only of the merged result.
    first = MakeJsonFile({"folders": {"releaseDir": "R"}}, "First.json")
    second = MakeJsonFile({"folders": {"buildDir": "B"}}, "Second.json")
    folders = MakeFoldersFromJsons([first, second])
    assert folders.absReleaseDir.endswith("R")
    assert folders.absBuildDir.endswith("B")


def test_a_tool_of_the_same_name_in_a_later_json_replaces_the_earlier_one(MakeJsonFile, tmp_path):
    first = MakeJsonFile(MakeToolJson(target="old.exe"), "First.json")
    second = MakeJsonFile(MakeToolJson(target="new.exe"), "Second.json")
    tools = MakeToolsFromJsons([first, second], rootDir=str(tmp_path))
    assert tools["sample"].files[0].absTarget.endswith("new.exe")


@pytest.mark.parametrize("section,data,Parse", [
    ("bundles.items[].name", {"bundles": {"items": [{}]}}, MakeBundlesFromJsons),
    ("bundles.packs[].name", {"bundles": {"packs": [{}]}}, MakeBundlesFromJsons),
    ("changelog.records[].sourceList", {"changelog": {"records": [{"targetList": ["a"]}]}},
     MakeChangeConfigFromJsons),
    ("changelog.records[].targetList", {"changelog": {"records": [{"sourceList": ["a"]}]}},
     MakeChangeConfigFromJsons),
])
def test_a_mandatory_key_is_required(MakeJsonFile, section, data, Parse):
    with pytest.raises(AssertionError) as error:
        Parse([MakeJsonFile(data)])
    assert "is required but is not set" in str(error.value)
