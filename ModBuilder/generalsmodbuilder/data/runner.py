import os.path
from glob import glob
from dataclasses import dataclass
from generalsmodbuilder.data.common import ParamsT, VerifyParamsType, VerifyStringListType
from generalsmodbuilder.util import JsonFile
from generalsmodbuilder import util


@dataclass(init=False)
class Runner:
    absGameInstallDir: str
    relGameExeFile: str
    gameExeArgs: ParamsT
    relevantGameDataFileTypes: list[str]
    absRegularGameDataFiles: list[str]
    gameLanguageRegKey: str

    def __init__(self):
        self.absGameInstallDir = None
        self.relGameExeFile = None
        self.gameExeArgs = ParamsT()
        self.relevantGameDataFileTypes = list[str]()
        self.absRegularGameDataFiles = list[str]()
        self.gameLanguageRegKey = ""

    def AbsGameExeFile(self) -> str:
        return os.path.join(self.absGameInstallDir, self.relGameExeFile)

    def Normalize(self) -> None:
        self.absGameInstallDir = os.path.normpath(self.absGameInstallDir)
        self.relGameExeFile = os.path.normpath(self.relGameExeFile)
        for i in range(len(self.absRegularGameDataFiles)):
            self.absRegularGameDataFiles[i] = os.path.normpath(self.absRegularGameDataFiles[i])

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
                # It is ok if globFiles is empty.
                for globFile in globFiles:
                    if os.path.isfile(globFile):
                        newFiles.append(globFile)
            else:
                newFiles.append(file)
        return newFiles


def MakeRunnerFromJsons(jsonFiles: list[JsonFile]) -> Runner:
    runner = Runner()

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsSmartFileDir(jsonFile.path)
        jRunner: dict = jsonFile.data.get("runner")

        if jRunner:
            runner.relGameExeFile = jRunner.get("gameExeFile", runner.relGameExeFile)
            runner.gameExeArgs = jRunner.get("gameExeArgs", runner.gameExeArgs)
            runner.relevantGameDataFileTypes = jRunner.get("relevantGameDataFileTypes", runner.relevantGameDataFileTypes)
            runner.absRegularGameDataFiles = jRunner.get("regularGameDataFiles", runner.absRegularGameDataFiles)
            runner.gameLanguageRegKey = jRunner.get("gameLanguageRegKey", runner.gameLanguageRegKey)

            gameInstallDir: str = jRunner.get("gameInstallPath")

            if isinstance(gameInstallDir, str) and gameInstallDir:
                runner.absGameInstallDir = os.path.join(jsonDir, gameInstallDir)
            else:
                gameInstallRegKey: str = jRunner.get("gameInstallRegKey")
                if isinstance(gameInstallRegKey, str) and gameInstallRegKey:
                    runner.absGameInstallDir = util.GetRegKeyValue(gameInstallRegKey)
                # If the first is invalid, try the second one.
                if not os.path.isfile(runner.AbsGameExeFile()):
                    gameInstall2RegKey: str = jRunner.get("gameInstall2RegKey")
                    if isinstance(gameInstall2RegKey, str) and gameInstall2RegKey:
                        runner.absGameInstallDir = util.GetRegKeyValue(gameInstall2RegKey)

    runner.VerifyTypes()
    runner.Normalize()

    for i in range(len(runner.absRegularGameDataFiles)):
        runner.absRegularGameDataFiles[i] = os.path.join(runner.absGameInstallDir, runner.absRegularGameDataFiles[i])

    runner.VerifyValues()
    runner.ResolveWildcards()
    return runner
