import utils
import os
import enum
from enum import Enum
from enum import Flag
from dataclasses import dataclass
from logging import warning
from glob import glob
from build.copy import BuildCopy
from build.thing import BuildFile, BuildFileStatus, BuildThing
from data.bundles import Bundles, BundlePack, BundleItem, BundleFile
from data.folders import Folders
from data.runner import Runner
from data.tools import Tool


class BuildStep(Flag):
    NONE = 0
    PRE_BUILD = enum.auto()
    BUILD = enum.auto()
    POST_BUILD = enum.auto()
    RELEASE = enum.auto()
    INSTALL = enum.auto()
    RUN = enum.auto()
    UNINSTALL = enum.auto()


@dataclass
class BuildSetup:
    step: BuildStep
    folders: Folders
    runner: Runner
    bundles: Bundles
    tools: dict[str, Tool]

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.step, BuildStep), "BuildSetup.step has incorrect type")
        utils.RelAssert(isinstance(self.folders, Folders), "BuildSetup.folders has incorrect type")
        utils.RelAssert(isinstance(self.runner, Runner), "BuildSetup.runner has incorrect type")
        utils.RelAssert(isinstance(self.bundles, Bundles), "BuildSetup.bundles has incorrect type")
        utils.RelAssert(isinstance(self.tools, dict), "BuildSetup.tools has incorrect type")
        for k,v in self.tools.items():
            utils.RelAssert(isinstance(k, str), "BuildSetup.tools has incorrect type")
            utils.RelAssert(isinstance(v, Tool), "BuildSetup.tools has incorrect type")

    def VerifyValues(self) -> None:
        utils.RelAssert(self.tools.get("crunch") != None, "BuildSetup.tools is missing a definition for 'crunch'")
        utils.RelAssert(self.tools.get("gametextcompiler") != None, "BuildSetup.tools is missing a definition for 'gametextcompiler'")
        utils.RelAssert(self.tools.get("generalsbigcreator") != None, "BuildSetup.tools is missing a definition for 'generalsbigcreator'")


@dataclass(init=False)
class BuildFilePathInfo:
    ownerThingName: str
    md5: str

    def __init__(self):
        pass


BuildFilePathInfosT = dict[str, BuildFilePathInfo]


@dataclass(init=False)
class BuildDiff:
    newInfos: BuildFilePathInfosT
    oldInfos: BuildFilePathInfosT
    loadPath: str

    def __init__(self, loadPath: str):
        self.newInfos = dict()
        self.oldInfos = dict()
        self.loadPath = loadPath
        self.TryLoadOldInfos()

    def TryLoadOldInfos(self) -> bool:
        try:
            self.oldInfos = utils.LoadPickle(self.loadPath)
            return True
        except:
            return False

    def SaveNewInfos(self) -> bool:
        utils.SavePickle(self.loadPath, self.newInfos)
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
    things: dict[str, BuildThing]
    diff: BuildDiff

    def __init__(self, diffPath: str):
        self.things = dict()
        self.diff = BuildDiff(loadPath=diffPath)


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

    def GetThings(self, index: DataIndex) -> dict[str, BuildThing]:
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


