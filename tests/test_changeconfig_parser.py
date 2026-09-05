import os

import pytest

from generalsmodbuilder.data.changeconfig import MakeChangeConfigFromJsons, Sort


def MakeChangelogJson(**overrides) -> dict:
    jRecord = {"sourceList": ["Log.yaml"], "targetList": ["Out/Log.md"]}
    jRecord.update(overrides)
    return {"changelog": {"version": 1, "records": [jRecord]}}


def test_source_and_target_files_are_resolved_against_the_json_directory(MakeJsonFile, MakeFile, tmp_path):
    MakeFile("Log.yaml")
    config = MakeChangeConfigFromJsons([MakeJsonFile(MakeChangelogJson())])
    record = config.records[0]
    assert record.absSourceFiles == [os.path.join(str(tmp_path), "Log.yaml")]
    assert record.absTargetFiles == [os.path.join(str(tmp_path), "Out", "Log.md")]


def test_a_source_wildcard_resolves_to_its_matches(MakeJsonFile, MakeFile, tmp_path):
    MakeFile("Logs/A.yaml")
    MakeFile("Logs/B.yaml")
    config = MakeChangeConfigFromJsons([MakeJsonFile(MakeChangelogJson(sourceList=["Logs/*.yaml"]))])
    assert sorted(os.path.basename(f) for f in config.records[0].absSourceFiles) == ["A.yaml", "B.yaml"]


def test_a_source_file_that_does_not_exist_is_rejected(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeChangeConfigFromJsons([MakeJsonFile(MakeChangelogJson())])
    assert "is not a valid file" in str(error.value)


def test_sort_definitions_are_parsed(MakeJsonFile, MakeFile):
    MakeFile("Log.yaml")
    config = MakeChangeConfigFromJsons([MakeJsonFile(MakeChangelogJson(
        sortList=[{"date": "descending"}, {"label": "Fix"}]))])
    definitions = config.records[0].sortDefinitions
    assert definitions[0].IsDateSort() and definitions[0].sort == Sort.Descending
    assert definitions[1].IsLabelSort() and definitions[1].label == "Fix"


@pytest.mark.parametrize("missing", ["sourceList", "targetList"])
def test_a_missing_mandatory_list_names_the_record_and_the_key(MakeJsonFile, MakeFile, missing):
    MakeFile("Log.yaml")
    jRecord = {"sourceList": ["Log.yaml"], "targetList": ["Out/Log.md"]}
    del jRecord[missing]
    with pytest.raises(AssertionError) as error:
        MakeChangeConfigFromJsons([MakeJsonFile({"changelog": {"records": [jRecord]}})])
    assert str(error.value).endswith(f"changelog.records[0].{missing} is required but is not set")


def test_a_source_entry_that_is_not_a_string_names_the_index(MakeJsonFile):
    # Joining a value that is not a string used to raise a bare TypeError.
    with pytest.raises(AssertionError) as error:
        MakeChangeConfigFromJsons([MakeJsonFile(MakeChangelogJson(sourceList=["Log.yaml", 5]))])
    assert str(error.value).endswith("changelog.records[0].sourceList[1] is type:int but should be type:str")


def test_a_sort_entry_that_is_not_a_dict_names_the_index(MakeJsonFile, MakeFile):
    MakeFile("Log.yaml")
    with pytest.raises(AssertionError) as error:
        MakeChangeConfigFromJsons([MakeJsonFile(MakeChangelogJson(sortList=["date"]))])
    assert str(error.value).endswith("changelog.records[0].sortList[0] is type:str but should be type:dict")


def test_no_changelog_section_yields_no_records(MakeJsonFile):
    assert MakeChangeConfigFromJsons([MakeJsonFile({})]).records == []


def test_an_unrecognized_sort_direction_is_rejected(MakeJsonFile, MakeFile):
    # It used to become Sort.Zero, which the generator compares against neither
    # direction, so the sort rule was silently dropped.
    MakeFile("Log.yaml")
    with pytest.raises(AssertionError) as error:
        MakeChangeConfigFromJsons([MakeJsonFile(MakeChangelogJson(sortList=[{"date": "ascendign"}]))])
    assert str(error.value).endswith(
        "changelog.records[0].sortList[0].date is 'ascendign', but must be 'ascending' or 'descending'")


def test_a_sort_entry_naming_neither_date_nor_label_is_rejected(MakeJsonFile, MakeFile):
    MakeFile("Log.yaml")
    with pytest.raises(AssertionError) as error:
        MakeChangeConfigFromJsons([MakeJsonFile(MakeChangelogJson(sortList=[{}]))])
    assert str(error.value).endswith(
        "changelog.records[0].sortList[0] must name exactly one of 'date' or 'label'")


def test_a_misspelled_sort_key_is_rejected_as_unknown(MakeJsonFile, MakeFile):
    MakeFile("Log.yaml")
    with pytest.raises(AssertionError) as error:
        MakeChangeConfigFromJsons([MakeJsonFile(MakeChangelogJson(sortList=[{"labl": "Fix"}]))])
    assert "changelog.records[0].sortList[0].labl is not a known key" in str(error.value)


def test_a_sort_entry_naming_both_date_and_label_is_rejected(MakeJsonFile, MakeFile):
    MakeFile("Log.yaml")
    with pytest.raises(AssertionError) as error:
        MakeChangeConfigFromJsons([MakeJsonFile(MakeChangelogJson(
            sortList=[{"date": "ascending", "label": "Fix"}]))])
    assert str(error.value).endswith(
        "changelog.records[0].sortList[0] must name exactly one of 'date' or 'label'")


def test_a_sort_direction_is_case_insensitive(MakeJsonFile, MakeFile):
    MakeFile("Log.yaml")
    config = MakeChangeConfigFromJsons([MakeJsonFile(MakeChangelogJson(sortList=[{"date": "Descending"}]))])
    assert config.records[0].sortDefinitions[0].sort == Sort.Descending
