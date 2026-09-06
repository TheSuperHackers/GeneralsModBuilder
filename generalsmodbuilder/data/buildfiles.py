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
        root = util.JsonContext(jsonFile.path)
        jBuild: dict = root.GetOptional(jsonFile.data, "build", dict)

        if jBuild:
            ctx = root.Sub("build")
            ctx.VerifyKnownKeys(jBuild, BUILD_KEYS)
            VerifyFormatVersion(ctx, jBuild, LATEST_BUILD_VERSION)

            jFiles: list = ctx.GetOptional(jBuild, "files", list, default=[], elementType=str)
            jFile: str
            for index, jFile in enumerate(jFiles):
                ctx.Sub("files").At(index).Verify(bool(jFile), "must not be empty")
                buildFiles.absFiles.append(os.path.join(jsonDir, jFile))
    return


def MakeBuildFilesFromJsons(jsonFiles: list[JsonFile]) -> BuildFiles:
    buildFiles = BuildFiles()

    AddBuildFilesFromJsons(jsonFiles, buildFiles)

    FinalizeParsedData(buildFiles)

    return buildFiles
