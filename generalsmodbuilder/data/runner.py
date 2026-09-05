import os.path
from dataclasses import dataclass
from generalsmodbuilder.data.common import FinalizeParsedData, ParamsT, ParsedData, VerifyParamsType
from generalsmodbuilder.util import JsonContext, JsonFile
from generalsmodbuilder import util


@dataclass(init=False)
class Runner(ParsedData):
    absGameInstallDir: str
    relGameExeFile: str
    gameExeArgs: ParamsT
    relevantGameDataFileTypes: list[str]
    absRegularGameDataFiles: list[str]
    gameLanguageRegKey: str

    def __init__(self):
        self.absGameInstallDir = ""
        self.relGameExeFile = ""
        self.gameExeArgs = ParamsT()
        self.relevantGameDataFileTypes = list[str]()
        self.absRegularGameDataFiles = list[str]()
        self.gameLanguageRegKey = ""

    def AbsGameExeFile(self) -> str:
        return os.path.join(self.absGameInstallDir, self.relGameExeFile)

    def VerifyTypes(self) -> None:
        # The json values are verified where they are read. What a read cannot express
        # is the types of the values inside the arguments dict.
        VerifyParamsType(self.gameExeArgs, "runner.gameExeArgs")

    def Normalize(self) -> None:
        self.absGameInstallDir = os.path.normpath(self.absGameInstallDir)
        self.relGameExeFile = os.path.normpath(self.relGameExeFile)
        for i, file in enumerate(self.absRegularGameDataFiles):
            self.absRegularGameDataFiles[i] = os.path.normpath(file)

    def ResolveWildcards(self) -> None:
        # This list says which game data files are allowed to be present, not which ones
        # are required. Every entry of a language that is not installed matches nothing,
        # which is expected and is not reported.
        self.absRegularGameDataFiles = util.ResolveFileWildcards(
            self.absRegularGameDataFiles, filesMustExist=False)

    def VerifyValues(self) -> None:
        util.Verify(os.path.isdir(self.absGameInstallDir),
                    f"runner game installation directory '{self.absGameInstallDir}' is not a valid path")
        util.Verify(os.path.isfile(self.AbsGameExeFile()),
                    f"runner game executable '{self.AbsGameExeFile()}' is not a valid file")


def __AddRegKeyInstallDir(
        absGameInstallDirs: list[str],
        ctx: JsonContext,
        jRunner: dict,
        key: str,
        relSubDir: str = "") -> None:
    """
    Adds the installation directory that a registry key names, when that key exists and
    holds a path. A registry value can also be a number, which is not a path.
    """
    regKey: str = ctx.GetOptional(jRunner, key, str)
    if not regKey:
        return

    keyValue = util.GetRegKeyValue(regKey)
    if isinstance(keyValue, str) and keyValue:
        absGameInstallDirs.append(os.path.join(keyValue, relSubDir) if relSubDir else keyValue)


def MakeRunnerFromJsons(jsonFiles: list[JsonFile]) -> Runner:
    runner = Runner()
    absGameInstallDirs = list[str]()

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsFileDir(jsonFile.path)
        root = util.JsonContext(jsonFile.path)
        jRunner: dict = root.GetOptional(jsonFile.data, "runner", dict)

        if jRunner:
            ctx = root.Sub("runner")
            runner.relGameExeFile = ctx.GetOptional(jRunner, "gameExeFile", str, runner.relGameExeFile)
            runner.gameExeArgs = ctx.GetOptional(jRunner, "gameExeArgs", dict, runner.gameExeArgs)
            runner.relevantGameDataFileTypes = ctx.GetOptional(
                jRunner, "relevantGameDataFileTypes", list, runner.relevantGameDataFileTypes, elementType=str)
            runner.absRegularGameDataFiles = ctx.GetOptional(
                jRunner, "regularGameDataFiles", list, runner.absRegularGameDataFiles, elementType=str)
            runner.gameLanguageRegKey = ctx.GetOptional(jRunner, "gameLanguageRegKey", str, runner.gameLanguageRegKey)

            # The candidates are searched in reverse below, so the last one added wins.
            __AddRegKeyInstallDir(absGameInstallDirs, ctx, jRunner, "tuczhGameInstallRegKey",
                                  relSubDir="Command and Conquer Generals Zero Hour")
            __AddRegKeyInstallDir(absGameInstallDirs, ctx, jRunner, "gameInstall2RegKey")
            __AddRegKeyInstallDir(absGameInstallDirs, ctx, jRunner, "gameInstallRegKey")

            if gameInstallDir := ctx.GetOptional(jRunner, "gameInstallPath", str):
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
