import utils
import enum
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


class Engine:
    setup: BuildSetup

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

        if self.setup.type & (BuildType.BUILD | BuildType.INSTALL | BuildType.UNINSTALL | BuildType.RELEASE):
            self.setup.type |= BuildType.PRE_BUILD

        if self.setup.type & (BuildType.RELEASE):
            self.setup.type |= BuildType.BUILD

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
        return True

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
