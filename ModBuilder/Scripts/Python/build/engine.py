import subprocess
import utils
import os
import enum
from dataclasses import dataclass
from logging import warning
from glob import glob
from build.common import ParamsToArgs
from build.copy import BuildCopy, BuildCopyOption
from build.thing import BuildFile, BuildFileStatus, BuildThing, BuildFilesT, BuildThingsT
from build.setup import BuildSetup, BuildStep
from data.bundles import Bundles, BundlePack, BundleItem, BundleFile
from data.folders import Folders
from data.runner import Runner
from data.tools import ToolsT


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


class BuildIndex(enum.Enum):
    RAW_BUNDLE_ITEM = 0
    BIG_BUNDLE_ITEM = enum.auto()
    RAW_BUNDLE_PACK = enum.auto()
    RELEASE_BUNDLE_PACK = enum.auto()
    INSTALL_BUNDLE_PACK = enum.auto()


g_DataIndexNames: list[str] = [None] * len(BuildIndex)
g_DataIndexNames[BuildIndex.RAW_BUNDLE_ITEM.value] = "RawBundleItem"
g_DataIndexNames[BuildIndex.BIG_BUNDLE_ITEM.value] = "BigBundleItem"
g_DataIndexNames[BuildIndex.RAW_BUNDLE_PACK.value] = "RawBundlePack"
g_DataIndexNames[BuildIndex.RELEASE_BUNDLE_PACK.value] = "ReleaseBundlePack"
g_DataIndexNames[BuildIndex.INSTALL_BUNDLE_PACK.value] = "InstallBundlePack"


def GetDataName(index: BuildIndex) -> str:
    return g_DataIndexNames[index.value]

def MakeThingName(index: BuildIndex, thingName: str) -> str:
    return f"{GetDataName(index)}_{thingName}"

def MakeDiffPath(index: BuildIndex, folders: Folders) -> str:
    return os.path.join(folders.absBuildDir, f"{GetDataName(index)}.pickle")


@dataclass(init=False)
class BuildIndexData:
    index: BuildIndex
    things: BuildThingsT
    diff: BuildDiff

    def __init__(self, index: BuildIndex):
        self.index = index
        self.things = BuildThingsT()


