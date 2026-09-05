import os

import pytest

from generalsmodbuilder.data.tools import MakeToolsFromJsons


def MakeToolsJson(files: list) -> dict:
    return {"tools": {"version": 2, "list": [{"name": "sample", "version": "1.0", "files": files}]}}


def test_call_instruction_without_call_args_is_parsed(MakeJsonFile, tmp_path):
    # callArgs defaulted to the ParamsT type rather than an instance of it, so verifying
    # it called items() on a type and raised AttributeError.
    jsonFile = MakeJsonFile(MakeToolsJson([{
        "target": "sample.exe",
        "runnable": True,
        "callList": [{"call": "sample.exe"}],
    }]))
    tools = MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path))
    instruction = tools["sample"].files[0].callInstructions[0]
    assert instruction.callArgs == {}


def test_call_args_keep_values_that_are_not_strings(MakeJsonFile, tmp_path):
    # Call arguments may be any param value, and replacing aliases used to call
    # replace() on every one of them.
    jsonFile = MakeJsonFile({"tools": {"version": 2, "aliases": {"{A}": "resolved"}, "list": [{
        "name": "sample",
        "files": [{
            "target": "sample.exe",
            "runnable": True,
            "callList": [{"call": "sample.exe", "callArgs": {
                "--text": "{A}/value",
                "--number": 7,
                "--flag": True,
                "--list": ["a", "b"],
            }}],
        }],
    }]}})
    tools = MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path))
    callArgs = tools["sample"].files[0].callInstructions[0].callArgs
    assert callArgs["--text"] == "resolved/value"
    assert callArgs["--number"] == 7
    assert callArgs["--flag"] is True
    assert callArgs["--list"] == ["a", "b"]


def test_aliases_do_not_modify_the_parsed_json_data(MakeJsonFile, tmp_path):
    jsonFile = MakeJsonFile({"tools": {"version": 2, "aliases": {"{A}": "resolved"}, "list": [{
        "name": "sample",
        "files": [{
            "target": "sample.exe",
            "runnable": True,
            "callList": [{"call": "sample.exe", "callArgs": {"--text": "{A}"}}],
        }],
    }]}})
    MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path))
    jCallArgs = jsonFile.data["tools"]["list"][0]["files"][0]["callList"][0]["callArgs"]
    assert jCallArgs["--text"] == "{A}"


def test_each_tools_json_roots_its_tools_in_its_own_directory(MakeJsonFile):
    # The root of the first tools json used to be kept and applied to every later one.
    first = MakeJsonFile(MakeToolsJson([{"target": "first.exe", "runnable": True}]), "A/First.json")
    second = MakeJsonFile(MakeToolsJson([{"target": "second.exe", "runnable": True}]), "B/Second.json")
    second.data["tools"]["list"][0]["name"] = "other"

    tools = MakeToolsFromJsons([first, second])
    assert os.path.dirname(tools["sample"].files[0].absTarget).endswith(os.path.join("A"))
    assert os.path.dirname(tools["other"].files[0].absTarget).endswith(os.path.join("B"))


def test_the_root_dir_override_applies_to_every_tools_json(MakeJsonFile, tmp_path):
    root = str(tmp_path / "Root")
    first = MakeJsonFile(MakeToolsJson([{"target": "first.exe", "runnable": True}]), "A/First.json")
    second = MakeJsonFile(MakeToolsJson([{"target": "second.exe", "runnable": True}]), "B/Second.json")
    second.data["tools"]["list"][0]["name"] = "other"

    tools = MakeToolsFromJsons([first, second], rootDir=root)
    assert tools["sample"].files[0].absTarget == os.path.join(root, "first.exe")
    assert tools["other"].files[0].absTarget == os.path.join(root, "second.exe")


