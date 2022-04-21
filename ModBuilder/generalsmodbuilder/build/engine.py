import importlib
import subprocess
import sys
import util
import os
import enum
from dataclasses import dataclass
from logging import warning
from glob import glob
from build.common import ParamsToArgs
from build.copy import BuildCopy, BuildCopyOption
from build.thing import BuildFile, BuildFileStatus, BuildThing, BuildFilesT, BuildThingsT
from build.setup import BuildSetup, BuildStep
from data.bundles import Bundles, BundlePack, BundleItem, BundleFile, BundleEvent, BundleEventType
from data.folders import Folders
from data.runner import Runner
from data.tools import ToolsT


@dataclass(init=False)
class BuildFilePathInfo:
    ownerThingName: str
    md5: str

    def __init__(self):
        self.ownerThingName = None
        self.md5 = None


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
            self.oldInfos = util.LoadPickle(self.loadPath)
            return True
        except:
            return False

    def SaveNewInfos(self) -> bool:
        util.SavePickle(self.loadPath, self.newInfos)
        return True


class BuildIndex(enum.Enum):
    RawBundleItem = 0
    BigBundleItem = enum.auto()
    RawBundlePack = enum.auto()
    ReleaseBundlePack = enum.auto()
    InstallBundlePack = enum.auto()


