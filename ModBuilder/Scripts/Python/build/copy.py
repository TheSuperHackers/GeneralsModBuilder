import enum
from enum import Enum
from dataclasses import dataclass
from typing import Any
from data.tools import Tool
from build.thing import BuildFile, BuildFileStatus, BuildThing


class BuildFileType(Enum):
    CSF = enum.auto()
    STR = enum.auto()
    BIG = enum.auto()
    ZIP = enum.auto()
    PSD = enum.auto()
    TGA = enum.auto()
    DDS = enum.auto()
    ANY = enum.auto()
    AUTO = enum.auto()


def GetFileTypeFromFileExt(ext: str):
    if ext.endswith("csf"):
        return BuildFileType.CSF
    if ext.endswith("str"):
        return BuildFileType.STR
    if ext.endswith("big"):
        return BuildFileType.BIG
    if ext.endswith("zip"):
        return BuildFileType.ZIP
    if ext.endswith("psd"):
        return BuildFileType.PSD
    if ext.endswith("tga"):
        return BuildFileType.TGA
    if ext.endswith("dds"):
        return BuildFileType.DDS
    return BuildFileType.ANY


@dataclass
class BuildCopy:
    tools: dict[Tool]


    def CopyThings(self, things: dict[BuildThing]) -> bool:
        success: bool = True
        thing: BuildThing

        for thing in things.values():
            if not self.CopyThing(thing):
                success = False

        return success


    def CopyThing(self, thing: BuildThing) -> bool:
        success: bool = True
        file: BuildFile

        if BuildCopy.__RequiresFullCopy(thing):
            for file in thing.files:
                success &= self.__CopyFile(file, thing.absParentDir)
        else:
            for file in thing.files:
                if file.sourceStatus != BuildFileStatus.UNCHANGED:
                    success &= self.__CopyFile(file, thing.absParentDir)

        return success


    def __CopyFile(self, file: BuildFile, absParentDir: str) -> bool:
        absSource: str = file.AbsSource()
        absTarget: str = file.AbsTarget(absParentDir)
        params: dict[str, Any] = file.params
        return self.Copy(absSource, absTarget, params)


    def Copy(
        self,
        absSource: str,
        absTarget: str,
        params: dict[str, Any] = None,
        sourceType = BuildFileType.AUTO,
        targetType = BuildFileType.AUTO) -> bool:
        success: bool = True

        return success


    @staticmethod
    def __RequiresFullCopy(thing: BuildThing) -> bool:
        return thing.parentHasDeletedFiles
