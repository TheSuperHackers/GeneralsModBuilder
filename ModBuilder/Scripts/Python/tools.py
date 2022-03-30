import utils
from utils import JsonFile
from dataclasses import dataclass


@dataclass(init=False)
class ToolFile:
    url: str
    target: str
    md5: str = ""
    runnable: bool = False

    def __init__(self):
        pass

    def Normalize(self) -> None:
        self.target = utils.NormalizePath(self.target)

    def Validate(self) -> None:
        utils.RelAssert(isinstance(self.url, str), "Tool.url has incorrect type")
        utils.RelAssert(isinstance(self.md5, str), "Tool.md5 has incorrect type")
        utils.RelAssert(isinstance(self.target, str), "Tool.target has incorrect type")
        utils.RelAssert(isinstance(self.runnable, bool), "Tool.runnable has incorrect type")


@dataclass(init=False)
class Tool:
    name: str
    files: list[ToolFile]

    def __init__(self):
        pass

    def Normalize(self) -> None:
        for file in self.files:
            file.Normalize()

    def Validate(self) -> None:
        utils.RelAssert(isinstance(self.name, str), "Tool.name has incorrect type")
        utils.RelAssert(isinstance(self.files, list), "Tool.files has incorrect type")
        for file in self.files:
            file.Validate()


def MakeToolsFromJsons(jsonFiles: list[JsonFile]) -> dict[Tool]:
    tools = dict()
    tool: Tool

    for jsonFile in jsonFiles:
        jsonDir: str = utils.MakeFileDir(jsonFile.path)
        jTools: dict = jsonFile.data.get("tools")
        jTool: dict
        jFile: dict

        if not jTools:
            continue

        jList: dict = jTools.get("list")

        if not jList:
            continue

        for jTool in jList:
            tool = Tool()
            tool.name = jTool.get("name")
            tool.files = []
            jFiles: dict = jTool.get("files")

            if jFiles:
                for jFile in jFiles:
                    toolFile = ToolFile()
                    toolFile.url = jFile.get("url")
                    toolFile.target = utils.JoinPathIfValid(None, jsonDir, jFile.get("target"))
                    toolFile.md5 = utils.GetSecondIfValid(toolFile.md5, jFile.get("md5"))
                    toolFile.runnable = utils.GetSecondIfValid(toolFile.runnable, jFile.get("runnable"))
                    tool.files.append(toolFile)

            tools[tool.name] = tool

    for tool in tools.values():
        tool.Normalize()
        print("Created", tool)

    return tools
