import enum
from enum import Enum
from dataclasses import dataclass
import os
from typing import Any, Callable


class BuildFileStatus(Enum):
    UNKNOWN = enum.auto()
    UNCHANGED = enum.auto()
    ADDED = enum.auto()
    CHANGED = enum.auto()


@dataclass(init=False)
class BuildFile:
    relTarget: str
    absSource: str
    params: dict[str, Any]
    sourceStatus: BuildFileStatus

    def __init__(self):
        self.params = None
        self.sourceStatus = BuildFileStatus.UNKNOWN

    def RelTarget(self) -> str:
        return self.relTarget

    def AbsTarget(self, absParentDir: str) -> str:
        return os.path.join(absParentDir, self.relTarget)

    def AbsSource(self) -> str:
        return self.absSource


@dataclass(init=False)
class BuildThing:
    name: str
    absParentDir: str
    files: list[BuildFile]
    childThings: list[Any]
    parentHasDeletedFiles: bool

    def __init__(self):
        self.childThings = list()
        self.parentHasDeletedFiles = False

    def ForEachChild(self, function: Callable[[Any], None]) -> None:
        child: BuildThing
        for child in self.childThings:
            function(child)
