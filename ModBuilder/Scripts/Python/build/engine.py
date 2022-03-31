import utils
from data.bundles import Bundle
from data.bundles import BundleFile
from data.folders import Folders
from data.runner import Runner
from data.tools import Tool
from dataclasses import dataclass


@dataclass
class Engine:
    folders: Folders
    runner: Runner
    bundles: list[Bundle]
    tools: dict[Tool]

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.folders, Folders), "Engine.folders has incorrect type")
        utils.RelAssert(isinstance(self.runner, Runner), "Engine.runner has incorrect type")
        utils.RelAssert(isinstance(self.bundles, list), "Engine.bundles has incorrect type")
        utils.RelAssert(isinstance(self.tools, dict), "Engine.tools has incorrect type")

    def VerifyValues(self) -> None:
        utils.RelAssert(self.tools.get("crunch") != None, "crunch tool definition is missing")
        utils.RelAssert(self.tools.get("gametextcompiler") != None, "gametextcompiler tool definition is missing")
        utils.RelAssert(self.tools.get("generalsbigcreator") != None, "generalsbigcreator tool definition is missing")
