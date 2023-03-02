import importlib
import subprocess
import sys
import os
from copy import deepcopy
from dataclasses import dataclass
from logging import warning
from glob import glob
import threading
import time
from typing import Any
from enum import Enum, auto
from generalsmodbuilder.build.common import ParamsToArgs
from generalsmodbuilder.build.copy import BuildCopy, BuildCopyOption
from generalsmodbuilder.build.filehashregistry import FileHash, FileHashRegistry
from generalsmodbuilder.build.thing import BuildFile, BuildFileStatus, BuildThing, BuildFilesT, BuildThingsT, IsStatusRelevantForBuild
from generalsmodbuilder.build.setup import BuildSetup, BuildStep
from generalsmodbuilder.data.bundles import BundleRegistryDefinition, Bundles, BundlePack, BundleItem, BundleFile, BundleEvent, BundleEventType
from generalsmodbuilder.data.common import ParamsT
from generalsmodbuilder.data.folders import Folders
from generalsmodbuilder.data.runner import Runner
from generalsmodbuilder.data.tools import ToolsT
from generalsmodbuilder import util


@dataclass
class BuildFilePathInfo:
    # This class is serialized and therefore may be missing attributes.
    modifiedTime: float
    md5: str
    params: ParamsT

    def Matches(self, other: Any) -> bool:
        try:
            return self.md5 == other.md5 and self.params == other.params
        except AttributeError:
            return False

    def GetModifiedTime(self) -> float:
        try:
            return self.modifiedTime
        except AttributeError:
            return 0.0


BuildFilePathInfosT = dict[str, BuildFilePathInfo]


class BuildDiffRegistry:
    filePathInfos: BuildFilePathInfosT
    lowerPath: bool

    def __init__(self):
        self.filePathInfos = BuildFilePathInfosT()
        self.lowerPath = True

    def __ProcessPath(self, filepath: str) -> str:
        if self.lowerPath:
            filepath = filepath.lower()
        return filepath

    def AddFile(self, filepath: str, time = 0.0, md5: str = "", params: ParamsT = None) -> BuildFilePathInfo:
        filepath = self.__ProcessPath(filepath)
        pathinfo = BuildFilePathInfo(time, md5, params)
        self.filePathInfos[filepath] = pathinfo
        return pathinfo

    def FindFile(self, filepath: str) -> BuildFilePathInfo | None:
        filepath = self.__ProcessPath(filepath)
        return self.filePathInfos.get(filepath)


@dataclass(init=False)
class BuildDiff:
    newDiffRegistry: BuildDiffRegistry
    oldDiffRegistry: BuildDiffRegistry
    loadPath: str
    includesParentDiff: bool
    registryDict: dict[int, FileHashRegistry]

    def __init__(self, loadPath: str, includesParentDiff: bool, useFileHashRegistry: bool):
        """
        loadPath : str
            String path to serialization file.
        includesParentDiff : bool
            Diff contains parent file diffs. This option is required when a build step can be run in isolation from other build steps.
            For example if a Build is run without a Release Build, then the Release diff would lose information if it did not store the parent diff.
        useFileHashRegistry : bool
            Intended to be used with file hash registry.
        """
        self.newDiffRegistry = BuildDiffRegistry()
        self.oldDiffRegistry = BuildDiffRegistry()
        self.loadPath = loadPath
        self.includesParentDiff = includesParentDiff
        self.registryDict = dict[int, FileHashRegistry]() if useFileHashRegistry else None
        self.TryLoadOldDiffRegistry()

    def UseFileHashRegistry(self) -> bool:
        return self.registryDict != None

    def GetOrCreateRegistry(self, registryDef: BundleRegistryDefinition) -> FileHashRegistry:
        assert(registryDef != None)
        if self.registryDict != None:
            registry: FileHashRegistry = self.registryDict.get(registryDef.crc32)
            if registry == None:
                registry = FileHashRegistry()
                for fullPath in registryDef.paths:
                    pathName: str = util.GetFileDirAndName(fullPath)
                    path: str = util.GetFileDir(pathName)
                    name: str = util.GetFileName(pathName)
                    registryTmp = FileHashRegistry()
                    if registryTmp.LoadRegistry(path, name):
                        registry.Merge(registryTmp)

                self.registryDict[registryDef.crc32] = registry

            return registry
        else:
            return None

    def TryLoadOldDiffRegistry(self) -> bool:
        try:
            self.oldDiffRegistry.filePathInfos = util.LoadPickle(self.loadPath)
            return True
        except:
            return False

    def SaveNewDiffRegistry(self) -> bool:
        util.SavePickle(self.loadPath, self.newDiffRegistry.filePathInfos)
        return True


