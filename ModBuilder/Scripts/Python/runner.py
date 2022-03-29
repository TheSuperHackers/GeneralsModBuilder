import utils
import re
from os.path import join as joinpath
from utils import JsonFile


class Runner:
    gameRootDir: str
    gameExeFile: str
    gameExeArgs: str = ""
    gameFilesToDisable: list[str] = []

    def __init__(self):
        pass

    def Normalize(self) -> None:
        self.gameRootDir = utils.NormalizePath(self.gameRootDir)
        self.gameExeFile = utils.NormalizePath(self.gameExeFile)
        self.gameFilesToDisable = utils.NormalizePaths(self.gameFilesToDisable)

    def Validate(self) -> None:
        utils.RelAssert(isinstance(self.gameRootDir, str), "Runner.gameRootDir has incorrect type")
        utils.RelAssert(isinstance(self.gameExeFile, str), "Runner.gameExeFile has incorrect type")
        utils.RelAssert(isinstance(self.gameExeArgs, str), "Runner.gameExeArgs has incorrect type")
        utils.RelAssert(isinstance(self.gameFilesToDisable, list), "Runner.gameFilesToDisable has incorrect type")
        for file in self.gameFilesToDisable:
            utils.RelAssert(isinstance(file, str), "Runner.gameFilesToDisable has incorrect type")


def __ParseAndGetFromRegistry(s: str) -> str:
    if s.startswith("REGISTRY:"):
        pathkey: str = re.search(":(.*)", s)
        if pathkey:
            path: str = re.search("(.*):", pathkey.group(1))
            key: str = re.search(":(.*)", pathkey.group(1))
            if path and key:
                return utils.GetKeyValueFromRegistry(path.group(1), key.group(1))
    return None


def MakeRunnerFromJsons(jsonFiles: list[JsonFile]) -> Runner:
    runner = Runner()
    runner.gameRootDir = None
    runner.gameExeFile = None

    for jsonFile in jsonFiles:
        jsonDir: str = utils.MakeFileDir(jsonFile.path)
        jRunner: dict = jsonFile.data.get("runner")

        if jRunner:
            gameRootDir: str = jRunner.get("gameRootDir")
            if gameRootDir:
                if gameRootDir.startswith("REGISTRY:"):
                    runner.gameRootDir = __ParseAndGetFromRegistry(gameRootDir)
                else:
                    runner.gameRootDir = joinpath(jsonDir, gameRootDir)

            runner.gameExeFile = utils.GetSecondIfValid(runner.gameExeFile, jRunner.get("gameExeFile"))
            runner.gameExeArgs = utils.GetSecondIfValid(runner.gameExeArgs, jRunner.get("gameExeArgs"))
            runner.gameFilesToDisable = utils.GetSecondIfValid(runner.gameFilesToDisable, jRunner.get("gameFilesToDisable"))

    runner.Validate()
    runner.Normalize()
    return runner
