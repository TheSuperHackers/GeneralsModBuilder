import concurrent.futures
import enum
import os
import PIL.Image
import PIL.TiffImagePlugin
import shutil
from concurrent.futures import Future, ProcessPoolExecutor
from dataclasses import dataclass, field
from psd_tools import PSDImage
from psd_tools.constants import ColorMode as PSDColorMode
from enum import Enum, Flag
from generalsmodbuilder.data.bundles import ParamsT
from generalsmodbuilder.data.tools import Tool, ToolsT
from generalsmodbuilder.build.caseinsensitivedict import CaseInsensitiveDict
from generalsmodbuilder.build.common import ParamsToArgs
from generalsmodbuilder.build.thing import BuildFile, BuildThing
from generalsmodbuilder import util
from PIL.Image import Image as PILImage
from PIL.Image import Resampling
from typing import Callable


class BuildFileType(Enum):
    big = enum.auto()
    blend = enum.auto()
    bmp = enum.auto()
    csf = enum.auto()
    dds = enum.auto()
    gz = enum.auto()
    ini = enum.auto()
    psd = enum.auto()
    str = enum.auto()
    tar = enum.auto()
    tga = enum.auto()
    tiff = enum.auto()
    w3d = enum.auto()
    wnd = enum.auto()
    zip = enum.auto()
    Any = enum.auto()
    Auto = enum.auto()

def __BuildFileTypeStringMap() -> dict[str, BuildFileType]:
    d = dict()
    for type in BuildFileType:
        d[type.name] = type
    d["tif"] = BuildFileType.tiff
    return d

FileTypeStringDict: dict[str, BuildFileType] = __BuildFileTypeStringMap()

def GetFileType(filePath: str) -> BuildFileType:
    ext: str = util.GetFileExt(filePath).lower()
    type: BuildFileType = FileTypeStringDict.get(ext)
    if type == None:
        type = BuildFileType.Any
    return type


CrunchTextureFormatSet: set[str] = {
    "-DXT1",
    "-DXT2",
    "-DXT3",
    "-DXT4",
    "-DXT5",
    "-3DC",
    "-DXN",
    "-DXT5A",
    "-DXT5_CCxY",
    "-DXT5_xGxR",
    "-DXT5_xGBR",
    "-DXT5_AGBR",
    "-DXT1A",
    "-ETC1",
    "-ETC2",
    "-ETC2A",
    "-ETC1S",
    "-ETC2AS",
    "-R8G8B8",
    "-L8",
    "-A8",
    "-A8L8",
    "-A8R8G8B8"
}


class BuildCopyOption(Flag):
    Zero = 0
    EnableBackup = enum.auto()
    EnableSymlinks = enum.auto()
    EnableLogging = enum.auto()


class BuildJob:
    success: bool
    absSource: str
    absTarget: str
    params: ParamsT


