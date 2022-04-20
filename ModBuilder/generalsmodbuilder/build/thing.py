import os
import enum
from dataclasses import dataclass
from typing import Any
from data.bundles import ParamsT


class BuildFileStatus(enum.Enum):
    Unknown = 0
    Unchanged = enum.auto()
    Removed = enum.auto()
    Missing = enum.auto()
    Added = enum.auto()
    Changed = enum.auto()


@dataclass(init=False)
class BuildFile:
    relTarget: str
    absSource: str
    targetStatus: BuildFileStatus
    sourceStatus: BuildFileStatus
    parentFile: Any
    params: ParamsT

    def __init__(self):
        self.targetStatus = BuildFileStatus.Unknown
        self.sourceStatus = BuildFileStatus.Unknown
        self.parentFile = None
        self.params = dict()

    def RelTarget(self) -> str:
        return self.relTarget

    def AbsTarget(self, absParentDir: str) -> str:
        return os.path.join(absParentDir, self.relTarget)

    def AbsRealTarget(self, absParentDir: str) -> str:
        return os.path.realpath(self.AbsTarget(absParentDir))

    def AbsSource(self) -> str:
        return self.absSource

    def AbsRealSource(self) -> str:
        return os.path.realpath(self.absSource)

    def GetCombinedStatus(self) -> BuildFileStatus:
        maxValue: int = max(self.targetStatus.value, self.sourceStatus.value)
        return BuildFileStatus(maxValue)

    def RequiresRebuild(self) -> bool:
        status: BuildFileStatus = self.GetCombinedStatus()
        return (status == BuildFileStatus.Removed or
                status == BuildFileStatus.Missing or
                status == BuildFileStatus.Added or
                status == BuildFileStatus.Changed)


BuildFilesT = list[BuildFile]


@dataclass(init=False)
class BuildThing:
    name: str
    absParentDir: str
    files: BuildFilesT
    parentThing: Any
    fileCounts: list[int]

    def __init__(self):
        self.childThings = list()
        self.parentThing = None
        self.fileCounts = [0] * len(BuildFileStatus)

    def GetFileCount(self, status: BuildFileStatus) -> int:
        return self.fileCounts[status.value]

    def GetMostSignificantFileStatus(self) -> BuildFileStatus:
        retStatus: BuildFileStatus = BuildFileStatus.Unknown
        status: BuildFileStatus
        for status in BuildFileStatus:
            if self.GetFileCount(status) > 0:
                retStatus = status
        return retStatus


BuildThingsT = dict[str, BuildThing]
