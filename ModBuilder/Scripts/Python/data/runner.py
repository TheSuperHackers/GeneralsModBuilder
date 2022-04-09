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
    absGameRootDir: str
    relGameExeFile: str
    gameExeArgs: ParamsT
    relevantGameDataFileTypes: list[str]
    absRegularGameDataFiles: list[str]

    def __init__(self):
        self.gameExeArgs = ParamsT()
        self.relevantGameDataFileTypes = list[str]()
        self.absRegularGameDataFiles = list[str]()

    def AbsGameExeFile(self) -> str:
        return os.path.join(self.absGameRootDir, self.relGameExeFile)

    def Normalize(self) -> None:
        self.absGameRootDir = utils.NormalizePath(self.absGameRootDir)
        self.relGameExeFile = utils.NormalizePath(self.relGameExeFile)
        for i in range(len(self.absRegularGameDataFiles)):
            self.absRegularGameDataFiles[i] = utils.NormalizePath(self.absRegularGameDataFiles[i])

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.absGameRootDir, str), "Runner.gameRootDir has incorrect type")
        utils.RelAssert(isinstance(self.relGameExeFile, str), "Runner.gameExeFile has incorrect type")
        VerifyParamsType(self.gameExeArgs, "Runner.gameExeArgs")
        VerifyStringListType(self.relevantGameDataFileTypes, "Runner.relevantGameDataFileTypes")
        VerifyStringListType(self.absRegularGameDataFiles, "Runner.regularGameDataFiles has incorrect type")

    def VerifyValues(self) -> None:
        utils.RelAssert(os.path.isdir(self.absGameRootDir), f"Runner.gameRootDir '{self.absGameRootDir}' is not a valid path")
        utils.RelAssert(os.path.isfile(self.AbsGameExeFile()), f"Runner.gameExeFile '{self.relGameExeFile}' is not a valid file")
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
    runner.absGameRootDir = None
    runner.relGameExeFile = None

    for jsonFile in jsonFiles:
        jsonDir: str = utils.GetFileDir(jsonFile.path)
        jRunner: dict = jsonFile.data.get("runner")

        if jRunner:
            runner.absGameRootDir = utils.GetSecondIfValid(runner.absGameRootDir, jRunner.get("gameRootDir"))
            runner.relGameExeFile = utils.GetSecondIfValid(runner.relGameExeFile, jRunner.get("gameExeFile"))
            runner.gameExeArgs = utils.GetSecondIfValid(runner.gameExeArgs, jRunner.get("gameExeArgs"))
            runner.relevantGameDataFileTypes = utils.GetSecondIfValid(runner.relevantGameDataFileTypes, jRunner.get("relevantGameDataFileTypes"))
            runner.absRegularGameDataFiles = utils.GetSecondIfValid(runner.absRegularGameDataFiles, jRunner.get("regularGameDataFiles"))

            if runner.absGameRootDir != None:
                if IsRegistryToken(runner.absGameRootDir):
                    runner.absGameRootDir = ResolveRegistryToken(runner.absGameRootDir)
                else:
                    runner.absGameRootDir = os.path.join(jsonDir, runner.absGameRootDir)

            if runner.absRegularGameDataFiles != None:
                for i in range(len(runner.absRegularGameDataFiles)):
                    runner.absRegularGameDataFiles[i] = os.path.join(runner.absGameRootDir, runner.absRegularGameDataFiles[i])

    runner.VerifyTypes()
    runner.Normalize()
    runner.ResolveWildcards()
    runner.VerifyValues()
    return runner
