import utils
from utils import JsonFile
from dataclasses import dataclass


@dataclass(init=False)
class Folders:
    releaseUnpackedDir: str
    releaseDir: str
    buildDir: str

    def __init__(self):
        pass

    def Normalize(self) -> None:
        self.releaseUnpackedDir = utils.NormalizePath(self.releaseUnpackedDir)
        self.releaseDir = utils.NormalizePath(self.releaseDir)
        self.buildDir = utils.NormalizePath(self.buildDir)

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.releaseUnpackedDir, str), "Folders.releaseUnpackedDir has incorrect type")
        utils.RelAssert(isinstance(self.releaseDir, str), "Folders.releaseDir has incorrect type")
        utils.RelAssert(isinstance(self.buildDir, str), "Folders.buildDir has incorrect type")


def MakeFoldersFromJsons(jsonFiles: list[JsonFile]) -> Folders:
    folders = Folders()
    folders.releaseUnpackedDir = None
    folders.releaseDir = None
    folders.buildDir = None

    for jsonFile in jsonFiles:
        jsonDir: str = utils.GetFileDir(jsonFile.path)
        jFolders: dict = jsonFile.data.get("folders")

        if jFolders:
            folders.releaseUnpackedDir = utils.JoinPathIfValid(folders.releaseUnpackedDir, jsonDir, jFolders.get("releaseUnpackedDir"))
            folders.releaseDir = utils.JoinPathIfValid(folders.releaseDir, jsonDir, jFolders.get("releaseDir"))
            folders.buildDir = utils.JoinPathIfValid(folders.buildDir, jsonDir, jFolders.get("buildDir"))

    folders.VerifyTypes()
    folders.Normalize()
    return folders
