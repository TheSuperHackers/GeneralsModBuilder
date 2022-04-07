import os
import subprocess
import shutil
import utils
import enum
from enum import Enum
from typing import Callable, Union
from dataclasses import dataclass
from data.bundles import ParamsT
from data.tools import ToolsT
from build.thing import BuildFile, BuildThing, BuildThingsT


class BuildFileType(Enum):
    CSF = enum.auto()
    STR = enum.auto()
    BIG = enum.auto()
    ZIP = enum.auto()
    TAR = enum.auto()
    GZTAR = enum.auto()
    PSD = enum.auto()
    BMP = enum.auto()
    TGA = enum.auto()
    DDS = enum.auto()
    ANY = enum.auto()
    AUTO = enum.auto()


def GetFileType(filePath: str) -> BuildFileType:
    if utils.HasFileExt(filePath, "csf"):
        return BuildFileType.CSF
    if utils.HasFileExt(filePath, "str"):
        return BuildFileType.STR
    if utils.HasFileExt(filePath, "big"):
        return BuildFileType.BIG
    if utils.HasFileExt(filePath, "zip"):
        return BuildFileType.ZIP
    if utils.HasFileExt(filePath, "tar"):
        return BuildFileType.TAR
    if utils.HasFileExt(filePath, "gz"):
        return BuildFileType.GZTAR
    if utils.HasFileExt(filePath, "psd"):
        return BuildFileType.PSD
    if utils.HasFileExt(filePath, "bmp"):
        return BuildFileType.BMP
    if utils.HasFileExt(filePath, "tga"):
        return BuildFileType.TGA
    if utils.HasFileExt(filePath, "dds"):
        return BuildFileType.DDS
    return BuildFileType.ANY


