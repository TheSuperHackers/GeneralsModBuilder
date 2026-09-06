import certifi
import http.client
import os
import os.path
import ssl
import urllib.request
import zipfile
from enum import Enum, auto
from dataclasses import dataclass
from generalsmodbuilder import util
from generalsmodbuilder.util import JsonContext, JsonFile
from generalsmodbuilder.data.common import (
    FinalizeParsedData, ParamsT, ParsedData, VerifyFormatVersion, VerifyParamsType)
from generalsmodbuilder.build.common import ParamsToArgs


LATEST_TOOLS_VERSION = 2

TOOLS_KEYS = {"version", "aliases", "list"}
# info is not consumed. It describes a tool for whoever reads the configuration.
TOOL_KEYS = {"name", "version", "info", "enabled", "files"}
TOOL_FILE_KEYS = {
    "url", "target", "extractDir", "md5", "sha256", "size", "callList", "runnable",
    "autoDeleteAfterInstall", "skipIfRunnableExists",
}
TOOL_CALL_KEYS = {"call", "callArgs"}


class InstallResultCode(Enum):
    Ok = auto()
    NoInstall = auto()
    SizeMismatch = auto()
    HashMismatch = auto()
    HttpError = auto()
    CallError = auto()


@dataclass
class InstallResult:
    code: InstallResultCode
    httpCode: int

    def Ok(self) -> bool:
        return self.code == InstallResultCode.Ok


@dataclass(init=False)
class ToolCallInstruction(ParsedData):
    absCall: str
    callArgs: ParamsT


    def __init__(self):
        self.absCall = ""
        self.callArgs = ParamsT()


    def Normalize(self) -> None:
        self.absCall = os.path.normpath(self.absCall)


    def VerifyTypes(self) -> None:
        VerifyParamsType(self.callArgs, "tools.list.files.callList.callArgs")


    def VerifyValues(self) -> None:
        util.Verify(util.IsValidPathName(self.absCall), f"tools.list.files.callList.call '{self.absCall}' is not a valid file name")


