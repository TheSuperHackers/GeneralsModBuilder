import os
from dataclasses import dataclass
from generalsmodbuilder.data.bundles import Bundles
from generalsmodbuilder.util import JsonFile
from generalsmodbuilder import util


@dataclass(init=False)
class BuildFiles:
    absFiles: list[str]

    def __init__(self):
        self.absFiles = list[str]()

    def VerifyTypes(self) -> None:
        util.VerifyType(self.absFiles, list, "BuildFiles.absFiles")
        for file in self.absFiles:
            util.VerifyType(file, str, "BuildFiles.absFiles.value")

    def Normalize(self) -> None:
        for file in self.absFiles:
            file = os.path.normpath(file)

    def VerifyValues(self) -> None:
        for file in self.absFiles:
            util.Verify(os.path.isfile(file), f"BuildFiles.absFiles '{file}' is not a valid file")


def AddBuildFilesFromJsons(jsonFiles: list[JsonFile], buildFiles: BuildFiles) -> Bundles:
    """
    Parses build file list from all json files where present.
    """
    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsSmartFileDir(jsonFile.path)
        jBuild: dict = jsonFile.data.get("build")

        if jBuild:
            jFiles: list = jBuild.get("files")
            if jFiles:
                jFile: str
                for jFile in jFiles:
                    filePath: str = util.JoinPathIfValid(None, jsonDir, jFile)
                    if filePath != None:
                        buildFiles.absFiles.append(filePath)
    return


def MakeBuildFilesFromJsons(jsonFiles: list[JsonFile]) -> BuildFiles:
    buildFiles = BuildFiles()

    AddBuildFilesFromJsons(jsonFiles, buildFiles)

    buildFiles.VerifyTypes()
    buildFiles.Normalize()
    buildFiles.VerifyValues()

    return buildFiles
