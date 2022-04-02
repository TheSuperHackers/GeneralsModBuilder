import utils
import os.path
import enum
from typing import Any
from enum import Enum
from enum import Flag
from data.bundles import BundlePack
from data.bundles import BundleItem
from data.bundles import BundleFile
from data.bundles import Bundles
from data.folders import Folders
from data.runner import Runner
from data.tools import Tool
from dataclasses import dataclass
from logging import warning


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
    status = BuildFileStatus.UNKNOWN
    refFile: Any = None


@dataclass(init=False)
class BuildThing:
    name: str
    absParentDir: str
    files: list[BuildFile]
    refThing: Any = None


@dataclass(init=False)
class BuildStructure:
    rawBundleItems: dict[BuildThing]
    bigBundleItems: dict[BuildThing]
    rawBundlePacks: dict[BuildThing]
    zipBundlePacks: dict[BuildThing]


@dataclass(init=False)
class BuildSourceInfo:
    md5: str


@dataclass(init=False)
class BuildDiff:
    newInfos: dict[BuildSourceInfo]
    oldInfos: dict[BuildSourceInfo]


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
            warning("Engine.setup.type is NONE. Exiting.")
            return True

        print("Run Build with ...")
        utils.PPrint(self.setup.folders)
        utils.PPrint(self.setup.runner)
        utils.PPrint(self.setup.bundles)
        utils.PPrint(self.setup.tools)

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
            newThing.name = item.name
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
                refThing: BuildThing = structure.rawBundleItems.get(item.name)
                assert(refThing != None)
                newThing = BuildThing()
                newThing.name = item.name
                newThing.absParentDir = os.path.join(folders.buildDir, "BigBundleItems")
                newThing.refThing = refThing
                newThing.files = [BuildFile()]
                newThing.files[0].absSource = refThing.absParentDir
                newThing.files[0].relTarget = item.name + ".big"
                structure.bigBundleItems[newThing.name] = newThing


    @staticmethod
    def __CreateStructureRawBundlePacks(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        structure.rawBundlePacks = dict()
        pack: BundlePack

        for pack in bundles.packs:
            newThing = BuildThing()
            newThing.name = pack.name
            newThing.absParentDir = os.path.join(folders.buildDir, "RawBundlePacks", pack.name)
            newThing.files = list()

            for packItemName in pack.itemNames:
                refThing: BuildThing
                refThing = structure.bigBundleItems.get(packItemName)
                if not refThing:
                    refThing = structure.rawBundleItems.get(packItemName)
                    assert refThing != None

                for refFile in refThing.files:
                    buildFile = BuildFile()
                    buildFile.absSource = os.path.join(refThing.absParentDir, refFile.relTarget)
                    buildFile.relTarget = refFile.relTarget
                    buildFile.refFile = refFile
                    newThing.files.append(buildFile)

            structure.rawBundlePacks[newThing.name] = newThing


    @staticmethod
    def __CreateStructureZipBundlePacks(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        structure.zipBundlePacks = dict()
        pack: BundlePack

        for pack in bundles.packs:
            refThing: BuildThing = structure.rawBundlePacks.get(pack.name)
            assert(refThing != None)
            newThing = BuildThing()
            newThing.name = pack.name
            newThing.absParentDir = folders.releaseDir
            newThing.refThing = refThing
            newThing.files = [BuildFile()]
            newThing.files[0].absSource = refThing.absParentDir
            newThing.files[0].relTarget = pack.name + ".zip"
            structure.zipBundlePacks[newThing.name] = newThing


    @staticmethod
    def __CreateBuildFileStatusInStructure(structure: BuildStructure, diff: BuildDiff) -> None:
        print("Create Build File Status ...")
        thing: BuildThing
        file: BuildFile

        for thing in structure.rawBundleItems.values():
            for file in thing.files:
                if not diff.newInfos.get(file.absSource):
                    info = BuildSourceInfo()
                    info.md5 = utils.GetFileMd5(file.absSource)
                    diff.newInfos[file.absSource] = info

        Engine.__CreateBuildFileStatusFromDiff(structure.rawBundleItems, diff)
        Engine.__CreateBuildFileStatusFromReferences(structure.bigBundleItems)
        Engine.__CreateBuildFileStatusFromReferences(structure.rawBundlePacks)
        Engine.__CreateBuildFileStatusFromReferences(structure.zipBundlePacks)

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
                newInfo: BuildSourceInfo = diff.newInfos.get(file.absSource)
                oldInfo: BuildSourceInfo = diff.oldInfos.get(file.absSource)

                if bool(newInfo) and bool(oldInfo):
                    if newInfo.md5 != oldInfo.md5:
                        file.status = BuildFileStatus.CHANGED
                    else:
                        file.status = BuildFileStatus.UNCHANGED
                elif bool(newInfo):
                    file.status = BuildFileStatus.ADDED


    @staticmethod
    def __CreateBuildFileStatusFromReferences(things: dict[BuildThing]) -> None:
        refThing: BuildThing
        refFile: BuildFile
        thing: BuildThing
        file: BuildFile
        status: BuildFileStatus

        for thing in things.values():
            refThing = thing.refThing
            if bool(refThing):
                status = BuildFileStatus.UNKNOWN
                for refFile in refThing.files:
                    if refFile.status == BuildFileStatus.CHANGED:
                        status = BuildFileStatus.CHANGED
                        break
                    elif refFile.status == BuildFileStatus.ADDED:
                        if status != BuildFileStatus.CHANGED:
                            status = BuildFileStatus.ADDED
                    elif refFile.status == BuildFileStatus.UNCHANGED:
                        if status != BuildFileStatus.CHANGED and status != BuildFileStatus.ADDED:
                            status = BuildFileStatus.UNCHANGED
                for file in thing.files:
                    file.status = status
            else:
                for file in thing.files:
                    refFile = file.refFile
                    if bool(refFile):
                        file.status = refFile.status


    @staticmethod
    def __PrintBuildFileStatus(things: dict[BuildThing]) -> None:
        thing: BuildThing
        file: BuildFile
        for thing in things.values():
            for file in thing.files:
                print(f"File {file.absSource} is {file.status.name}")


    @staticmethod
    def __DiffFilePath(folders: Folders) -> str:
        return os.path.join(folders.buildDir, "RawBundleItems.pickle")


    @staticmethod
    def __LoadDiff(folders: Folders) -> BuildDiff:
        diff = BuildDiff()
        diff.oldInfos = dict()
        diff.newInfos = dict()
        try:
            diff.oldInfos = utils.SerializeLoad(Engine.__DiffFilePath(folders))
        except FileNotFoundError:
            pass
        return diff


    @staticmethod
    def __SaveDiff(diff: BuildDiff, folders: Folders) -> None:
        utils.SerializeSave(Engine.__DiffFilePath(folders), diff.newInfos)


    def __Build(self) -> bool:
        print("Do Build ...")

        folders: Folders = self.setup.folders

        self.diff = Engine.__LoadDiff(folders)

        Engine.__CreateBuildFileStatusInStructure(self.structure, self.diff)

        utils.PPrint(self.structure)

        return True


    def __PostBuild(self) -> bool:
        print("Do Post Build ...")

        Engine.__SaveDiff(self.diff, self.setup.folders)

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