@dataclass
class BuildCopy:
    tools: ToolsT


    def CopyThings(self, things: BuildThingsT) -> bool:
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
                if not file.IsUnchanged():
                    success &= self.__CopyFile(file, thing.absParentDir)

        return success


    @staticmethod
    def __RequiresFullCopy(thing: BuildThing) -> bool:
        return thing.parentHasDeletedFiles


    def __CopyFile(self, file: BuildFile, absParentDir: str) -> bool:
        absSource: str = file.AbsSource()
        absTarget: str = file.AbsTarget(absParentDir)
        params: ParamsT = file.params
        return self.Copy(absSource, absTarget, params)


    def Copy(
            self,
            source: str,
            target: str,
            params: ParamsT = None,
            sourceType = BuildFileType.AUTO,
            targetType = BuildFileType.AUTO) -> bool:

        if sourceType == BuildFileType.AUTO:
            sourceType = GetFileType(source)

        if targetType == BuildFileType.AUTO:
            targetType = GetFileType(target)

        utils.MakeDirsForFile(target)

        copyFunction: Callable = self.__GetCopyFunction(sourceType, targetType)
        success: bool = copyFunction(source, target, params)

        return success


    @staticmethod
    def __PrintCopyResult(source: str, target: str) -> None:
        print("Copy", source)
        print("  to", target)


    @staticmethod
    def __PrintLinkResult(source: str, target: str) -> None:
        print("Link", source)
        print("  to", target)


    @staticmethod
    def __PrintMakeResult(source: str, target: str) -> None:
        print("With", source)
        print("make", target)


    def __GetCopyFunction(self, sourceT: BuildFileType, targetT: BuildFileType) -> Callable:
        if targetT == BuildFileType.ANY or sourceT == targetT:
            return self.__CopyTo

        if targetT == BuildFileType.CSF and sourceT == BuildFileType.STR:
            return self.__CopyToCSF

        if targetT == BuildFileType.STR and sourceT == BuildFileType.CSF:
            return self.__CopyToSTR

        if targetT == BuildFileType.BIG:
            return self.__CopyToBIG

        if targetT == BuildFileType.ZIP:
            return self.__CopyToZIP

        if targetT == BuildFileType.TAR:
            return self.__CopyToTAR

        if targetT == BuildFileType.GZTAR:
            return self.__CopyToGZTAR

        if targetT == BuildFileType.BMP and (sourceT == BuildFileType.PSD or sourceT == BuildFileType.TGA):
            return self.__CopyToBMP

        if targetT == BuildFileType.TGA and sourceT == BuildFileType.PSD:
            return self.__CopyToTGA

        if targetT == BuildFileType.DDS and (sourceT == BuildFileType.PSD or sourceT == BuildFileType.TGA):
            return self.__CopyToDDS

        return self.__CopyTo


    def __CopyTo(self, source: str, target: str, params: ParamsT) -> bool:
        try:
            os.symlink(src=source, dst=target)
            BuildCopy.__PrintLinkResult(source, target)
        except OSError:
            shutil.copy(src=source, dst=target)
            BuildCopy.__PrintCopyResult(source, target)

        return True


    def __CopyToCSF(self, source: str, target: str, params: ParamsT) -> bool:
        exec: str = self.__GetToolExePath("gametextcompiler")
        args = [exec,
            "-LOAD_STR", source,
            "-SAVE_CSF", target]

        language: str = params.get("language")
        if language != None and isinstance(language, str):
            args.extend(["-LOAD_STR_LANGUAGES", language])

        subprocess.run(args, check=True)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToSTR(self, source: str, target: str, params: ParamsT) -> bool:
        exec: str = self.__GetToolExePath("gametextcompiler")
        args: list[str] = [exec,
            "-LOAD_CSF", source,
            "-SAVE_STR", target]

        language: str = params.get("language")
        if language != None and isinstance(language, str):
            args.extend(["-SAVE_STR_LANGUAGES", language])

        subprocess.run(args, check=True)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToBIG(self, source: str, target: str, params: ParamsT) -> bool:
        exec: str = self.__GetToolExePath("generalsbigcreator")
        args: list[str] = [exec,
            "-source", source,
            "-dest", target]

        subprocess.run(args=args, check=True)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToZIP(self, source: str, target: str, params: ParamsT) -> bool:
        shutil.make_archive(base_name=utils.GetFileDirAndName(target), format="zip", root_dir=source)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToTAR(self, source: str, target: str, params: ParamsT) -> bool:
        shutil.make_archive(base_name=utils.GetFileDirAndName(target), format="tar", root_dir=source)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToGZTAR(self, source: str, target: str, params: ParamsT) -> bool:
        shutil.make_archive(base_name=utils.GetFileDirAndName(target), format="gztar", root_dir=source)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToBMP(self, source: str, target: str, params: ParamsT) -> bool:
        exec: str = self.__GetToolExePath("crunch")

        argsRun: list[str] = [exec,
            "-file", source,
            "-out", target,
            "-fileformat", "bmp"]

        argsRun.extend(BuildCopy.__ParamsToArgs(params))

        subprocess.run(args=argsRun, check=True)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToTGA(self, source: str, target: str, params: ParamsT) -> bool:
        hasAlpha: bool = self.__HasAlphaChannel(source)

        exec: str = self.__GetToolExePath("crunch")
        args: list[str] = [exec,
            "-file", source,
            "-out", target,
            "-fileformat", "tga"]

        args.extend(BuildCopy.__ParamsToArgs(params))
        args.append("-A8R8G8B8" if hasAlpha else "-R8G8B8")

        subprocess.run(args=args, check=True)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToDDS(self, source: str, target: str, params: ParamsT) -> bool:
        hasAlpha: bool = self.__HasAlphaChannel(source)

        exec: str = self.__GetToolExePath("crunch")
        args: list[str] = [exec,
            "-file", source,
            "-out", target,
            "-fileformat", "dds"]

        args.extend(BuildCopy.__ParamsToArgs(params))
        args.append("-DXT5" if hasAlpha else "-DXT1")

        subprocess.run(args=args, check=True)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __HasAlphaChannel(self, source: str) -> bool:
        exec: str = self.__GetToolExePath("crunch")
        args: list[str] = [exec, "-file", source, "-info"]
        output: str = subprocess.run(args=args, check=True, capture_output=True).stdout
        upper: str = output.upper()
        hasAlpha: bool = False
        if (b"FORMAT: A8L8" in upper) or (b"FORMAT: A8R8G8B8" in upper):
            hasAlpha = True
        return hasAlpha


    @staticmethod
    def __ParamsToArgs(params: ParamsT) -> list[str]:
        args = list()
        for key,value in params.items():
            BuildCopy.__AppendParamToArgs(args, key)

            if isinstance(value, list):
                for subValue in value:
                    BuildCopy.__AppendParamToArgs(args, subValue)
            else:
                BuildCopy.__AppendParamToArgs(args, value)

        return args


    @staticmethod
    def __AppendParamToArgs(args: list[str], val: Union[str, int, float, bool]) -> None:
        if strVal := str(val):
            args.append(strVal)


    def __GetToolExePath(self, name: str) -> str:
        return self.tools.get(name).GetExecutable()