@dataclass(init=False)
class ToolFile(ParsedData):
    url: str
    absTarget: str
    absExtractDir: str
    md5: str
    sha256: str
    size: int
    callInstructions: list[ToolCallInstruction]
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
        self.callInstructions = list[ToolCallInstruction]()
        self.runnable = False
        self.autoDeleteAfterInstall = False
        self.skipIfRunnableExists = False
        self.isInstalledCached = False


    def Normalize(self) -> None:
        if self.absTarget:
            self.absTarget = os.path.normpath(self.absTarget)
        if self.absExtractDir:
            self.absExtractDir = os.path.normpath(self.absExtractDir)
        for instruction in self.callInstructions:
            instruction.Normalize()


    def VerifyTypes(self) -> None:
        for instruction in self.callInstructions:
            instruction.VerifyTypes()


    def VerifyValues(self) -> None:
        # TODO Verify url format?
        util.Verify(util.IsValidPathName(self.absTarget), f"tools.list.files.target '{self.absTarget}' is not a valid file name")
        if self.absExtractDir:
            util.Verify(util.IsValidPathName(self.absExtractDir), f"tools.list.files.extractDir '{self.absExtractDir}' is not a valid file name")
        for instruction in self.callInstructions:
            instruction.VerifyValues()


    def VerifyInstall(self) -> None:
        util.Verify(os.path.isfile(self.absTarget), f"tools.list.files.target file '{self.absTarget}' does not exist")
        if self.md5:
            actual: str = util.GetFileMd5(self.absTarget)
            util.Verify(self.md5 == actual, f"ToolFile.md5 '{self.md5}' does not match md5 '{actual}' of target file '{self.absTarget}'")
        if self.sha256:
            actual: str = util.GetFileSha256(self.absTarget)
            util.Verify(self.sha256 == actual, f"ToolFile.sha256 '{self.sha256}' does not match sha256 '{actual}' of target file '{self.absTarget}'")
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


    def Install(self) -> InstallResult:
        result = InstallResult(InstallResultCode.Ok, 0)

        if not self.IsInstalled():
            result = InstallResult(InstallResultCode.NoInstall, 0)

        if not result.Ok():
            if self.url:
                print(f"Downloading from '{self.url}' ...")
                response: http.client.HTTPResponse
                cafile: str = certifi.where()
                print(f"Using cafile '{cafile}'")
                context: ssl.SSLContext = ssl.create_default_context(cafile=cafile)
                with urllib.request.urlopen(self.url, context=context) as response:
                    if response.code == 200:
                        sizeOk: bool = self.size < 0
                        len: str = response.headers['Content-Length']

                        if not sizeOk:
                            sizeOk = len and int(len) == self.size

                        if sizeOk:
                            size = int(len) if len else self.size
                            print(f"Downloading {int(size / 1024)} kb to '{self.absTarget}' ...")
                            util.MakeDirsForFile(self.absTarget)
                            ToolFile.DownloadToFile(response, self.absTarget)
                            if self.IsInstalled():
                                result = InstallResult(InstallResultCode.Ok, response.code)
                            elif not self.SizeOk():
                                result = InstallResult(InstallResultCode.SizeMismatch, response.code)
                            elif not self.HashOk():
                                result = InstallResult(InstallResultCode.HashMismatch, response.code)
                        else:
                            result = InstallResult(InstallResultCode.SizeMismatch, response.code)
                    else:
                        result = InstallResult(InstallResultCode.HttpError, response.code)

        if result.Ok():
            if self.absExtractDir:
                os.makedirs(self.absExtractDir, exist_ok=True)
                if util.HasFileExt(self.absTarget, "zip"):
                    with zipfile.ZipFile(self.absTarget, "r") as zfile:
                        zfile.extractall(self.absExtractDir)

        if result.Ok():
            instruction: ToolCallInstruction
            for instruction in self.callInstructions:
                args: list[str] = [instruction.absCall]
                args.extend(ParamsToArgs(instruction.callArgs))
                if not util.RunProcess(args):
                    result = InstallResult(InstallResultCode.CallError, 0)

        if result.Ok():
            if self.autoDeleteAfterInstall:
                util.DeleteFile(self.absTarget)

        return result


    @staticmethod
    def DownloadToFile(response: http.client.HTTPResponse, absTarget: str) -> None:
        BUF_SIZE = 1024 * 64
        with open(absTarget, 'wb', buffering=BUF_SIZE) as wfile:
            fullbuf = bytearray(BUF_SIZE)
            while True:
                readsize: int = response.readinto(fullbuf)
                if readsize == 0:
                    break
                if readsize != BUF_SIZE:
                    readbuf: bytearray = fullbuf[:readsize]
                    wfile.write(readbuf)
                    break
                else:
                    wfile.write(fullbuf)


@dataclass(init=False)
class Tool(ParsedData):
    name: str
    files: list[ToolFile]
    versionStr: str


    def __init__(self):
        self.name = None
        self.files = list[ToolFile]()
        self.versionStr = ""


    def Normalize(self) -> None:
        for file in self.files:
            file.Normalize()


    def VerifyTypes(self) -> None:
        for file in self.files:
            file.VerifyTypes()


    def VerifyValues(self) -> None:
        runnableCount: int = sum(1 for file in self.files if file.runnable)
        util.Verify(runnableCount > 0, f"tools.list '{self.name}' has no runnable file")
        util.Verify(runnableCount < 2, f"tools.list '{self.name}' marks {runnableCount} files as runnable, "
                                       f"but only one of them can be the executable")
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


    def Install(self) -> None:
        file: ToolFile
        runnablesInstalled: int = 0

        for file in self.files:
            if file.runnable and file.IsInstalled():
                runnablesInstalled += 1

        for file in self.files:
            if file.skipIfRunnableExists and runnablesInstalled > 0:
                continue
            result: InstallResult = file.Install()
            if result.Ok():
                print(f"Tool '{self.name} {self.versionStr}' file '{file.absTarget}' is installed")
                if file.absExtractDir:
                    print(f"File '{file.absTarget}' is extracted to '{file.absExtractDir}'")
            else:
                msg: str = f"Tool '{self.name} {self.versionStr}' file '{file.absTarget}' was not installed"
                if result.code == InstallResultCode.NoInstall:
                    msg += (" - No url is configured to download it from, and the file is missing"
                            " or does not match its configured size or hash")
                elif result.code == InstallResultCode.SizeMismatch:
                    msg += " - Size mismatch was detected"
                elif result.code == InstallResultCode.HashMismatch:
                    msg += " - Hash mismatch was detected"
                elif result.code == InstallResultCode.HttpError:
                    msg += f" - Http returned error code {result.httpCode}"
                elif result.code == InstallResultCode.CallError:
                    msg += " - Error on call instruction"
                raise RuntimeError(msg)




