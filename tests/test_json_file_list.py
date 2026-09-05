import json
import os

import pytest

from generalsmodbuilder.buildfunctions import CreateJsonFileList


@pytest.fixture
def WriteJson(tmp_path):
    def Write(name: str, data: dict) -> str:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)
    return Write


def Names(jsonFiles) -> list[str]:
    return [os.path.basename(jsonFile.path) for jsonFile in jsonFiles]


def test_build_sections_are_followed_to_any_depth(WriteJson):
    # Only one level used to be followed, so a build section in an included file was
    # silently ignored and its bundle items never reached the build.
    WriteJson("C.json", {"bundles": {"items": []}})
    WriteJson("B.json", {"build": {"files": ["C.json"]}})
    root = WriteJson("A.json", {"build": {"files": ["B.json"]}})
    assert Names(CreateJsonFileList([root])) == ["A.json", "B.json", "C.json"]


def test_the_given_files_keep_their_order_and_come_first(WriteJson):
    # A later file overrides an earlier one, so the order has to be preserved.
    WriteJson("IncludedByFirst.json", {})
    WriteJson("IncludedBySecond.json", {})
    first = WriteJson("First.json", {"build": {"files": ["IncludedByFirst.json"]}})
    second = WriteJson("Second.json", {"build": {"files": ["IncludedBySecond.json"]}})
    assert Names(CreateJsonFileList([first, second])) == [
        "First.json", "Second.json", "IncludedByFirst.json", "IncludedBySecond.json"]


def test_a_file_listed_twice_is_read_once(WriteJson):
    # Reading it twice used to fail much later with a duplicate bundle item name.
    WriteJson("Shared.json", {})
    root = WriteJson("A.json", {"build": {"files": ["Shared.json", "Shared.json"]}})
    assert Names(CreateJsonFileList([root])) == ["A.json", "Shared.json"]


def test_a_diamond_include_reads_the_shared_file_once(WriteJson):
    WriteJson("Shared.json", {})
    WriteJson("B.json", {"build": {"files": ["Shared.json"]}})
    WriteJson("C.json", {"build": {"files": ["Shared.json"]}})
    root = WriteJson("A.json", {"build": {"files": ["B.json", "C.json"]}})
    assert Names(CreateJsonFileList([root])) == ["A.json", "B.json", "C.json", "Shared.json"]


def test_a_cycle_terminates(WriteJson):
    WriteJson("B.json", {"build": {"files": ["A.json"]}})
    root = WriteJson("A.json", {"build": {"files": ["B.json"]}})
    assert Names(CreateJsonFileList([root])) == ["A.json", "B.json"]


def test_a_file_reached_through_two_different_paths_is_read_once(WriteJson):
    WriteJson("Sub/Shared.json", {})
    root = WriteJson("A.json", {"build": {"files": ["Sub/Shared.json", "Sub/../Sub/Shared.json"]}})
    assert Names(CreateJsonFileList([root])) == ["A.json", "Shared.json"]