class BuildIndex(Enum):
    RawBundleItem = 0
    BigBundleItem = auto()
    RawBundlePack = auto()
    ReleaseBundlePack = auto()
    InstallBundlePack = auto()


def GetBuildIndexName(index: BuildIndex) -> str:
    return index.name

def MakeThingName(index: BuildIndex, thingName: str) -> str:
    return f"{GetBuildIndexName(index)}_{thingName}"

def MakeDiffPath(index: BuildIndex, folders: Folders) -> str:
    return os.path.join(folders.absBuildDir, f"{GetBuildIndexName(index)}.pickle")


g_buildIndexToStartBuildEvent: dict[BuildIndex, BundleEventType] = {
    BuildIndex.RawBundleItem: BundleEventType.OnStartBuildRawBundleItem,
    BuildIndex.BigBundleItem: BundleEventType.OnStartBuildBigBundleItem,
    BuildIndex.RawBundlePack: BundleEventType.OnStartBuildRawBundlePack,
    BuildIndex.ReleaseBundlePack: BundleEventType.OnStartBuildReleaseBundlePack,
    BuildIndex.InstallBundlePack: BundleEventType.OnStartBuildInstallBundlePack,
}

g_buildIndexToFinishBuildEvent: dict[BuildIndex, BundleEventType] = {
    BuildIndex.RawBundleItem: BundleEventType.OnFinishBuildRawBundleItem,
    BuildIndex.BigBundleItem: BundleEventType.OnFinishBuildBigBundleItem,
    BuildIndex.RawBundlePack: BundleEventType.OnFinishBuildRawBundlePack,
    BuildIndex.ReleaseBundlePack: BundleEventType.OnFinishBuildReleaseBundlePack,
    BuildIndex.InstallBundlePack: BundleEventType.OnFinishBuildInstallBundlePack,
}

def GetStartBuildEvent(index: BuildIndex) -> BundleEventType:
    return g_buildIndexToStartBuildEvent.get(index)

def GetFinishBuildEvent(index: BuildIndex) -> BundleEventType:
    return g_buildIndexToFinishBuildEvent.get(index)


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

    def GetIndexData(self, index: BuildIndex) -> BuildIndexData:
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

    def FindThingWithPlainName(self, index: BuildIndex, name: str) -> BuildThing:
        thingName: str = MakeThingName(index, name)
        return self.data[index.value].things.get(thingName)