class BuildEngine:
    setup: BuildSetup
    structure: BuildStructure


    def __init__(self):
        self.setup = None
        self.structure = None
        pass


    def Run(self, setup: BuildSetup) -> bool:
        if setup.step == BuildStep.NONE:
            warning("setup.step is NONE. Exiting.")
            return True

        self.setup = setup
        self.setup.VerifyTypes()
        self.setup.VerifyValues()

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

        self.setup = None
        self.structure = None

        return success


    def __PreBuild(self) -> bool:
        print("Do Pre Build ...")

        folders: Folders = self.setup.folders
        bundles: Bundles = self.setup.bundles

        self.structure = BuildStructure(folders)

        BuildEngine.__PopulateStructureRawBundleItems(self.structure, bundles, folders)
        BuildEngine.__PopulateStructureBigBundleItems(self.structure, bundles, folders)
        BuildEngine.__PopulateStructureRawBundlePacks(self.structure, bundles, folders)
        BuildEngine.__PopulateStructureZipBundlePacks(self.structure, bundles, folders)

        return True


    @staticmethod
    def __PopulateStructureRawBundleItems(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        item: BundleItem
        itemFile: BundleFile

        for item in bundles.items:
            newThing = BuildThing()
            newThing.name = MakeThingName(DataIndex.RAW_BUNDLE_ITEM, item.name)
            newThing.absParentDir = os.path.join(folders.buildDir, "RawBundleItems", item.name)
            newThing.files = list()
            for itemFile in item.files:
                buildFile = BuildFile()
                buildFile.absSource = itemFile.absSourceFile
                buildFile.relTarget = itemFile.relTargetFile
                buildFile.params = itemFile.params
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
                    buildFile.absSource = parentFile.AbsTarget(parentThing.absParentDir)
                    buildFile.relTarget = parentFile.RelTarget()
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

        buildCopy = BuildCopy(tools=self.setup.tools)
        structure: BuildStructure = self.structure
        index: DataIndex

        for index in DataIndex:
            data: BuildProcessData = structure.GetProcessData(index)
            data.diff.newInfos = BuildEngine.__CreateFilePathInfoDictFromThings(data.things)

            utils.pprint(data.diff)

            BuildEngine.__PopulateBuildFileStatusInThings(data.things, data.diff)
            BuildEngine.__DeleteObsoleteFilesOfThings(data.things, data.diff)

            buildCopy.CopyThings(data.things)

            data.diff.SaveNewInfos()

        return True


    @staticmethod
    def __CreateFilePathInfoDictFromThings(buildThings: dict[str, BuildThing]) -> dict[BuildFilePathInfo]:
        print("Create File Path Info Dict From Things ...")

        infos: dict[BuildFilePathInfo] = dict()
        thing: BuildThing
        for thing in buildThings.values():
            infos.update(BuildEngine.__CreateFilePathInfoDictFromThing(thing))

        return infos


    @staticmethod
    def __CreateFilePathInfoDictFromThing(thing: BuildThing) -> BuildFilePathInfosT:
        infos: BuildFilePathInfosT = dict()
        file: BuildFile

        for file in thing.files:
            absSource = file.absSource
            if not infos.get(absSource):
                info = BuildFilePathInfo()
                info.ownerThingName = thing.name
                info.md5 = utils.GetFileMd5(absSource)
                infos[absSource] = info

        for file in thing.files:
            absTarget = file.AbsTarget(thing.absParentDir)
            absTargetDirs: list[str] = utils.GetAllFileDirs(absTarget, thing.absParentDir)
            absTargetDir: str
            for absTargetDir in absTargetDirs:
                if not infos.get(absTargetDir):
                    info = BuildFilePathInfo()
                    info.ownerThingName = thing.name
                    info.md5 = ""
                    infos[absTargetDir] = info

            absTarget = file.AbsTarget(thing.absParentDir)
            if not infos.get(absTarget):
                info = BuildFilePathInfo()
                info.ownerThingName = thing.name
                info.md5 = utils.GetFileMd5(absTarget)
                infos[absTarget] = info

        return infos


    @staticmethod
    def __PopulateBuildFileStatusInThings(things: dict[str, BuildThing], diff: BuildDiff) -> None:
        print("Create Build File Status In Things ...")

        thing: BuildThing
        for thing in things.values():
            BuildEngine.__PopulateBuildFileStatusInThing(thing, diff)


    @staticmethod
    def __PopulateBuildFileStatusInThing(thing: BuildThing, diff: BuildDiff) -> None:
        file: BuildFile

        for file in thing.files:
            absSource: str = file.AbsSource()
            file.sourceStatus = BuildEngine.__PopulateBuildFileStatusInFile(absSource, diff)
            if file.sourceStatus != BuildFileStatus.UNCHANGED:
                print(f"Source {absSource} is {file.sourceStatus.name}")

        for file in thing.files:
            absTarget: str = file.AbsTarget(thing.absParentDir)
            file.targetStatus = BuildEngine.__PopulateBuildFileStatusInFile(absTarget, diff)
            if file.sourceStatus != BuildFileStatus.UNCHANGED:
                print(f"Target {absTarget} is {file.targetStatus.name}")


    @staticmethod
    def __PopulateBuildFileStatusInFile(filePath: str,  diff: BuildDiff) -> BuildFileStatus:
        if os.path.exists(filePath):
            oldInfo: BuildFilePathInfo = diff.oldInfos.get(filePath)

            if oldInfo == None:
                return BuildFileStatus.ADDED
            else:
                newInfo: BuildFilePathInfo = diff.newInfos.get(filePath)
                utils.RelAssert(newInfo != None, "Info must exist")

                if newInfo.md5 != oldInfo.md5:
                    return BuildFileStatus.CHANGED
                else:
                    return BuildFileStatus.UNCHANGED
        else:
            return BuildFileStatus.MISSING


    @staticmethod
    def __DeleteObsoleteFilesOfThings(things: dict[str, BuildThing], diff: BuildDiff) -> None:
        print("Delete Obsolete Files ...")

        def SetParentHasDeletedFiles(thing: BuildThing) -> None:
            thing.parentHasDeletedFiles = True

        thing: BuildThing

        for thing in things.values():
            fileNames: list[str] = BuildEngine.__CreateListOfExistingFilesFromThing(thing)
            fileName: str

            for fileName in fileNames:
                if os.path.exists(fileName):
                    newInfo: BuildFilePathInfo = diff.newInfos.get(fileName)
                    if newInfo == None:
                        oldInfo: BuildFilePathInfo = diff.oldInfos.get(fileName)
                        if oldInfo != None:
                            thing.ForEachChild(SetParentHasDeletedFiles)

                        if utils.DeleteFileOrPath(fileName):
                            print("Deleted", fileName)


    @staticmethod
    def __CreateListOfExistingFilesFromThing(thing: BuildThing) -> list[str]:
        search: str = os.path.join(thing.absParentDir, "**", "*")
        return glob(search, recursive=True)


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
