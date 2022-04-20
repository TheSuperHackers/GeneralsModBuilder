import os.path
import util
from glob import glob
from util import JsonFile
from dataclasses import dataclass
from data.common import ParamsT, VerifyParamsType, VerifyStringListType


@dataclass(init=False)
class Runner:
    absGameInstallDir: str
    relGameExeFile: str
    gameExeArgs: ParamsT
    relevantGameDataFileTypes: list[str]
    absRegularGameDataFiles: list[str]
    gameLanguageRegKey: str

    def __init__(self):
        self.gameExeArgs = ParamsT()
        self.relevantGameDataFileTypes = list[str]()
        self.absRegularGameDataFiles = list[str]()
        self.gameLanguageRegKey = ""

    def AbsGameExeFile(self) -> str:
        return os.path.join(self.absGameInstallDir, self.relGameExeFile)

    def Normalize(self) -> None:
        self.absGameInstallDir = util.NormalizePath(self.absGameInstallDir)
        self.relGameExeFile = util.NormalizePath(self.relGameExeFile)
        for i in range(len(self.absRegularGameDataFiles)):
            self.absRegularGameDataFiles[i] = util.NormalizePath(self.absRegularGameDataFiles[i])

    def VerifyTypes(self) -> None:
        util.RelAssertType(self.absGameInstallDir, str, "Runner.absGameRootDir")
        util.RelAssertType(self.relGameExeFile, str, "Runner.relGameExeFile")
        VerifyParamsType(self.gameExeArgs, "Runner.gameExeArgs")
        VerifyStringListType(self.relevantGameDataFileTypes, "Runner.relevantGameDataFileTypes")
        VerifyStringListType(self.absRegularGameDataFiles, "Runner.absRegularGameDataFiles")
        util.RelAssertType(self.gameLanguageRegKey, str, "Runner.gameLanguageRegKey")

    def VerifyValues(self) -> None:
        util.RelAssert(os.path.isdir(self.absGameInstallDir), f"Runner.absGameRootDir '{self.absGameInstallDir}' is not a valid path")
        util.RelAssert(os.path.isfile(self.AbsGameExeFile()), f"Runner.AbsGameExeFile() '{self.AbsGameExeFile()}' is not a valid file")

    def ResolveWildcards(self) -> None:
        self.absRegularGameDataFiles = Runner.ResolveWildcardsInFileList(self.absRegularGameDataFiles)

    @staticmethod
    def ResolveWildcardsInFileList(fileList: list[str]) -> list[str]:
        file: str
        globFiles: list[str]
        newFiles = list[str]()
        for file in fileList:
            if not os.path.isfile(file) and "*" in file:
                globFiles = glob(file, recursive=True)
                util.RelAssert(bool(globFiles), f"Wildcard '{file}' matches nothing")
                for globFile in globFiles:
                    if os.path.isfile(globFile):
                        newFiles.append(globFile)
            else:
                newFiles.append(file)
        return newFiles


def MakeRunnerFromJsons(jsonFiles: list[JsonFile]) -> Runner:
    runner = Runner()
    runner.absGameInstallDir = None
    runner.relGameExeFile = None

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsSmartFileDir(jsonFile.path)
        jRunner: dict = jsonFile.data.get("runner")

        if jRunner:
            runner.relGameExeFile = util.GetSecondIfValid(runner.relGameExeFile, jRunner.get("gameExeFile"))
            runner.gameExeArgs = util.GetSecondIfValid(runner.gameExeArgs, jRunner.get("gameExeArgs"))
            runner.relevantGameDataFileTypes = util.GetSecondIfValid(runner.relevantGameDataFileTypes, jRunner.get("relevantGameDataFileTypes"))
            runner.absRegularGameDataFiles = util.GetSecondIfValid(runner.absRegularGameDataFiles, jRunner.get("regularGameDataFiles"))
            runner.gameLanguageRegKey = jRunner.get("gameLanguageRegKey")

            gameInstallDir: str = jRunner.get("gameInstallPath")
            gameInstallRegKey: str = jRunner.get("gameInstallRegKey")

            if isinstance(gameInstallDir, str) and gameInstallDir:
                runner.absGameInstallDir = os.path.join(jsonDir, gameInstallDir)
            elif isinstance(gameInstallRegKey, str) and gameInstallRegKey:
                runner.absGameInstallDir = util.GetRegKeyValue(gameInstallRegKey)

    runner.VerifyTypes()
    runner.Normalize()

    for i in range(len(runner.absRegularGameDataFiles)):
        runner.absRegularGameDataFiles[i] = os.path.join(runner.absGameInstallDir, runner.absRegularGameDataFiles[i])

    runner.ResolveWildcards()
    runner.VerifyValues()
    return runner
