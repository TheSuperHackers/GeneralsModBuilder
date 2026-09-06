"""
Covers BuildCopy end to end on the paths that need no build tool, and on the tool paths
with the process call standing in for the tool, so that these run anywhere.
"""
import io
import os

import pytest

from generalsmodbuilder import util
from generalsmodbuilder.build.copy import BuildCopy, BuildCopyOption
from generalsmodbuilder.data.tools import Tool, ToolFile, ToolsT


CR = chr(13)
LF = chr(10)
CRLF = CR + LF


def MakeTools(*names: str) -> ToolsT:
    """
    Tools that name an executable which is never run, because the tests stand in for the
    process call itself.
    """
    tools = ToolsT()
    for name in names:
        toolFile = ToolFile()
        toolFile.absTarget = name + ".exe"
        toolFile.runnable = True
        tool = Tool()
        tool.name = name
        tool.files = [toolFile]
        tools[name] = tool
    return tools


def WriteFile(path, text: str) -> str:
    path = str(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="ascii", newline="") as wfile:
        wfile.write(text)
    return path


def ReadFile(path: str) -> str:
    with io.open(str(path), "r", encoding="ascii", newline="") as rfile:
        return rfile.read()


@pytest.fixture
def StandInForProcess(monkeypatch):
    """
    Replaces the process call with a function that records the command line, and optionally
    writes the file that the tool would have written.
    """
    calls = []

    def Install(writeTarget: str = None, text: str = "", fail: bool = False):
        def Run(args) -> bool:
            calls.append(args)
            if fail:
                raise Exception("the tool failed")
            if writeTarget != None:
                WriteFile(writeTarget, text)
            return True
        monkeypatch.setattr(util, "RunProcess", Run)
        return calls

    return Install


def test_csf_to_str_applies_the_text_params(tmp_path, StandInForProcess):
    # All params of a build file apply to the file that it builds. The compiler cannot
    # apply the text ones, so they have to be applied to what it wrote.
    source = WriteFile(tmp_path / "Src" / "generals.csf", "")
    target = str(tmp_path / "Out" / "generals.str")
    toolText = "LABEL" + LF + '"value" ; a comment' + LF + "END" + LF
    StandInForProcess(writeTarget=target + ".tmp.str", text=toolText)

    copy = BuildCopy(tools=MakeTools("gametextcompiler"))
    result = copy.Copy([source], target, {"deleteComments": ";", "forceEOL": CRLF})

    assert result.success
    assert ReadFile(target) == "LABEL" + CRLF + '"value" ' + CRLF + "END" + CRLF
    assert not os.path.isfile(target + ".tmp.str")


def test_csf_to_str_without_text_params_keeps_what_the_tool_wrote(tmp_path, StandInForProcess):
    source = WriteFile(tmp_path / "Src" / "generals.csf", "")
    target = str(tmp_path / "Out" / "generals.str")
    toolText = "LABEL" + LF + '"value"' + LF + "END" + LF
    calls = StandInForProcess(writeTarget=target, text=toolText)

    copy = BuildCopy(tools=MakeTools("gametextcompiler"))
    result = copy.Copy([source], target, {"language": "English"})

    assert result.success
    # The tool writes the target itself when there is nothing to apply to it afterwards.
    assert calls[0][1:] == ["-LOAD_CSF", source, "-SAVE_STR", target, "-SAVE_STR_LANGUAGES", "English"]
    assert ReadFile(target) == toolText


def MakeSourceTree(tmp_path) -> str:
    WriteFile(tmp_path / "Pack" / "Data" / "INI" / "Weapon.ini", "Weapon" + CRLF)
    WriteFile(tmp_path / "Pack" / "readme.txt", "read me" + CRLF)
    return str(tmp_path / "Pack")


@pytest.mark.parametrize("targetName", ["Mod.zip", "Mod.tar", "Mod.gz"])
def test_an_archive_is_written_to_the_target_that_was_asked_for(tmp_path, targetName):
    # make_archive appends the suffix of its format, which is .tar.gz for a gztar, so the
    # file it writes is not the target file unless it is moved onto it.
    source = MakeSourceTree(tmp_path)
    target = str(tmp_path / "Release" / targetName)

    result = BuildCopy(tools=ToolsT()).Copy([source], target)

    assert result.success
    assert os.path.isfile(target)
    assert os.listdir(str(tmp_path / "Release")) == [targetName]


def test_a_zip_holds_the_source_tree(tmp_path):
    import zipfile
    source = MakeSourceTree(tmp_path)
    target = str(tmp_path / "Release" / "Mod.zip")

    BuildCopy(tools=ToolsT()).Copy([source], target)

    with zipfile.ZipFile(target) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        assert sorted(names) == ["Data/INI/Weapon.ini", "readme.txt"]
        assert archive.read("readme.txt") == b"read me" + CRLF.encode()


def ListDir(path) -> list:
    return sorted(os.listdir(str(path)))


def test_a_failed_str_to_csf_leaves_no_temp_file(tmp_path, StandInForProcess):
    source = WriteFile(tmp_path / "Src" / "generals.str", "LABEL" + LF)
    target = str(tmp_path / "Out" / "generals.csf")
    os.makedirs(str(tmp_path / "Out"), exist_ok=True)
    StandInForProcess(fail=True)

    copy = BuildCopy(tools=MakeTools("gametextcompiler"))
    with pytest.raises(Exception):
        copy.Copy([source], target, {"deleteComments": ";"})

    assert ListDir(tmp_path / "Out") == []