def GetDataName(index: BuildIndex) -> str:
    return index.name

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
        self.diff = None


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
    installLanguagePicklePath: str


    def __init__(self):
        self.__Reset()


    def __Reset(self):
        self.setup = None
        self.structure = None
        self.installCopy = None
        self.installLanguagePicklePath = None


    def Run(self, setup: BuildSetup) -> bool:
        print("Run Build ...")

        if setup.step == BuildStep.Zero:
            warning("setup.step is NONE. Exiting.")
            return True

        self.setup = setup
        self.setup.VerifyTypes()
        self.setup.VerifyValues()

        if self.setup.printConfig:
            util.pprint(self.setup.folders)
            util.pprint(self.setup.runner)
            util.pprint(self.setup.bundles)
            util.pprint(self.setup.tools)

        if self.setup.step & (BuildStep.Release):
            self.setup.step |= BuildStep.Build

        if self.setup.step & (BuildStep.Build):
            self.setup.step |= BuildStep.PostBuild

        if self.setup.step & (BuildStep.Build | BuildStep.Install | BuildStep.Uninstall):
            self.setup.step |= BuildStep.PreBuild

        success = True

        if success and self.setup.step & BuildStep.PreBuild:
            success &= self.__PreBuild()
        if success and self.setup.step & BuildStep.Build:
            success &= self.__Build()
        if success and self.setup.step & BuildStep.PostBuild:
            success &= self.__PostBuild()
        if success and self.setup.step & BuildStep.Release:
            self.__BuildRelease()
        if success and self.setup.step & BuildStep.Install:
            success &= self.__Install()
        if success and self.setup.step & BuildStep.Run:
            self.__Run()
        if success and self.setup.step & BuildStep.Uninstall:
            success &= self.__Uninstall()

        self.__Reset()

        return success


    def __CallScript(event: BundleEvent, kwargs: dict) -> bool:
        scriptPath: str = event.GetScriptDir()
        scriptName: str = event.GetScriptName()

        if not scriptPath in sys.path:
            sys.path.append(scriptPath)

        kwargs.update(event.kwargs)

        importlib.import_module(scriptName)
        scriptModule: object = sys.modules.get(scriptName)
        scriptFunction = getattr(scriptModule, event.funcName)
        scriptFunction(**kwargs)

        return True


    def __SendBundleEvents(bundles: Bundles, eventType: BundleEventType):
        sent: bool = False
        item: BundleItem
        pack: BundlePack

        for item in bundles.items:
            event: BundleEvent = item.events.get(eventType)
            if event != None:
                kwargs = dict()
                kwargs["BundleItem"] = item
                sent |= BuildEngine.__CallScript(event, kwargs)
                item.VerifyTypes()
                item.Normalize()

        for pack in bundles.packs:
            event: BundleEvent = pack.events.get(eventType)
            if event != None:
                kwargs = dict()
                kwargs["BundlePack"] = pack
                sent |= BuildEngine.__CallScript(event, kwargs)
                pack.VerifyTypes()
                pack.Normalize()

        return sent


    def __PreBuild(self) -> bool:
        print("Do Pre Build ...")

        folders: Folders = self.setup.folders
        runner: Runner = self.setup.runner
        bundles: Bundles = self.setup.bundles
        tools: ToolsT = self.setup.tools

        options = BuildCopyOption.EnableBackup | BuildCopyOption.EnableSymlinks
        self.structure = BuildStructure()
        self.installCopy = BuildCopy(tools=tools, options=options)
        self.installLanguagePicklePath = os.path.join(folders.absBuildDir, "GameLanguage.pickle")

        sent: bool = BuildEngine.__SendBundleEvents(bundles, BundleEventType.OnPreBuild)

        if sent:
            bundles.VerifyValues()

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
            newThing.name = MakeThingName(BuildIndex.RawBundleItem, item.name)
            newThing.absParentDir = os.path.join(folders.absBuildDir, "RawBundleItems", item.name)
            newThing.files = BuildFilesT()

            for itemFile in item.files:
                buildFile = BuildFile()
                buildFile.absSource = itemFile.absSourceFile
                buildFile.relTarget = itemFile.relTargetFile
                buildFile.params = itemFile.params
                newThing.files.append(buildFile)

            structure.AddThing(BuildIndex.RawBundleItem, newThing)


    @staticmethod
    def __PopulateStructureBigBundleItems(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        item: BundleItem

        for item in bundles.items:
            if item.isBig:
                parentName: str = MakeThingName(BuildIndex.RawBundleItem, item.name)
                parentThing: BuildThing = structure.FindAnyThing(parentName)
                assert(parentThing != None)
                newThing = BuildThing()
                newThing.name = MakeThingName(BuildIndex.BigBundleItem, item.name)
                newThing.absParentDir = os.path.join(folders.absBuildDir, "BigBundleItems")
                newThing.files = [BuildFile()]
                newThing.files[0].absSource = parentThing.absParentDir
                newThing.files[0].relTarget = item.namePrefix + item.name + item.nameSuffix + ".big"
                newThing.parentThing = parentThing

                structure.AddThing(BuildIndex.BigBundleItem, newThing)


    @staticmethod
    def __PopulateStructureRawBundlePacks(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        pack: BundlePack
        itemName: str
        parentFile: BuildFile

        releaseUnpackedDirWithWildcards = os.path.join(folders.absReleaseUnpackedDir, "**", "*.*")
        absReleaseFiles = glob(releaseUnpackedDirWithWildcards, recursive=True)
        relReleaseFiles = util.CreateRelPaths(absReleaseFiles, folders.absReleaseUnpackedDir)

        for pack in bundles.packs:
            newThing = BuildThing()
            newThing.name = MakeThingName(BuildIndex.RawBundlePack, pack.name)
            newThing.absParentDir = os.path.join(folders.absBuildDir, "RawBundlePacks", pack.name)
            newThing.files = BuildFilesT()

            for i in range(len(absReleaseFiles)):
                buildFile = BuildFile()
                buildFile.absSource = absReleaseFiles[i]
                buildFile.relTarget = relReleaseFiles[i]
                newThing.files.append(buildFile)

            for itemName in pack.itemNames:
                parentName: str = MakeThingName(BuildIndex.BigBundleItem, itemName)
                parentThing: BuildThing = structure.FindAnyThing(parentName)
                if parentThing == None:
                    parentName = MakeThingName(BuildIndex.RawBundleItem, itemName)
                    parentThing = structure.FindAnyThing(parentName)
                    assert(parentThing != None)

                newThing.parentThing = parentThing

                for parentFile in parentThing.files:
                    buildFile = BuildFile()
                    buildFile.absSource = parentFile.AbsTarget(parentThing.absParentDir)
                    buildFile.relTarget = parentFile.RelTarget()
                    buildFile.parentFile = parentFile
                    newThing.files.append(buildFile)

            structure.AddThing(BuildIndex.RawBundlePack, newThing)


    @staticmethod
    def __PopulateStructureZipBundlePacks(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        pack: BundlePack

        for pack in bundles.packs:
            parentName: str = MakeThingName(BuildIndex.RawBundlePack, pack.name)
            parentThing: BuildThing = structure.FindAnyThing(parentName)
            assert(parentThing != None)
            newThing = BuildThing()
            newThing.name = MakeThingName(BuildIndex.ReleaseBundlePack, pack.name)
            newThing.absParentDir = folders.absReleaseDir
            newThing.files = [BuildFile()]
            newThing.files[0].absSource = parentThing.absParentDir
            newThing.files[0].relTarget = pack.namePrefix + pack.name + pack.nameSuffix + ".zip"
            newThing.parentThing = parentThing

            structure.AddThing(BuildIndex.ReleaseBundlePack, newThing)


    @staticmethod
    def __PopulateStructureInstallBundlePacks(structure: BuildStructure, bundles: Bundles, runner: Runner) -> None:
        parentFile: BuildFile
        pack: BundlePack

        for pack in bundles.packs:
            if pack.install:
                parentName: str = MakeThingName(BuildIndex.RawBundlePack, pack.name)
                parentThing: BuildThing = structure.FindAnyThing(parentName)
                assert(parentThing != None)
                newThing = BuildThing()
                newThing.name = MakeThingName(BuildIndex.InstallBundlePack, pack.name)
                newThing.absParentDir = runner.absGameInstallDir
                newThing.files = BuildFilesT()
                newThing.parentThing = parentThing
                newThing.setGameLanguageOnInstall = pack.setGameLanguageOnInstall

                for parentFile in parentThing.files:
                    if util.HasAnyFileExt(parentFile.relTarget, runner.relevantGameDataFileTypes):
                        newFile = BuildFile()
                        newFile.absSource = parentFile.AbsTarget(parentThing.absParentDir)
                        newFile.relTarget = parentFile.relTarget
                        newThing.files.append(newFile)

                structure.AddThing(BuildIndex.InstallBundlePack, newThing)


    def __Build(self) -> bool:
        print("Do Build ...")

        structure: BuildStructure = self.structure
        tools: ToolsT = self.setup.tools
        copy = BuildCopy(tools=tools, options=BuildCopyOption.EnableSymlinks)

        BuildEngine.__BuildWithData(structure.GetProcessData(BuildIndex.RawBundleItem), copy, self.setup)
        BuildEngine.__BuildWithData(structure.GetProcessData(BuildIndex.BigBundleItem), copy, self.setup)
        BuildEngine.__BuildWithData(structure.GetProcessData(BuildIndex.RawBundlePack), copy, self.setup)

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
                info.md5 = util.GetFileMd5(absRealSource)
                infos[absRealSource] = info

            # Plain source will not be hashed as optimization.
            if not infos.get(absSource):
                info = BuildFilePathInfo()
                info.ownerThingName = thing.name
                info.md5 = ""
                infos[absSource] = info

        for file in thing.files:
            absTarget = file.AbsTarget(thing.absParentDir)
            absTargetDirs: list[str] = util.GetAbsFileDirs(absTarget, thing.absParentDir)
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
                info.md5 = util.GetFileMd5(absRealTarget)
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
                    targetInfo.md5 = util.GetFileMd5(absTarget)


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
            if status != BuildFileStatus.Unchanged:
                count: int = thing.GetFileCount(status)
                if count > 0:
                    print(f"{thing.name} has {count} files {status.name}")

        for file in thing.files:
            if file.sourceStatus != BuildFileStatus.Unchanged:
                absSource: str = file.absSource
                print(f"Source {absSource} is {file.sourceStatus.name}")

        for file in thing.files:
            if file.targetStatus != BuildFileStatus.Unchanged:
                absTarget: str = file.AbsTarget(thing.absParentDir)
                print(f"Target {absTarget} is {file.targetStatus.name}")


    @staticmethod
    def __GetBuildFileStatus(filePath: str, parentStatus: BuildFileStatus, diff: BuildDiff) -> BuildFileStatus:
        if os.path.exists(filePath):
            oldInfo: BuildFilePathInfo = diff.oldInfos.get(filePath)

            if oldInfo == None:
                return BuildFileStatus.Added
            else:
                newInfo: BuildFilePathInfo = diff.newInfos.get(filePath)
                util.RelAssert(newInfo != None, "Info must exist")

                if newInfo.md5 != oldInfo.md5:
                    return BuildFileStatus.Changed
                else:
                    if parentStatus != None and parentStatus != BuildFileStatus.Unknown:
                        return parentStatus
                    else:
                        return BuildFileStatus.Unchanged
        else:
            return BuildFileStatus.Missing


    @staticmethod
    def __DeleteObsoleteFilesOfThings(things: BuildThingsT, diff: BuildDiff) -> None:
        thing: BuildThing

        for thing in things.values():
            print(f"Delete files for {thing.name} ...")

            fileNames: list[str] = BuildEngine.__CreateListOfExistingFilesFromThing(thing)
            fileName: str

            for fileName in fileNames:
                if os.path.lexists(fileName):
                    newInfo: BuildFilePathInfo = diff.newInfos.get(fileName)
                    if newInfo == None:
                        oldInfo: BuildFilePathInfo = diff.oldInfos.get(fileName)
                        if oldInfo != None:
                            thing.fileCounts[BuildFileStatus.Removed.value] += 1

                        if util.DeleteFileOrPath(fileName):
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

            os.makedirs(thing.absParentDir, exist_ok=True)

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

        BuildEngine.__BuildWithData(self.structure.GetProcessData(BuildIndex.ReleaseBundlePack), copy, self.setup)

        return True


    def __Install(self) -> bool:
        print("Do Install ...")

        setup: BuildSetup = self.setup
        data: BuildIndexData = self.structure.GetProcessData(BuildIndex.InstallBundlePack)

        BuildEngine.__PopulateDiffFromThings(data, setup.folders)
        BuildEngine.__PopulateBuildFileStatusInThings(data.things, data.diff)
        BuildEngine.__CopyFilesOfThings(data.things, self.installCopy)
        BuildEngine.__RehashFilePathInfoDict(data.diff.newInfos, data.things)

        data.diff.SaveNewInfos()

        installedFiles: list[str] = BuildEngine.__GetAllTargetFilesFromThings(data.things)
        BuildEngine.__CheckGameInstallFiles(installedFiles, self.setup.runner)

        thing: BuildThing
        for thing in data.things.values():
            if thing.setGameLanguageOnInstall:
                BuildEngine.__SetGameLanguage(thing.setGameLanguageOnInstall, setup)

        return True


    @staticmethod
    def __CheckGameInstallFiles(installedFiles: list[str], runner: Runner) -> None:
        search: str = os.path.join(runner.absGameInstallDir, "**", "*")
        allGameFiles: list[str] = glob(search, recursive=True)
        gameDataFilesFilter = filter(lambda file: util.HasAnyFileExt(file, runner.relevantGameDataFileTypes), allGameFiles)
        relevantGameDataFiles = list[str](gameDataFilesFilter)
        expectedGameDataFiles = runner.absRegularGameDataFiles
        expectedGameDataFiles.extend(installedFiles)
        expectedGameDataFilesDict: dict[str, None] = dict.fromkeys(runner.absRegularGameDataFiles, 1)
        unexpectedGameFiles = list[str]()

        file: str
        for file in relevantGameDataFiles:
            if expectedGameDataFilesDict.get(file) == None:
                unexpectedGameFiles.append(file)

        print(f"Checking game install at {runner.absGameInstallDir} ...")
        if len(unexpectedGameFiles) > 0:
            warning(f"The installed Mod may not work correctly. {len(unexpectedGameFiles)} unexpected file(s) were found:")
            for file in unexpectedGameFiles:
                warning(file)


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

        data: BuildIndexData = self.structure.GetProcessData(BuildIndex.InstallBundlePack)

        BuildEngine.__UncopyFilesOfThings(data.things, self.installCopy)

        BuildEngine.__RestoreGameLanguage(self.setup)

        return True


    @staticmethod
    def __MakeLanguagePicklePath(folders: Folders) -> str:
        return os.path.join(folders.absBuildDir, "GameLanguage.pickle")


    @staticmethod
    def __SetGameLanguage(language: str, setup: BuildSetup) -> None:
        regKey: str = setup.runner.gameLanguageRegKey
        curLanguage: str = util.GetRegKeyValue(regKey)

        if language.lower() != curLanguage.lower():
            picklePath: str = BuildEngine.__MakeLanguagePicklePath(setup.folders)

            if not os.path.isfile(picklePath):
                
                util.SavePickle(picklePath, curLanguage)

            util.SetRegKeyValue(regKey, language)


    @staticmethod
    def __RestoreGameLanguage(setup: BuildSetup) -> None:
        picklePath: str = BuildEngine.__MakeLanguagePicklePath(setup.folders)

        if os.path.isfile(picklePath):
            language: str = util.LoadPickle(picklePath)
            regKey: str = setup.runner.gameLanguageRegKey
            util.SetRegKeyValue(regKey, language)
            os.remove(picklePath)
