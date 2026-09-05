import os.path
from dataclasses import dataclass
from generalsmodbuilder.data.common import FinalizeParsedData, ParsedData, VerifyFormatVersion
from generalsmodbuilder.util import JsonFile
from generalsmodbuilder import util


LATEST_FOLDERS_VERSION = 1

FOLDERS_KEYS = {"version", "releaseDir", "buildDir"}


@dataclass(init=False)
class Folders(ParsedData):
    absReleaseDir: str
    absBuildDir: str

    def __init__(self):
        self.absReleaseDir = None
        self.absBuildDir = None

    def VerifyTypes(self) -> None:
        # The json values are verified where they are read. What is left is that the
        # merged result has both directories, because either one may be set by any of
        # the configuration files. This has to hold before Normalize runs.
        util.Verify(self.absReleaseDir != None, "folders.releaseDir is not set by any configuration file")
        util.Verify(self.absBuildDir != None, "folders.buildDir is not set by any configuration file")

    def Normalize(self) -> None:
        self.absReleaseDir = os.path.normpath(self.absReleaseDir)
        self.absBuildDir = os.path.normpath(self.absBuildDir)

    def VerifyValues(self) -> None:
        util.Verify(util.IsValidPathName(self.absReleaseDir), f"folders.releaseDir '{self.absReleaseDir}' is not a valid path name")
        util.Verify(util.IsValidPathName(self.absBuildDir), f"folders.buildDir '{self.absBuildDir}' is not a valid path name")
        # Compared the way file names are compared on Windows, where two paths that
        # differ in upper and lower case only name the same directory.
        util.Verify(self.absReleaseDir.lower() != self.absBuildDir.lower(),
                    f"folders.releaseDir and folders.buildDir are both '{self.absReleaseDir}', "
                    f"but the release is built out of the build directory and would overwrite it")


def MakeFoldersFromJsons(jsonFiles: list[JsonFile]) -> Folders:
    folders = Folders()

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsFileDir(jsonFile.path)
        root = util.JsonContext(jsonFile.path)
        jFolders: dict = root.GetOptional(jsonFile.data, "folders", dict)

        if jFolders:
            ctx = root.Sub("folders")
            ctx.VerifyKnownKeys(jFolders, FOLDERS_KEYS)
            VerifyFormatVersion(ctx, jFolders, LATEST_FOLDERS_VERSION)

            folders.absReleaseDir = util.JoinPathIfValid(
                folders.absReleaseDir, jsonDir, ctx.GetOptional(jFolders, "releaseDir", str))
            folders.absBuildDir = util.JoinPathIfValid(
                folders.absBuildDir, jsonDir, ctx.GetOptional(jFolders, "buildDir", str))

    FinalizeParsedData(folders)
    return folders
