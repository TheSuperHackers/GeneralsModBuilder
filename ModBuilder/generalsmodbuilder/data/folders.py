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

    def VerifyValues(self) -> None:
        util.RelAssert(util.IsValidPathName(self.absReleaseUnpackedDir), f"Folders.absReleaseUnpackedDir '{self.absReleaseUnpackedDir}' is not a valid path name")
        util.RelAssert(util.IsValidPathName(self.absReleaseDir), f"Folders.absReleaseDir '{self.absReleaseDir}' is not a valid path name")
        util.RelAssert(util.IsValidPathName(self.absBuildDir), f"Folders.absBuildDir '{self.absBuildDir}' is not a valid path name")

def MakeFoldersFromJsons(jsonFiles: list[JsonFile]) -> Folders:
    folders = Folders()
    folders.absReleaseUnpackedDir = None
    folders.absReleaseDir = None
    folders.absBuildDir = None

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsSmartFileDir(jsonFile.path)
        jFolders: dict = jsonFile.data.get("folders")

        if jFolders:
            folders.absReleaseUnpackedDir = util.JoinPathIfValid(folders.absReleaseUnpackedDir, jsonDir, jFolders.get("releaseUnpackedDir"))
            folders.absReleaseDir = util.JoinPathIfValid(folders.absReleaseDir, jsonDir, jFolders.get("releaseDir"))
            folders.absBuildDir = util.JoinPathIfValid(folders.absBuildDir, jsonDir, jFolders.get("buildDir"))

    folders.VerifyTypes()
    folders.Normalize()
    folders.VerifyValues()
    return folders
