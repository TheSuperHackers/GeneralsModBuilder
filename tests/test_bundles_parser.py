import os

import pytest

from generalsmodbuilder.data.bundles import BundleEventType, MakeBundlesFromJsons


def MakeItemsJson(files: list, **itemOverrides) -> dict:
    jItem = {"name": "SampleItem", "big": True, "files": files}
    jItem.update(itemOverrides)
    return {"bundles": {"version": 1, "items": [jItem]}}


def test_a_source_and_target_pair_is_parsed(MakeJsonFile, MakeFile):
    MakeFile("Src/Data/Weapon.ini")
    bundles = MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([
        {"sourceParent": "Src", "source": "Data/Weapon.ini", "target": "Data/Renamed.ini"}]))])
    file = bundles.items[0].files[0]
    assert file.relTargetFile == os.path.join("Data", "Renamed.ini")
    assert file.GetFirstAbsSourceFile().endswith(os.path.join("Src", "Data", "Weapon.ini"))


def test_a_source_list_derives_its_targets(MakeJsonFile, MakeFile):
    MakeFile("Src/A.ini")
    MakeFile("Src/B.ini")
    bundles = MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([
        {"sourceParent": "Src", "sourceList": ["A.ini", "B.ini"]}]))])
    assert [f.relTargetFile for f in bundles.items[0].files] == ["A.ini", "B.ini"]


def test_a_multi_source_builds_one_target(MakeJsonFile, MakeFile):
    MakeFile("Src/A.ini")
    MakeFile("Src/B.ini")
    bundles = MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([
        {"sourceParent": "Src", "multiSource": ["A.ini", "B.ini"], "target": "Joined.ini"}]))])
    file = bundles.items[0].files[0]
    assert file.HasMultiSourceFile()
    assert file.relTargetFile == "Joined.ini"
    assert len(file.absSourceFiles) == 2


def test_a_missing_item_name_names_the_file_and_the_index(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile({"bundles": {"items": [{"big": True}]}})])
    assert str(error.value).endswith("bundles.items[0].name is required but is not set")


def test_a_missing_source_in_a_source_target_list_names_the_element(MakeJsonFile, MakeFile):
    # A missing source used to be reported as an absSourceFiles value being None.
    MakeFile("Src/A.ini")
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([
            {"sourceParent": "Src", "sourceTargetList": [{"target": "A.ini"}]}]))])
    assert str(error.value).endswith(
        "bundles.items[0] 'SampleItem'.files[0].sourceTargetList[0].source is required but is not set")


def test_a_source_target_element_that_is_not_a_dict_names_the_element(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([
            {"sourceParent": "Src", "sourceTargetList": ["A.ini"]}]))])
    assert str(error.value).endswith(
        "bundles.items[0] 'SampleItem'.files[0].sourceTargetList[0] is type:str but should be type:dict")


def test_a_missing_pack_item_names_list_is_reported(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile({"bundles": {"packs": [{"name": "Core"}]}})])
    assert str(error.value).endswith("bundles.packs[0] 'Core'.itemNames is required but is not set")


def test_a_pack_referencing_an_unknown_item_is_reported(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile({"bundles": {"packs": [{"name": "Core", "itemNames": ["Absent"]}]}})])
    assert str(error.value) == "bundles.packs 'Core' references unknown bundle item 'Absent'"


def test_an_event_is_parsed_and_its_script_is_mandatory(MakeJsonFile, MakeFile):
    MakeFile("Src/A.ini")
    MakeFile("Event.py")
    bundles = MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson(
        [{"sourceParent": "Src", "sourceList": ["A.ini"]}],
        onPreBuild={"script": "Event.py", "function": "Run"}))])
    event = bundles.items[0].events[BundleEventType.OnPreBuild]
    assert event.funcName == "Run"
    assert event.GetScriptName() == "Event"

    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson(
            [{"sourceParent": "Src", "sourceList": ["A.ini"]}], onPreBuild={"function": "Run"}))])
    assert str(error.value).endswith("bundles.items[0] 'SampleItem'.onPreBuild.script is required but is not set")


def test_the_registry_list_does_not_modify_the_parsed_json_data(MakeJsonFile, MakeFile):
    MakeFile("Src/A.ini")
    MakeFile("Registry.zip")
    jsonFile = MakeJsonFile(MakeItemsJson([
        {"sourceParent": "Src", "sourceList": ["A.ini"], "registryList": ["Registry.zip"]}]))
    bundles = MakeBundlesFromJsons([jsonFile])
    assert bundles.items[0].files[0].registryDef.crc32 != 0
    assert jsonFile.data["bundles"]["items"][0]["files"][0]["registryList"] == ["Registry.zip"]


def test_a_bad_params_value_is_reported(MakeJsonFile, MakeFile):
    MakeFile("Src/A.ini")
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([
            {"sourceParent": "Src", "sourceList": ["A.ini"], "params": {"nested": {"a": 1}}}]))])
    assert "bundles.items.files.params.value" in str(error.value)


def test_item_prefixes_carry_over_to_a_later_json_file(MakeJsonFile, MakeFile):
    MakeFile("Src/A.ini")
    MakeFile("B/Src/A.ini")
    first = MakeJsonFile({"bundles": {"itemsPrefix": "001_", "items": [
        {"name": "First", "files": [{"sourceParent": "Src", "sourceList": ["A.ini"]}]}]}}, "First.json")
    second = MakeJsonFile({"bundles": {"items": [
        {"name": "Second", "files": [{"sourceParent": "Src", "sourceList": ["A.ini"]}]}]}}, "B/Second.json")
    bundles = MakeBundlesFromJsons([first, second])
    assert bundles.FindItemByName("First").GetBigFileName() == "001_First.big"
    assert bundles.FindItemByName("Second").GetBigFileName() == "001_Second.big"
