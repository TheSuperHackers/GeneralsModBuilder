from enum import Flag, auto
from dataclasses import dataclass
from generalsmodbuilder.data.bundles import Bundles
from generalsmodbuilder.data.folders import Folders
from generalsmodbuilder.data.runner import Runner
from generalsmodbuilder.data.tools import Tool, ToolsT
from generalsmodbuilder import util


class BuildStep(Flag):
    Zero = 0
    PreBuild = auto()
    Clean = auto()
    Build = auto()
    PostBuild = auto()
    Release = auto()
    Install = auto()
    Run = auto()
    Uninstall = auto()


@dataclass
class BuildSetup:
    step: BuildStep
    folders: Folders
    runner: Runner
    bundles: Bundles
    tools: ToolsT
    printConfig: bool
    verboseLogging: bool
    multiProcessing: bool

    def VerifyTypes(self) -> None:
        util.VerifyType(self.step, BuildStep, "BuildSetup.step")
        util.VerifyType(self.folders, Folders, "BuildSetup.folders")
        util.VerifyType(self.runner, Runner, "BuildSetup.runner")
        util.VerifyType(self.bundles, Bundles, "BuildSetup.bundles")
        util.VerifyType(self.tools, dict, "BuildSetup.tools")
        util.VerifyType(self.printConfig, bool, "BuildSetup.printConfig")
        util.VerifyType(self.verboseLogging, bool, "BuildSetup.verboseLogging")
        util.VerifyType(self.multiProcessing, bool, "BuildSetup.multiProcessing")
        for key, value in self.tools.items():
            util.VerifyType(key, str, "BuildSetup.tools.key")
            util.VerifyType(value, Tool, "BuildSetup.tools.value")

    def VerifyValues(self) -> None:
        if self.tools.get("crunch") == None:
            print(f"Warning: BuildSetup.tools is missing a definition for 'crunch', which may be required to build DDS files.")
        if self.tools.get("gametextcompiler") == None:
            print(f"Warning: BuildSetup.tools is missing a definition for 'gametextcompiler', which may be required to build CSF and STR files.")
        if self.tools.get("generalsbigcreator") == None:
            print(f"Warning: BuildSetup.tools is missing a definition for 'generalsbigcreator', which may be required to build BIG files.")
        if self.tools.get("blender") == None:
            print(f"Warning: BuildSetup.tools is missing a definition for 'blender', which may be required to build W3D files.")
