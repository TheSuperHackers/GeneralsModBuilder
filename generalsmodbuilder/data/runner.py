import os.path
import shlex
from dataclasses import dataclass
from generalsmodbuilder.build.common import ParamsToArgs
from generalsmodbuilder.data.common import (
    FinalizeParsedData, ParamsT, ParsedData, VerifyFormatVersion, VerifyParamsType)
from generalsmodbuilder.util import JsonNode, JsonFile
from generalsmodbuilder import util


LATEST_RUNNER_VERSION = 1
LATEST_USER_RUNNER_VERSION = 1

RUNNER_KEYS = {
    "version",
    "gameExeFile",
    "gameExeArgs",
    "relevantGameDataFileTypes",
    "regularGameDataFiles",
    "gameLanguageRegKey",
    "gameInstallPath",
    "gameInstallRegKey",
    "gameInstall2RegKey",
    "tuczhGameInstallRegKey",
}

USER_RUNNER_KEYS = {
    "version",
    "gameInstallPath",
    "gameExeFile",
    "gameExeArgs",
}


@dataclass(init=False)
class JsonRunner(ParsedData):
    """
    What the configuration files say about running the game. The installation directory is
    one of the candidates and the game data files are relative to it.
    """
    absGameInstallDirCandidates: list[str]
    relGameExeFile: str
    gameExeArgs: ParamsT
    relevantGameDataFileTypes: list[str]
    relRegularGameDataFiles: list[str]
    gameLanguageRegKey: str

    def __init__(self):
        self.absGameInstallDirCandidates = list[str]()
        self.relGameExeFile = ""
        self.gameExeArgs = ParamsT()
        self.relevantGameDataFileTypes = list[str]()
        self.relRegularGameDataFiles = list[str]()
        self.gameLanguageRegKey = ""

    def VerifyTypes(self) -> None:
        VerifyParamsType(self.gameExeArgs, "runner.gameExeArgs")


@dataclass
class UserRunner(ParsedData):
    """
    Game launch settings that one user set for their own machine.
    """
    absGameInstallDir: str = ""
    relGameExeFile: str = ""
    gameExeArgs: list[str] = None

    def VerifyTypes(self) -> None:
        util.VerifyType(self.absGameInstallDir, str, "userRunner.gameInstallPath")
        util.VerifyType(self.relGameExeFile, str, "userRunner.gameExeFile")
        if self.gameExeArgs != None:
            util.VerifyType(self.gameExeArgs, list, "userRunner.gameExeArgs")
            for i, arg in enumerate(self.gameExeArgs):
                util.VerifyType(arg, str, f"userRunner.gameExeArgs[{i}]")

    def Normalize(self) -> None:
        if self.absGameInstallDir:
            self.absGameInstallDir = os.path.normpath(self.absGameInstallDir)
        if self.relGameExeFile:
            self.relGameExeFile = os.path.normpath(self.relGameExeFile)


@dataclass(init=False)
class Runner(ParsedData):
    absGameInstallDir: str
    # Every directory that was considered for absGameInstallDir, so that a failure can
    # tell the user where the game was looked for.
    absGameInstallDirCandidates: list[str]
    relGameExeFile: str
    gameExeArgs: list[str]
    relevantGameDataFileTypes: list[str]
    # This list says which game data files are allowed to be present, not which ones are required.
    absRegularGameDataFiles: list[str]
    gameLanguageRegKey: str

    def __init__(self):
        self.absGameInstallDir = ""
        self.absGameInstallDirCandidates = list[str]()
        self.relGameExeFile = ""
        self.gameExeArgs = list[str]()
        self.relevantGameDataFileTypes = list[str]()
        self.absRegularGameDataFiles = list[str]()
        self.gameLanguageRegKey = ""

    def AbsGameExeFile(self) -> str:
        return os.path.join(self.absGameInstallDir, self.relGameExeFile)

    def Normalize(self) -> None:
        if self.absGameInstallDir:
            self.absGameInstallDir = os.path.normpath(self.absGameInstallDir)
        if self.relGameExeFile:
            self.relGameExeFile = os.path.normpath(self.relGameExeFile)
        for i, file in enumerate(self.absRegularGameDataFiles):
            self.absRegularGameDataFiles[i] = os.path.normpath(file)

    def ResolveWildcards(self) -> None:
        self.absRegularGameDataFiles = util.ResolveFileWildcards(
            self.absRegularGameDataFiles, filesMustExist=False)

    def VerifyValues(self) -> None:
        util.Verify(bool(self.relGameExeFile),
                    "runner.gameExeFile is not set by any configuration file or user setting, but "
                    "is required to locate the game installation directory")
        if not self.absGameInstallDir:
            raise AssertionError(self.__MakeInstallDirNotFoundMessage())
        util.Verify(os.path.isdir(self.absGameInstallDir),
                    f"runner game installation directory '{self.absGameInstallDir}' is not a valid path")
        util.Verify(os.path.isfile(self.AbsGameExeFile()),
                    f"runner game executable '{self.AbsGameExeFile()}' is not a valid file")

    def __MakeInstallDirNotFoundMessage(self) -> str:
        searched: str = "".join(f"\n  {candidate}" for candidate in reversed(self.absGameInstallDirCandidates))
        if not searched:
            searched = "\n  nothing, because none of those keys named a directory"
        return (f"runner game installation directory containing '{self.relGameExeFile}' was not found. "
                f"Searched:{searched}")


