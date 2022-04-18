import os.path
import util
import urllib.request
import http.client
from util import JsonFile
from logging import warning
from dataclasses import dataclass


@dataclass(init=False)
class ToolFile:
    url: str
    absTarget: str
    md5: str
    sha256: str
    size: str
    runnable: bool

    def __init__(self):
        self.md5 = ""
        self.sha256 = ""
        self.size = -1
        self.runnable = False

    def Normalize(self) -> None:
        self.absTarget = util.NormalizePath(self.absTarget)

    def VerifyTypes(self) -> None:
        util.RelAssertType(self.url, str, "ToolFile.url")
        util.RelAssertType(self.absTarget, str, "ToolFile.absTarget")
        util.RelAssertType(self.md5, str, "ToolFile.md5")
        util.RelAssertType(self.sha256, str, "ToolFile.sha256")
        util.RelAssertType(self.size, int, "ToolFile.size")
        util.RelAssertType(self.runnable, bool, "ToolFile.runnable")

    def VerifyInstall(self) -> None:
        util.RelAssert(os.path.isfile(self.absTarget), f"ToolFile.absTarget file '{self.absTarget}' does not exist")
        if self.md5:
            actual: str = util.GetFileMd5(self.absTarget)
            util.RelAssert(self.md5 == actual, f"ToolFile.md5 '{self.md5}' does not match md5 '{actual}' of target file '{self.absTarget}'")
        if self.sha256:
            actual: str = util.GetFileSha256(self.absTarget)
            util.RelAssert(self.md5 == actual, f"ToolFile.sha256 '{self.md5}' does not match sha256 '{actual}' of target file '{self.absTarget}'")
        if self.size >= 0:
            actual: int = util.GetFileSize(self.absTarget)
            util.RelAssert(self.size == actual, f"ToolFile.size '{self.size}' does not match size '{actual}' of target file '{self.absTarget}'")

    def HashOk(self) -> bool:
        md5Ok = (not self.md5 or self.md5 == util.GetFileMd5(self.absTarget))
        shaOk = (not self.sha256 or self.sha256 == util.GetFileSha256(self.absTarget))
        return md5Ok and shaOk
    
    def SizeOk(self) -> bool:
        return self.size < 0 or self.size == util.GetFileSize(self.absTarget)

    def IsInstalled(self) -> bool:
        return os.path.isfile(self.absTarget) and self.SizeOk() and self.HashOk()

    def Install(self) -> bool:
        success = self.IsInstalled()
        if not success:
            if self.url:
                response: http.client.HTTPResponse = urllib.request.urlopen(self.url)
                if response.code == 200:
                    sizeOk: bool = self.size < 0

                    if not sizeOk:
                        len: str = response.headers['Content-Length']
                        sizeOk = len and int(len) == self.size

                    if sizeOk:
                        data: bytes = response.read()
                        util.MakeDirsForFile(self.absTarget)
                        with open(self.absTarget, 'wb') as wfile:
                            wfile.write(data)
                        success = self.IsInstalled()

        return success


@dataclass(init=False)
class Tool:
    name: str
    files: list[ToolFile]
    version: float

    def __init__(self):
        self.version = 0.0

    def Normalize(self) -> None:
        for file in self.files:
            file.Normalize()

    def Verify(self) -> None:
        util.RelAssertType(self.name, str, "Tool.name")
        util.RelAssertType(self.version, float, "Tool.version")
        util.RelAssertType(self.files, list, "Tool.files")
        for file in self.files:
            file.VerifyTypes()
        util.RelAssert(self.GetExecutable() != None, "Tool.files contains no runnable file")

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
    toolFile.absTarget = util.JoinPathIfValid(None, jsonDir, jFile.get("target"))
    toolFile.md5 = util.GetSecondIfValid(toolFile.md5, jFile.get("md5"))
    toolFile.sha256 = util.GetSecondIfValid(toolFile.sha256, jFile.get("sha256"))
    toolFile.size = util.GetSecondIfValid(toolFile.size, jFile.get("size"))
    toolFile.runnable = util.GetSecondIfValid(toolFile.runnable, jFile.get("runnable"))
    return toolFile


def __MakeToolFromDict(jTool: dict, jsonDir: str) -> Tool:
    tool = Tool()
    tool.name = jTool.get("name")
    tool.files = list()
    tool.version = util.GetSecondIfValid(tool.version, jTool.get("version"))

    jFiles: dict = jTool.get("files")
    if jFiles:
        jFile: dict
        for jFile in jFiles:
            toolFile = __MakeToolFileFromDict(jFile, jsonDir)
            tool.files.append(toolFile)

    return tool


def MakeToolsFromJsons(jsonFiles: list[JsonFile]) -> ToolsT:
    tools = ToolsT()
    tool: Tool

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsSmartFileDir(jsonFile.path)
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

    return tools


def InstallTools(tools: ToolsT) -> bool:
    tool: Tool
    success: bool = True
    for tool in tools.values():
        if not tool.Install():
            success = False
    return success
