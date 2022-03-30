import os.path
import utils
import urllib.request
import http.client
from utils import JsonFile
from logging import warning
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

    def ValidateInstall(self) -> None:
        utils.RelAssert(os.path.isfile(self.target), f"Tool.target file '{self.target}' does not exist")
        if self.md5:
            actualMd5 = utils.GetFileMd5(self.target)
            utils.RelAssert(self.md5 == actualMd5, f"Tool.md5 '{self.md5}' does not match md5 '{actualMd5}' of target file '{self.target}'")

    def IsInstalled(self) -> bool:
        return os.path.isfile(self.target) and (not self.md5 or utils.GetFileMd5(self.target) == self.md5)

    def Install(self) -> bool:
        success = True
        if not self.IsInstalled():
            success = False
            if self.url:
                response: http.client.HTTPResponse = urllib.request.urlopen(self.url)
                if response.code == 200:
                    data: bytes = response.read()
                    utils.MakeDirsForFile(self.target)
                    with open(self.target, 'wb') as wfile:
                        wfile.write(data)
                    success = self.IsInstalled()

        return success


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
        utils.RelAssert(self.GetExecutable() != None, "Tool.files contains no runnable file")

    def ValidateInstall(self) -> None:
        for file in self.files:
            file.ValidateInstall()

    def GetExecutable(self) -> str:
        file: ToolFile
        for file in self.files:
            if file.runnable:
                return file.target
        return None

    def Install(self) -> bool:
        file: ToolFile
        success: bool = True
        for file in self.files:
            installed: bool = file.Install()
            if installed:
                print(f"Tool '{self.name}' file '{file.target}' is installed")
            else:
                warning(f"Tool '{self.name}' file '{file.target}' was not installed")
                success = False

        return success


def MakeToolsFromJsons(jsonFiles: list[JsonFile]) -> dict[Tool]:
    tools = dict()
    tool: Tool

    for jsonFile in jsonFiles:
        jsonDir: str = utils.GetFileDir(jsonFile.path)
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
        tool.Validate()
        tool.Normalize()
        tool.Install()
        tool.ValidateInstall()
        print("Created", tool)

    return tools


def InstallTools(tools: dict[Tool]) -> bool:
    tool: Tool
    success: bool = True
    for tool in tools.values():
        if not tool.Install():
            success = False
    return success
