import os
import glob
import utils
from os.path import join as joinpath
from os.path import normpath as normpath
from bundles import Bundle
from bundles import BundleFile
from folders import Folders
from runner import Runner
from tools import Tool


class Builder:
    folders: Folders
    runner: Runner
    bundles: list[Bundle]
    tools: dict[Tool]

    def __init__(self):
        self.folders = Folders()
        self.runner = Runner()
        self.bundles = []

    def SetFolders(self, folders: Folders) -> None:
        self.folders = folders

    def SetRunner(self, runner: Runner) -> None:
        self.runner = runner

    def SetBundles(self, bundles: list[Bundle]) -> None:
        self.bundles = bundles

    def SetTools(self, tools: dict[Tool]) -> None:
        self.tools = tools
        utils.RelAssert(tools.get("crunch") is not None, "crunch tool definition is missing")
        utils.RelAssert(tools.get("gametextcompiler") is not None, "gametextcompiler tool definition is missing")
        utils.RelAssert(tools.get("generalsbigcreator") is not None, "generalsbigcreator tool definition is missing")

    def AddBundle(self, name: str, files: list[BundleFile]) -> None:
        files = self.__NormalizePathsInBundleFiles(files)
        files = self.__RemoveGameFilesDirPrefixesInBundleFiles(files)
        files = self.__ResolveWildcardsInBundleFiles(files)
        self.__VerifyBundleFiles(files)
        newBundle = Bundle(name, files)
        print(f"Add bundle:\n{newBundle}")
        self.bundles.append(newBundle)

    def __RemoveGameFilesDirPrefix(self, path: str) -> str:
        path = path.removeprefix(self.folders.gameFilesDir)
        if path.startswith(os.sep):
            path = path[len(os.sep):]
        return path

    def __RemoveGameFilesDirPrefixesInBundleFiles(self, files: list[BundleFile]) -> list[BundleFile]:
        for i in range(len(files)):
            assert files[i].absSourceFile is not None
            files[i].absSourceFile = self.__RemoveGameFilesDirPrefix(files[i].absSourceFile)
            if files[i].relTargetFile is not None:
                files[i].relTargetFile = self.__RemoveGameFilesDirPrefix(files[i].relTargetFile)
        return files

    def __NormalizePath(self, path: str) -> str:
        return os.path.normpath(path)

    def __NormalizePathsInBundleFiles(self, files: list[BundleFile]) -> list[BundleFile]:
        for i in range(len(files)):
            assert files[i].absSourceFile is not None
            files[i].absSourceFile = self.__NormalizePath(files[i].absSourceFile)
            if files[i].relTargetFile is not None:
                files[i].relTargetFile = self.__NormalizePath(files[i].relTargetFile)
        return files

    def __NormalizePaths(self, files: list[str]) -> list[str]:
        for i in range(len(files)):
            files[i] = self.__NormalizePath(files[i])
        return files

    def __ResolveWildcardsInBundleFiles(self, files: list[BundleFile]) -> list[BundleFile]:
        newFiles: list[BundleFile] = []
        for file in files:
            assert file.absSourceFile is not None
            filePath = self.__MakeGameFilePath(file.absSourceFile)
            if not os.path.exists(filePath):
                globFiles = glob.glob(filePath)
                assert bool(globFiles), f"{file.absSourceFile} matches nothing"
                for globFile in globFiles:
                    newFile = file
                    newFile.absSourceFile = globFile
                    newFiles.append(newFile)
            else:
                newFiles.append(file)
        return newFiles

    def __VerifyBundleFiles(self, files: list[BundleFile]) -> list[BundleFile]:
        for file in files:
            assert isinstance(file, BundleFile), f"{file} is not a BundleFile"
            assert os.path.isfile(self.__MakeGameFilePath(file.absSourceFile)), f"{file.absSourceFile} is not a path to a file"

    def __MakeGameFilePath(self, filePath: str) -> str:
        if os.path.isabs(filePath):
            return filePath
        else:
            return joinpath(self.folders.gameFilesDir, filePath)
