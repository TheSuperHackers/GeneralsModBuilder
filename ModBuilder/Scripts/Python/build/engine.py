import utils
import os
import enum
import shutil
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
    ADDED = enum.auto()
    CHANGED = enum.auto()
    UNCHANGED = enum.auto()


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
    parentFile: Any

    def __init__(self):
        self.status = BuildFileStatus.UNKNOWN
        self.parentFile = None


@dataclass(init=False)
class BuildThing:
    name: str
    absParentDir: str
    files: list[BuildFile]
    parentThing: Any
    childThings: list[Any]
    forceRebuild: bool

    def __init__(self):
        self.parentThing = None
        self.childThings = list()
        self.forceRebuild = False

    def ForEachChild(self, function: Callable[[Any], None]) -> None:
        child: BuildThing
        for child in self.childThings:
            function(child)
            child.ForEachChild(function)


@dataclass(init=False)
class BuildStructure:
    rawBundleItems: dict[BuildThing]
    bigBundleItems: dict[BuildThing]
    rawBundlePacks: dict[BuildThing]
    zipBundlePacks: dict[BuildThing]

    def FindAny(self, name: str) -> BuildThing:
        thing: BuildThing
        if thing := self.rawBundleItems.get(name):
            return thing
        if thing := self.bigBundleItems.get(name):
            return thing
        if thing := self.rawBundlePacks.get(name):
            return thing
        if thing := self.zipBundlePacks.get(name):
            return thing
        return None

    def FindRawBundleItem(self, itemName: str) -> BuildThing:
        return self.rawBundleItems.get(BuildStructure.GetRawBundleItemName(itemName))

    def FindBigBundleItem(self, itemName: str) -> BuildThing:
        return self.bigBundleItems.get(BuildStructure.GetBigBundleItemName(itemName))

    def FindRawBundlePack(self, packName: str) -> BuildThing:
        return self.rawBundlePacks.get(BuildStructure.GetRawBundlePackName(packName))

    def FindZipBundlePack(self, packName: str) -> BuildThing:
        return self.zipBundlePacks.get(BuildStructure.GetZipBundlePackName(packName))

    @staticmethod
    def GetRawBundleItemName(itemName: str) -> str:
        return "RawBundleItem_" + itemName

    @staticmethod
    def GetBigBundleItemName(itemName: str) -> str:
        return "BigBundleItem_" + itemName

    @staticmethod
    def GetRawBundlePackName(packName: str) -> str:
        return "RawBundlePack_" + packName

    @staticmethod
    def GetZipBundlePackName(packName: str) -> str:
        return "ZipBundlePack_" + packName


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
        self.TryLoadOld()

    def TryLoadOld(self) -> bool:
        try:
            self.oldInfos = utils.SerializeLoad(self.path)
            return True
        except:
            return False

    def SaveNew(self) -> bool:
        utils.SerializeSave(self.path, self.newInfos)
        return True