class BuildEngine:
    setup: BuildSetup
    structure: BuildStructure
    copyDict: dict[BuildIndex, BuildCopy]
    processHandle: subprocess.Popen
    processLock: threading.RLock


    def __init__(self):
        self.__Reset()


    def __Reset(self):
        self.setup = None
        self.structure = None
        self.copyDict = None
        self.processHandle = None
        self.processLock = threading.RLock()


    def Run(self, setup: BuildSetup) -> bool:
        print("Run Build Job ...")

        if setup.step == BuildStep.Zero:
            warning("setup.step is Zero. Exiting.")
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

        if self.setup.step & (BuildStep.Clean | BuildStep.Build | BuildStep.Install | BuildStep.Uninstall | BuildStep.Run):
            self.setup.step |= BuildStep.PreBuild

        success = True

        if success and self.setup.step & BuildStep.PreBuild:
            success &= self.__PreBuild()
        if success and self.setup.step & BuildStep.Clean:
            success &= self.__Uninstall()
            success &= self.__Clean()
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

        print("Build Job done.")

        return success


    def CanAbort(self) -> bool:
        with self.processLock:
            return self.processHandle != None


    def Abort(self) -> None:
        with self.processLock:
            if self.processHandle != None:
                self.processHandle.terminate()


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


    @staticmethod
    def __SendBundleEvents(structure: BuildStructure, setup: BuildSetup, eventType: BundleEventType):
        bundles: Bundles = setup.bundles
        folders: Folders = setup.folders
        sent: bool = False
        item: BundleItem
        pack: BundlePack

        for item in bundles.items:
            event: BundleEvent = item.events.get(eventType)
            if event != None:
                kwargs = dict()
                kwargs["_tools"] = setup.tools
                kwargs["_bundleItem"] = item
                kwargs["_absBuildDir"] = folders.absBuildDir
                kwargs["_absReleaseDir"] = folders.absReleaseDir
                kwargs["_absReleaseUnpackedDir"] = folders.absReleaseUnpackedDir
                kwargs["_rawBuildThing"] = structure.FindThingWithPlainName(BuildIndex.RawBundleItem, item.name)
                kwargs["_bigBuildThing"] = structure.FindThingWithPlainName(BuildIndex.BigBundleItem, item.name)
                sent |= BuildEngine.__CallScript(event, kwargs)
                item.VerifyTypes()
                item.Normalize()

        for pack in bundles.packs:
            event: BundleEvent = pack.events.get(eventType)
            if event != None:
                kwargs = dict()
                kwargs["_tools"] = setup.tools
                kwargs["_bundlePack"] = pack
                kwargs["_absBuildDir"] = folders.absBuildDir
                kwargs["_absReleaseDir"] = folders.absReleaseDir
                kwargs["_absReleaseUnpackedDir"] = folders.absReleaseUnpackedDir
                kwargs["_rawBuildThing"] = structure.FindThingWithPlainName(BuildIndex.RawBundlePack, pack.name)
                kwargs["_releaseBuildThing"] = structure.FindThingWithPlainName(BuildIndex.ReleaseBundlePack, pack.name)
                kwargs["_installBuildThing"] = structure.FindThingWithPlainName(BuildIndex.InstallBundlePack, pack.name)
                sent |= BuildEngine.__CallScript(event, kwargs)
                pack.VerifyTypes()
                pack.Normalize()

        if sent:
            bundles.VerifyValues()

        return sent


    def __PreBuild(self) -> bool:
        print("Do Pre Build ...")

        folders: Folders = self.setup.folders
        runner: Runner = self.setup.runner
        bundles: Bundles = self.setup.bundles
        tools: ToolsT = self.setup.tools

        self.structure = BuildStructure()
        self.copyDict = {
            BuildIndex.RawBundleItem: BuildCopy(tools=tools, options=BuildCopyOption.EnableSymlinks),
            BuildIndex.BigBundleItem: BuildCopy(tools=tools, options=BuildCopyOption.EnableSymlinks),
            BuildIndex.RawBundlePack: BuildCopy(tools=tools, options=BuildCopyOption.EnableSymlinks),
            BuildIndex.ReleaseBundlePack: BuildCopy(tools=tools),
            BuildIndex.InstallBundlePack: BuildCopy(tools=tools, options=BuildCopyOption.EnableBackup | BuildCopyOption.EnableSymlinks),
        }

        BuildEngine.__SendBundleEvents(self.structure, self.setup, BundleEventType.OnPreBuild)

        BuildEngine.__PopulateStructureRawBundleItems(self.structure, bundles, folders)
        BuildEngine.__PopulateStructureBigBundleItems(self.structure, bundles, folders)
        BuildEngine.__PopulateStructureRawBundlePacks(self.structure, bundles, folders)
        BuildEngine.__PopulateStructureZipBundlePacks(self.structure, bundles, folders)
        BuildEngine.__PopulateStructureInstallBundlePacks(self.structure, bundles, runner)

        return True


    def __Clean(self) -> bool:
        print("Do Clean ...")

        util.DeleteFileOrPath(self.setup.folders.absBuildDir)
        util.DeleteFileOrPath(self.setup.folders.absReleaseDir)

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
                buildFile.registryDef = itemFile.registryDef
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
                isBigFile: bool = parentThing != None
                item: BundleItem = bundles.FindItemByName(itemName)

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

                    if isBigFile:
                        buildFile.relTarget += item.bigSuffix

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
                newThing.setGameLanguageOnInstall = bundles.FindFirstGameLanguageForInstall(pack.name)

                for parentFile in parentThing.files:
                    # if util.HasAnyFileExt(parentFile.relTarget, runner.relevantGameDataFileTypes):
                    #     continue
                    newFile = BuildFile()
                    newFile.absSource = parentFile.AbsTarget(parentThing.absParentDir)
                    newFile.relTarget = parentFile.relTarget
                    newThing.files.append(newFile)

                structure.AddThing(BuildIndex.InstallBundlePack, newThing)


    def __Build(self) -> bool:
        print("Do Build ...")

        BuildEngine.__SendBundleEvents(self.structure, self.setup, BundleEventType.OnBuild)

        self.__BuildWithData(BuildIndex.RawBundleItem, diffWithFileHashRegistry=True)
        self.__BuildWithData(BuildIndex.BigBundleItem)
        self.__BuildWithData(BuildIndex.RawBundlePack)

        return True


    def __PostBuild(self) -> bool:
        print("Do Post Build ...")

        BuildEngine.__SendBundleEvents(self.structure, self.setup, BundleEventType.OnPostBuild)

        return True


    def __BuildWithData(
            self,
            index: BuildIndex,
            deleteObsoleteFiles: bool = True,
            diffWithParentThings: bool = False,
            diffWithFileHashRegistry: bool = False) -> None:

        structure: BuildStructure = self.structure
        setup: BuildSetup = self.setup
        copy: BuildCopy = self.copyDict[index]
        data: BuildIndexData = structure.GetIndexData(index)

        # Start event is sent before populating the build diff to allow for file modifications and file injections.
        BuildEngine.__SendBundleEvents(structure, setup, GetStartBuildEvent(index))

        BuildEngine.__PopulateDiff(data, setup.folders, diffWithParentThings, diffWithFileHashRegistry)
        BuildEngine.__PopulateBuildFileStatusInThings(data.things, data.diff)

        if deleteObsoleteFiles:
            BuildEngine.__DeleteObsoleteFilesOfThings(data.things, data.diff)

        BuildEngine.__CopyFilesOfThings(data.things, copy)

        # Finish event is sent before finalizing the build diff to allow for file verifications with hard failures.
        BuildEngine.__SendBundleEvents(structure, setup, GetFinishBuildEvent(index))

        BuildEngine.__RehashFilePathInfoDict(data.diff.newDiffRegistry, data.things)

        data.diff.SaveNewDiffRegistry()


    @staticmethod
    def __PopulateDiff(data: BuildIndexData, folders: Folders, withParentThings: bool, useFileHashRegistry: bool) -> None:
        path: str = MakeDiffPath(data.index, folders)
        data.diff = BuildDiff(path, withParentThings, useFileHashRegistry)
        BuildEngine.__PopulateDiffFromThings(data.diff, data.things)


    @staticmethod
    def __PopulateDiffFromThings(diff: BuildDiff, things: BuildThingsT) -> None:
        thing: BuildThing

        for thing in things.values():
            print(f"Create file infos for {thing.name} ...")

            BuildEngine.__PopulateFilePathInfosFromThing(diff, thing)

            if diff.includesParentDiff and thing.parentThing != None:
                BuildEngine.__PopulateFilePathInfosFromThing(diff, thing.parentThing)


    @staticmethod
    def __PopulateFilePathInfosFromThing(diff: BuildDiff, thing: BuildThing) -> None:
        file: BuildFile

        for file in thing.files:
            absRealSource = file.AbsRealSource()
            absSource = file.AbsSource()
            sourceTime: float = 0.0
            sourceMd5: str = ""

            if not diff.newDiffRegistry.FindFile(absRealSource):
                sourceTime = util.GetFileModifiedTime(absRealSource)
                # Optimization: Use old hash when file modification time is unchanged.
                oldInfo: BuildFilePathInfo = diff.oldDiffRegistry.FindFile(absRealSource)
                if oldInfo != None and sourceTime > 0.0 and sourceTime == oldInfo.GetModifiedTime():
                    sourceMd5 = oldInfo.md5
                else:
                    sourceMd5 = util.GetFileMd5(absRealSource)
                diff.newDiffRegistry.AddFile(absRealSource, time=sourceTime, md5=sourceMd5, params=None)

            if not diff.newDiffRegistry.FindFile(absSource):
                diff.newDiffRegistry.AddFile(absSource, time=sourceTime, md5=sourceMd5, params=None)

        for file in thing.files:
            absRealTarget = file.AbsRealTarget(thing.absParentDir)
            absTarget = file.AbsTarget(thing.absParentDir)
            absTargetDirs: list[str] = util.GetAbsFileDirs(absTarget, thing.absParentDir)
            absTargetDir: str
            targetTime: float = 0.0
            targetMd5: str = ""
            targetParams: ParamsT = None

            for absTargetDir in absTargetDirs:
                if not diff.newDiffRegistry.FindFile(absTargetDir):
                    diff.newDiffRegistry.AddFile(absTargetDir)

            if not diff.newDiffRegistry.FindFile(absRealTarget):
                targetTime = util.GetFileModifiedTime(absRealTarget)
                targetParams = deepcopy(file.params)
                # Optimization: Use old hash when file modification time is unchanged.
                oldInfo: BuildFilePathInfo = diff.oldDiffRegistry.FindFile(absRealTarget)
                if oldInfo != None and targetTime > 0.0 and targetTime == oldInfo.GetModifiedTime():
                    targetMd5 = oldInfo.md5
                else:
                    targetMd5 = util.GetFileMd5(absRealTarget)
                diff.newDiffRegistry.AddFile(absRealTarget, time=targetTime, md5=targetMd5, params=targetParams)

            if not diff.newDiffRegistry.FindFile(absTarget):
                diff.newDiffRegistry.AddFile(absTarget, time=targetTime, md5=targetMd5, params=targetParams)


    @staticmethod
    def __RehashFilePathInfoDict(diffRegistry: BuildDiffRegistry, things: BuildThingsT) -> None:
        thing: BuildThing
        file: BuildFile

        for thing in things.values():
            print(f"Rehash files for {thing.name} ...")

            for file in thing.files:
                if file.RequiresRebuild():
                    absTarget: str = file.AbsTarget(thing.absParentDir)
                    targetInfo: BuildFilePathInfo = diffRegistry.FindFile(absTarget)
                    assert(targetInfo != None)
                    targetInfo.md5 = util.GetFileMd5(absTarget)


    @staticmethod
    def __PopulateBuildFileStatusInThings(things: BuildThingsT, diff: BuildDiff) -> None:
        thing: BuildThing

        for thing in things.values():
            print(f"Populate file status for {thing.name} ...")

            if diff.includesParentDiff and thing.parentThing != None:
                BuildEngine.__PopulateFileStatusInThing(thing.parentThing, diff)

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

            file.sourceStatus = BuildEngine.__GetStatusWithFileHashRegistry(absSource, file.relTarget, diff, file.registryDef)
            if file.sourceStatus == BuildFileStatus.Unknown:
                file.sourceStatus = BuildEngine.__GetBuildFileStatus(absSource, parentStatus, diff)
            if file.sourceStatus != BuildFileStatus.Irrelevant:
                file.targetStatus = BuildEngine.__GetBuildFileStatus(absTarget, None, diff)

        for status in BuildFileStatus:
            thing.fileCounts[status.value] = 0

        for file in thing.files:
            status: BuildFileStatus = file.GetCombinedStatus()
            thing.fileCounts[status.value] += 1

        for status in BuildFileStatus:
            if IsStatusRelevantForBuild(status):
                count: int = thing.GetFileCount(status)
                if count > 0:
                    print(f"{thing.name} has {count} files {status.name}")

        for file in thing.files:
            if IsStatusRelevantForBuild(file.sourceStatus):
                absSource: str = file.absSource
                print(f"Source {absSource} is {file.sourceStatus.name}")

        for file in thing.files:
            if IsStatusRelevantForBuild(file.targetStatus):
                absTarget: str = file.AbsTarget(thing.absParentDir)
                print(f"Target {absTarget} is {file.targetStatus.name}")


    @staticmethod
    def __GetStatusWithFileHashRegistry(absFilePath: str, relFilePath: str, diff: BuildDiff, registryDef: BundleRegistryDefinition) -> BuildFileStatus:
        if registryDef != None and diff.UseFileHashRegistry():
            filePathInfo: BuildFilePathInfo = diff.newDiffRegistry.FindFile(absFilePath)
            if filePathInfo != None:
                registry: FileHashRegistry = diff.GetOrCreateRegistry(registryDef)
                assert registry != None
                fileHash: FileHash = registry.FindFile(relFilePath)
                if fileHash != None:
                    if filePathInfo.md5 == fileHash.md5:
                        return BuildFileStatus.Irrelevant

        return BuildFileStatus.Unknown


    @staticmethod
    def __GetBuildFileStatus(filePath: str, parentStatus: BuildFileStatus, diff: BuildDiff) -> BuildFileStatus:
        if os.path.exists(filePath):
            oldInfo: BuildFilePathInfo = diff.oldDiffRegistry.FindFile(filePath)

            if oldInfo == None:
                return BuildFileStatus.Added
            else:
                newInfo: BuildFilePathInfo = diff.newDiffRegistry.FindFile(filePath)
                util.Verify(newInfo != None, "Info must exist")

                if newInfo.Matches(oldInfo):
                    if parentStatus != None and parentStatus != BuildFileStatus.Unknown:
                        return parentStatus
                    else:
                        return BuildFileStatus.Unchanged
                else:
                    return BuildFileStatus.Changed
        else:
            return BuildFileStatus.Missing


    @staticmethod
    def __DeleteObsoleteFilesOfThings(things: BuildThingsT, diff: BuildDiff) -> None:
        thing: BuildThing

        for thing in things.values():
            print(f"Delete files for {thing.name} ...")

            fileNames: list[str] = BuildEngine.__CreateListOfExistingFilesFromThing(thing)
            fileName: str
            buildFile: BuildFile

            for buildFile in thing.files:
                if buildFile.sourceStatus == BuildFileStatus.Irrelevant:
                    fileName = buildFile.AbsTarget(thing.absParentDir)
                    if util.DeleteFile(fileName):
                        oldInfo: BuildFilePathInfo = diff.oldDiffRegistry.FindFile(fileName)
                        if oldInfo != None and oldInfo.md5:
                            thing.fileCounts[BuildFileStatus.Removed.value] += 1
                        print("Deleted", fileName)

            for fileName in fileNames:
                if os.path.lexists(fileName):
                    newInfo: BuildFilePathInfo = diff.newDiffRegistry.FindFile(fileName)
                    if newInfo == None:
                        if util.DeleteFileOrPath(fileName):
                            oldInfo: BuildFilePathInfo = diff.oldDiffRegistry.FindFile(fileName)
                            if oldInfo != None and oldInfo.md5:
                                thing.fileCounts[BuildFileStatus.Removed.value] += 1
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


    def __BuildRelease(self) -> bool:
        print("Do Build Release ...")

        BuildEngine.__SendBundleEvents(self.structure, self.setup, BundleEventType.OnRelease)

        self.__BuildWithData(BuildIndex.ReleaseBundlePack, diffWithParentThings=True)

        return True


    def __Install(self) -> bool:
        print("Do Install ...")

        copy: BuildCopy = self.copyDict.get(BuildIndex.InstallBundlePack)

        # Cleanup before install to avoid duplicated consecutive installs.
        BuildEngine.__RevertInstalledThings(self.setup, copy)
        BuildEngine.__RestoreGameLanguage(self.setup)

        BuildEngine.__SendBundleEvents(self.structure, self.setup, BundleEventType.OnInstall)

        data: BuildIndexData = self.structure.GetIndexData(BuildIndex.InstallBundlePack)

        self.__BuildWithData(data.index, deleteObsoleteFiles=False, diffWithParentThings=True)
        BuildEngine.__SaveInstalledThingsInfo(data.things, self.setup)

        thing: BuildThing
        for thing in data.things.values():
            if thing.setGameLanguageOnInstall:
                BuildEngine.__SetGameLanguage(thing.setGameLanguageOnInstall, self.setup)

        installedFiles: list[str] = BuildEngine.__GetAllTargetFilesFromThings(data.things)
        BuildEngine.__CheckGameInstallFiles(installedFiles, self.setup.runner)

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

        BuildEngine.__SendBundleEvents(self.structure, self.setup, BundleEventType.OnRun)

        self.processHandle: subprocess.Popen = subprocess.Popen(args=args)

        while True:
            with self.processLock:
                if self.processHandle.poll() != None:
                    self.processHandle = None
                    break
            time.sleep(0.1)

        return True


    def __Uninstall(self) -> bool:
        print("Do Uninstall ...")

        copy: BuildCopy = self.copyDict.get(BuildIndex.InstallBundlePack)

        BuildEngine.__SendBundleEvents(self.structure, self.setup, BundleEventType.OnUninstall)

        BuildEngine.__RevertInstalledThings(self.setup, copy)
        BuildEngine.__RestoreGameLanguage(self.setup)

        return True


    @staticmethod
    def __MakeLanguagePicklePath(folders: Folders) -> str:
        return os.path.join(folders.absBuildDir, "GameLanguage.pickle")


    @staticmethod
    def __SetGameLanguage(language: str, setup: BuildSetup) -> None:
        print(f"Set Game Language to '{language}' ...")

        regKey: str = setup.runner.gameLanguageRegKey
        curLanguage: str = util.GetRegKeyValue(regKey)

        if language.lower() != curLanguage.lower():
            picklePath: str = BuildEngine.__MakeLanguagePicklePath(setup.folders)

            if not os.path.isfile(picklePath):
                util.SavePickle(picklePath, curLanguage)

            util.SetRegKeyValue(regKey, language)


    @staticmethod
    def __RestoreGameLanguage(setup: BuildSetup) -> None:
        print(f"Restore Game Language ...")

        picklePath: str = BuildEngine.__MakeLanguagePicklePath(setup.folders)
        if os.path.isfile(picklePath):
            try:
                language: str = util.LoadPickle(picklePath)
            except:
                return
            finally:
                os.remove(picklePath)

            regKey: str = setup.runner.gameLanguageRegKey
            util.SetRegKeyValue(regKey, language)


    @staticmethod
    def __MakeInstalledThingsPicklePath(folders: Folders) -> str:
        return os.path.join(folders.absBuildDir, "InstalledThings.pickle")


    @staticmethod
    def __LoadInstalledThingsInfo(setup: BuildSetup) -> BuildThingsT:
        picklePath: str = BuildEngine.__MakeInstalledThingsPicklePath(setup.folders)
        try:
            return util.LoadPickle(picklePath)
        except:
            return BuildThingsT()


    @staticmethod
    def __SaveInstalledThingsInfo(things: BuildThingsT, setup: BuildSetup) -> None:
        print(f"Save Installed Things ...")

        picklePath: str = BuildEngine.__MakeInstalledThingsPicklePath(setup.folders)
        installedThings: BuildThingsT = BuildEngine.__LoadInstalledThingsInfo(setup)
        installedThings.update(things)
        util.SavePickle(picklePath, installedThings)


    @staticmethod
    def __DeleteInstalledThingsInfo(setup: BuildSetup) -> None:
        picklePath: str = BuildEngine.__MakeInstalledThingsPicklePath(setup.folders)
        if os.path.isfile(picklePath):
            print("Remove", picklePath)
            os.remove(picklePath)


    @staticmethod
    def __RevertInstalledThings(setup: BuildSetup, copy: BuildCopy) -> None:
        print(f"Revert Installed Things ...")

        installedThings: BuildThingsT = BuildEngine.__LoadInstalledThingsInfo(setup)
        BuildEngine.__UncopyFilesOfThings(installedThings, copy)
        BuildEngine.__DeleteInstalledThingsInfo(setup)
