import os
import enum
from dataclasses import dataclass
from typing import Any
from generalsmodbuilder.data.bundles import BundleRegistryDefinition, ParamsT


class BuildFileStatus(enum.Enum):
    Unknown = 0
    Irrelevant = enum.auto()
    Unchanged = enum.auto()
    Removed = enum.auto()
    Missing = enum.auto()
    Added = enum.auto()
    Changed = enum.auto()


def IsStatusRelevantForBuild(status: BuildFileStatus) -> bool:
    return (status == BuildFileStatus.Removed or
            status == BuildFileStatus.Missing or
            status == BuildFileStatus.Added or
            status == BuildFileStatus.Changed)


@dataclass(init=False)
class BuildFile:
    # This class is serialized and therefore may be missing attributes.
    relTarget: str
    absSources: list[str]
    targetStatus: BuildFileStatus
    sourceStatus: BuildFileStatus
    parentFile: Any
    params: ParamsT
    registryDef: BundleRegistryDefinition

    def __init__(self):
        self.relTarget = None
        self.absSources = None
        self.targetStatus = BuildFileStatus.Unknown
        self.sourceStatus = BuildFileStatus.Unknown
        self.parentFile = None
        self.params = None
        self.registryDef = None

    def RelTarget(self) -> str:
        return self.relTarget

    def AbsTarget(self, absParentDir: str) -> str:
        path = os.path.join(absParentDir, self.relTarget)
        path = os.path.normpath(path)
        return path

    def AbsSources(self) -> list[str]:
        try:
            return self.absSources
        except AttributeError:
            # Legacy. Was serialized by a release that stored one source file in absSource.
            return [self.absSource]

    def AbsSource(self) -> str:
        """
        Returns the first source file. Build event scripts of mod projects call this,
        so it keeps its name and its meaning for a file that has just one source file.
        """
        return self.AbsSources()[0]

    def HasMultiSource(self) -> bool:
        return len(self.AbsSources()) > 1

    def GetCombinedStatus(self) -> BuildFileStatus:
        maxValue: int = max(self.targetStatus.value, self.sourceStatus.value)
        return BuildFileStatus(maxValue)

    def RequiresRebuild(self) -> bool:
        status: BuildFileStatus = self.GetCombinedStatus()
        return IsStatusRelevantForBuild(status)


BuildFilesT = list[BuildFile]


@dataclass(init=False)
class BuildThing:
    name: str
    absParentDir: str
    files: BuildFilesT
    parentThing: Any
    fileCounts: list[int]
    setGameLanguageOnInstall: str

    def __init__(self):
        self.name = None
        self.absParentDir = None
        self.files = None
        self.parentThing = None
        self.fileCounts = [0] * len(BuildFileStatus)
        self.setGameLanguageOnInstall = None

    def GetFileCount(self, status: BuildFileStatus) -> int:
        return self.fileCounts[status.value]

    def GetMostSignificantFileStatus(self) -> BuildFileStatus:
        retStatus: BuildFileStatus = BuildFileStatus.Unknown
        status: BuildFileStatus
        for status in BuildFileStatus:
            if self.GetFileCount(status) > 0:
                retStatus = status
        return retStatus

    def NumberOfFilesBuildFromParentDir(self) -> int:
        count = 0
        file: BuildFile
        if self.parentThing != None:
            for file in self.files:
                if file.AbsSource() == self.parentThing.absParentDir:
                    count += 1
        return count


BuildThingsT = dict[str, BuildThing]
