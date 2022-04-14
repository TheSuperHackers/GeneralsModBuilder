import util
from util import JsonFile
from dataclasses import dataclass


@dataclass(init=False)
class Folders:
    absReleaseUnpackedDir: str
    absReleaseDir: str
    absBuildDir: str

    def __init__(self):
        pass

    def Normalize(self) -> None:
        self.absReleaseUnpackedDir = util.NormalizePath(self.absReleaseUnpackedDir)
        self.absReleaseDir = util.NormalizePath(self.absReleaseDir)
        self.absBuildDir = util.NormalizePath(self.absBuildDir)

    def VerifyTypes(self) -> None:
        util.RelAssertType(self.absReleaseUnpackedDir, str, "Folders.absReleaseUnpackedDir")
        util.RelAssertType(self.absReleaseDir, str, "Folders.absReleaseDir")
        util.RelAssertType(self.absBuildDir, str, "Folders.absBuildDir")


def MakeFoldersFromJsons(jsonFiles: list[JsonFile]) -> Folders:
    folders = Folders()
    folders.absReleaseUnpackedDir = None
    folders.absReleaseDir = None
    folders.absBuildDir = None

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetFileDir(jsonFile.path)
        jFolders: dict = jsonFile.data.get("folders")

        if jFolders:
            folders.absReleaseUnpackedDir = util.JoinPathIfValid(folders.absReleaseUnpackedDir, jsonDir, jFolders.get("releaseUnpackedDir"))
            folders.absReleaseDir = util.JoinPathIfValid(folders.absReleaseDir, jsonDir, jFolders.get("releaseDir"))
            folders.absBuildDir = util.JoinPathIfValid(folders.absBuildDir, jsonDir, jFolders.get("buildDir"))

    folders.VerifyTypes()
    folders.Normalize()
    return folders