def test_a_failed_csf_to_str_leaves_no_temp_file(tmp_path, StandInForProcess):
    source = WriteFile(tmp_path / "Src" / "generals.csf", "")
    target = str(tmp_path / "Out" / "generals.str")
    os.makedirs(str(tmp_path / "Out"), exist_ok=True)
    StandInForProcess(fail=True)

    copy = BuildCopy(tools=MakeTools("gametextcompiler"))
    with pytest.raises(Exception):
        copy.Copy([source], target, {"deleteComments": ";"})

    assert ListDir(tmp_path / "Out") == []


def test_a_failed_game_text_merge_leaves_no_temp_files(tmp_path, StandInForProcess):
    first = WriteFile(tmp_path / "Src" / "base.str", "LABEL" + LF)
    second = WriteFile(tmp_path / "Src" / "override.str", "LABEL" + LF)
    target = str(tmp_path / "Out" / "generals.csf")
    os.makedirs(str(tmp_path / "Out"), exist_ok=True)
    StandInForProcess(fail=True)

    copy = BuildCopy(tools=MakeTools("gametextcompiler"))
    with pytest.raises(Exception):
        copy.Copy([first, second], target, {"deleteComments": ";"})

    assert ListDir(tmp_path / "Out") == []


def test_a_successful_game_text_merge_leaves_no_temp_files(tmp_path, StandInForProcess):
    first = WriteFile(tmp_path / "Src" / "base.str", "LABEL" + LF)
    second = WriteFile(tmp_path / "Src" / "override.str", "LABEL" + LF)
    target = str(tmp_path / "Out" / "generals.csf")
    StandInForProcess(writeTarget=target, text="")

    copy = BuildCopy(tools=MakeTools("gametextcompiler"))
    assert copy.Copy([first, second], target, {"deleteComments": ";"}).success

    assert ListDir(tmp_path / "Out") == ["generals.csf"]


@pytest.mark.parametrize("name", ["Data/INI/Weapon.ini", "Window/Chat.wnd", "Data/generals.str"])
def test_a_text_file_without_text_params_arrives_as_it_is(tmp_path, name):
    text = "Weapon ; a comment" + CRLF + "  Value = 1" + CRLF + "End" + CRLF
    source = WriteFile(tmp_path / "Src" / name, text)
    target = str(tmp_path / "Out" / name)

    result = BuildCopy(tools=ToolsT()).Copy([source], target)

    assert result.success
    assert ReadFile(target) == text


@pytest.mark.parametrize("name", ["Data/INI/Weapon.ini", "Window/Chat.wnd", "Data/generals.str"])
def test_a_text_file_with_text_params_arrives_transformed(tmp_path, name):
    text = "Weapon ; a comment" + LF + "  Value   =  1" + LF + "End" + LF
    source = WriteFile(tmp_path / "Src" / name, text)
    target = str(tmp_path / "Out" / name)

    result = BuildCopy(tools=ToolsT()).Copy(
        [source], target, {"deleteComments": ";", "deleteWhitespace": 1, "forceEOL": CRLF})

    assert result.success
    assert ReadFile(target) == "Weapon" + CRLF + "Value = 1" + CRLF + "End" + CRLF


def test_multi_source_text_files_are_appended_in_order(tmp_path):
    first = WriteFile(tmp_path / "Src" / "10_First.ini", "Part = 1" + CRLF)
    second = WriteFile(tmp_path / "Src" / "20_Second.ini", "Part = 2" + CRLF)
    target = str(tmp_path / "Out" / "Joined.ini")

    result = BuildCopy(tools=ToolsT()).Copy([first, second], target)

    assert result.success
    assert ReadFile(target) == "Part = 1" + CRLF + "Part = 2" + CRLF


def test_an_appended_file_without_a_trailing_newline_does_not_merge_into_the_next(tmp_path):
    first = WriteFile(tmp_path / "Src" / "10_First.ini", "Part = 1" + CRLF + "Last")
    second = WriteFile(tmp_path / "Src" / "20_Second.ini", "Part = 2" + CRLF)
    target = str(tmp_path / "Out" / "Joined.ini")

    BuildCopy(tools=ToolsT()).Copy([first, second], target)

    assert ReadFile(target) == "Part = 1" + CRLF + "Last" + CRLF + "Part = 2" + CRLF


def test_a_marked_region_may_span_two_appended_files(tmp_path):
    # The sample project builds an ini this way, opening the marker in one part and closing
    # it in the next, which only works if the params apply to the appended result.
    first = WriteFile(tmp_path / "Src" / "10_First.ini",
                      "Keep = 1" + CRLF + ";begin-exclusion-marker" + CRLF + "Drop = 1" + CRLF)
    second = WriteFile(tmp_path / "Src" / "20_Second.ini",
                       "Drop = 2" + CRLF + ";end-exclusion-marker" + CRLF + "Keep = 2" + CRLF)
    target = str(tmp_path / "Out" / "Joined.ini")

    BuildCopy(tools=ToolsT()).Copy(
        [first, second], target,
        {"excludeMarkersList": [[";begin-exclusion-marker", ";end-exclusion-marker"]]})

    assert ReadFile(target) == "Keep = 1" + CRLF + "Keep = 2" + CRLF
