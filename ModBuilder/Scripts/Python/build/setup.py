import utils
import enum
from dataclasses import dataclass
from data.bundles import Bundles
from data.folders import Folders
from data.runner import Runner
from data.tools import Tool, ToolsT


class BuildStep(enum.Flag):
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
        utils.RelAssertType(self.step, BuildStep, "BuildSetup.step")
        utils.RelAssertType(self.folders, Folders, "BuildSetup.folders")
        utils.RelAssertType(self.runner, Runner, "BuildSetup.runner")
        utils.RelAssertType(self.bundles, Bundles, "BuildSetup.bundles")
        utils.RelAssertType(self.tools, dict, "BuildSetup.tools")
        for k,v in self.tools.items():
            utils.RelAssertType(k, str, "BuildSetup.tools.key")
            utils.RelAssertType(v, Tool, "BuildSetup.tools.value")

    def VerifyValues(self) -> None:
        utils.RelAssert(self.tools.get("crunch") != None, "BuildSetup.tools is missing a definition for 'crunch'")
        utils.RelAssert(self.tools.get("gametextcompiler") != None, "BuildSetup.tools is missing a definition for 'gametextcompiler'")
        utils.RelAssert(self.tools.get("generalsbigcreator") != None, "BuildSetup.tools is missing a definition for 'generalsbigcreator'")
