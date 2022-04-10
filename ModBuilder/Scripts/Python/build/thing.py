import os
import enum
from dataclasses import dataclass
from typing import Any
from data.bundles import ParamsT


class BuildFileStatus(enum.Enum):
    UNKNOWN = 0
    UNCHANGED = enum.auto()
    REMOVED = enum.auto()
    MISSING = enum.auto()
    ADDED = enum.auto()
    CHANGED = enum.auto()


@dataclass(init=False)
class BuildFile:
    relTarget: str
    absSource: str
    targetStatus: BuildFileStatus
    sourceStatus: BuildFileStatus
    parentFile: Any
    params: ParamsT

    def __init__(self):
        self.targetStatus = BuildFileStatus.UNKNOWN
        self.sourceStatus = BuildFileStatus.UNKNOWN
        self.parentFile = None
        self.params = dict()

    def RelTarget(self) -> str:
        return self.relTarget

    def AbsTarget(self, absParentDir: str) -> str:
        return os.path.join(absParentDir, self.relTarget)

    def AbsSource(self) -> str:
        return self.absSource

    def GetCombinedStatus(self) -> BuildFileStatus:
        maxValue: int = max(self.targetStatus.value, self.sourceStatus.value)
        return BuildFileStatus(maxValue)

    def RequiresRebuild(self) -> bool:
        status: BuildFileStatus = self.GetCombinedStatus()
        return (status == BuildFileStatus.REMOVED or
                status == BuildFileStatus.MISSING or
                status == BuildFileStatus.ADDED or
                status == BuildFileStatus.CHANGED)


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
        retStatus: BuildFileStatus = BuildFileStatus.UNKNOWN
        status: BuildFileStatus
        for status in BuildFileStatus:
            if self.GetFileCount(status) > 0:
                retStatus = status
        return retStatus


BuildThingsT = dict[str, BuildThing]