class Engine:
    setup: BuildSetup
    structure: BuildStructure
    diff: BuildDiff


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

        self.structure = BuildStructure()

        Engine.__CreateStructureRawBundleItems(self.structure, bundles, folders)
        Engine.__CreateStructureBigBundleItems(self.structure, bundles, folders)
        Engine.__CreateStructureRawBundlePacks(self.structure, bundles, folders)
        Engine.__CreateStructureZipBundlePacks(self.structure, bundles, folders)

        return True


    @staticmethod
    def __CreateStructureRawBundleItems(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        structure.rawBundleItems = dict()
        item: BundleItem

        for item in bundles.items:
            newThing = BuildThing()
            newThing.name = BuildStructure.GetRawBundleItemName(item.name)
            newThing.absParentDir = os.path.join(folders.buildDir, "RawBundleItems", item.name)
            newThing.files = list()
            for itemFile in item.files:
                buildFile = BuildFile()
                buildFile.absSource = itemFile.absSourceFile
                buildFile.relTarget = itemFile.relTargetFile
                newThing.files.append(buildFile)
            structure.rawBundleItems[newThing.name] = newThing


    @staticmethod
    def __CreateStructureBigBundleItems(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        structure.bigBundleItems = dict()
        item: BundleItem

        for item in bundles.items:
            if item.isBig:
                parentThing: BuildThing = structure.FindRawBundleItem(item.name)
                assert(parentThing != None)
                newThing = BuildThing()
                newThing.name = BuildStructure.GetBigBundleItemName(item.name)
                newThing.absParentDir = os.path.join(folders.buildDir, "BigBundleItems")
                newThing.parentThing = parentThing
                newThing.files = [BuildFile()]
                newThing.files[0].absSource = parentThing.absParentDir
                newThing.files[0].relTarget = item.name + ".big"
                parentThing.childThings.append(newThing)
                structure.bigBundleItems[newThing.name] = newThing


    @staticmethod
    def __CreateStructureRawBundlePacks(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        structure.rawBundlePacks = dict()
        pack: BundlePack

        releaseUnpackedDirWithWildcards = os.path.join(folders.releaseUnpackedDir, "**", "*.*")
        absReleaseFiles = glob(releaseUnpackedDirWithWildcards, recursive=True)
        relReleaseFiles = utils.CreateRelPaths(absReleaseFiles, folders.releaseUnpackedDir)

        for pack in bundles.packs:
            newThing = BuildThing()
            newThing.name = BuildStructure.GetRawBundlePackName(pack.name)
            newThing.absParentDir = os.path.join(folders.buildDir, "RawBundlePacks", pack.name)
            newThing.files = list()

            for i in range(len(absReleaseFiles)):
                buildFile = BuildFile()
                buildFile.absSource = absReleaseFiles[i]
                buildFile.relTarget = relReleaseFiles[i]
                newThing.files.append(buildFile)

            for packItemName in pack.itemNames:
                parentThing: BuildThing
                parentThing = structure.FindBigBundleItem(packItemName)
                if not parentThing:
                    parentThing = structure.FindRawBundleItem(packItemName)
                    assert parentThing != None
                parentThing.childThings.append(newThing)

                for parentFile in parentThing.files:
                    buildFile = BuildFile()
                    buildFile.absSource = os.path.join(parentThing.absParentDir, parentFile.relTarget)
                    buildFile.relTarget = parentFile.relTarget
                    buildFile.parentFile = parentFile
                    newThing.files.append(buildFile)

            structure.rawBundlePacks[newThing.name] = newThing


    @staticmethod
    def __CreateStructureZipBundlePacks(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        structure.zipBundlePacks = dict()
        pack: BundlePack

        for pack in bundles.packs:
            parentThing: BuildThing = structure.FindRawBundlePack(pack.name)
            assert(parentThing != None)
            newThing = BuildThing()
            newThing.name = BuildStructure.GetZipBundlePackName(pack.name)
            newThing.absParentDir = folders.releaseDir
            newThing.parentThing = parentThing
            newThing.files = [BuildFile()]
            newThing.files[0].absSource = parentThing.absParentDir
            newThing.files[0].relTarget = pack.name + ".zip"
            parentThing.childThings.append(newThing)
            structure.zipBundlePacks[newThing.name] = newThing


    def __Build(self) -> bool:
        print("Do Build ...")

        diffFile = os.path.join(self.setup.folders.buildDir, "Diff.pickle")
        self.diff = BuildDiff(diffFile)
        self.diff.newInfos = dict()
        self.diff.newInfos.update(Engine.__CreateFilePathInfoDictFromThings(self.structure.rawBundleItems, sourceMd5=True))
        self.diff.newInfos.update(Engine.__CreateFilePathInfoDictFromThings(self.structure.bigBundleItems))
        self.diff.newInfos.update(Engine.__CreateFilePathInfoDictFromThings(self.structure.rawBundlePacks))
        self.diff.newInfos.update(Engine.__CreateFilePathInfoDictFromThings(self.structure.zipBundlePacks))

        utils.pprint(self.diff)
        
        Engine.__CreateFileStatusInStructure(self.structure, self.diff)

        #utils.pprint(self.structure)

        Engine.__DeleteObsoleteFiles(self.structure, self.diff)

        return True


    @staticmethod
    def __CreateFilePathInfoDictFromThings(buildThings: dict[BuildThing], sourceMd5=False) -> dict[BuildFilePathInfo]:
        print("Create File Path Info Dict From Things ...")

        infos: dict[BuildFilePathInfo] = dict()
        thing: BuildThing
        file: BuildFile

        for thing in buildThings.values():
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
                    info.md5 = utils.GetFileMd5(absSource) if sourceMd5 else ""
                    infos[absSource] = info

                if not infos.get(absTarget):
                    info = BuildFilePathInfo()
                    info.ownerThingName = thing.name
                    info.md5 = ""
                    infos[absTarget] = info

        return infos


    @staticmethod
    def __CreateFileStatusInStructure(structure: BuildStructure, diff: BuildDiff) -> None:
        print("Create Build File Status ...")

        Engine.__CreateBuildFileStatusFromDiff(structure.rawBundleItems, diff)
        Engine.__CreateBuildFileStatusFromParents(structure.bigBundleItems)
        Engine.__CreateBuildFileStatusFromParents(structure.rawBundlePacks)
        Engine.__CreateBuildFileStatusFromParents(structure.zipBundlePacks)

        Engine.__PrintBuildFileStatus(structure.rawBundleItems)
        Engine.__PrintBuildFileStatus(structure.bigBundleItems)
        Engine.__PrintBuildFileStatus(structure.rawBundlePacks)
        Engine.__PrintBuildFileStatus(structure.zipBundlePacks)


    @staticmethod
    def __CreateBuildFileStatusFromDiff(things: dict[BuildThing], diff: BuildDiff) -> None:
        thing: BuildThing
        file: BuildFile

        for thing in things.values():
            for file in thing.files:
                newInfo: BuildFilePathInfo = diff.newInfos.get(file.absSource)
                oldInfo: BuildFilePathInfo = diff.oldInfos.get(file.absSource)

                if bool(newInfo) and bool(oldInfo):
                    if newInfo.md5 != oldInfo.md5:
                        file.status = BuildFileStatus.CHANGED
                    else:
                        file.status = BuildFileStatus.UNCHANGED
                elif bool(newInfo):
                    file.status = BuildFileStatus.ADDED


    @staticmethod
    def __CreateBuildFileStatusFromParents(things: dict[BuildThing]) -> None:
        parentThing: BuildThing
        parentFile: BuildFile
        thing: BuildThing
        file: BuildFile
        status: BuildFileStatus

        for thing in things.values():
            parentThing = thing.parentThing
            if bool(parentThing):
                status = BuildFileStatus.UNKNOWN
                for parentFile in parentThing.files:
                    if parentFile.status == BuildFileStatus.CHANGED:
                        status = BuildFileStatus.CHANGED
                        break
                    elif parentFile.status == BuildFileStatus.ADDED:
                        if status != BuildFileStatus.CHANGED:
                            status = BuildFileStatus.ADDED
                    elif parentFile.status == BuildFileStatus.UNCHANGED:
                        if status != BuildFileStatus.CHANGED and status != BuildFileStatus.ADDED:
                            status = BuildFileStatus.UNCHANGED
                for file in thing.files:
                    file.status = status
            else:
                for file in thing.files:
                    parentFile = file.parentFile
                    if bool(parentFile):
                        file.status = parentFile.status
                    else:
                        absSource = file.absSource
                        absTarget = os.path.join(thing.absParentDir, file.relTarget)
                        if os.path.isfile(absSource) and os.path.isfile(absTarget):
                            sourceMd5 = utils.GetFileMd5(absSource)
                            targetMd5 = utils.GetFileMd5(absTarget)
                            if sourceMd5 != targetMd5:
                                file.status = BuildFileStatus.CHANGED
                            else:
                                file.status = BuildFileStatus.UNCHANGED
                        elif os.path.isfile(absSource):
                            file.status = BuildFileStatus.ADDED


    @staticmethod
    def __PrintBuildFileStatus(things: dict[BuildThing]) -> None:
        thing: BuildThing
        file: BuildFile
        for thing in things.values():
            for file in thing.files:
                print(f"File {file.absSource} is {file.status.name}")


    @staticmethod
    def __DeleteObsoleteFiles(structure: BuildStructure, diff: BuildDiff) -> None:
        print("Delete Obsolete Files ...")

        def __SetForceRebuildInThing(thing: BuildThing) -> None:
            thing.forceRebuild = True

        fileNames: list[str] = list()
        fileNames.extend(Engine.__CreateListOfGeneratedFilesFromThings(structure.rawBundleItems))
        fileNames.extend(Engine.__CreateListOfGeneratedFilesFromThings(structure.bigBundleItems))
        fileNames.extend(Engine.__CreateListOfGeneratedFilesFromThings(structure.rawBundlePacks))
        fileNames.extend(Engine.__CreateListOfGeneratedFilesFromThings(structure.zipBundlePacks))
        fileName: str

        for fileName in fileNames:
            if os.path.exists(fileName) and not diff.newInfos.get(fileName):
                oldInfo: BuildFilePathInfo = diff.oldInfos.get(fileName)
                if oldInfo:
                    thing: BuildThing = structure.FindAny(oldInfo.ownerThingName)
                    thing.ForEachChild(__SetForceRebuildInThing)
                if os.path.isfile(fileName):
                    os.remove(fileName)
                    print("Deleted", fileName)
                elif os.path.isdir(fileName):
                    shutil.rmtree(fileName)
                    print("Deleted", fileName)


    @staticmethod
    def __CreateListOfGeneratedFilesFromThings(things: dict[BuildThing]) -> list[str]:
        dirs: list[str] = Engine.__CreateListOfDirsFromThings(things)
        dir: str
        files: list[str] = list()
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

        self.diff.SaveNew()

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
