import utils
import enum
import os.path
from data.bundles import BundlePack
from data.bundles import BundleItem
from data.bundles import BundleFile
from data.bundles import Bundles
from data.folders import Folders
from data.runner import Runner
from data.tools import Tool
from dataclasses import dataclass
from logging import warning
from pprint import pprint


class BuildType(enum.Flag):
    NONE = 0
    BUILD = enum.auto()
    RELEASE = enum.auto()
    INSTALL = enum.auto()
    UNINSTALL = enum.auto()
    RUN = enum.auto()
    PRE_BUILD = enum.auto()


@dataclass
class BuildSetup:
    type: BuildType
    folders: Folders
    runner: Runner
    bundles: Bundles
    tools: dict[Tool]

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.type, BuildType), "BuildSetup.type has incorrect type")
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


@dataclass(init=False)
class BuildThing:
    name: str
    absParent: str
    files: list[BuildFile]


@dataclass(init=False)
class BuildStructure:
    rawBundleItems: dict[BuildThing]
    bigBundleItems: dict[BuildThing]
    rawBundlePacks: dict[BuildThing]
    zipBundlePacks: dict[BuildThing]


class Engine:
    setup: BuildSetup
    structure: BuildStructure

    def __init__(self):
        pass

    def Run(self, setup: BuildSetup) -> bool:
        self.setup = setup
        self.setup.VerifyTypes()
        self.setup.VerifyValues()

        if self.setup.type == BuildType.NONE:
            warning("Engine.setup.type is NONE. Exiting.")
            return True

        print("Run Build with ...")
        pprint(self.setup.folders)
        pprint(self.setup.runner)
        pprint(self.setup.bundles)
        pprint(self.setup.tools)

        if self.setup.type & (BuildType.RELEASE):
            self.setup.type |= BuildType.BUILD

        if self.setup.type & (BuildType.BUILD | BuildType.INSTALL | BuildType.UNINSTALL):
            self.setup.type |= BuildType.PRE_BUILD

        success = True

        if success and self.setup.type & BuildType.PRE_BUILD:
            success &= self.__PreBuild()
        if success and self.setup.type & BuildType.BUILD:
            success &= self.__Build()
        if success and self.setup.type & BuildType.RELEASE:
            self.__BuildRelease()
        if success and self.setup.type & BuildType.INSTALL:
            success &= self.__Install()
        if success and self.setup.type & BuildType.RUN:
            self.__Run()
        if success and self.setup.type & BuildType.UNINSTALL:
            success &= self.__Uninstall()

        return success


    def __PreBuild(self) -> bool:
        print("Do Pre Build ...")

        folders: Folders = self.setup.folders
        bundles: Bundles = self.setup.bundles

        self.structure = BuildStructure()

        Engine.__SetupRawBundleItems(self.structure, bundles, folders)
        Engine.__SetupBigBundleItems(self.structure, bundles, folders)
        Engine.__SetupRawBundlePacks(self.structure, bundles, folders)
        Engine.__SetupZipBundlePacks(self.structure, bundles, folders)

        pprint(self.structure)

        return True

    @staticmethod
    def __SetupRawBundleItems(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        structure.rawBundleItems = dict()
        item: BundleItem
        for item in bundles.items:
            newThing = BuildThing()
            newThing.name = item.name
            newThing.absParent = os.path.join(folders.buildDir, "RawBundleItems", item.name)
            newThing.files = list()
            for itemFile in item.files:
                buildFile = BuildFile()
                buildFile.absSource = itemFile.absSourceFile
                buildFile.relTarget = itemFile.relTargetFile
                newThing.files.append(buildFile)
            structure.rawBundleItems[newThing.name] = newThing

    @staticmethod
    def __SetupBigBundleItems(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        structure.bigBundleItems = dict()
        item: BundleItem
        for item in bundles.items:
            if item.isBig:
                refThing: BuildThing = structure.rawBundleItems.get(item.name)
                assert(refThing != None)
                newThing = BuildThing()
                newThing.name = item.name
                newThing.absParent = os.path.join(folders.buildDir, "BigBundleItems")
                newThing.files = [BuildFile()]
                newThing.files[0].absSource = refThing.absParent
                newThing.files[0].relTarget = item.name + ".big"
                structure.bigBundleItems[newThing.name] = newThing

    @staticmethod
    def __SetupRawBundlePacks(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        structure.rawBundlePacks = dict()
        pack: BundlePack
        for pack in bundles.packs:
            newThing = BuildThing()
            newThing.name = pack.name
            newThing.absParent = os.path.join(folders.buildDir, "RawBundlePacks", pack.name)
            newThing.files = list()
            for packItemName in pack.itemNames:
                refThing: BuildThing = structure.bigBundleItems.get(packItemName)
                if not refThing:
                    refThing = structure.rawBundleItems.get(packItemName)
                    assert refThing != None
                for otherThingFile in refThing.files:
                    buildFile = BuildFile()
                    buildFile.absSource = os.path.join(refThing.absParent, otherThingFile.relTarget)
                    buildFile.relTarget = otherThingFile.relTarget
                    newThing.files.append(buildFile)
            structure.rawBundlePacks[newThing.name] = newThing

    @staticmethod
    def __SetupZipBundlePacks(structure: BuildStructure, bundles: Bundles, folders: Folders) -> None:
        structure.zipBundlePacks = dict()
        pack: BundlePack
        for pack in bundles.packs:
            refThing: BuildThing = structure.rawBundlePacks.get(pack.name)
            assert(refThing != None)
            newThing = BuildThing()
            newThing.name = pack.name
            newThing.absParent = folders.releaseDir
            newThing.files = [BuildFile()]
            newThing.files[0].absSource = refThing.absParent
            newThing.files[0].relTarget = pack.name + ".zip"
            structure.zipBundlePacks[newThing.name] = newThing


    def __Build(self) -> bool:
        print("Do Build ...")
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
