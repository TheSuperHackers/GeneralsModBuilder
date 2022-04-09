import os.path
import utils
import re
from glob import glob
from typing import Match
from utils import JsonFile
from dataclasses import dataclass
from data.common import ParamsT, VerifyParamsType, VerifyStringListType


@dataclass(init=False)
class Runner:
    gameRootDir: str
    gameExeFile: str
    gameExeArgs: ParamsT
    relevantGameDataFileTypes: list[str]
    absRegularGameDataFiles: list[str]

    def __init__(self):
        self.gameExeArgs = ParamsT()
        self.relevantGameDataFileTypes = list[str]()
        self.absRegularGameDataFiles = list[str]()

    def AbsGameExeFile(self) -> str:
        return os.path.join(self.gameRootDir, self.gameExeFile)

    def Normalize(self) -> None:
        self.gameRootDir = utils.NormalizePath(self.gameRootDir)
        self.gameExeFile = utils.NormalizePath(self.gameExeFile)
        for i in range(len(self.absRegularGameDataFiles)):
            self.absRegularGameDataFiles[i] = utils.NormalizePath(self.absRegularGameDataFiles[i])

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.gameRootDir, str), "Runner.gameRootDir has incorrect type")
        utils.RelAssert(isinstance(self.gameExeFile, str), "Runner.gameExeFile has incorrect type")
        VerifyParamsType(self.gameExeArgs, "Runner.gameExeArgs")
        VerifyStringListType(self.relevantGameDataFileTypes, "Runner.relevantGameDataFileTypes")
        VerifyStringListType(self.absRegularGameDataFiles, "Runner.regularGameDataFiles has incorrect type")

    def VerifyValues(self) -> None:
        utils.RelAssert(os.path.isdir(self.gameRootDir), f"Runner.gameRootDir '{self.gameRootDir}' is not a valid path")
        utils.RelAssert(os.path.isfile(self.AbsGameExeFile()), f"Runner.gameExeFile '{self.gameExeFile}' is not a valid file")
        file: str
        for file in self.absRegularGameDataFiles:
            utils.RelAssert(os.path.isfile(self.AbsGameExeFile()), f"Runner.regularGameDataFiles {file} is not a valid file")

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
                utils.RelAssert(bool(globFiles), f"Wildcard '{file}' matches nothing")
                for globFile in globFiles:
                        utils.RelAssert(os.path.isfile(globFile), f"Wildcard file '{globFile}' is not a file")
                        newFiles.append(globFile)
            else:
                newFiles.append(file)
        return newFiles


def IsRegistryToken(s: str) -> bool:
    return s.startswith("REGISTRY:")


def ResolveRegistryToken(s: str) -> str:
    pathkey: Match = re.search("REGISTRY:(.*)", s)
    if pathkey:
        path: Match = re.search("(.*):", pathkey.group(1))
        key: Match = re.search(":(.*)", pathkey.group(1))
        if path and key:
            return utils.GetKeyValueFromRegistry(path.group(1), key.group(1))
    return None


def MakeRunnerFromJsons(jsonFiles: list[JsonFile]) -> Runner:
    runner = Runner()
    runner.gameRootDir = None
    runner.gameExeFile = None

    for jsonFile in jsonFiles:
        jsonDir: str = utils.GetFileDir(jsonFile.path)
        jRunner: dict = jsonFile.data.get("runner")

        if jRunner:
            runner.gameRootDir = utils.GetSecondIfValid(runner.gameRootDir, jRunner.get("gameRootDir"))
            runner.gameExeFile = utils.GetSecondIfValid(runner.gameExeFile, jRunner.get("gameExeFile"))
            runner.gameExeArgs = utils.GetSecondIfValid(runner.gameExeArgs, jRunner.get("gameExeArgs"))
            runner.relevantGameDataFileTypes = utils.GetSecondIfValid(runner.relevantGameDataFileTypes, jRunner.get("relevantGameDataFileTypes"))
            runner.absRegularGameDataFiles = utils.GetSecondIfValid(runner.absRegularGameDataFiles, jRunner.get("regularGameDataFiles"))

            if runner.gameRootDir != None:
                if IsRegistryToken(runner.gameRootDir):
                    runner.gameRootDir = ResolveRegistryToken(runner.gameRootDir)
                else:
                    runner.gameRootDir = os.path.join(jsonDir, runner.gameRootDir)

            if runner.absRegularGameDataFiles != None:
                for i in range(len(runner.absRegularGameDataFiles)):
                    runner.absRegularGameDataFiles[i] = os.path.join(runner.gameRootDir, runner.absRegularGameDataFiles[i])

    runner.VerifyTypes()
    runner.Normalize()
    runner.ResolveWildcards()
    runner.VerifyValues()
    return runner
