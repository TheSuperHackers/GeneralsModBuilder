import enum
from dataclasses import dataclass
from generalsmodbuilder.data.bundles import Bundles
from generalsmodbuilder.data.folders import Folders
from generalsmodbuilder.data.runner import Runner
from generalsmodbuilder.data.tools import Tool, ToolsT
from generalsmodbuilder import util


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
    printConfig: bool

    def VerifyTypes(self) -> None:
        util.RelAssertType(self.step, BuildStep, "BuildSetup.step")
        util.RelAssertType(self.folders, Folders, "BuildSetup.folders")
        util.RelAssertType(self.runner, Runner, "BuildSetup.runner")
        util.RelAssertType(self.bundles, Bundles, "BuildSetup.bundles")
        util.RelAssertType(self.tools, dict, "BuildSetup.tools")
        util.RelAssertType(self.printConfig, bool, "BuildSetup.printConfig")
        for k,v in self.tools.items():
            util.RelAssertType(k, str, "BuildSetup.tools.key")
            util.RelAssertType(v, Tool, "BuildSetup.tools.value")

    def VerifyValues(self) -> None:
        util.RelAssert(self.tools.get("crunch") != None, "BuildSetup.tools is missing a definition for 'crunch'")
        util.RelAssert(self.tools.get("gametextcompiler") != None, "BuildSetup.tools is missing a definition for 'gametextcompiler'")
        util.RelAssert(self.tools.get("generalsbigcreator") != None, "BuildSetup.tools is missing a definition for 'generalsbigcreator'")
