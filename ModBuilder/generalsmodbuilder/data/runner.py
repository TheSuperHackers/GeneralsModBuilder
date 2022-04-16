import os.path
import util
import re
from glob import glob
from typing import Match
from util import JsonFile
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
        self.absGameRootDir = util.NormalizePath(self.absGameRootDir)
        self.relGameExeFile = util.NormalizePath(self.relGameExeFile)
        for i in range(len(self.absRegularGameDataFiles)):
            self.absRegularGameDataFiles[i] = util.NormalizePath(self.absRegularGameDataFiles[i])

    def VerifyTypes(self) -> None:
        util.RelAssertType(self.absGameRootDir, str, "Runner.absGameRootDir")
        util.RelAssertType(self.relGameExeFile, str, "Runner.relGameExeFile")
        VerifyParamsType(self.gameExeArgs, "Runner.gameExeArgs")
        VerifyStringListType(self.relevantGameDataFileTypes, "Runner.relevantGameDataFileTypes")
        VerifyStringListType(self.absRegularGameDataFiles, "Runner.absRegularGameDataFiles")

    def VerifyValues(self) -> None:
        util.RelAssert(os.path.isdir(self.absGameRootDir), f"Runner.absGameRootDir '{self.absGameRootDir}' is not a valid path")
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


def IsRegistryToken(s: str) -> bool:
    return s.startswith("REGISTRY:")


def ResolveRegistryToken(s: str) -> str:
    pathkey: Match = re.search("REGISTRY:(.*)", s)
    if pathkey:
        path: Match = re.search("(.*):", pathkey.group(1))
        key: Match = re.search(":(.*)", pathkey.group(1))
        if path and key:
            return util.GetKeyValueFromRegistry(path.group(1), key.group(1))
    return None


def MakeRunnerFromJsons(jsonFiles: list[JsonFile]) -> Runner:
    runner = Runner()
    runner.absGameRootDir = None
    runner.relGameExeFile = None

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsFileDir(jsonFile.path)
        jRunner: dict = jsonFile.data.get("runner")

        if jRunner:
            runner.absGameRootDir = util.GetSecondIfValid(runner.absGameRootDir, jRunner.get("gameRootDir"))
            runner.relGameExeFile = util.GetSecondIfValid(runner.relGameExeFile, jRunner.get("gameExeFile"))
            runner.gameExeArgs = util.GetSecondIfValid(runner.gameExeArgs, jRunner.get("gameExeArgs"))
            runner.relevantGameDataFileTypes = util.GetSecondIfValid(runner.relevantGameDataFileTypes, jRunner.get("relevantGameDataFileTypes"))
            runner.absRegularGameDataFiles = util.GetSecondIfValid(runner.absRegularGameDataFiles, jRunner.get("regularGameDataFiles"))

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
