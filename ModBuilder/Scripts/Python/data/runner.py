import os.path
from typing import Match
import utils
import re
from utils import JsonFile
from dataclasses import dataclass
from data.common import ParamsT, VerifyParamsType, VerifyStringListType


@dataclass(init=False)
class Runner:
    gameRootDir: str
    gameExeFile: str
    gameExeArgs: ParamsT

    def __init__(self):
        self.gameExeArgs = ParamsT()

    def Normalize(self) -> None:
        self.gameRootDir = utils.NormalizePath(self.gameRootDir)
        self.gameExeFile = utils.NormalizePath(self.gameExeFile)

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.gameRootDir, str), "Runner.gameRootDir has incorrect type")
        utils.RelAssert(isinstance(self.gameExeFile, str), "Runner.gameExeFile has incorrect type")
        VerifyParamsType(self.gameExeArgs, "Runner.gameExeArgs")


def __ParseAndGetFromRegistry(s: str) -> str:
    if s.startswith("REGISTRY:"):
        pathkey: Match = re.search(":(.*)", s)
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
            gameRootDir: str = jRunner.get("gameRootDir")
            if gameRootDir:
                if gameRootDir.startswith("REGISTRY:"):
                    runner.gameRootDir = __ParseAndGetFromRegistry(gameRootDir)
                else:
                    runner.gameRootDir = os.path.join(jsonDir, gameRootDir)

            runner.gameExeFile = utils.GetSecondIfValid(runner.gameExeFile, jRunner.get("gameExeFile"))
            runner.gameExeArgs = utils.GetSecondIfValid(runner.gameExeArgs, jRunner.get("gameExeArgs"))

    runner.VerifyTypes()
    runner.Normalize()
    return runner
