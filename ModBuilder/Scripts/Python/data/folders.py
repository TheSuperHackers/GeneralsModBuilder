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
        utils.RelAssertType(self.absReleaseUnpackedDir, str, "Folders.absReleaseUnpackedDir")
        utils.RelAssertType(self.absReleaseDir, str, "Folders.absReleaseDir")
        utils.RelAssertType(self.absBuildDir, str, "Folders.absBuildDir")


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
