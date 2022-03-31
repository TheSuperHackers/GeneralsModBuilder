import utils
from utils import JsonFile
from dataclasses import dataclass


@dataclass(init=False)
class Folders:
    releaseUnpackedDir: str
    releaseDir: str
    tmpBigUnpackedDir: str
    tmpBigDir: str
    tmpReleaseUnpackedDir: str

    def __init__(self):
        pass

    def Normalize(self) -> None:
        self.releaseUnpackedDir = utils.NormalizePath(self.releaseUnpackedDir)
        self.releaseDir = utils.NormalizePath(self.releaseDir)
        self.tmpBigUnpackedDir = utils.NormalizePath(self.tmpBigUnpackedDir)
        self.tmpBigDir = utils.NormalizePath(self.tmpBigDir)
        self.tmpReleaseUnpackedDir = utils.NormalizePath(self.tmpReleaseUnpackedDir)

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.releaseUnpackedDir, str), "Folders.releaseUnpackedDir has incorrect type")
        utils.RelAssert(isinstance(self.releaseDir, str), "Folders.releaseDir has incorrect type")
        utils.RelAssert(isinstance(self.tmpBigUnpackedDir, str), "Folders.tmpBigUnpackedDir has incorrect type")
        utils.RelAssert(isinstance(self.tmpBigDir, str), "Folders.tmpBigDir has incorrect type")
        utils.RelAssert(isinstance(self.tmpReleaseUnpackedDir, str), "Folders.tmpReleaseUnpackedDir has incorrect type")


def MakeFoldersFromJsons(jsonFiles: list[JsonFile]) -> Folders:
    folders = Folders()
    folders.releaseUnpackedDir = None
    folders.releaseDir = None
    folders.tmpBigUnpackedDir = None
    folders.tmpBigDir = None
    folders.tmpReleaseUnpackedDir = None

    for jsonFile in jsonFiles:
        jsonDir: str = utils.GetFileDir(jsonFile.path)
        jFolders: dict = jsonFile.data.get("folders")

        if jFolders:
            folders.releaseUnpackedDir = utils.JoinPathIfValid(folders.releaseUnpackedDir, jsonDir, jFolders.get("releaseUnpackedDir"))
            folders.releaseDir = utils.JoinPathIfValid(folders.releaseDir, jsonDir, jFolders.get("releaseDir"))
            folders.tmpBigUnpackedDir = utils.JoinPathIfValid(folders.tmpBigUnpackedDir, jsonDir, jFolders.get("tmpBigUnpackedDir"))
            folders.tmpBigDir = utils.JoinPathIfValid(folders.tmpBigDir, jsonDir, jFolders.get("tmpBigDir"))
            folders.tmpReleaseUnpackedDir = utils.JoinPathIfValid(folders.tmpReleaseUnpackedDir, jsonDir, jFolders.get("tmpReleaseUnpackedDir"))

    folders.VerifyTypes()
    folders.Normalize()
    return folders
