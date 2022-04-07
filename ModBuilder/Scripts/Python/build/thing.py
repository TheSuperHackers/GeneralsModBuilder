import os
import enum
from enum import Enum
from dataclasses import dataclass
from typing import Any, Callable
from data.bundles import ParamsT


class BuildFileStatus(Enum):
    UNKNOWN = enum.auto()
    UNCHANGED = enum.auto()
    MISSING = enum.auto()
    ADDED = enum.auto()
    CHANGED = enum.auto()


@dataclass(init=False)
class BuildFile:
    relTarget: str
    absSource: str
    params: ParamsT
    targetStatus: BuildFileStatus
    sourceStatus: BuildFileStatus

    def __init__(self):
        self.params = dict()

    def RelTarget(self) -> str:
        return self.relTarget

    def AbsTarget(self, absParentDir: str) -> str:
        return os.path.join(absParentDir, self.relTarget)

    def AbsSource(self) -> str:
        return self.absSource

    def IsUnchanged(self) -> bool:
        return self.targetStatus == BuildFileStatus.UNCHANGED and self.sourceStatus == BuildFileStatus.UNCHANGED


BuildFilesT = list[BuildFile]


@dataclass(init=False)
class BuildThing:
    name: str
    absParentDir: str
    files: BuildFilesT
    childThings: list[Any]
    parentHasDeletedFiles: bool

    def __init__(self):
        self.childThings = list()
        self.parentHasDeletedFiles = False

    def ForEachChild(self, function: Callable[[Any], None]) -> None:
        child: BuildThing
        for child in self.childThings:
            function(child)


BuildThingsT = dict[str, BuildThing]