def SplitGameExeArgs(text: str) -> list[str]:
    """
    Splits a command line that a user wrote into the arguments the game is launched with.
    Posix mode is not used because it eats the backslashes of an unquoted windows path.
    """
    args = list[str]()

    for arg in shlex.split(text, posix=False):
        if len(arg) >= 2 and arg.startswith('"') and arg.endswith('"'):
            arg = arg[1:-1]
        if arg:
            args.append(arg)

    return args


def JoinGameExeArgs(args: list[str]) -> str:
    """
    Writes an argument list back as the command line a user would type for it.
    """
    return " ".join(f'"{arg}"' if " " in arg else arg for arg in args)


def __AddRegKeyInstallDir(
        absGameInstallDirs: list[str],
        node: JsonNode,
        key: str,
        relSubDir: str = "") -> None:
    """
    Adds the installation directory that a registry key names, when that key exists and
    holds a path. A registry value can also be a number, which is not a path.
    """
    regKey: str = node.GetOptional(key, str)
    if not regKey:
        return

    keyValue = util.GetRegKeyValue(regKey)
    if isinstance(keyValue, str) and keyValue:
        absGameInstallDirs.append(os.path.join(keyValue, relSubDir) if relSubDir else keyValue)


def MakeJsonRunnerFromJsons(jsonFiles: list[JsonFile]) -> JsonRunner:
    jsonRunner = JsonRunner()
    absGameInstallDirs: list[str] = jsonRunner.absGameInstallDirCandidates

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsFileDir(jsonFile.path)
        root = util.JsonNode(jsonFile.path, jsonFile.data)

        if node := root.SubOptional("runner"):
            node.VerifyKnownKeys(RUNNER_KEYS)
            VerifyFormatVersion(node, LATEST_RUNNER_VERSION)

            jsonRunner.relGameExeFile = node.GetOptional("gameExeFile", str, jsonRunner.relGameExeFile)
            jsonRunner.gameExeArgs = node.GetOptional("gameExeArgs", dict, jsonRunner.gameExeArgs)
            jsonRunner.relevantGameDataFileTypes = node.GetOptional(
                "relevantGameDataFileTypes", list, jsonRunner.relevantGameDataFileTypes, elementType=str)
            jsonRunner.relRegularGameDataFiles = node.GetOptional(
                "regularGameDataFiles", list, jsonRunner.relRegularGameDataFiles, elementType=str)
            jsonRunner.gameLanguageRegKey = node.GetOptional("gameLanguageRegKey", str, jsonRunner.gameLanguageRegKey)

            # The candidates are searched in reverse below, so the last one added wins.
            __AddRegKeyInstallDir(absGameInstallDirs, node, "tuczhGameInstallRegKey",
                                  relSubDir="Command and Conquer Generals Zero Hour")
            __AddRegKeyInstallDir(absGameInstallDirs, node, "gameInstall2RegKey")
            __AddRegKeyInstallDir(absGameInstallDirs, node, "gameInstallRegKey")

            if gameInstallDir := node.GetOptional("gameInstallPath", str):
                absGameInstallDirs.append(os.path.join(jsonDir, gameInstallDir))

    FinalizeParsedData(jsonRunner)
    return jsonRunner


def MakeUserRunnerFromJson(jsonFile: JsonFile) -> UserRunner:
    userRunner = UserRunner()
    root = util.JsonNode(jsonFile.path, jsonFile.data)

    if node := root.SubOptional("userRunner"):
        node.VerifyKnownKeys(USER_RUNNER_KEYS)
        VerifyFormatVersion(node, LATEST_USER_RUNNER_VERSION)

        userRunner.absGameInstallDir = node.GetOptional("gameInstallPath", str, "")
        userRunner.relGameExeFile = node.GetOptional("gameExeFile", str, "")

        gameExeArgs: str = node.GetOptional("gameExeArgs", str)
        if gameExeArgs != None:
            userRunner.gameExeArgs = SplitGameExeArgs(gameExeArgs)

    return userRunner


def MakeRunner(jsonRunner: JsonRunner, userRunner: UserRunner = None) -> Runner:
    if userRunner == None:
        userRunner = UserRunner()

    FinalizeParsedData(userRunner)

    runner = Runner()

    if userRunner.relGameExeFile:
        runner.relGameExeFile = userRunner.relGameExeFile
    else:
        runner.relGameExeFile = jsonRunner.relGameExeFile

    runner.relevantGameDataFileTypes = jsonRunner.relevantGameDataFileTypes
    runner.gameLanguageRegKey = jsonRunner.gameLanguageRegKey

    if userRunner.gameExeArgs != None:
        runner.gameExeArgs = list(userRunner.gameExeArgs)
    else:
        runner.gameExeArgs = ParamsToArgs(jsonRunner.gameExeArgs)

    if userRunner.absGameInstallDir:
        # A directory that the user named is the only one searched, so that it is never
        # passed over in silence in favour of a registry key.
        runner.absGameInstallDirCandidates = [userRunner.absGameInstallDir]
    else:
        runner.absGameInstallDirCandidates = jsonRunner.absGameInstallDirCandidates

    if runner.relGameExeFile:
        for absGameInstallDir in reversed(runner.absGameInstallDirCandidates):
            absGameExeFile: str = os.path.join(absGameInstallDir, runner.relGameExeFile)
            if os.path.isfile(absGameExeFile):
                runner.absGameInstallDir = absGameInstallDir
                break

    # The game data files are listed relative to the installation directory. They are
    # joined before the phases run, so that Normalize sees the paths they end up being.
    runner.absRegularGameDataFiles = [
        os.path.join(runner.absGameInstallDir, file) for file in jsonRunner.relRegularGameDataFiles]

    FinalizeParsedData(runner)
    return runner
