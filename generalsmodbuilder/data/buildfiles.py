import os
from dataclasses import dataclass
from generalsmodbuilder.data.common import FinalizeParsedData, ParsedData
from generalsmodbuilder.util import JsonFile
from generalsmodbuilder import util


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


def AddBuildFilesFromJsons(jsonFiles: list[JsonFile], buildFiles: BuildFiles) -> None:
    """
    Parses build file list from all json files where present.
    """
    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsFileDir(jsonFile.path)
        root = util.JsonContext(jsonFile.path)
        jBuild: dict = root.GetOptional(jsonFile.data, "build", dict)

        if jBuild:
            ctx = root.Sub("build")
            jFiles: list = ctx.GetOptional(jBuild, "files", list, default=[], elementType=str)
            jFile: str
            for jFile in jFiles:
                buildFiles.absFiles.append(os.path.join(jsonDir, jFile))
    return


def MakeBuildFilesFromJsons(jsonFiles: list[JsonFile]) -> BuildFiles:
    buildFiles = BuildFiles()

    AddBuildFilesFromJsons(jsonFiles, buildFiles)

    FinalizeParsedData(buildFiles)

    return buildFiles
