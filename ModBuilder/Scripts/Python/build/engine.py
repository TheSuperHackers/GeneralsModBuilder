import utils
import os
import enum
from typing import Any, Callable
from enum import Enum
from enum import Flag
from data.bundles import BundlePack
from data.bundles import BundleItem
from data.bundles import BundleFile
from data.bundles import Bundles
from data.folders import Folders
from data.runner import Runner
from data.tools import Tool
from dataclasses import dataclass, field
from logging import warning
from glob import glob


class BuildStep(Flag):
    NONE = 0
    PRE_BUILD = enum.auto()
    BUILD = enum.auto()
    POST_BUILD = enum.auto()
    RELEASE = enum.auto()
    INSTALL = enum.auto()
    RUN = enum.auto()
    UNINSTALL = enum.auto()


class BuildFileStatus(Enum):
    UNKNOWN = enum.auto()
    UNCHANGED = enum.auto()
    ADDED = enum.auto()
    CHANGED = enum.auto()


@dataclass
class BuildSetup:
    step: BuildStep
    folders: Folders
    runner: Runner
    bundles: Bundles
    tools: dict[Tool]

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.step, BuildStep), "BuildSetup.step has incorrect type")
        utils.RelAssert(isinstance(self.folders, Folders), "BuildSetup.folders has incorrect type")
        utils.RelAssert(isinstance(self.runner, Runner), "BuildSetup.runner has incorrect type")
        utils.RelAssert(isinstance(self.bundles, Bundles), "BuildSetup.bundles has incorrect type")
        utils.RelAssert(isinstance(self.tools, dict), "BuildSetup.tools has incorrect type")
        for tool in self.tools.values():
            utils.RelAssert(isinstance(tool, Tool), "BuildSetup.tools[tool] has incorrect type")

    def VerifyValues(self) -> None:
        utils.RelAssert(self.tools.get("crunch") != None, "BuildSetup.tools is missing a definition for 'crunch'")
        utils.RelAssert(self.tools.get("gametextcompiler") != None, "BuildSetup.tools is missing a definition for 'gametextcompiler'")
        utils.RelAssert(self.tools.get("generalsbigcreator") != None, "BuildSetup.tools is missing a definition for 'generalsbigcreator'")


@dataclass(init=False)
class BuildFile:
    relTarget: str
    absSource: str
    status: BuildFileStatus

    def __init__(self):
        self.status = BuildFileStatus.UNKNOWN


@dataclass(init=False)
class BuildThing:
    name: str
    absParentDir: str
    files: list[BuildFile]
    childThings: list[Any]
    parentHasDeletedFiles: bool

    def __init__(self):
        self.childThings = list()
        self.parentHasDeletedFiles = False

    def ForEachChild(self, function: Callable[[Any], None]) -> None:
        child: BuildThing
        for child in self.childThings:
            function(child)


@dataclass(init=False)
class BuildFilePathInfo:
    ownerThingName: str
    md5: str


@dataclass(init=False)
class BuildDiff:
    newInfos: dict[BuildFilePathInfo]
    oldInfos: dict[BuildFilePathInfo]
    path: str

    def __init__(self, path: str):
        self.newInfos = dict()
        self.oldInfos = dict()
        self.path = path
        self.TryLoadOldInfos()

    def TryLoadOldInfos(self) -> bool:
        try:
            self.oldInfos = utils.SerializeLoad(self.path)
            return True
        except:
            return False

    def SaveNewInfos(self) -> bool:
        utils.SerializeSave(self.path, self.newInfos)
        return True


class DataIndex(Enum):
    RAW_BUNDLE_ITEM = 0
    BIG_BUNDLE_ITEM = enum.auto()
    RAW_BUNDLE_PACK = enum.auto()
    ZIP_BUNDLE_PACK = enum.auto()

def MakeThingName(index: DataIndex, name: str) -> str:
    if index == DataIndex.RAW_BUNDLE_ITEM:
        return "RawBundleItem_" + name
    if index == DataIndex.BIG_BUNDLE_ITEM:
        return "BigBundleItem_" + name
    if index == DataIndex.RAW_BUNDLE_PACK:
        return "RawBundlePack_" + name
    if index == DataIndex.ZIP_BUNDLE_PACK:
        return "ZipBundlePack_" + name

