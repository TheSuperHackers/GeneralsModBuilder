import util
import enum
from dataclasses import dataclass
from data.bundles import Bundles
from data.folders import Folders
from data.runner import Runner
from data.tools import Tool, ToolsT


class BuildStep(enum.Flag):
    Zero = 0
    PreBuild = enum.auto()
    Build = enum.auto()
    PostBuild = enum.auto()
    Release = enum.auto()
    Install = enum.auto()
    Run = enum.auto()
    Uninstall = enum.auto()


@dataclass
class BuildSetup:
    step: BuildStep
    folders: Folders
    runner: Runner
    bundles: Bundles
    tools: ToolsT

    def VerifyTypes(self) -> None:
        util.RelAssertType(self.step, BuildStep, "BuildSetup.step")
        util.RelAssertType(self.folders, Folders, "BuildSetup.folders")
        util.RelAssertType(self.runner, Runner, "BuildSetup.runner")
        util.RelAssertType(self.bundles, Bundles, "BuildSetup.bundles")
        util.RelAssertType(self.tools, dict, "BuildSetup.tools")
        for k,v in self.tools.items():
            util.RelAssertType(k, str, "BuildSetup.tools.key")
            util.RelAssertType(v, Tool, "BuildSetup.tools.value")

    def VerifyValues(self) -> None:
        util.RelAssert(self.tools.get("crunch") != None, "BuildSetup.tools is missing a definition for 'crunch'")
        util.RelAssert(self.tools.get("gametextcompiler") != None, "BuildSetup.tools is missing a definition for 'gametextcompiler'")
        util.RelAssert(self.tools.get("generalsbigcreator") != None, "BuildSetup.tools is missing a definition for 'generalsbigcreator'")
