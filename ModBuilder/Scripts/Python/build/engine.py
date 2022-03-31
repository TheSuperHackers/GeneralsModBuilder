import utils
import enum
from data.bundles import Bundle
from data.bundles import BundleFile
from data.folders import Folders
from data.runner import Runner
from data.tools import Tool
from dataclasses import dataclass
from logging import warning


class BuildType(enum.Flag):
    NONE = 0
    BUILD = enum.auto()
    RELEASE = enum.auto()
    INSTALL = enum.auto()
    UNINSTALL = enum.auto()
    RUN = enum.auto()
    PRE_BUILD = enum.auto()
    BUILD_TMP_FILES = enum.auto()


@dataclass
class BuildSetup:
    type: BuildType
    folders: Folders
    runner: Runner
    bundles: list[Bundle]
    tools: dict[Tool]

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.type, BuildType), "Engine.type has incorrect type")
        utils.RelAssert(isinstance(self.folders, Folders), "Engine.folders has incorrect type")
        utils.RelAssert(isinstance(self.runner, Runner), "Engine.runner has incorrect type")
        utils.RelAssert(isinstance(self.bundles, list), "Engine.bundles has incorrect type")
        utils.RelAssert(isinstance(self.tools, dict), "Engine.tools has incorrect type")

    def VerifyValues(self) -> None:
        utils.RelAssert(self.tools.get("crunch") != None, "crunch tool definition is missing")
        utils.RelAssert(self.tools.get("gametextcompiler") != None, "gametextcompiler tool definition is missing")
        utils.RelAssert(self.tools.get("generalsbigcreator") != None, "generalsbigcreator tool definition is missing")


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

        if self.setup.type & (BuildType.BUILD | BuildType.INSTALL | BuildType.UNINSTALL | BuildType.RELEASE):
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