def MakeDiffPath(index: DataIndex, folders: Folders) -> str:
    if index == DataIndex.RAW_BUNDLE_ITEM:
        return os.path.join(folders.buildDir, "RawBundleItem.pickle")
    if index == DataIndex.BIG_BUNDLE_ITEM:
        return os.path.join(folders.buildDir, "BigBundleItem.pickle")
    if index == DataIndex.RAW_BUNDLE_PACK:
        return os.path.join(folders.buildDir, "RawBundlePack.pickle")
    if index == DataIndex.ZIP_BUNDLE_PACK:
        return os.path.join(folders.buildDir, "ZipBundlePack.pickle")


@dataclass(init=False)
class BuildProcessData:
    things: dict[BuildThing]
    diff: BuildDiff

    def __init__(self, diffPath: str):
        self.things = dict()
        self.diff = BuildDiff(path=diffPath)


@dataclass(init=False)
class BuildStructure:
    data: list[BuildProcessData]

    def __init__(self, folders: Folders):
        self.data = list()
        for index in DataIndex:
            diffPath: str = MakeDiffPath(index, folders)
            self.data.append(BuildProcessData(diffPath=diffPath))

    def GetProcessData(self, index: DataIndex) -> BuildProcessData:
        return self.data[index.value]

    def GetThings(self, index: DataIndex) -> dict[BuildThing]:
        return self.data[index.value].things

    def GetDiff(self, index: DataIndex) -> BuildDiff:
        return self.data[index.value].diff

    def AddThing(self, index: DataIndex, thing: BuildThing) -> None:
        self.data[index.value].things[thing.name] = thing

    def FindThing(self, index: DataIndex, name: str) -> BuildThing:
        return self.data[index.value].things.get(name)

    def FindAnyThing(self, name: str) -> BuildThing:
        thing: BuildThing
        for index in DataIndex:
            if thing := self.FindThing(index, name):
                return thing
        return None


