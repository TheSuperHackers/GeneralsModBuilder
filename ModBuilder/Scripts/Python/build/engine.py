import subprocess
import utils
import os
import enum
from enum import Enum
from enum import Flag
from dataclasses import dataclass
from logging import warning
from glob import glob
from build.copy import BuildCopy, BuildCopyOption
from build.thing import BuildFile, BuildFileStatus, BuildThing, BuildFilesT, BuildThingsT
from build.common import ParamsToArgs
from data.bundles import Bundles, BundlePack, BundleItem, BundleFile
from data.folders import Folders
from data.runner import Runner
from data.tools import Tool, ToolsT


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
    tools: ToolsT

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
        self.newInfos = BuildFilePathInfosT()
        self.oldInfos = BuildFilePathInfosT()
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
    INSTALL_BUNDLE_PACK = enum.auto()

def MakeThingName(index: DataIndex, name: str) -> str:
    if index == DataIndex.RAW_BUNDLE_ITEM:
        return "RawBundleItem_" + name
    if index == DataIndex.BIG_BUNDLE_ITEM:
        return "BigBundleItem_" + name
    if index == DataIndex.RAW_BUNDLE_PACK:
        return "RawBundlePack_" + name
    if index == DataIndex.ZIP_BUNDLE_PACK:
        return "ZipBundlePack_" + name
    if index == DataIndex.INSTALL_BUNDLE_PACK:
        return "InstallBundlePack_" + name

def MakeDiffPath(index: DataIndex, folders: Folders) -> str:
    if index == DataIndex.RAW_BUNDLE_ITEM:
        return os.path.join(folders.absBuildDir, "RawBundleItem.pickle")
    if index == DataIndex.BIG_BUNDLE_ITEM:
        return os.path.join(folders.absBuildDir, "BigBundleItem.pickle")
    if index == DataIndex.RAW_BUNDLE_PACK:
        return os.path.join(folders.absBuildDir, "RawBundlePack.pickle")
    if index == DataIndex.ZIP_BUNDLE_PACK:
        return os.path.join(folders.absBuildDir, "ZipBundlePack.pickle")
    if index == DataIndex.INSTALL_BUNDLE_PACK:
        return os.path.join(folders.absBuildDir, "InstallBundlePack.pickle")


@dataclass(init=False)
class BuildProcessData:
    index: DataIndex
    things: BuildThingsT
    diff: BuildDiff

    def __init__(self, index: DataIndex):
        self.index = index
        self.things = BuildThingsT()