ToolsT = dict[str, Tool]


def __ProcessAliases(thing: str | ParamsT, aliases: dict) -> str | ParamsT:
    if not isinstance(aliases, dict):
        return thing

    def ReplaceAliases(value: str) -> str:
        for aliasKey, aliasVal in aliases.items():
            value = value.replace(aliasKey, aliasVal)
        return value

    if isinstance(thing, str):
        return ReplaceAliases(thing)

    if isinstance(thing, dict):
        # Call arguments are not all strings, and a new dict is built so that the
        # parsed json data of the caller is left untouched.
        return {key: ReplaceAliases(value) if isinstance(value, str) else value
                for key, value in thing.items()}

    return thing


def __MakeToolFileFromDict(ctx: JsonContext, jFile: dict, rootDir: str, aliases: dict) -> ToolFile:
    toolFile = ToolFile()
    ctx.VerifyKnownKeys(jFile, TOOL_FILE_KEYS)

    toolFile.url = ctx.GetOptional(jFile, "url", str, toolFile.url)
    toolFile.md5 = ctx.GetOptional(jFile, "md5", str, toolFile.md5)
    toolFile.sha256 = ctx.GetOptional(jFile, "sha256", str, toolFile.sha256)
    toolFile.size = ctx.GetOptional(jFile, "size", int, toolFile.size)
    toolFile.runnable = ctx.GetOptional(jFile, "runnable", bool, toolFile.runnable)
    toolFile.autoDeleteAfterInstall = ctx.GetOptional(jFile, "autoDeleteAfterInstall", bool, toolFile.autoDeleteAfterInstall)
    toolFile.skipIfRunnableExists = ctx.GetOptional(jFile, "skipIfRunnableExists", bool, toolFile.skipIfRunnableExists)

    jTarget: str = ctx.GetMandatory(jFile, "target", str)
    ctx.Verify(bool(jTarget), "must not be empty", key="target")

    # Aliases are replaced before the path is joined to the root directory, so that an
    # alias that stands for an absolute path yields that path instead of being appended
    # to the root directory.
    toolFile.absTarget = __ProcessAliases(jTarget, aliases)
    toolFile.absTarget = util.JoinPathIfValid(None, rootDir, toolFile.absTarget)
    toolFile.absExtractDir = __ProcessAliases(ctx.GetOptional(jFile, "extractDir", str, toolFile.absExtractDir), aliases)
    toolFile.absExtractDir = util.JoinPathIfValid(toolFile.absExtractDir, rootDir, toolFile.absExtractDir)

    jCallList: list = ctx.GetOptional(jFile, "callList", list, elementType=dict)
    if jCallList is not None:
        toolFile.callInstructions.clear()
        jCall: dict
        for index, jCall in enumerate(jCallList):
            callCtx: JsonContext = ctx.Sub("callList").At(index)
            callCtx.VerifyKnownKeys(jCall, TOOL_CALL_KEYS)
            instruction = ToolCallInstruction()
            jCallPath: str = callCtx.GetMandatory(jCall, "call", str)
            callCtx.Verify(bool(jCallPath), "must not be empty", key="call")
            instruction.absCall = __ProcessAliases(jCallPath, aliases)
            instruction.absCall = util.JoinPathIfValid(instruction.absCall, rootDir, instruction.absCall)
            instruction.callArgs = callCtx.GetOptional(jCall, "callArgs", dict, instruction.callArgs)
            instruction.callArgs = __ProcessAliases(instruction.callArgs, aliases)
            toolFile.callInstructions.append(instruction)

    return toolFile