class Engine:
    setup: BuildSetup
    structure: BuildStructure


    def __init__(self):
        pass


    def Run(self, setup: BuildSetup) -> bool:
        self.setup = setup
        self.setup.VerifyTypes()
        self.setup.VerifyValues()

        if self.setup.step == BuildStep.NONE:
            warning("Engine.setup.step is NONE. Exiting.")
            return True

        print("Run Build with ...")
        utils.pprint(self.setup.folders)
        utils.pprint(self.setup.runner)
        utils.pprint(self.setup.bundles)
        utils.pprint(self.setup.tools)

        if self.setup.step & (BuildStep.RELEASE):
            self.setup.step |= BuildStep.BUILD

        if self.setup.step & (BuildStep.BUILD):
            self.setup.step |= BuildStep.POST_BUILD

        if self.setup.step & (BuildStep.BUILD | BuildStep.INSTALL | BuildStep.UNINSTALL):
            self.setup.step |= BuildStep.PRE_BUILD

        success = True

        if success and self.setup.step & BuildStep.PRE_BUILD:
            success &= self.__PreBuild()
        if success and self.setup.step & BuildStep.BUILD:
            success &= self.__Build()
        if success and self.setup.step & BuildStep.POST_BUILD:
            success &= self.__PostBuild()
        if success and self.setup.step & BuildStep.RELEASE:
            self.__BuildRelease()
        if success and self.setup.step & BuildStep.INSTALL:
            success &= self.__Install()
        if success and self.setup.step & BuildStep.RUN:
            self.__Run()
        if success and self.setup.step & BuildStep.UNINSTALL:
            success &= self.__Uninstall()

        return success


    def __PreBuild(self) -> bool:
        print("Do Pre Build ...")

        folders: Folders = self.setup.folders
        bundles: Bundles = self.setup.bundles

        self.structure = BuildStructure(folders)

        Engine.__PopulateStructureRawBundleItems(self.structure, bundles, folders)
        Engine.__PopulateStructureBigBundleItems(self.structure, bundles, folders)
        Engine.__PopulateStructureRawBundlePacks(self.structure, bundles, folders)
        Engine.__PopulateStructureZipBundlePacks(self.structure, bundles, folders)

        return True


    @staticmethod
    def __PopulateStructureRawBundleItems(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        item: BundleItem

        for item in bundles.items:
            newThing = BuildThing()
            newThing.name = MakeThingName(DataIndex.RAW_BUNDLE_ITEM, item.name)
            newThing.absParentDir = os.path.join(folders.buildDir, "RawBundleItems", item.name)
            newThing.files = list()
            for itemFile in item.files:
                buildFile = BuildFile()
                buildFile.absSource = itemFile.absSourceFile
                buildFile.relTarget = itemFile.relTargetFile
                newThing.files.append(buildFile)
            structure.AddThing(DataIndex.RAW_BUNDLE_ITEM, newThing)


    @staticmethod
    def __PopulateStructureBigBundleItems(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        item: BundleItem

        for item in bundles.items:
            if item.isBig:
                parentName: str = MakeThingName(DataIndex.RAW_BUNDLE_ITEM, item.name)
                parentThing: BuildThing = structure.FindAnyThing(parentName)
                assert(parentThing != None)
                newThing = BuildThing()
                newThing.name = MakeThingName(DataIndex.BIG_BUNDLE_ITEM, item.name)
                newThing.absParentDir = os.path.join(folders.buildDir, "BigBundleItems")
                newThing.files = [BuildFile()]
                newThing.files[0].absSource = parentThing.absParentDir
                newThing.files[0].relTarget = item.name + ".big"
                parentThing.childThings.append(newThing)
                structure.AddThing(DataIndex.BIG_BUNDLE_ITEM, newThing)


    @staticmethod
    def __PopulateStructureRawBundlePacks(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        pack: BundlePack
        itemName: str
        parentFile: BuildFile

        releaseUnpackedDirWithWildcards = os.path.join(folders.releaseUnpackedDir, "**", "*.*")
        absReleaseFiles = glob(releaseUnpackedDirWithWildcards, recursive=True)
        relReleaseFiles = utils.CreateRelPaths(absReleaseFiles, folders.releaseUnpackedDir)

        for pack in bundles.packs:
            newThing = BuildThing()
            newThing.name = MakeThingName(DataIndex.RAW_BUNDLE_PACK, pack.name)
            newThing.absParentDir = os.path.join(folders.buildDir, "RawBundlePacks", pack.name)
            newThing.files = list()

            for i in range(len(absReleaseFiles)):
                buildFile = BuildFile()
                buildFile.absSource = absReleaseFiles[i]
                buildFile.relTarget = relReleaseFiles[i]
                newThing.files.append(buildFile)

            for itemName in pack.itemNames:
                parentName: str = MakeThingName(DataIndex.BIG_BUNDLE_ITEM, itemName)
                parentThing: BuildThing = structure.FindAnyThing(parentName)
                if not parentThing:
                    parentName = MakeThingName(DataIndex.RAW_BUNDLE_ITEM, itemName)
                    parentThing = structure.FindAnyThing(parentName)
                    assert parentThing != None
                parentThing.childThings.append(newThing)

                for parentFile in parentThing.files:
                    buildFile = BuildFile()
                    buildFile.absSource = os.path.join(parentThing.absParentDir, parentFile.relTarget)
                    buildFile.relTarget = parentFile.relTarget
                    newThing.files.append(buildFile)

            structure.AddThing(DataIndex.RAW_BUNDLE_PACK, newThing)


    @staticmethod
    def __PopulateStructureZipBundlePacks(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        pack: BundlePack

        for pack in bundles.packs:
            parentName: str = MakeThingName(DataIndex.RAW_BUNDLE_PACK, pack.name)
            parentThing: BuildThing = structure.FindAnyThing(parentName)
            assert(parentThing != None)
            newThing = BuildThing()
            newThing.name = MakeThingName(DataIndex.ZIP_BUNDLE_PACK, pack.name)
            newThing.absParentDir = folders.releaseDir
            newThing.files = [BuildFile()]
            newThing.files[0].absSource = parentThing.absParentDir
            newThing.files[0].relTarget = pack.name + ".zip"
            parentThing.childThings.append(newThing)
            structure.AddThing(DataIndex.ZIP_BUNDLE_PACK, newThing)


    def __Build(self) -> bool:
        print("Do Build ...")

        structure: BuildStructure = self.structure
        index: DataIndex

        for index in DataIndex:
            data: BuildProcessData = structure.GetProcessData(index)
            data.diff.newInfos = Engine.__CreateFilePathInfoDictFromThings(data.things)

            utils.pprint(data.diff)

            Engine.__PopulateBuildFileStatusInThings(data.things, data.diff)
            Engine.__PrintBuildFileStatusFromThings(data.things)
            Engine.__DeleteObsoleteFilesOfThings(data.things, data.diff, structure)

            # Copy files

            data.diff.SaveNewInfos()

        #utils.pprint(self.structure)

        return True

    @staticmethod
    def __CreateFilePathInfoDictFromThings(buildThings: dict[BuildThing]) -> dict[BuildFilePathInfo]:
        print("Create File Path Info Dict From Things ...")

        infos: dict[BuildFilePathInfo] = dict()
        thing: BuildThing
        for thing in buildThings.values():
            infos.update(Engine.__CreateFilePathInfoDictFromThing(thing))

        return infos


    @staticmethod
    def __CreateFilePathInfoDictFromThing(thing: BuildThing) -> dict[BuildFilePathInfo]:
        infos: dict[BuildFilePathInfo] = dict()
        file: BuildFile

        for file in thing.files:
            absSource = file.absSource
            absTarget = os.path.join(thing.absParentDir, file.relTarget)
            absTargetDirs: list[str] = utils.GetAllFileDirs(absTarget, thing.absParentDir)
            absTargetDir: str

            for absTargetDir in absTargetDirs:
                if not infos.get(absTargetDir):
                    info = BuildFilePathInfo()
                    info.ownerThingName = thing.name
                    info.md5 = ""
                    infos[absTargetDir] = info

            if not infos.get(absSource):
                info = BuildFilePathInfo()
                info.ownerThingName = thing.name
                info.md5 = utils.GetFileMd5(absSource)
                infos[absSource] = info

            if not infos.get(absTarget):
                info = BuildFilePathInfo()
                info.ownerThingName = thing.name
                info.md5 = ""
                infos[absTarget] = info

        return infos


    @staticmethod
    def __PopulateBuildFileStatusInThings(things: dict[BuildThing], diff: BuildDiff) -> None:
        print("Create Build File Status In Things ...")

        thing: BuildThing
        for thing in things.values():
            Engine.__PopulateBuildFileStatusInThing(thing, diff)


    @staticmethod
    def __PopulateBuildFileStatusInThing(thing: BuildThing, diff: BuildDiff) -> None:
        file: BuildFile
        for file in thing.files:
            newInfo: BuildFilePathInfo = diff.newInfos.get(file.absSource)
            if newInfo != None and newInfo.md5:
                oldInfo: BuildFilePathInfo = diff.oldInfos.get(file.absSource)
                if oldInfo != None and oldInfo.md5:
                    if newInfo.md5 != oldInfo.md5:
                        file.status = BuildFileStatus.CHANGED
                    else:
                        file.status = BuildFileStatus.UNCHANGED
                else:
                    file.status = BuildFileStatus.ADDED


    @staticmethod
    def __PrintBuildFileStatusFromThings(things: dict[BuildThing]) -> None:
        thing: BuildThing
        for thing in things.values():
            Engine.__PrintBuildFileStatusFromThing(thing)


    @staticmethod
    def __PrintBuildFileStatusFromThing(thing: BuildThing) -> None:
        file: BuildFile
        for file in thing.files:
            print(f"Source {file.absSource} is {file.status.name}")


    @staticmethod
    def __DeleteObsoleteFilesOfThings(things: dict[BuildThing], diff: BuildDiff, structure: BuildStructure) -> None:
        print("Delete Obsolete Files ...")

        def SetParentHasDeletedFiles(thing: BuildThing) -> None:
            thing.parentHasDeletedFiles = True

        fileNames: list[str] = Engine.__CreateListOfGeneratedFilesFromThings(things)
        fileName: str

        for fileName in fileNames:
            if os.path.exists(fileName):
                newInfo: BuildFilePathInfo = diff.newInfos.get(fileName)
                if newInfo == None:
                    oldInfo: BuildFilePathInfo = diff.oldInfos.get(fileName)
                    if oldInfo != None:
                        thing: BuildThing = structure.FindAnyThing(oldInfo.ownerThingName)
                        thing.ForEachChild(SetParentHasDeletedFiles)

                    if utils.DeleteFileOrPath(fileName):
                        print("Deleted", fileName)


    @staticmethod
    def __CreateListOfGeneratedFilesFromThings(things: dict[BuildThing]) -> list[str]:
        files: list[str] = list()
        dirs: list[str] = Engine.__CreateListOfDirsFromThings(things)
        dir: str
        for dir in dirs:
            globFiles = glob(os.path.join(dir, "**", "*"), recursive=True)
            files.extend(globFiles)
        return files


    @staticmethod
    def __CreateListOfDirsFromThings(things: dict[BuildThing]) -> list[str]:
        dirs = list()
        thing: BuildThing
        for thing in things.values():
            dirs.append(thing.absParentDir)
        return dirs


    def __PostBuild(self) -> bool:
        print("Do Post Build ...")
        return True


    def __BuildRelease(self) -> bool:
        print("Do Build Release ...")
        return True


    def __Install(self) -> bool:
        print("Do Install ...")
        return True


    def __Run(self) -> bool:
        print("Do Run ...")
        return True


    def __Uninstall(self) -> bool:
        print("Do Uninstall ...")
        return True