@dataclass
class BuildCopy:
    tools: ToolsT
    options: BuildCopyOption = field(default=BuildCopyOption.Zero)
    processPool: ProcessPoolExecutor = field(default=None)

    def CopyThing(self, thing: BuildThing) -> bool:
        if self.processPool != None:
            return self.CopyThingMultiProcess(thing)
        else:
            return self.CopyThingSingleProcess(thing)


    def CopyThingSingleProcess(self, thing: BuildThing) -> bool:
        success: bool = True
        file: BuildFile

        for file in thing.files:
            if file.RequiresRebuild():
                absSource: str = file.AbsSource()
                absTarget: str = file.AbsTarget(thing.absParentDir)
                params: ParamsT = file.params
                success &= self.Copy(absSource, absTarget, params)
                if not success:
                    raise Exception(f"Unable to copy source '{absSource}' to target '{absTarget}'.")

        return success


    def CopyThingMultiProcess(self, thing: BuildThing) -> bool:
        success: bool = True
        options = self.options & ~BuildCopyOption.EnableLogging
        futures = list[Future]()
        future: Future
        buildJob: BuildJob
        file: BuildFile

        for file in thing.files:
            if file.RequiresRebuild():
                buildJob = BuildJob()
                buildJob.success = False
                buildJob.absSource = file.AbsSource()
                buildJob.absTarget = file.AbsTarget(thing.absParentDir)
                buildJob.params = file.params
                future = self.processPool.submit(CopyWithProcess, self.tools, options, buildJob)
                futures.append(future)

        concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

        for future in futures:
            buildJob = future.result()
            success &= buildJob.success
            if not success:
                raise Exception(f"Unable to copy source '{buildJob.absSource}' to target '{buildJob.absTarget}'.")

        return success


    def UncopyThing(self, thing: BuildThing, respectBuildFileStatus=True) -> bool:
        success: bool = True
        file: BuildFile

        for file in thing.files:
            if file.RequiresRebuild() or not respectBuildFileStatus:
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

        if not os.path.exists(source):
            return False

        if sourceType == BuildFileType.Auto:
            sourceType = GetFileType(source)

        if targetType == BuildFileType.Auto:
            targetType = GetFileType(target)

        util.MakeDirsForFile(target)

        if self.options & BuildCopyOption.EnableBackup:
            BuildCopy.__CreateBackup(target)

        util.DeleteFileOrDir(target)

        copyFunction: Callable = self.__GetCopyFunction(sourceType, targetType)
        success: bool = copyFunction(source, target, params)

        return success


    def Uncopy(self, file: str) -> bool:
        success: bool = False

        if util.DeleteFileOrDir(file):
            if self.options & BuildCopyOption.EnableLogging:
                BuildCopy.__PrintUncopyResult(file)
            success = True

        if self.options & BuildCopyOption.EnableBackup:
            BuildCopy.__RevertBackup(file)

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
        if targetT == BuildFileType.ini:
            return self.__CopyToTextFile

        if targetT == BuildFileType.wnd:
            return self.__CopyToTextFile

        if targetT == BuildFileType.str and not sourceT == BuildFileType.csf:
            return self.__CopyToTextFile

        if targetT == BuildFileType.dds and sourceT == BuildFileType.dds:
            return self.__CopyToDDS

        # Be mindful about what comes before and after this.
        if targetT == BuildFileType.Any or sourceT == targetT:
            return self.__CopyTo

        if targetT == BuildFileType.csf and sourceT == BuildFileType.str:
            return self.__CopySTRtoCSF

        if targetT == BuildFileType.str and sourceT == BuildFileType.csf:
            return self.__CopyCSFtoSTR

        if targetT == BuildFileType.big:
            return self.__CopyToBIG

        if targetT == BuildFileType.zip:
            return self.__CopyToZIP

        if targetT == BuildFileType.tar:
            return self.__CopyToTAR

        if targetT == BuildFileType.gz:
            return self.__CopyToGZTAR

        if targetT == BuildFileType.bmp and (
            sourceT == BuildFileType.psd or
            sourceT == BuildFileType.tga or
            sourceT == BuildFileType.tiff):
            return self.__CopyToBMP

        if targetT == BuildFileType.tga and (
            sourceT == BuildFileType.psd or
            sourceT == BuildFileType.tiff):
            return self.__CopyToTGA

        if targetT == BuildFileType.dds and (
            sourceT == BuildFileType.psd or
            sourceT == BuildFileType.tga or
            sourceT == BuildFileType.tiff):
            return self.__CopyToDDS

        if targetT == BuildFileType.w3d and sourceT == BuildFileType.blend:
            return self.__CopyToW3D

        return self.__CopyTo


    def __CopyTo(self, source: str, target: str, params: ParamsT) -> bool:
        if self.options & BuildCopyOption.EnableSymlinks:
            try:
                os.symlink(src=source, dst=target)
                if self.options & BuildCopyOption.EnableLogging:
                    BuildCopy.__PrintLinkResult(source, target)
                return True
            except OSError:
                pass

        shutil.copy(src=source, dst=target)
        if self.options & BuildCopyOption.EnableLogging:
            BuildCopy.__PrintCopyResult(source, target)
        return True


    def __CopySTRtoCSF(self, source: str, target: str, params: ParamsT) -> bool:
        tmpTarget: str = target + ".tmp"
        if self.__CopyToTextFileIfNeeded(source, tmpTarget, params):
            source = tmpTarget

        iparams = CaseInsensitiveDict(params)
        exec: str = self.__GetToolExePath("gametextcompiler")
        args: list[str] = [exec,
            "-LOAD_STR", source,
            "-SAVE_CSF", target]

        language: str = iparams.get("language")
        if isinstance(language, str) and bool(language):
            args.extend(["-LOAD_STR_LANGUAGES", language])

        swapAndSetLanguage: str = iparams.get("swapAndSetLanguage")
        if isinstance(swapAndSetLanguage, str) and bool(swapAndSetLanguage):
            args.extend(["-SWAP_AND_SET_LANGUAGE", swapAndSetLanguage])

        success: bool = util.RunProcess(args)
        if success and self.options & BuildCopyOption.EnableLogging:
            BuildCopy.__PrintMakeResult(source, target)

        if tmpTarget == source:
            util.DeleteFile(tmpTarget)

        return success


    def __CopyCSFtoSTR(self, source: str, target: str, params: ParamsT) -> bool:
        iparams = CaseInsensitiveDict(params)
        exec: str = self.__GetToolExePath("gametextcompiler")
        args: list[str] = [exec,
            "-LOAD_CSF", source,
            "-SAVE_STR", target]

        language: str = iparams.get("language")
        if isinstance(language, str) and bool(language):
            args.extend(["-SAVE_STR_LANGUAGES", language])

        success: bool = util.RunProcess(args)
        if success and self.options & BuildCopyOption.EnableLogging:
            BuildCopy.__PrintMakeResult(source, target)

        return success


    def __CopyToBIG(self, source: str, target: str, params: ParamsT) -> bool:
        exec: str = self.__GetToolExePath("generalsbigcreator")
        args: list[str] = [exec,
            "-source", source,
            "-dest", target]

        success: bool = util.RunProcess(args)
        if success and self.options & BuildCopyOption.EnableLogging:
            BuildCopy.__PrintMakeResult(source, target)

        return success


    def __CopyToZIP(self, source: str, target: str, params: ParamsT) -> bool:
        shutil.make_archive(base_name=util.GetFileDirAndName(target), format="zip", root_dir=source)

        if self.options & BuildCopyOption.EnableLogging:
            BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToTAR(self, source: str, target: str, params: ParamsT) -> bool:
        shutil.make_archive(base_name=util.GetFileDirAndName(target), format="tar", root_dir=source)

        if self.options & BuildCopyOption.EnableLogging:
            BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToGZTAR(self, source: str, target: str, params: ParamsT) -> bool:
        shutil.make_archive(base_name=util.GetFileDirAndName(target), format="gztar", root_dir=source)

        if self.options & BuildCopyOption.EnableLogging:
            BuildCopy.__PrintMakeResult(source, target)
        return True


    def __CopyToBMP(self, source: str, target: str, params: ParamsT) -> bool:
        return self.__CopyToImage(source, target, params)


    def __CopyToTGA(self, source: str, target: str, params: ParamsT) -> bool:
        return self.__CopyToImage(source, target, params)


    def __CopyToImage(self, source: str, target: str, params: ParamsT) -> bool:
        success: bool = False

        img: PILImage = None
        fileType: BuildFileType = GetFileType(source)

        if fileType == BuildFileType.psd:
            img = BuildCopy.__BuildImageFromPSD(source)
        elif fileType == BuildFileType.tiff:
            img = BuildCopy.__BuildImageFromTIFF(source)
        else:
            img = PIL.Image.open(fp=source)

        if img != None:
            img = BuildCopy.__ResizeImageWithParams(img, params)
            img.save(target, compression=None)
            img.close()
            if self.options & BuildCopyOption.EnableLogging:
                BuildCopy.__PrintMakeResult(source, target)
            success = True

        return success


    @staticmethod
    def __BuildImageFromPSD(source: str) -> PILImage:
        psd: PSDImage = PSDImage.open(fp=source)

        util.Verify(psd.color_mode == PSDColorMode.RGB, f"PSD image '{source}' has unsupported color mode '{psd.color_mode}'.")
        util.Verify(psd.channels >= 3, f"PSD image '{source}' has unsupported channel size '{psd.channels}'.")

        if psd.channels == 3:
            # Does composite the image.
            # If the psd was saved with "Maximize Compatibility", then the precomputed composite is read from it.
            img: PILImage = psd.composite()
            return img

        elif psd.channels > 3:
            # Does composite the image and preserves background alpha.
            # If the psd was saved with "Maximize Compatibility", then the precomputed composite is read from it.
            img: PILImage = psd.composite(color=0.0, alpha=1.0)
            r: PILImage = img.getchannel(0)
            g: PILImage = img.getchannel(1)
            b: PILImage = img.getchannel(2)

            # Composite alpha from each alpha channel.
            white: PILImage = PIL.Image.new("L", psd.size, 255)
            black: PILImage = PIL.Image.new("L", psd.size, 0)
            a: PILImage = white
            for channel in range(3, psd.channels):
                an: PILImage = psd.topil(channel=channel)
                a = PIL.Image.composite(an, black, a)

            return PIL.Image.merge("RGBA", (r, g, b, a))


    @staticmethod
    def __BuildImageFromTIFF(source: str) -> PILImage:
        tif: PIL.TiffImagePlugin.TiffImageFile = PIL.Image.open(fp=source)

        util.Verify(tif.mode == "RGB" or tif.mode == "RGBA" or tif.mode == "RGBX", f"TIFF image '{source}' has unsupported color mode '{tif.mode}'.")
        r: PILImage
        g: PILImage
        b: PILImage
        a: PILImage

        if tif.mode == "RGB":
            r, g, b = tif.split()
            img: PILImage = PIL.Image.merge("RGB", (r, g, b))
            tif.close()
            return img

        if tif.mode == "RGBA" or tif.mode == "RGBX":
            # NOTE: No composite. Does not support more than one alpha channel and no transparent background.
            r, g, b, a = tif.split()
            img: PILImage = PIL.Image.merge("RGBA", (r, g, b, a))
            tif.close()
            return img


    def __CopyToDDS(self, source: str, target: str, params: ParamsT) -> bool:
        tmpSourceType: BuildFileType = GetFileType(source)
        targetType: BuildFileType = GetFileType(target)

        if tmpSourceType == targetType:
            if not bool(params):
                # Simply copy the file when no processing is required.
                return self.__CopyTo(source, target, params)

        tmpSource: str = source

        if (BuildCopy.__HasResizeParams(params) or
            tmpSourceType == BuildFileType.psd or
            tmpSourceType == BuildFileType.tiff):
            # Crunch does not handle PSD files and image resize well.
            # 1. With a PSD texture of size 4096x1024 it discards the Alpha Channel.
            # 2. When halving source image resolution it introduces unnecessary visual glitches.
            # Therefore, PSD, TIFF and scaled texture is converted to TGA first, and then passed to crunch tool afterwards.
            tmpSource = target + ".tga"
            tmpSourceType = BuildFileType.tga
            copyOk: bool = self.__CopyToTGA(source, tmpSource, params)
            assert copyOk == True

        exec: str = self.__GetToolExePath("crunch")
        args: list[str] = [exec,
            "-file", tmpSource,
            "-out", target,
            "-fileformat", "dds",
            "-noprogress"]

        # Quiet crunching.
        if not (self.options & BuildCopyOption.EnableLogging):
            args.append("-quiet")

        # Append all args that begin with a dash, because all command line arguments of crunch do.
        userArgs: list[str] = ParamsToArgs(params, includeRegex="^-")
        args.extend(userArgs)

        hasTextureFormat = bool(CrunchTextureFormatSet & set(userArgs))

        if not hasTextureFormat:
            # Auto select DDS texture format depending on source format.
            hasAlpha: bool = BuildCopy.__HasAlphaChannel(tmpSource, tmpSourceType)
            args.append("-DXT5" if hasAlpha else "-DXT1")

        success: bool = util.RunProcess(args)

        if tmpSource != source:
            util.DeleteFile(tmpSource)

        if success and self.options & BuildCopyOption.EnableLogging:
            BuildCopy.__PrintMakeResult(tmpSource, target)

        return success


    @staticmethod
    def __HasResizeParams(params: ParamsT) -> bool:
        iparams = CaseInsensitiveDict(params)
        return (iparams.get("resize") != None) or (iparams.get("rescale") != None)


    @staticmethod
    def __ResizeImageWithParams(img: PILImage, params: ParamsT) -> PILImage:
        iparams = CaseInsensitiveDict(params)
        size: tuple[int, int] = img.size

        # Resize, for example 512 512 to 1024 1024

        resize: list[int, int] = iparams.get("resize")
        if isinstance(resize, list):
            if len(resize) == 1:
                size = (int(resize[0]), int(resize[0]))
            elif len(resize) == 2:
                size = (int(resize[0]), int(resize[1]))
        elif isinstance(resize, (float, int)):
            size = (int(resize), int(resize))

        # Rescale, for example 512*2 512*2

        rescale: list[float, float] = iparams.get("rescale")
        if isinstance(rescale, list):
            if len(rescale) == 1:
                size = (int(rescale[0] * size[0]), int(rescale[0] * size[1]))
            elif len(rescale) == 2:
                size = (int(rescale[0] * size[0]), int(rescale[1] * size[1]))
        elif isinstance(rescale, (float, int)):
            size = (int(rescale * size[0]), int(rescale * size[1]))

        # Resampling mode. Options:
        # NEAREST
        # BOX
        # BILINEAR
        # HAMMING
        # BICUBIC
        # LANCZOS

        resample = Resampling.BILINEAR
        resampling: str = iparams.get("resampling")
        if isinstance(resampling, str):
            resampling = resampling.lower()
            for option in Resampling:
                if option.name.lower() == resampling:
                    resample = option
                    break

        if size != img.size:
            r: PILImage
            g: PILImage
            b: PILImage
            a: PILImage

            if img.mode == "RGBA":
                # The RGB channels lose color information on image resize where the Alpha channel is black.
                # To workaround this issue, resize each channel separately.
                r, g, b, a = img.split()
                r = r.resize(size=size, resample=resample)
                g = g.resize(size=size, resample=resample)
                b = b.resize(size=size, resample=resample)
                a = a.resize(size=size, resample=resample)
                img = PIL.Image.merge("RGBA", (r, g, b, a))

            else:
                img = img.resize(size=size, resample=resample)

        return img


    @staticmethod
    def __HasAlphaChannel(source: str, fileType: BuildFileType) -> bool:
        hasAlpha: bool = False

        if fileType == BuildFileType.psd:
            psd: PSDImage = PSDImage.open(fp=source)
            hasAlpha = psd.channels > 3

        elif (fileType == BuildFileType.tga or
              fileType == BuildFileType.dds or
              fileType == BuildFileType.tiff):
            img: PILImage = PIL.Image.open(fp=source)
            hasAlpha = img.mode == "RGBA" or img.mode == "RGBX"
            img.close()

        return hasAlpha


    def __GetToolExePath(self, name: str) -> str:
        tool: Tool = self.tools.get(name)
        if tool == None:
            raise Exception(f"Tool '{name}' is required but does not exist or is disabled")
        return tool.GetExecutable()


    def __CopyToTextFile(self, source: str, target: str, params: ParamsT) -> bool:
        if self.__CopyToTextFileIfNeeded(source, target, params):
            return True
        else:
            return self.__CopyTo(source, target, params)


    class Marker:
        begin: str
        end: str

        def __init__(self, begin: str, end: str):
            self.begin = begin
            self.end = end


    @staticmethod
    def __FilterText(lines: list[str], markers: list[Marker]) -> list[str]:
        outputLines = []
        activeMarkers = []

        for line in lines:
            hadActiveMarkers = bool(activeMarkers)

            for marker in markers:
                if marker.begin in line:
                    activeMarkers.append(marker)
                if marker.end in line:
                    activeMarkers.remove(marker)

            hasActiveMarkers = bool(activeMarkers)
            if not hadActiveMarkers and not hasActiveMarkers:
                outputLines.append(line)

        return outputLines


    def __CopyToTextFileIfNeeded(self, source: str, target: str, params: ParamsT) -> bool:
        iparams = CaseInsensitiveDict(params)

        forceEOL: str = iparams.get("forceEOL")
        deleteComments: str = iparams.get("deleteComments")
        deleteWhitespace: int = iparams.get("deleteWhitespace")
        sourceEncoding: str = iparams.get("sourceEncoding") # https://docs.python.org/3/library/codecs.html
        targetEncoding: str = iparams.get("targetEncoding")
        excludeMarkersList: list[list[str]] = iparams.get("excludeMarkersList")
        if excludeMarkersList:
            excludeMarkers = [BuildCopy.Marker(t[0], t[1]) for t in excludeMarkersList]
        else:
            excludeMarkers = None

        doForceEOL: bool = isinstance(forceEOL, str) and bool(forceEOL)
        doDeleteComments: bool = isinstance(deleteComments, str) and bool(deleteComments)
        doDeleteWhitespace: bool = isinstance(deleteWhitespace, int) and deleteWhitespace > 0
        doEncode: bool = isinstance(sourceEncoding, str) or isinstance(targetEncoding, str)
        doExclude: bool = isinstance(excludeMarkers, list)

        if doDeleteWhitespace or doDeleteComments or doForceEOL or doEncode or doExclude:
            if not sourceEncoding:
                sourceEncoding = "utf-8"
            if not targetEncoding:
                targetEncoding = "utf-8"

            with open(source, "r", encoding=sourceEncoding) as sourceFile:
                with open(target, "w", encoding=targetEncoding, newline="") as targetFile:
                    sourceLines: list[str] = [line.rstrip("\r\n") for line in sourceFile]

                    # Exclude text inside markers ...
                    if doExclude:
                        sourceLines = BuildCopy.__FilterText(sourceLines, excludeMarkers)

                    # Delete comments ...
                    if doDeleteComments:
                        for i, s in enumerate(sourceLines):
                            sourceLines[i] = s.split(deleteComments, 1)[0]

                    # Delete obsolete spaces ...
                    if doDeleteWhitespace:
                        for i, s in enumerate(sourceLines):
                            sourceLines[i] = " ".join(s.split())

                    # Delete empty lines ...
                    if doDeleteWhitespace:
                        sourceLines[:] = [line for line in sourceLines if line.strip()]

                    # Set line ending ...
                    if doForceEOL:
                        for i, s in enumerate(sourceLines):
                            sourceLines[i] = s + forceEOL
                    else:
                        for i, s in enumerate(sourceLines):
                            sourceLines[i] = s + "\n"

                    # Write out ...
                    for line in sourceLines:
                        targetFile.write(line)

                    if self.options & BuildCopyOption.EnableLogging:
                        BuildCopy.__PrintMakeResult(source, target)
                    return True

        return False


    def __CopyToW3D(self, source: str, target: str, params: ParamsT) -> bool:
        iparams = CaseInsensitiveDict(params)
        w3dExportHierarchy: bool = iparams.get("w3dExportHierarchy", True)
        w3dExportAnimation: bool = iparams.get("w3dExportAnimation", False)
        w3dExportMesh : bool = iparams.get("w3dExportMesh", True)
        w3dUseExistingSkeleton: bool = iparams.get("w3dUseExistingSkeleton", False)
        w3dCompressTimeCoded: bool = iparams.get("w3dCompressTimeCoded", False)
        w3dForceVertexMaterials: bool = iparams.get("w3dForceVertexMaterials", False)
        w3dCreateIndividualFiles: bool = iparams.get("w3dCreateIndividualFiles", False)
        w3dCreateTextureXmls: bool = iparams.get("w3dCreateTextureXmls", False)

        if w3dExportHierarchy and w3dExportAnimation and w3dExportMesh:
            export_mode = "HAM"
        elif w3dExportHierarchy and w3dExportMesh:
            export_mode = "HM"
        elif w3dExportHierarchy:
            export_mode = "H"
        elif w3dExportAnimation:
            export_mode = "A"
        elif w3dExportMesh:
            export_mode = "M"
        else:
            raise Exception(f"Source '{source}' has unrecognized export setup")

        if w3dCompressTimeCoded:
            animation_compression = "TC"
        else:
            animation_compression = "U"

        expr = f"""
import bpy
bpy.ops.preferences.addon_enable(module='io_mesh_w3d')
bpy.ops.export_mesh.westwood_w3d(
    filepath=r'{target}',
    check_existing=False,
    file_format='W3D',
    export_mode='{export_mode}',
    use_existing_skeleton={w3dUseExistingSkeleton},
    animation_compression='{animation_compression}',
    force_vertex_materials={w3dForceVertexMaterials},
    individual_files={w3dCreateIndividualFiles},
    create_texture_xmls={w3dCreateTextureXmls})
"""

        exec: str = self.__GetToolExePath("blender")
        args: list[str] = [exec, source, "--background", "--python-expr", expr]

        success: bool = util.RunProcess(args)
        if success and self.options & BuildCopyOption.EnableLogging:
            BuildCopy.__PrintMakeResult(source, target)

        return success



def CopyWithProcess(tools: ToolsT, options: BuildCopyOption, buildJob: BuildJob):
    buildCopy = BuildCopy(tools=tools, options=options)
    buildJob.success = buildCopy.Copy(buildJob.absSource, buildJob.absTarget, buildJob.params)
    return buildJob
