import utils
from utils import JsonFile
from dataclasses import dataclass


@dataclass(init=False)
class Folders:
    absReleaseUnpackedDir: str
    absReleaseDir: str
    absBuildDir: str

    def __init__(self):
        pass

    def Normalize(self) -> None:
        self.absReleaseUnpackedDir = utils.NormalizePath(self.absReleaseUnpackedDir)
        self.absReleaseDir = utils.NormalizePath(self.absReleaseDir)
        self.absBuildDir = utils.NormalizePath(self.absBuildDir)

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.absReleaseUnpackedDir, str), "Folders.releaseUnpackedDir has incorrect type")
        utils.RelAssert(isinstance(self.absReleaseDir, str), "Folders.releaseDir has incorrect type")
        utils.RelAssert(isinstance(self.absBuildDir, str), "Folders.buildDir has incorrect type")


def MakeFoldersFromJsons(jsonFiles: list[JsonFile]) -> Folders:
    folders = Folders()
    folders.absReleaseUnpackedDir = None
    folders.absReleaseDir = None
    folders.absBuildDir = None

    for jsonFile in jsonFiles:
        jsonDir: str = utils.GetFileDir(jsonFile.path)
        jFolders: dict = jsonFile.data.get("folders")

        if jFolders:
            folders.absReleaseUnpackedDir = utils.JoinPathIfValid(folders.absReleaseUnpackedDir, jsonDir, jFolders.get("releaseUnpackedDir"))
            folders.absReleaseDir = utils.JoinPathIfValid(folders.absReleaseDir, jsonDir, jFolders.get("releaseDir"))
            folders.absBuildDir = utils.JoinPathIfValid(folders.absBuildDir, jsonDir, jFolders.get("buildDir"))

    folders.VerifyTypes()
    folders.Normalize()
    return folders
