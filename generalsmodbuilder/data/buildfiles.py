import os
from dataclasses import dataclass
from generalsmodbuilder.data.common import FinalizeParsedData, ParsedData, VerifyFormatVersion
from generalsmodbuilder.util import JsonFile
from generalsmodbuilder import util


LATEST_BUILD_VERSION = 1

BUILD_KEYS = {"version", "files"}


@dataclass(init=False)
class BuildFiles(ParsedData):
    absFiles: list[str]

    def __init__(self):
        self.absFiles = list[str]()

    def Normalize(self) -> None:
        for i, file in enumerate(self.absFiles):
            self.absFiles[i] = os.path.normpath(file)

    def VerifyValues(self) -> None:
        for file in self.absFiles:
            util.Verify(os.path.isfile(file), f"build.files '{file}' is not a valid file")
            util.Verify(util.HasFileExt(file, "json"), f"build.files '{file}' is not a json file")


def AddBuildFilesFromJsons(jsonFiles: list[JsonFile], buildFiles: BuildFiles) -> None:
    """
    Parses build file list from all json files where present.
    """
    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsFileDir(jsonFile.path)
        root = util.JsonNode(jsonFile.path, jsonFile.data)

        if node := root.SubOptional("build"):
            node.VerifyKnownKeys(BUILD_KEYS)
            VerifyFormatVersion(node, LATEST_BUILD_VERSION)

            fileNode: util.JsonNode
            for fileNode in node.Elements("files", str):
                fileNode.Verify(bool(fileNode.data), "must not be empty")
                buildFiles.absFiles.append(os.path.join(jsonDir, fileNode.data))
    return


def MakeBuildFilesFromJsons(jsonFiles: list[JsonFile]) -> BuildFiles:
    buildFiles = BuildFiles()

    AddBuildFilesFromJsons(jsonFiles, buildFiles)

    FinalizeParsedData(buildFiles)

    return buildFiles
