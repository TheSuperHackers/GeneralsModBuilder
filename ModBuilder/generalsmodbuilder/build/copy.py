import os
import subprocess
import shutil
import sys
import util
import enum
from enum import Enum, Flag
from typing import Callable
from dataclasses import dataclass, field
from data.bundles import ParamsT
from data.tools import ToolsT
from build.thing import BuildFile, BuildThing
from build.common import ParamsToArgs


class BuildFileType(Enum):
    csf = 0
    str = enum.auto()
    big = enum.auto()
    zip = enum.auto()
    tar = enum.auto()
    gz = enum.auto()
    psd = enum.auto()
    bmp = enum.auto()
    tga = enum.auto()
    dds = enum.auto()
    Any = enum.auto()
    Auto = enum.auto()


def GetFileType(filePath: str) -> BuildFileType:
    type: BuildFileType
    ext: str = util.GetFileExt(filePath)
    for type in BuildFileType:
        if ext.lower() == type.name:
            return type
    return BuildFileType.Any


class BuildCopyOption(Flag):
    Zero = 0
    EnableBackup = enum.auto()
    EnableSymlinks = enum.auto()


@dataclass
class BuildCopy:
    tools: ToolsT
    options: BuildCopyOption = field(default=BuildCopyOption.Zero)


    def CopyThing(self, thing: BuildThing) -> bool:
        success: bool = True
        file: BuildFile

        for file in thing.files:
            if file.RequiresRebuild():
                absSource: str = file.AbsSource()
                absTarget: str = file.AbsTarget(thing.absParentDir)
                params: ParamsT = file.params
                success &= self.Copy(absSource, absTarget, params)

        return success


    def UncopyThing(self, thing: BuildThing) -> bool:
        success: bool = True
        file: BuildFile

        for file in thing.files:
            absTarget: str = file.AbsTarget(thing.absParentDir)
            success &= self.Uncopy(absTarget)

        return success


    def Copy(
            self,
            source: str,
            target: str,
            params: ParamsT = None,
            sourceType = BuildFileType.Auto,
            targetType = BuildFileType.Auto) -> bool:

        if sourceType == BuildFileType.Auto:
            sourceType = GetFileType(source)

        if targetType == BuildFileType.Auto:
            targetType = GetFileType(target)

        util.MakeDirsForFile(target)

        if self.options & BuildCopyOption.EnableBackup:
            BuildCopy.__CreateBackup(target)

        util.DeleteFileOrPath(target)

        copyFunction: Callable = self.__GetCopyFunction(sourceType, targetType)
        success: bool = copyFunction(source, target, params)

        return success


    def Uncopy(self, file: str) -> bool:
        success: bool = True

        if os.path.isfile(file):
            os.remove(file)
            BuildCopy.__PrintUncopyResult(file)

        if self.options & BuildCopyOption.EnableBackup:
            success &= BuildCopy.__RevertBackup(file)

        return success


    @staticmethod
    def __CreateBackup(file: str) -> bool:
        if os.path.isfile(file):
            backupFile: str = BuildCopy.__MakeBackupFileName(file)

            if not os.path.isfile(backupFile):
                os.rename(src=file, dst=backupFile)
                return True

        return False


    @staticmethod
    def __RevertBackup(file: str) -> bool:
        backupFile: str = BuildCopy.__MakeBackupFileName(file)

        if os.path.isfile(backupFile):
            os.rename(src=backupFile, dst=file)
            return True

        return False


    @staticmethod
    def __MakeBackupFileName(file: str) -> str:
        return file + ".BAK"


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


    @staticmethod
    def __PrintUncopyResult(file) -> None:
        print("Remove", file)


    def __GetCopyFunction(self, sourceT: BuildFileType, targetT: BuildFileType) -> Callable:
        if targetT == BuildFileType.Any or sourceT == targetT:
            return self.__CopyTo

        if targetT == BuildFileType.csf and sourceT == BuildFileType.str:
            return self.__CopyToCSF

        if targetT == BuildFileType.str and sourceT == BuildFileType.csf:
            return self.__CopyToSTR

        if targetT == BuildFileType.big:
            return self.__CopyToBIG

        if targetT == BuildFileType.zip:
            return self.__CopyToZIP

        if targetT == BuildFileType.tar:
            return self.__CopyToTAR

        if targetT == BuildFileType.gz:
            return self.__CopyToGZTAR

        if targetT == BuildFileType.bmp and (sourceT == BuildFileType.psd or sourceT == BuildFileType.tga):
            return self.__CopyToBMP

        if targetT == BuildFileType.tga and sourceT == BuildFileType.psd:
            return self.__CopyToTGA

        if targetT == BuildFileType.dds and (sourceT == BuildFileType.psd or sourceT == BuildFileType.tga):
            return self.__CopyToDDS

        return self.__CopyTo


    def __CopyTo(self, source: str, target: str, params: ParamsT) -> bool:
        if self.options & BuildCopyOption.EnableSymlinks:
            try:
                os.symlink(src=source, dst=target)
                BuildCopy.__PrintLinkResult(source, target)
                return True
            except OSError:
                pass

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
        shutil.make_archive(base_name=util.GetFileDirAndName(target), format="zip", root_dir=source)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToTAR(self, source: str, target: str, params: ParamsT) -> bool:
        shutil.make_archive(base_name=util.GetFileDirAndName(target), format="tar", root_dir=source)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToGZTAR(self, source: str, target: str, params: ParamsT) -> bool:
        shutil.make_archive(base_name=util.GetFileDirAndName(target), format="gztar", root_dir=source)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToBMP(self, source: str, target: str, params: ParamsT) -> bool:
        exec: str = self.__GetToolExePath("crunch")

        argsRun: list[str] = [exec,
            "-file", source,
            "-out", target,
            "-fileformat", "bmp"]

        argsRun.extend(ParamsToArgs(params))

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

        args.extend(ParamsToArgs(params))
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

        args.extend(ParamsToArgs(params))
        args.append("-DXT5" if hasAlpha else "-DXT1")

        subprocess.run(args=args, check=True)

        BuildCopy.__PrintMakeResult(source, target)
        return True


    def __HasAlphaChannel(self, source: str) -> bool:
        exec: str = self.__GetToolExePath("crunch")
        args: list[str] = [exec, "-file", source, "-info"]
        outputBytes: bytes = subprocess.run(args=args, check=True, capture_output=True).stdout
        outputStr: str = outputBytes.decode(sys.getdefaultencoding())
        upper: str = outputStr.upper()
        hasAlpha: bool = False
        if ("FORMAT: A8L8" in upper) or ("FORMAT: A8R8G8B8" in upper):
            hasAlpha = True
        return hasAlpha


    def __GetToolExePath(self, name: str) -> str:
        return self.tools.get(name).GetExecutable()
