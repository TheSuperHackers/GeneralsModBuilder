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