def test_an_alias_that_is_an_absolute_path_yields_that_path(MakeJsonFile, tmp_path):
    # Aliases used to be replaced after the join, so an absolute alias was appended to
    # the root directory instead of replacing it.
    elsewhere = str(tmp_path / "Elsewhere")
    jsonFile = MakeJsonFile({"tools": {"version": 2, "aliases": {"{ELSEWHERE}": elsewhere}, "list": [{
        "name": "sample",
        "files": [{"target": "{ELSEWHERE}/sample.exe", "runnable": True}],
    }]}})
    tools = MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path / "Root"))
    assert tools["sample"].files[0].absTarget == os.path.join(elsewhere, "sample.exe")


def test_the_default_tools_config_resolves_the_addon_zip_into_the_root_dir(tmp_path):
    # The blender addon install argument named THIS_DIR, which is the packaged config
    # directory, while the zip is downloaded into the root directory.
    from generalsmodbuilder import util
    from generalsmodbuilder.util import JsonFile

    jsonFile = JsonFile(os.path.join(util.g_appDir, "config", "DefaultTools.json"))
    root = str(tmp_path / "Cache")
    tools = MakeToolsFromJsons([jsonFile], rootDir=root)

    addonFile = next(f for f in tools["blender"].files if f.callInstructions)
    instruction = addonFile.callInstructions[0]
    assert addonFile.absTarget == os.path.join(root, ".tools", "io_mesh_w3d.zip")

    # The expression normalizes the path it is given, so compare it the same way.
    expression: str = instruction.callArgs["--python-expr"]
    quotedPath: str = expression.split("normpath('", 1)[1].split("')", 1)[0]
    assert os.path.normpath(quotedPath) == addonFile.absTarget


def test_a_missing_tool_name_names_the_file_and_the_key(MakeJsonFile, tmp_path):
    jsonFile = MakeJsonFile({"tools": {"version": 2, "list": [
        {"files": [{"target": "sample.exe", "runnable": True}]}]}})
    with pytest.raises(AssertionError) as error:
        MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path))
    assert str(error.value).endswith("tools.list[0].name is required but is not set")


def test_a_missing_target_names_the_tool_and_the_file_index(MakeJsonFile, tmp_path):
    jsonFile = MakeJsonFile(MakeToolsJson([{"runnable": True}]))
    with pytest.raises(AssertionError) as error:
        MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path))
    assert str(error.value).endswith("tools.list[0] 'sample'.files[0].target is required but is not set")


def test_an_empty_target_is_rejected(MakeJsonFile, tmp_path):
    jsonFile = MakeJsonFile(MakeToolsJson([{"target": "", "runnable": True}]))
    with pytest.raises(AssertionError) as error:
        MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path))
    assert str(error.value).endswith("tools.list[0] 'sample'.files[0].target must not be empty")


def test_a_tool_without_a_runnable_file_is_rejected(MakeJsonFile, tmp_path):
    jsonFile = MakeJsonFile(MakeToolsJson([{"target": "sample.dat"}]))
    with pytest.raises(AssertionError) as error:
        MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path))
    assert str(error.value) == "tools.list 'sample' has no runnable file"


def test_a_bad_size_names_the_file_and_the_key(MakeJsonFile, tmp_path):
    jsonFile = MakeJsonFile(MakeToolsJson([{"target": "sample.exe", "runnable": True, "size": "big"}]))
    with pytest.raises(AssertionError) as error:
        MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path))
    assert str(error.value).endswith("tools.list[0] 'sample'.files[0].size is type:str but should be type:int")


def test_a_tools_version_that_is_not_a_number_is_rejected(MakeJsonFile, tmp_path):
    # Comparing the version used to raise TypeError before it could be reported.
    jsonFile = MakeJsonFile({"tools": {"version": "2", "list": []}})
    with pytest.raises(AssertionError) as error:
        MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path))
    assert str(error.value).endswith("tools.version is type:str but should be type:int")


def test_a_disabled_tool_is_skipped(MakeJsonFile, tmp_path):
    jsonFile = MakeJsonFile(MakeToolsJson([{"target": "sample.exe", "runnable": True}]))
    jsonFile.data["tools"]["list"][0]["enabled"] = False
    assert MakeToolsFromJsons([jsonFile], rootDir=str(tmp_path)) == {}
