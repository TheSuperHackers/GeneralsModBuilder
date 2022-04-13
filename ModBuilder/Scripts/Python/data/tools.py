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
    absTarget: str
    md5: str = ""
    runnable: bool = False

    def __init__(self):
        pass

    def Normalize(self) -> None:
        self.absTarget = utils.NormalizePath(self.absTarget)

    def VerifyTypes(self) -> None:
        utils.RelAssertType(self.url, str, "ToolFile.url")
        utils.RelAssertType(self.md5, str, "ToolFile.md5")
        utils.RelAssertType(self.absTarget, str, "ToolFile.absTarget")
        utils.RelAssertType(self.runnable, bool, "ToolFile.runnable")

    def VerifyInstall(self) -> None:
        utils.RelAssert(os.path.isfile(self.absTarget), f"ToolFile.absTarget file '{self.absTarget}' does not exist")
        if self.md5:
            actualMd5 = utils.GetFileMd5(self.absTarget)
            utils.RelAssert(self.md5 == actualMd5, f"ToolFile.md5 '{self.md5}' does not match md5 '{actualMd5}' of target file '{self.absTarget}'")

    def IsInstalled(self) -> bool:
        return os.path.isfile(self.absTarget) and (not self.md5 or utils.GetFileMd5(self.absTarget) == self.md5)

    def Install(self) -> bool:
        success = True
        if not self.IsInstalled():
            success = False
            if self.url:
                response: http.client.HTTPResponse = urllib.request.urlopen(self.url)
                if response.code == 200:
                    data: bytes = response.read()
                    utils.MakeDirsForFile(self.absTarget)
                    with open(self.absTarget, 'wb') as wfile:
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

    def Verify(self) -> None:
        utils.RelAssertType(self.name, str, "Tool.name")
        utils.RelAssertType(self.files, list, "Tool.files")
        for file in self.files:
            file.VerifyTypes()
        utils.RelAssert(self.GetExecutable() != None, "Tool.files contains no runnable file")

    def VerifyInstall(self) -> None:
        for file in self.files:
            file.VerifyInstall()

    def GetExecutable(self) -> str:
        file: ToolFile
        for file in self.files:
            if file.runnable:
                return file.absTarget
        return None

    def Install(self) -> bool:
        file: ToolFile
        success: bool = True
        for file in self.files:
            installed: bool = file.Install()
            if installed:
                print(f"Tool '{self.name}' file '{file.absTarget}' is installed")
            else:
                warning(f"Tool '{self.name}' file '{file.absTarget}' was not installed")
                success = False

        return success


ToolsT = dict[str, Tool]


def __MakeToolFileFromDict(jFile: dict, jsonDir: str) -> ToolFile:
    toolFile = ToolFile()
    toolFile.url = jFile.get("url")
    toolFile.absTarget = utils.JoinPathIfValid(None, jsonDir, jFile.get("target"))
    toolFile.md5 = utils.GetSecondIfValid(toolFile.md5, jFile.get("md5"))
    toolFile.runnable = utils.GetSecondIfValid(toolFile.runnable, jFile.get("runnable"))
    return toolFile


def __MakeToolFromDict(jTool: dict, jsonDir: str) -> Tool:
    tool = Tool()
    tool.name = jTool.get("name")
    tool.files = list()
    jFiles: dict = jTool.get("files")
    if jFiles:
        jFile: dict
        for jFile in jFiles:
            toolFile = __MakeToolFileFromDict(jFile, jsonDir)
            tool.files.append(toolFile)
    return tool


def MakeToolsFromJsons(jsonFiles: list[JsonFile]) -> ToolsT:
    tools = dict()
    tool: Tool

    for jsonFile in jsonFiles:
        jsonDir: str = utils.GetFileDir(jsonFile.path)
        jTools: dict = jsonFile.data.get("tools")
        if jTools:
            jList: dict = jTools.get("list")
            if jList:
                jTool: dict
                for jTool in jList:
                    tool = __MakeToolFromDict(jTool, jsonDir)
                    tools[tool.name] = tool

    for tool in tools.values():
        tool.Verify()
        tool.Normalize()
        tool.Install()
        tool.VerifyInstall()

    return tools


def InstallTools(tools: ToolsT) -> bool:
    tool: Tool
    success: bool = True
    for tool in tools.values():
        if not tool.Install():
            success = False
    return success