def __MakeToolFromDict(ctx: JsonContext, jTool: dict, rootDir: str, jVersion: int, aliases: dict) -> Tool:
    tool = Tool()
    ctx.VerifyKnownKeys(jTool, TOOL_KEYS)
    tool.name = ctx.GetMandatory(jTool, "name", str)
    if jVersion <= 1:
        # Version 1 wrote the tool version as a number rather than as a string.
        jToolVersion = ctx.GetOptional(jTool, "version", (int, float))
        if jToolVersion != None:
            tool.versionStr = str(jToolVersion)
    else:
        tool.versionStr = ctx.GetOptional(jTool, "version", str, tool.versionStr)

    jFiles: list = ctx.GetOptional(jTool, "files", list, default=[], elementType=dict)
    jFile: dict
    for index, jFile in enumerate(jFiles):
        tool.files.append(__MakeToolFileFromDict(ctx.Sub("files").At(index), jFile, rootDir, aliases))

    return tool


def MakeToolsFromJsons(jsonFiles: list[JsonFile], rootDir: str=None) -> ToolsT:
    tools = ToolsT()
    tool: Tool

    for jsonFile in jsonFiles:
        root = util.JsonContext(jsonFile.path)
        jTools: dict = root.GetOptional(jsonFile.data, "tools", dict)
        if jTools:
            ctx = root.Sub("tools")
            ctx.VerifyKnownKeys(jTools, TOOLS_KEYS)
            jVersion: int = VerifyFormatVersion(ctx, jTools, LATEST_TOOLS_VERSION)
            jsonDir: str = util.GetAbsFileDir(jsonFile.path)
            # Without an override, every tools json roots its own tools in its own
            # directory. The root of one file must not carry over to the next one.
            fileRootDir: str = rootDir if rootDir else jsonDir
            aliases: dict = {
                "{THIS_DIR}": jsonDir,
                "{ROOT_DIR}": fileRootDir
            }
            if jAliases := ctx.GetOptional(jTools, "aliases", dict, elementType=str):
                aliases.update(jAliases)
            jList: list = ctx.GetOptional(jTools, "list", list, default=[], elementType=dict)
            jTool: dict
            for index, jTool in enumerate(jList):
                toolCtx: JsonContext = ctx.Sub("list").At(index, jTool.get("name", ""))
                if toolCtx.GetOptional(jTool, "enabled", bool, True):
                    tool = __MakeToolFromDict(toolCtx, jTool, fileRootDir, jVersion, aliases)
                    tools[tool.name] = tool

    for tool in tools.values():
        FinalizeParsedData(tool)

    return tools


def InstallTools(tools: ToolsT) -> None:
    tool: Tool
    for tool in tools.values():
        tool.Install()


def VerifyToolIsInstalled(tools: ToolsT, name: str, reason: str = "") -> None:
    """
    Fails when the named tool is not usable. The reason tells what the tool is required for.
    """
    tool: Tool = tools.get(name)
    util.Verify(tool != None, f"Tool '{name}' is required for {reason}, but is not defined or is disabled")
    # Tool.VerifyValues guarantees that every tool has a runnable file, so the executable is never None here.
    exe: str = tool.GetExecutable()
    util.Verify(os.path.isfile(exe), f"Tool '{name}' is required for {reason}, but its executable '{exe}' does not exist")
