import os

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
