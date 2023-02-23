import os
import os.path
import urllib.request
import http.client
import zipfile
from logging import warning
from dataclasses import dataclass
from generalsmodbuilder.util import JsonFile
from generalsmodbuilder import util


@dataclass(init=False)
class ToolFile:
    url: str
    absTarget: str
    absExtractDir: str
    md5: str
    sha256: str
    size: str
    runnable: bool
    autoDeleteAfterInstall: bool
    skipIfRunnableExists: bool
    isInstalledCached: bool

    def __init__(self):
        self.url = ""
        self.absTarget = None
        self.absExtractDir = ""
        self.md5 = ""
        self.sha256 = ""
        self.size = -1
        self.runnable = False
        self.autoDeleteAfterInstall = False
        self.skipIfRunnableExists = False
        self.isInstalledCached = False

    def Normalize(self) -> None:
        if self.absTarget:
            self.absTarget = os.path.normpath(self.absTarget)
        if self.absExtractDir:
            self.absExtractDir = os.path.normpath(self.absExtractDir)

    def VerifyTypes(self) -> None:
        util.VerifyType(self.url, str, "ToolFile.url")
        util.VerifyType(self.absTarget, str, "ToolFile.absTarget")
        util.VerifyType(self.absExtractDir, str, "ToolFile.absExtractDir")
        util.VerifyType(self.md5, str, "ToolFile.md5")
        util.VerifyType(self.sha256, str, "ToolFile.sha256")
        util.VerifyType(self.size, int, "ToolFile.size")
        util.VerifyType(self.runnable, bool, "ToolFile.runnable")
        util.VerifyType(self.autoDeleteAfterInstall, bool, "ToolFile.autoDeleteAfterInstall")
        util.VerifyType(self.skipIfRunnableExists, bool, "ToolFile.skipIfRunnableExists")

    def VerifyValues(self) -> None:
        # TODO Verify url format?
        util.Verify(util.IsValidPathName(self.absTarget), f"ToolFile.absTarget '{self.absTarget}' is not a valid file name")
        if self.absExtractDir:
            util.Verify(util.IsValidPathName(self.absExtractDir), f"ToolFile.absExtractDir '{self.absExtractDir}' is not a valid file name")

    def VerifyInstall(self) -> None:
        util.Verify(os.path.isfile(self.absTarget), f"ToolFile.absTarget file '{self.absTarget}' does not exist")
        if self.md5:
            actual: str = util.GetFileMd5(self.absTarget)
            util.Verify(self.md5 == actual, f"ToolFile.md5 '{self.md5}' does not match md5 '{actual}' of target file '{self.absTarget}'")
        if self.sha256:
            actual: str = util.GetFileSha256(self.absTarget)
            util.Verify(self.md5 == actual, f"ToolFile.sha256 '{self.md5}' does not match sha256 '{actual}' of target file '{self.absTarget}'")
        if self.size >= 0:
            actual: int = util.GetFileSize(self.absTarget)
            util.Verify(self.size == actual, f"ToolFile.size '{self.size}' does not match size '{actual}' of target file '{self.absTarget}'")

    def HashOk(self) -> bool:
        md5Ok = (not self.md5 or self.md5 == util.GetFileMd5(self.absTarget))
        shaOk = (not self.sha256 or self.sha256 == util.GetFileSha256(self.absTarget))
        return md5Ok and shaOk

    def SizeOk(self) -> bool:
        return self.size < 0 or self.size == util.GetFileSize(self.absTarget)

    def IsInstalled(self) -> bool:
        if self.isInstalledCached:
            return True
        self.isInstalledCached = os.path.isfile(self.absTarget) and self.SizeOk() and self.HashOk()
        return self.isInstalledCached

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

            if success:
                if self.absExtractDir:
                    os.makedirs(self.absExtractDir, exist_ok=True)

                    if util.HasFileExt(self.absTarget, "zip"):
                        with zipfile.ZipFile(self.absTarget, "r") as zfile:
                            zfile.extractall(self.absExtractDir)

                if self.autoDeleteAfterInstall:
                    util.DeleteFile(self.absTarget)

        return success


@dataclass(init=False)
class Tool:
    name: str
    files: list[ToolFile]
    version: float

    def __init__(self):
        self.name = None
        self.files = list[ToolFile]()
        self.version = 0.0

    def Normalize(self) -> None:
        for file in self.files:
            file.Normalize()

    def VerifyTypes(self) -> None:
        util.VerifyType(self.name, str, "Tool.name")
        util.VerifyType(self.version, float, "Tool.version")
        util.VerifyType(self.files, list, "Tool.files")
        for file in self.files:
            file.VerifyTypes()

    def VerifyValues(self) -> None:
        util.Verify(self.GetExecutable() != None, "Tool.files contains no runnable file")
        for file in self.files:
            file.VerifyValues()

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
        runnablesInstalled: int = 0

        for file in self.files:
            if file.runnable and file.IsInstalled():
                runnablesInstalled += 1

        for file in self.files:
            if file.skipIfRunnableExists and runnablesInstalled > 0:
                continue
            installed: bool = file.Install()
            if installed:
                print(f"Tool '{self.name}' file '{file.absTarget}' is installed")
                if file.absExtractDir:
                    print(f"File '{file.absTarget}' is extracted to '{file.absExtractDir}'")
            else:
                warning(f"Tool '{self.name}' file '{file.absTarget}' was not installed")
                success = False

        return success


ToolsT = dict[str, Tool]


def __MakeToolFileFromDict(jFile: dict, jsonDir: str) -> ToolFile:
    toolFile = ToolFile()
    toolFile.url = jFile.get("url", toolFile.url)
    toolFile.absTarget = util.JoinPathIfValid(None, jsonDir, jFile.get("target"))
    toolFile.absExtractDir = util.JoinPathIfValid(toolFile.absExtractDir, jsonDir, jFile.get("extractDir"))
    toolFile.md5 = jFile.get("md5", toolFile.md5)
    toolFile.sha256 = jFile.get("sha256", toolFile.sha256)
    toolFile.size = jFile.get("size", toolFile.size)
    toolFile.runnable = jFile.get("runnable", toolFile.runnable)
    toolFile.autoDeleteAfterInstall = jFile.get("autoDeleteAfterInstall", toolFile.autoDeleteAfterInstall)
    toolFile.skipIfRunnableExists = jFile.get("skipIfRunnableExists", toolFile.skipIfRunnableExists)
    return toolFile


def __MakeToolFromDict(jTool: dict, jsonDir: str) -> Tool:
    tool = Tool()
    tool.name = jTool.get("name")
    tool.version = jTool.get("version", tool.version)

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
        tool.VerifyTypes()
        tool.Normalize()
        tool.VerifyValues()
        tool.Install()

    return tools


def InstallTools(tools: ToolsT) -> bool:
    tool: Tool
    success: bool = True
    for tool in tools.values():
        if not tool.Install():
            success = False
    return success