@dataclass(init=False)
class BuildStructure:
    data: list[BuildProcessData]

    def __init__(self):
        self.data = list[BuildProcessData]()
        for index in DataIndex:
            self.data.append(BuildProcessData(index))

    def GetProcessData(self, index: DataIndex) -> BuildProcessData:
        return self.data[index.value]

    def GetThings(self, index: DataIndex) -> BuildThingsT:
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
    installCopy: BuildCopy


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
        runner: Runner = self.setup.runner
        bundles: Bundles = self.setup.bundles
        tools: ToolsT = self.setup.tools

        self.installCopy = BuildCopy(tools=tools, options=BuildCopyOption.ENABLE_BACKUP)
        self.structure = BuildStructure()

        BuildEngine.__PopulateStructureRawBundleItems(self.structure, bundles, folders)
        BuildEngine.__PopulateStructureBigBundleItems(self.structure, bundles, folders)
        BuildEngine.__PopulateStructureRawBundlePacks(self.structure, bundles, folders)
        BuildEngine.__PopulateStructureZipBundlePacks(self.structure, bundles, folders)
        BuildEngine.__PopulateStructureInstallBundlePacks(self.structure, bundles, runner)

        return True


    @staticmethod
    def __PopulateStructureRawBundleItems(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        item: BundleItem
        itemFile: BundleFile

        for item in bundles.items:
            newThing = BuildThing()
            newThing.name = MakeThingName(DataIndex.RAW_BUNDLE_ITEM, item.name)
            newThing.absParentDir = os.path.join(folders.absBuildDir, "RawBundleItems", item.name)
            newThing.files = BuildFilesT()
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
                newThing.absParentDir = os.path.join(folders.absBuildDir, "BigBundleItems")
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

        releaseUnpackedDirWithWildcards = os.path.join(folders.absReleaseUnpackedDir, "**", "*.*")
        absReleaseFiles = glob(releaseUnpackedDirWithWildcards, recursive=True)
        relReleaseFiles = utils.CreateRelPaths(absReleaseFiles, folders.absReleaseUnpackedDir)

        for pack in bundles.packs:
            newThing = BuildThing()
            newThing.name = MakeThingName(DataIndex.RAW_BUNDLE_PACK, pack.name)
            newThing.absParentDir = os.path.join(folders.absBuildDir, "RawBundlePacks", pack.name)
            newThing.files = BuildFilesT()

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
            newThing.absParentDir = folders.absReleaseDir
            newThing.files = [BuildFile()]
            newThing.files[0].absSource = parentThing.absParentDir
            newThing.files[0].relTarget = pack.name + ".zip"
            parentThing.childThings.append(newThing)
            structure.AddThing(DataIndex.ZIP_BUNDLE_PACK, newThing)


    @staticmethod
    def __PopulateStructureInstallBundlePacks(structure: BuildStructure, bundles: Bundles, runner: Runner) -> None:
        parentFile: BuildFile
        pack: BundlePack

        for pack in bundles.packs:
            if pack.install:
                parentName: str = MakeThingName(DataIndex.RAW_BUNDLE_PACK, pack.name)
                parentThing: BuildThing = structure.FindAnyThing(parentName)
                assert(parentThing != None)
                newThing = BuildThing()
                newThing.name = MakeThingName(DataIndex.INSTALL_BUNDLE_PACK, pack.name)
                newThing.absParentDir = runner.absGameRootDir
                newThing.files = BuildFilesT()

                for parentFile in parentThing.files:
                    if utils.HasAnyFileExt(parentFile.relTarget, runner.relevantGameDataFileTypes):
                        newFile = BuildFile()
                        newFile.absSource = parentFile.AbsTarget(parentThing.absParentDir)
                        newFile.relTarget = parentFile.relTarget
                        newThing.files.append(newFile)

                parentThing.childThings.append(newThing)
                structure.AddThing(DataIndex.INSTALL_BUNDLE_PACK, newThing)


    def __Build(self) -> bool:
        print("Do Build ...")

        BuildEngine.__BuildWithData(self.structure.GetProcessData(DataIndex.RAW_BUNDLE_ITEM), self.setup)
        BuildEngine.__BuildWithData(self.structure.GetProcessData(DataIndex.BIG_BUNDLE_ITEM), self.setup)
        BuildEngine.__BuildWithData(self.structure.GetProcessData(DataIndex.RAW_BUNDLE_PACK), self.setup)

        return True


    @staticmethod
    def __BuildWithData(data: BuildProcessData, setup: BuildSetup) -> None:
        copy = BuildCopy(tools=setup.tools)

        BuildEngine.__PopulateDiffFromThings(data, setup.folders)
        BuildEngine.__PopulateBuildFileStatusInThings(data.things, data.diff)
        BuildEngine.__DeleteObsoleteFilesOfThings(data.things, data.diff)
        BuildEngine.__CopyFilesOfThings(data.things, copy)
        BuildEngine.__RehashFilePathInfoDict(data.diff.newInfos, data.things)

        data.diff.SaveNewInfos()


    @staticmethod
    def __PopulateDiffFromThings(data: BuildProcessData, folders: Folders) -> None:
        path: str = MakeDiffPath(data.index, folders)
        data.diff = BuildDiff(path)
        data.diff.newInfos = BuildEngine.__CreateFilePathInfoDictFromThings(data.things)


    @staticmethod
    def __CreateFilePathInfoDictFromThings(things: BuildThingsT) -> BuildFilePathInfosT:
        infos = BuildFilePathInfosT()
        thing: BuildThing

        for thing in things.values():
            print(f"Create file infos for {thing.name} ...")

            infos.update(BuildEngine.__CreateFilePathInfoDictFromThing(thing))

        return infos


    @staticmethod
    def __CreateFilePathInfoDictFromThing(thing: BuildThing) -> BuildFilePathInfosT:
        infos = BuildFilePathInfosT()
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
    def __RehashFilePathInfoDict(infos: BuildFilePathInfosT, things: BuildThingsT) -> None:
        thing: BuildThing
        file: BuildFile

        for thing in things.values():
            print(f"Rehash files for {thing.name} ...")

            for file in thing.files:
                if file.targetStatus != BuildFileStatus.UNCHANGED:
                    absTarget: str = file.AbsTarget(thing.absParentDir)
                    targetInfo: BuildFilePathInfo = infos.get(absTarget)
                    targetInfo.md5 = utils.GetFileMd5(absTarget)


    @staticmethod
    def __PopulateBuildFileStatusInThings(things: BuildThingsT, diff: BuildDiff) -> None:
        thing: BuildThing

        for thing in things.values():
            print(f"Populate file status for {thing.name} ...")

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
    def __DeleteObsoleteFilesOfThings(things: BuildThingsT, diff: BuildDiff) -> None:
        def SetParentHasDeletedFiles(thing: BuildThing) -> None:
            thing.parentHasDeletedFiles = True

        thing: BuildThing

        for thing in things.values():
            print(f"Delete files for {thing.name} ...")

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


    @staticmethod
    def __CopyFilesOfThings(things: BuildThingsT, copy: BuildCopy) -> None:
        thing: BuildThing

        for thing in things.values():
            print(f"Copy files for {thing.name} ...")

            copy.CopyThing(thing)


    @staticmethod
    def __UncopyFilesOfThings(things: BuildThingsT, copy: BuildCopy) -> None:
        thing: BuildThing

        for thing in things.values():
            print(f"Remove files for {thing.name} ...")

            copy.UncopyThing(thing)


    def __PostBuild(self) -> bool:
        print("Do Post Build ...")
        return True


    def __BuildRelease(self) -> bool:
        print("Do Build Release ...")

        BuildEngine.__BuildWithData(self.structure.GetProcessData(DataIndex.ZIP_BUNDLE_PACK), self.setup)

        return True


    def __Install(self) -> bool:
        print("Do Install ...")

        setup: BuildSetup = self.setup
        data: BuildProcessData = self.structure.GetProcessData(DataIndex.INSTALL_BUNDLE_PACK)

        BuildEngine.__PopulateDiffFromThings(data, setup.folders)
        BuildEngine.__PopulateBuildFileStatusInThings(data.things, data.diff)
        BuildEngine.__CopyFilesOfThings(data.things, self.installCopy)
        BuildEngine.__RehashFilePathInfoDict(data.diff.newInfos, data.things)

        data.diff.SaveNewInfos()

        installedFiles: list[str] = BuildEngine.__GetAllTargetFilesFromThings(data.things)
        BuildEngine.__CheckGameInstallFiles(installedFiles, self.setup.runner)

        return True


    @staticmethod
    def __CheckGameInstallFiles(installedFiles: list[str], runner: Runner) -> None:
        search: str = os.path.join(runner.absGameRootDir, "**", "*")
        allGameFiles: list[str] = glob(search, recursive=True)
        gameDataFilesFilter = filter(lambda file: utils.HasAnyFileExt(file, runner.relevantGameDataFileTypes), allGameFiles)
        relevantGameDataFiles = list[str](gameDataFilesFilter)
        expectedGameDataFiles = runner.absRegularGameDataFiles
        expectedGameDataFiles.extend(installedFiles)
        expectedGameDataFilesDict: dict[str, None] = dict.fromkeys(runner.absRegularGameDataFiles, 1)
        unexpectedGameFiles = list[str]()

        file: str
        for file in relevantGameDataFiles:
            if expectedGameDataFilesDict.get(file) == None:
                unexpectedGameFiles.append(file)

        print(f"Checking game install at {runner.absGameRootDir} ...")
        if len(unexpectedGameFiles) > 0:
            print(f"WARNING: The installed Mod may not work correctly. {len(unexpectedGameFiles)} unexpected file(s) were found:")
            for file in unexpectedGameFiles:
                print("Unexpected:", file)


    @staticmethod
    def __GetAllTargetFilesFromThings(things: BuildThingsT) -> list[str]:
        allFiles = list[str]()
        thing: BuildThing
        file: BuildFile

        for thing in things.values():
            for file in thing.files:
                absTarget: str = file.AbsTarget(thing.absParentDir)
                allFiles.append(absTarget)

        return allFiles


    def __Run(self) -> bool:
        runner: Runner = self.setup.runner
        exec: str = runner.AbsGameExeFile()
        args: list[str] = [exec]
        args.extend(ParamsToArgs(runner.gameExeArgs))

        print("Run", " ".join(args))

        subprocess.run(args=args)

        return True


    def __Uninstall(self) -> bool:
        print("Do Uninstall ...")

        data: BuildProcessData = self.structure.GetProcessData(DataIndex.INSTALL_BUNDLE_PACK)

        BuildEngine.__UncopyFilesOfThings(data.things, self.installCopy)

        return True
