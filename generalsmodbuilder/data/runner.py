import os.path
from dataclasses import dataclass
from generalsmodbuilder.data.common import (
    FinalizeParsedData, ParamsT, ParsedData, VerifyFormatVersion, VerifyParamsType)
from generalsmodbuilder.util import JsonNode, JsonFile
from generalsmodbuilder import util


LATEST_RUNNER_VERSION = 1

RUNNER_KEYS = {
    "version", "gameExeFile", "gameExeArgs", "relevantGameDataFileTypes", "regularGameDataFiles",
    "gameLanguageRegKey", "gameInstallPath", "gameInstallRegKey", "gameInstall2RegKey",
    "tuczhGameInstallRegKey",
}


@dataclass(init=False)
class Runner(ParsedData):
    absGameInstallDir: str
    # Every directory that was considered for absGameInstallDir, so that a failure can
    # tell the user where the game was looked for.
    absGameInstallDirCandidates: list[str]
    relGameExeFile: str
    gameExeArgs: ParamsT
    relevantGameDataFileTypes: list[str]
    # This list says which game data files are allowed to be present, not which ones are required.
    absRegularGameDataFiles: list[str]
    gameLanguageRegKey: str

    def __init__(self):
        self.absGameInstallDir = ""
        self.absGameInstallDirCandidates = list[str]()
        self.relGameExeFile = ""
        self.gameExeArgs = ParamsT()
        self.relevantGameDataFileTypes = list[str]()
        self.absRegularGameDataFiles = list[str]()
        self.gameLanguageRegKey = ""

    def AbsGameExeFile(self) -> str:
        return os.path.join(self.absGameInstallDir, self.relGameExeFile)

    def VerifyTypes(self) -> None:
        VerifyParamsType(self.gameExeArgs, "runner.gameExeArgs")

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
                    "runner.gameExeFile is not set by any configuration file, but is required to "
                    "locate the game installation directory")
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
                f"It is taken from runner.gameInstallPath, runner.gameInstallRegKey, "
                f"runner.gameInstall2RegKey or runner.tuczhGameInstallRegKey. Searched:{searched}")


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


def MakeRunnerFromJsons(jsonFiles: list[JsonFile]) -> Runner:
    runner = Runner()
    absGameInstallDirs: list[str] = runner.absGameInstallDirCandidates

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsFileDir(jsonFile.path)
        root = util.JsonNode(jsonFile.path, jsonFile.data)

        if node := root.SubOptional("runner"):
            node.VerifyKnownKeys(RUNNER_KEYS)
            VerifyFormatVersion(node, LATEST_RUNNER_VERSION)

            runner.relGameExeFile = node.GetOptional("gameExeFile", str, runner.relGameExeFile)
            runner.gameExeArgs = node.GetOptional("gameExeArgs", dict, runner.gameExeArgs)
            runner.relevantGameDataFileTypes = node.GetOptional(
                "relevantGameDataFileTypes", list, runner.relevantGameDataFileTypes, elementType=str)
            runner.absRegularGameDataFiles = node.GetOptional(
                "regularGameDataFiles", list, runner.absRegularGameDataFiles, elementType=str)
            runner.gameLanguageRegKey = node.GetOptional("gameLanguageRegKey", str, runner.gameLanguageRegKey)

            # The candidates are searched in reverse below, so the last one added wins.
            __AddRegKeyInstallDir(absGameInstallDirs, node, "tuczhGameInstallRegKey",
                                  relSubDir="Command and Conquer Generals Zero Hour")
            __AddRegKeyInstallDir(absGameInstallDirs, node, "gameInstall2RegKey")
            __AddRegKeyInstallDir(absGameInstallDirs, node, "gameInstallRegKey")

            if gameInstallDir := node.GetOptional("gameInstallPath", str):
                absGameInstallDirs.append(os.path.join(jsonDir, gameInstallDir))

    if runner.relGameExeFile:
        for absGameInstallDir in reversed(absGameInstallDirs):
            absGameExeFile: str = os.path.join(absGameInstallDir, runner.relGameExeFile)
            if os.path.isfile(absGameExeFile):
                runner.absGameInstallDir = absGameInstallDir
                break

    # The game data files are listed relative to the installation directory. They are
    # joined before the phases run, so that Normalize sees the paths they end up being.
    for i, file in enumerate(runner.absRegularGameDataFiles):
        runner.absRegularGameDataFiles[i] = os.path.join(runner.absGameInstallDir, file)

    FinalizeParsedData(runner)
    return runner