@dataclass(init=False)
class BuildStructure:
    data: list[BuildIndexData]

    def __init__(self):
        self.data = list[BuildIndexData]()
        for index in BuildIndex:
            self.data.append(BuildIndexData(index))

    def GetProcessData(self, index: BuildIndex) -> BuildIndexData:
        return self.data[index.value]

    def GetThings(self, index: BuildIndex) -> BuildThingsT:
        return self.data[index.value].things

    def GetDiff(self, index: BuildIndex) -> BuildDiff:
        return self.data[index.value].diff

    def AddThing(self, index: BuildIndex, thing: BuildThing) -> None:
        self.data[index.value].things[thing.name] = thing

    def FindThing(self, index: BuildIndex, name: str) -> BuildThing:
        return self.data[index.value].things.get(name)

    def FindAnyThing(self, name: str) -> BuildThing:
        thing: BuildThing
        for index in BuildIndex:
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
        options = BuildCopyOption.ENABLE_BACKUP | BuildCopyOption.ENABLE_SYMLINKS
        self.installCopy = BuildCopy(tools=tools, options=options)
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
            newThing.name = MakeThingName(BuildIndex.RAW_BUNDLE_ITEM, item.name)
            newThing.absParentDir = os.path.join(folders.absBuildDir, "RawBundleItems", item.name)
            newThing.files = BuildFilesT()

            for itemFile in item.files:
                buildFile = BuildFile()
                buildFile.absSource = itemFile.absSourceFile
                buildFile.relTarget = itemFile.relTargetFile
                buildFile.params = itemFile.params
                newThing.files.append(buildFile)

            structure.AddThing(BuildIndex.RAW_BUNDLE_ITEM, newThing)


    @staticmethod
    def __PopulateStructureBigBundleItems(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        item: BundleItem

        for item in bundles.items:
            if item.isBig:
                parentName: str = MakeThingName(BuildIndex.RAW_BUNDLE_ITEM, item.name)
                parentThing: BuildThing = structure.FindAnyThing(parentName)
                assert(parentThing != None)
                newThing = BuildThing()
                newThing.name = MakeThingName(BuildIndex.BIG_BUNDLE_ITEM, item.name)
                newThing.absParentDir = os.path.join(folders.absBuildDir, "BigBundleItems")
                newThing.files = [BuildFile()]
                newThing.files[0].absSource = parentThing.absParentDir
                newThing.files[0].relTarget = item.namePrefix + item.name + item.nameSuffix + ".big"
                newThing.parentThing = parentThing

                structure.AddThing(BuildIndex.BIG_BUNDLE_ITEM, newThing)


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
            newThing.name = MakeThingName(BuildIndex.RAW_BUNDLE_PACK, pack.name)
            newThing.absParentDir = os.path.join(folders.absBuildDir, "RawBundlePacks", pack.name)
            newThing.files = BuildFilesT()

            for i in range(len(absReleaseFiles)):
                buildFile = BuildFile()
                buildFile.absSource = absReleaseFiles[i]
                buildFile.relTarget = relReleaseFiles[i]
                newThing.files.append(buildFile)

            for itemName in pack.itemNames:
                parentName: str = MakeThingName(BuildIndex.BIG_BUNDLE_ITEM, itemName)
                parentThing: BuildThing = structure.FindAnyThing(parentName)
                if parentThing == None:
                    parentName = MakeThingName(BuildIndex.RAW_BUNDLE_ITEM, itemName)
                    parentThing = structure.FindAnyThing(parentName)
                    assert(parentThing != None)

                newThing.parentThing = parentThing

                for parentFile in parentThing.files:
                    buildFile = BuildFile()
                    buildFile.absSource = parentFile.AbsTarget(parentThing.absParentDir)
                    buildFile.relTarget = parentFile.RelTarget()
                    buildFile.parentFile = parentFile
                    newThing.files.append(buildFile)

            structure.AddThing(BuildIndex.RAW_BUNDLE_PACK, newThing)


    @staticmethod
    def __PopulateStructureZipBundlePacks(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        pack: BundlePack

        for pack in bundles.packs:
            parentName: str = MakeThingName(BuildIndex.RAW_BUNDLE_PACK, pack.name)
            parentThing: BuildThing = structure.FindAnyThing(parentName)
            assert(parentThing != None)
            newThing = BuildThing()
            newThing.name = MakeThingName(BuildIndex.RELEASE_BUNDLE_PACK, pack.name)
            newThing.absParentDir = folders.absReleaseDir
            newThing.files = [BuildFile()]
            newThing.files[0].absSource = parentThing.absParentDir
            newThing.files[0].relTarget = pack.namePrefix + pack.name + pack.nameSuffix + ".zip"
            newThing.parentThing = parentThing

            structure.AddThing(BuildIndex.RELEASE_BUNDLE_PACK, newThing)


    @staticmethod
    def __PopulateStructureInstallBundlePacks(structure: BuildStructure, bundles: Bundles, runner: Runner) -> None:
        parentFile: BuildFile
        pack: BundlePack

        for pack in bundles.packs:
            if pack.install:
                parentName: str = MakeThingName(BuildIndex.RAW_BUNDLE_PACK, pack.name)
                parentThing: BuildThing = structure.FindAnyThing(parentName)
                assert(parentThing != None)
                newThing = BuildThing()
                newThing.name = MakeThingName(BuildIndex.INSTALL_BUNDLE_PACK, pack.name)
                newThing.absParentDir = runner.absGameRootDir
                newThing.files = BuildFilesT()
                newThing.parentThing = parentThing

                for parentFile in parentThing.files:
                    if utils.HasAnyFileExt(parentFile.relTarget, runner.relevantGameDataFileTypes):
                        newFile = BuildFile()
                        newFile.absSource = parentFile.AbsTarget(parentThing.absParentDir)
                        newFile.relTarget = parentFile.relTarget
                        newThing.files.append(newFile)

                structure.AddThing(BuildIndex.INSTALL_BUNDLE_PACK, newThing)


    def __Build(self) -> bool:
        print("Do Build ...")

        structure: BuildStructure = self.structure
        tools: ToolsT = self.setup.tools
        copy = BuildCopy(tools=tools, options=BuildCopyOption.ENABLE_SYMLINKS)

        BuildEngine.__BuildWithData(structure.GetProcessData(BuildIndex.RAW_BUNDLE_ITEM), copy, self.setup)
        BuildEngine.__BuildWithData(structure.GetProcessData(BuildIndex.BIG_BUNDLE_ITEM), copy, self.setup)
        BuildEngine.__BuildWithData(structure.GetProcessData(BuildIndex.RAW_BUNDLE_PACK), copy, self.setup)

        return True


    @staticmethod
    def __BuildWithData(data: BuildIndexData, copy: BuildCopy, setup: BuildSetup) -> None:
        BuildEngine.__PopulateDiffFromThings(data, setup.folders)
        BuildEngine.__PopulateBuildFileStatusInThings(data.things, data.diff)
        BuildEngine.__DeleteObsoleteFilesOfThings(data.things, data.diff)
        BuildEngine.__CopyFilesOfThings(data.things, copy)
        BuildEngine.__RehashFilePathInfoDict(data.diff.newInfos, data.things)

        data.diff.SaveNewInfos()


    @staticmethod
    def __PopulateDiffFromThings(data: BuildIndexData, folders: Folders) -> None:
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
            absRealSource = file.AbsRealSource()
            absSource = file.AbsSource()

            if not infos.get(absRealSource):
                info = BuildFilePathInfo()
                info.ownerThingName = thing.name
                info.md5 = utils.GetFileMd5(absRealSource)
                infos[absRealSource] = info

            # Plain source will not be hashed as optimization.
            if not infos.get(absSource):
                info = BuildFilePathInfo()
                info.ownerThingName = thing.name
                info.md5 = ""
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

            absRealTarget = file.AbsRealTarget(thing.absParentDir)
            if not infos.get(absRealTarget):
                info = BuildFilePathInfo()
                info.ownerThingName = thing.name
                info.md5 = utils.GetFileMd5(absRealTarget)
                infos[absRealTarget] = info

            # Plain target will not be hashed as optimization.
            if not infos.get(absTarget):
                info = BuildFilePathInfo()
                info.ownerThingName = thing.name
                info.md5 = ""
                infos[absTarget] = info

        return infos


    @staticmethod
    def __RehashFilePathInfoDict(infos: BuildFilePathInfosT, things: BuildThingsT) -> None:
        thing: BuildThing
        file: BuildFile

        for thing in things.values():
            print(f"Rehash files for {thing.name} ...")

            for file in thing.files:
                if file.RequiresRebuild():
                    absTarget: str = file.AbsTarget(thing.absParentDir)
                    targetInfo: BuildFilePathInfo = infos.get(absTarget)
                    assert(targetInfo != None)
                    targetInfo.md5 = utils.GetFileMd5(absTarget)


    @staticmethod
    def __PopulateBuildFileStatusInThings(things: BuildThingsT, diff: BuildDiff) -> None:
        thing: BuildThing

        for thing in things.values():
            print(f"Populate file status for {thing.name} ...")

            BuildEngine.__PopulateFileStatusInThing(thing, diff)


    @staticmethod
    def __PopulateFileStatusInThing(thing: BuildThing, diff: BuildDiff) -> None:
        file: BuildFile

        parentStatus: BuildFileStatus = None
        parentThing: BuildThing = thing.parentThing
        if parentThing != None:
            parentStatus = parentThing.GetMostSignificantFileStatus()

        for file in thing.files:
            parentFile: BuildFile = file.parentFile
            parentStatus: BuildFileStatus = parentStatus if parentFile == None else parentFile.GetCombinedStatus()
            absSource: str = file.AbsRealSource()
            absTarget: str = file.AbsRealTarget(thing.absParentDir)
            file.sourceStatus = BuildEngine.__GetBuildFileStatus(absSource, parentStatus, diff)
            file.targetStatus = BuildEngine.__GetBuildFileStatus(absTarget, None, diff)

        for status in BuildFileStatus:
            thing.fileCounts[status.value] = 0

        for file in thing.files:
            status: BuildFileStatus = file.GetCombinedStatus()
            thing.fileCounts[status.value] += 1

        for status in BuildFileStatus:
            if status != BuildFileStatus.UNCHANGED:
                count: int = thing.GetFileCount(status)
                if count > 0:
                    print(f"{thing.name} has {count} files {status.name}")

        for file in thing.files:
            if file.sourceStatus != BuildFileStatus.UNCHANGED:
                absSource: str = file.absSource
                print(f"Source {absSource} is {file.sourceStatus.name}")

        for file in thing.files:
            if file.targetStatus != BuildFileStatus.UNCHANGED:
                absTarget: str = file.AbsTarget(thing.absParentDir)
                print(f"Target {absTarget} is {file.targetStatus.name}")


    @staticmethod
    def __GetBuildFileStatus(filePath: str, parentStatus: BuildFileStatus, diff: BuildDiff) -> BuildFileStatus:
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
                    if parentStatus != None and parentStatus != BuildFileStatus.UNKNOWN:
                        return parentStatus
                    else:
                        return BuildFileStatus.UNCHANGED
        else:
            return BuildFileStatus.MISSING


    @staticmethod
    def __DeleteObsoleteFilesOfThings(things: BuildThingsT, diff: BuildDiff) -> None:
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
                            thing.fileCounts[BuildFileStatus.REMOVED.value] += 1

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

        tools: ToolsT = self.setup.tools
        copy = BuildCopy(tools=tools)

        BuildEngine.__BuildWithData(self.structure.GetProcessData(BuildIndex.RELEASE_BUNDLE_PACK), copy, self.setup)

        return True


    def __Install(self) -> bool:
        print("Do Install ...")

        setup: BuildSetup = self.setup
        data: BuildIndexData = self.structure.GetProcessData(BuildIndex.INSTALL_BUNDLE_PACK)

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

        data: BuildIndexData = self.structure.GetProcessData(BuildIndex.INSTALL_BUNDLE_PACK)

        BuildEngine.__UncopyFilesOfThings(data.things, self.installCopy)

        return True
