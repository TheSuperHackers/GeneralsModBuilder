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


def test_an_entry_naming_no_source_key_is_rejected(MakeJsonFile):
    # A misspelled source key used to make the entry build nothing at all, in silence.
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([{"sourceParent": "Src", "sourceLst": ["A.ini"]}]))])
    assert str(error.value).endswith(
        "bundles.items[0] 'SampleItem'.files[0] must name at least one of 'source', 'sourceList', "
        "'sourceTargetList', 'multiSource' or 'multiSourceTargetList', otherwise it builds no file at all")


@pytest.mark.parametrize("key", ["source", "sourceList", "sourceTargetList", "multiSource", "multiSourceTargetList"])
def test_an_empty_source_collection_is_rejected(MakeJsonFile, key):
    empty = "" if key == "source" else []
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([{"sourceParent": "Src", key: empty}]))])
    assert str(error.value).endswith(
        f"bundles.items[0] 'SampleItem'.files[0].{key} must not be empty, otherwise it builds no file at all")


@pytest.mark.parametrize("key", ["sourceList", "sourceTargetList"])
def test_a_target_that_nothing_consumes_is_rejected(MakeJsonFile, MakeFile, key):
    MakeFile("Src/A.ini")
    value = ["A.ini"] if key == "sourceList" else [{"source": "A.ini", "target": "A.ini"}]
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([
            {"sourceParent": "Src", key: value, "target": "Ignored.ini"}]))])
    assert str(error.value).endswith(
        "bundles.items[0] 'SampleItem'.files[0].target is only used together with 'source' or 'multiSource'")


def test_a_target_next_to_multi_source_and_a_source_target_list_stays_valid(MakeJsonFile, MakeFile):
    # The target belongs to the multiSource half. A live sample config relies on this.
    MakeFile("Src/A.ini")
    MakeFile("Src/B.ini")
    bundles = MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([{
        "sourceParent": "Src",
        "multiSource": ["A.ini"],
        "target": "Joined.ini",
        "sourceTargetList": [{"source": "B.ini", "target": "Renamed.ini"}],
    }]))])
    assert sorted(f.relTargetFile for f in bundles.items[0].files) == ["Joined.ini", "Renamed.ini"]


def test_a_multi_source_without_a_target_is_rejected(MakeJsonFile, MakeFile):
    MakeFile("Src/A.ini")
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([
            {"sourceParent": "Src", "multiSource": ["A.ini"]}]))])
    assert "target is mandatory with 'multiSource'" in str(error.value)


def test_a_multi_source_target_wildcard_is_rejected(MakeJsonFile, MakeFile):
    MakeFile("Src/A.ini")
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([
            {"sourceParent": "Src", "multiSource": ["A.ini"], "target": "Data/*.ini"}]))])
    assert "cannot contain a wildcard with 'multiSource'" in str(error.value)


def test_source_and_multi_source_together_are_rejected(MakeJsonFile, MakeFile):
    MakeFile("Src/A.ini")
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([
            {"sourceParent": "Src", "source": "A.ini", "multiSource": ["A.ini"], "target": "J.ini"}]))])
    assert "cannot specify 'source' and 'multiSource' together" in str(error.value)


def test_an_item_without_files_stays_valid(MakeJsonFile):
    # The sample project ships a deliberate empty item.
    bundles = MakeBundlesFromJsons([MakeJsonFile(MakeItemsJson([]))])
    assert bundles.items[0].files == []
