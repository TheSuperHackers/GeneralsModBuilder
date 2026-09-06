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
    """
    The file types that the builder knows, followed by two markers that are not file types
    at all and must never be treated as a file extension.

    Any is an extension that the builder has no conversion rule for. A file of such a type
    is copied as it is, because there is nothing to convert it into.

    Auto is not a type but a request to work the type out from the file path. It is only
    ever given to BuildCopy.Copy, which replaces it with the result of GetFileType, so no
    other function ever sees it.
    """
    # File types ...
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

    # Markers, not file types ...
    Any = enum.auto()
    Auto = enum.auto()


BuildFileTypeMarkers: set[BuildFileType] = {BuildFileType.Any, BuildFileType.Auto}


def __BuildFileTypeStringMap() -> dict[str, BuildFileType]:
    """
    Maps a lower case file extension to the file type that it names.
    The markers are left out, because they are not file types and name no extension, so
    that a file called Foo.any is an unknown extension like any other and never resolves
    to a marker by the name of it.
    """
    d = dict()
    for type in BuildFileType:
        if type not in BuildFileTypeMarkers:
            d[type.name.lower()] = type
    d["tif"] = BuildFileType.tiff
    return d

FileTypeStringDict: dict[str, BuildFileType] = __BuildFileTypeStringMap()

def GetFileType(filePath: str) -> BuildFileType:
    """
    Tells the file type of a file path, or Any when the builder knows no conversion for its
    extension. Never returns Auto, which is a request for this function and not a type.
    """
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

# The same formats in upper case, to look one up by. Some of them are spelled with lower
# case letters of their own, so the set above cannot be compared against directly.
CrunchTextureFormatKeySet: set[str] = {name.upper() for name in CrunchTextureFormatSet}


class BuildCopyOption(Flag):
    Zero = 0
    EnableBackup = enum.auto()
    EnableSymlinks = enum.auto()
    EnableLogging = enum.auto()


class BuildCopyPrintType(Enum):
    Nothing = enum.auto()
    Copy = enum.auto()
    Link = enum.auto()
    Make = enum.auto()


@dataclass
class BuildCopyResult:
    success: bool = field(default=False)
    printType: BuildCopyPrintType = field(default=BuildCopyPrintType.Nothing)


BuildCopyFunctionT = Callable[[str, str, ParamsT], BuildCopyResult]
BuildMultiCopyFunctionT = Callable[[list[str], str, ParamsT], BuildCopyResult]


def SupportsMultiSource(sourceType: BuildFileType, targetType: BuildFileType) -> bool:
    """
    Tells whether multiple source files can build the given target file together.
    """
    if targetType == BuildFileType.ini or targetType == BuildFileType.wnd:
        return sourceType == targetType

    if targetType == BuildFileType.str or targetType == BuildFileType.csf:
        return sourceType == BuildFileType.str or sourceType == BuildFileType.csf

    return False


def RequiresTool(toolName: str):
    """
    Marks a copy function as requiring the named build tool, so that a build
    can ask what a copy would need before performing the copy.
    """
    def decorate(function):
        function.requiredToolName = toolName
        return function
    return decorate


def GetRequiredToolNameOfCopyFunction(function) -> str:
    """
    Tells the build tool that the given copy function requires, or None when it requires none.
    """
    return getattr(function, "requiredToolName", None)


class TextMarker:
    """
    A begin and an end token that mark a region of text.
    """
    begin: str
    end: str

    def __init__(self, begin: str, end: str):
        self.begin = begin
        self.end = end


class TextLine:
    """
    One line of a text file: its text without the line ending, and the line ending that
    followed it. The two are kept together so that a transformation can change the text of
    a line, or drop the line entirely, without losing the line ending that it came with.
    """
    text: str
    eol: str

    def __init__(self, text: str, eol: str):
        self.text = text
        self.eol = eol


class TextTransform:
    """
    Holds the text transformation params of a build file in evaluated form.
    """
    forceEOL: str
    deleteComments: str
    deleteWhitespace: bool
    sourceEncoding: str
    targetEncoding: str
    excludeMarkers: list[TextMarker]

    def __init__(self, params: ParamsT):
        """
        The type of every param read here is verified where the params are parsed, in
        data.common.VerifyBuildFileParams, so a value that is present is a value of the
        right type and is only tested for saying something.
        """
        iparams = CaseInsensitiveDict(params)

        self.forceEOL = TextTransform.__GetNonEmptyString(iparams, "forceEOL")
        self.deleteComments = TextTransform.__GetNonEmptyString(iparams, "deleteComments")
        self.deleteWhitespace = TextTransform.__HasPositiveNumber(iparams, "deleteWhitespace")
        self.sourceEncoding = TextTransform.__GetString(iparams, "sourceEncoding")
        self.targetEncoding = TextTransform.__GetString(iparams, "targetEncoding")
        self.excludeMarkers = TextTransform.__GetMarkers(iparams, "excludeMarkersList")


    @staticmethod
    def __GetString(iparams: CaseInsensitiveDict, key: str) -> str:
        return iparams.get(key)


    @staticmethod
    def __GetNonEmptyString(iparams: CaseInsensitiveDict, key: str) -> str:
        value: str = TextTransform.__GetString(iparams, key)
        return value if value else None


    @staticmethod
    def __HasPositiveNumber(iparams: CaseInsensitiveDict, key: str) -> bool:
        value: int = iparams.get(key)
        return value != None and value > 0


    @staticmethod
    def __GetMarkers(iparams: CaseInsensitiveDict, key: str) -> list[TextMarker]:
        """
        A list without markers is treated as absent, the way __GetNonEmptyString treats an
        empty string, so that it does not make a transformation required that changes
        nothing about the text.
        """
        value: list[list[str]] = iparams.get(key)
        if not value:
            return None
        return [TextMarker(marker[0], marker[1]) for marker in value]


    def IsRequired(self) -> bool:
        """
        Tells whether any param changes the text or its encoding,
        and therefore requires the target file to be written anew.
        """
        return (self.forceEOL != None or
                self.deleteComments != None or
                self.deleteWhitespace or
                self.sourceEncoding != None or
                self.targetEncoding != None or
                self.excludeMarkers != None)


    def GetSourceEncoding(self) -> str:
        # https://docs.python.org/3/library/codecs.html
        return self.sourceEncoding or "utf-8"


    def GetTargetEncoding(self) -> str:
        return self.targetEncoding or "utf-8"


    def ReadLines(self, source: str) -> list[TextLine]:
        """
        Reads the lines of a text file, each with the line ending that follows it. The file
        is opened without newline translation, so that a line keeps the ending it was
        written with and only 'forceEOL' can change it.
        A last line that has no ending of its own is given the ending of the line before it,
        so that an unterminated file does not end in an ending foreign to it, and does not
        merge into the first line of the next file when several files are appended.
        """
        with open(source, "r", encoding=self.GetSourceEncoding(), newline="") as sourceFile:
            lines: list[TextLine] = [TextTransform.__SplitLineEnding(line) for line in sourceFile]

        if lines and not lines[-1].eol:
            lines[-1].eol = lines[-2].eol if len(lines) > 1 else "\n"

        return lines


    @staticmethod
    def __SplitLineEnding(line: str) -> TextLine:
        text: str = line.rstrip("\r\n")
        return TextLine(text, line[len(text):])


    def WriteLines(self, target: str, lines: list[TextLine]) -> None:
        with open(target, "w", encoding=self.GetTargetEncoding(), newline="") as targetFile:
            for line in lines:
                targetFile.write(line.text)
                targetFile.write(line.eol)


    def TransformLines(self, lines: list[TextLine], sources: list[str] = None) -> list[TextLine]:
        """
        Applies all text transformations of the params to the given lines.
        A line keeps the line ending that it was read with, unless 'forceEOL' names another
        one, so that a param that says nothing about line endings does not change them.
        sources : list[str]
            The files that the lines were read from. Names them in a message about a bad
            exclusion marker, which is the one transformation that can fail.
        """
        # Exclude text inside markers ...
        if self.excludeMarkers:
            lines = TextTransform.__FilterText(lines, self.excludeMarkers, sources)

        # Delete comments ...
        if self.deleteComments != None:
            for line in lines:
                line.text = line.text.split(self.deleteComments, 1)[0]

        if self.deleteWhitespace:
            # Delete obsolete spaces ...
            for line in lines:
                line.text = " ".join(line.text.split())

            # Delete empty lines ...
            lines[:] = [line for line in lines if line.text]

        # Set line ending ...
        if self.forceEOL != None:
            for line in lines:
                line.eol = self.forceEOL

        return lines


    @staticmethod
    def __FilterText(lines: list[TextLine], markers: list[TextMarker], sources: list[str]) -> list[TextLine]:
        """
        Removes every line of a marked region, including the lines that open and close it.
        A region is counted, not flagged, so that the same marker can open again inside
        itself. It may also open in one source file and close in a later one, because the
        lines of all source files of a target file are filtered here as one text.
        """
        outputLines = list[TextLine]()
        openCounts = [0] * len(markers)
        marker: TextMarker

        for line in lines:
            wasOpen: bool = any(openCounts)
            opensHere: bool = False

            for index, marker in enumerate(markers):
                if marker.begin in line.text:
                    openCounts[index] += 1
                    opensHere = True

                if marker.end in line.text:
                    openCounts[index] -= 1
                    util.Verify(openCounts[index] >= 0,
                                f"Text of {TextTransform.__NameSources(sources)} closes exclusion marker "
                                f"'{marker.end}' in line '{line.text}', but it was never opened with "
                                f"'{marker.begin}'")

            # A line that opens a region is part of it, even when the region closes again on
            # that same line, so it is dropped along with everything the region contains.
            if not wasOpen and not opensHere and not any(openCounts):
                outputLines.append(line)

        for index, marker in enumerate(markers):
            util.Verify(openCounts[index] == 0,
                        f"Text of {TextTransform.__NameSources(sources)} opens exclusion marker "
                        f"'{marker.begin}' {openCounts[index]} time(s) without closing it with "
                        f"'{marker.end}'")

        return outputLines


    @staticmethod
    def __NameSources(sources: list[str]) -> str:
        """
        Names the source files of a message about them. All of them are named, because a
        marked region may span several of them and the bad one is not known.
        """
        if not sources:
            return "the source file"
        return "'" + "', '".join(sources) + "'"


@dataclass
class BuildJob:
    """
    One file to build, and the result of building it, as it travels to a worker process
    and back.
    """
    absSources: list[str] = field(default=None)
    absTarget: str = field(default=None)
    params: ParamsT = field(default=None)
    result: BuildCopyResult = field(default=None)


def ResizeImageWithParams(img: PILImage, params: ParamsT) -> PILImage:
    """
    Returns the image in the size that the params ask for, or the image itself when they
    ask for the size that it already has. 'resize' names the size, 'rescale' multiplies the
    size that the image has, and 'rescale' applies to the result of 'resize'.
    """
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


def HasAlphaChannel(source: str, fileType: BuildFileType) -> bool:
    """
    Tells whether the image file carries an alpha channel, which decides the dds texture
    format when the params name none. Only the header of the file is read for it.
    """
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


def HasCrunchTextureFormat(params: ParamsT) -> bool:
    """
    Tells whether the params already name the dds texture format that crunch is to write.
    Names are compared in upper case, because crunch reads its arguments in any case, so a
    format written as -dxt5 names the same format as -DXT5 and must not be overruled by an
    automatically chosen one.
    """
    return any(arg.upper() in CrunchTextureFormatKeySet
               for arg in ParamsToArgs(params, includeRegex="^-"))


def MakeCrunchArgs(
        exec: str,
        source: str,
        target: str,
        params: ParamsT,
        textureFormat: str,
        quiet: bool) -> list[str]:
    """
    Builds the command line that compresses the source image into the target dds file.
    textureFormat : str
        The texture format to write when the params name none of their own. Is empty when
        they do, because crunch is then told the format twice.
    """
    args: list[str] = [exec,
        "-file", source,
        "-out", target,
        "-fileformat", "dds",
        "-noprogress"]

    if quiet:
        args.append("-quiet")

    # Append all params that begin with a dash, because all command line arguments of crunch do.
    args.extend(ParamsToArgs(params, includeRegex="^-"))

    if textureFormat:
        args.append(textureFormat)

    return args


def MakeW3DExportMode(source: str, exportHierarchy: bool, exportAnimation: bool, exportMesh: bool) -> str:
    """
    Tells the export mode that the blender w3d exporter takes for the wanted parts of a
    model. The exporter knows hierarchy, animation and mesh together, hierarchy with mesh,
    and each of the three on its own. It has no mode for hierarchy with animation but
    without mesh, and none for animation with mesh but without hierarchy, so those two are
    reported rather than exported as something that nobody asked for.
    """
    if exportHierarchy and exportAnimation and exportMesh:
        return "HAM"

    if exportHierarchy and exportMesh:
        return "HM"

    if exportHierarchy and not exportAnimation:
        return "H"

    if exportAnimation and not exportHierarchy and not exportMesh:
        return "A"

    if exportMesh and not exportHierarchy and not exportAnimation:
        return "M"

    raise Exception(
        f"Source '{source}' asks for w3dExportHierarchy:{exportHierarchy}, "
        f"w3dExportAnimation:{exportAnimation}, w3dExportMesh:{exportMesh}, which the w3d "
        f"exporter has no export mode for. It exports hierarchy, animation and mesh "
        f"together, or hierarchy with mesh, or each of the three on its own.")


# The characters of the compiler command syntax that a file path cannot carry. A merge
# names its files inside commands of the form COMMAND(KEY:value,KEY:value), where a comma
# ends a value and a closing parenthesis ends the command, and the compiler offers no way
# of quoting or escaping either of them: a path written in quotes is opened with the quotes
# as part of its name. A space is not among them, because every command is passed to the
# tool as one argument of its own and is never split on spaces.
GameTextPathReservedChars: str = ",)"


def VerifyGameTextMergePath(path: str) -> None:
    """
    Fails a file path that a game text merge command line cannot carry.
    """
    for character in GameTextPathReservedChars:
        util.Verify(character not in path,
                    f"Path '{path}' contains a '{character}', which the game text compiler cannot "
                    f"read in a merge, because it is part of its command syntax and cannot be escaped")


def MakeGameTextMergeArgs(
        exec: str,
        sources: list[str],
        target: str,
        params: ParamsT,
        targetT: BuildFileType) -> list[str]:
    """
    Builds the command line that merges several game text files into one target file.
    Each source file is loaded into its own compiler slot and is merged over the first slot,
    so a label that is defined again in a later source file overwrites the earlier one.
    """
    for path in sources:
        VerifyGameTextMergePath(path)
    VerifyGameTextMergePath(target)

    iparams = CaseInsensitiveDict(params)
    args: list[str] = [exec]

    language: str = iparams.get("language")
    hasLanguage: bool = bool(language)

    # The language of a merge is optional, and without it the compiler merges the language
    # that the loaded files already carry. That is what a merge without the param wants, and
    # naming no language is the only way to ask for it.
    mergeLanguage: str = f",LANGUAGE:{language}" if hasLanguage else ""

    for index, source in enumerate(sources):
        if GetFileType(source) == BuildFileType.csf:
            args.append(f"LOAD_CSF(FILE_ID:{index},FILE_PATH:{source})")
        elif hasLanguage:
            args.append(f"LOAD_MULTI_STR(FILE_ID:{index},FILE_PATH:{source},LANGUAGE:{language})")
        else:
            args.append(f"LOAD_STR(FILE_ID:{index},FILE_PATH:{source})")

        if index > 0:
            args.append(f"MERGE_AND_OVERWRITE(FILE_ID:0,FILE_ID:{index}{mergeLanguage})")

    swapAndSetLanguage: str = iparams.get("swapAndSetLanguage")
    if swapAndSetLanguage:
        args.append(f"SWAP_AND_SET_LANGUAGE(FILE_ID:0,LANGUAGE:{swapAndSetLanguage})")

    # A CSF file stores its language, but a STR file needs the language(s) written out with it.
    if targetT == BuildFileType.csf:
        args.append(f"SAVE_CSF(FILE_ID:0,FILE_PATH:{target})")
    elif hasLanguage:
        args.append(f"SAVE_MULTI_STR(FILE_ID:0,FILE_PATH:{target},LANGUAGE:{language})")
    else:
        args.append(f"SAVE_STR(FILE_ID:0,FILE_PATH:{target})")

    return args


@dataclass
class BuildCopy:
    tools: ToolsT
    options: BuildCopyOption = field(default=BuildCopyOption.Zero)
    processPool: ProcessPoolExecutor = field(default=None)

    def CopyThing(self, thing: BuildThing) -> None:
        """
        Builds every file of the thing that requires a rebuild. A file that cannot be built
        ends the build with a message that names it.
        """
        if self.processPool != None:
            self.CopyThingMultiProcess(thing)
        else:
            self.CopyThingSingleProcess(thing)


    def CopyThingSingleProcess(self, thing: BuildThing) -> None:
        file: BuildFile

        for file in thing.files:
            if file.RequiresRebuild():
                absSources: list[str] = file.AbsSources()
                absTarget: str = file.AbsTarget(thing.absParentDir)
                params: ParamsT = file.params
                result: BuildCopyResult = self.Copy(absSources, absTarget, params)
                BuildCopy.__VerifyCopied(result, absSources, absTarget)

                if self.options & BuildCopyOption.EnableLogging:
                    BuildCopy.__PrintResult(result.printType, absSources, absTarget)


    def CopyThingMultiProcess(self, thing: BuildThing) -> None:
        options = self.options & ~BuildCopyOption.EnableLogging
        futures = list[Future]()
        future: Future
        buildJob: BuildJob
        file: BuildFile

        for file in thing.files:
            if file.RequiresRebuild():
                buildJob = BuildJob(
                    absSources=file.AbsSources(),
                    absTarget=file.AbsTarget(thing.absParentDir),
                    params=file.params)
                future = self.processPool.submit(CopyWithProcess, self.tools, options, buildJob)
                futures.append(future)

        concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

        for future in futures:
            buildJob = future.result()
            BuildCopy.__VerifyCopied(buildJob.result, buildJob.absSources, buildJob.absTarget)

            if self.options & BuildCopyOption.EnableLogging:
                BuildCopy.__PrintResult(buildJob.result.printType, buildJob.absSources, buildJob.absTarget)


    def UncopyThing(self, thing: BuildThing, respectBuildFileStatus=True) -> None:
        """
        Removes the files of the thing that a build has written. A file that is not there
        is not an error, because being gone is the state that this asks for.
        """
        file: BuildFile

        for file in thing.files:
            if file.RequiresRebuild() or not respectBuildFileStatus:
                absTarget: str = file.AbsTarget(thing.absParentDir)
                self.Uncopy(absTarget)


    def Copy(
            self,
            sources: list[str],
            target: str,
            params: ParamsT = None,
            sourceType = BuildFileType.Auto,
            targetType = BuildFileType.Auto) -> BuildCopyResult:
        """
        Builds the target file from the source file(s).
        sourceType, targetType : BuildFileType
            Auto works the type out from the file path, which is what a build does. Another
            type builds the files as that type instead, whatever their extensions say.
        """

        source: str
        for source in sources:
            util.Verify(os.path.exists(source),
                        f"Source file '{source}' of target '{target}' does not exist")

        if sourceType == BuildFileType.Auto:
            sourceType = GetFileType(sources[0])

        if targetType == BuildFileType.Auto:
            targetType = GetFileType(target)

        util.MakeDirsForFile(target)

        # Creating a backup renames the target out of the way, which leaves nothing to
        # delete. Without a backup, or when one already exists, the target is deleted.
        backedUp: bool = False

        if self.options & BuildCopyOption.EnableBackup:
            backedUp = BuildCopy.__CreateBackup(target)

        if not backedUp:
            util.DeleteFileOrDir(target)

        if len(sources) > 1:
            multiCopyFunction: BuildMultiCopyFunctionT = self.__GetMultiCopyFunction(sources, target, targetType)
            return multiCopyFunction(sources, target, params)

        copyFunction: BuildCopyFunctionT = self.__GetCopyFunction(sources[0], target, sourceType, targetType, params)
        return copyFunction(sources[0], target, params)


    def GetRequiredToolName(self, sources: list[str], target: str, params: ParamsT = None) -> str:
        """
        Tells the build tool that Copy would require for these files, without copying anything.
        Returns None when the copy requires no tool.
        """
        targetType: BuildFileType = GetFileType(target)

        if len(sources) > 1:
            multiCopyFunction: BuildMultiCopyFunctionT = self.__GetMultiCopyFunction(sources, target, targetType)
            return GetRequiredToolNameOfCopyFunction(multiCopyFunction)

        copyFunction: BuildCopyFunctionT = self.__GetCopyFunction(
            sources[0], target, GetFileType(sources[0]), targetType, params)
        return GetRequiredToolNameOfCopyFunction(copyFunction)


    def Uncopy(self, file: str) -> bool:
        """
        Removes a file that a build has written and puts back the file that it replaced.
        Tells whether there was anything to remove. Nothing to remove is not a failure: a
        target that is already gone is the state that this asks for.
        """
        removed: bool = util.DeleteFileOrDir(file)

        if removed and self.options & BuildCopyOption.EnableLogging:
            BuildCopy.__PrintUncopyResult(file)

        # The backup is only put back once the file that replaced it is gone, so that a
        # target which could not be removed is not overwritten by the file it replaced.
        if not os.path.lexists(file) and self.options & BuildCopyOption.EnableBackup:
            BuildCopy.__RevertBackup(file)

        return removed


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
    def __VerifyCopied(result: BuildCopyResult, sources: list[str], target: str) -> None:
        """
        A copy that does not do its work reports it by raising, so this only holds the last
        word of the contract, for a copy function that answers a failure instead.
        """
        util.Verify(result.success,
                    f"Unable to copy source(s) '{BuildCopy.__JoinSources(sources)}' to target '{target}'.")


    @staticmethod
    def __JoinSources(sources: list[str]) -> str:
        return "', '".join(sources)


    @staticmethod
    def __PrintResult(type: BuildCopyPrintType, sources: list[str], target: str) -> None:
        source: str
        for source in sources:
            if type == BuildCopyPrintType.Copy:
                BuildCopy.__PrintCopyResult(source, target)
            elif type == BuildCopyPrintType.Link:
                BuildCopy.__PrintLinkResult(source, target)
            elif type == BuildCopyPrintType.Make:
                BuildCopy.__PrintMakeResult(source, target)


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
    def __PrintUncopyResult(file: str) -> None:
        print("Remove", file)


    def __GetCopyFunction(
            self,
            source: str,
            target: str,
            sourceT: BuildFileType,
            targetT: BuildFileType,
            params: ParamsT) -> BuildCopyFunctionT:
        """
        Selects the function that builds the target file from the source file.
        Fails on a pair of file types that the builder has no conversion for, so that a
        source file is never copied into a target file whose type it is not.
        source, target : str
            Name the files of that message. They take no part in the selection.
        """
        if targetT == BuildFileType.ini:
            return self.__CopyToTextFile

        if targetT == BuildFileType.wnd:
            return self.__CopyToTextFile

        if targetT == BuildFileType.str and not sourceT == BuildFileType.csf:
            return self.__CopyToTextFile

        if targetT == BuildFileType.dds and sourceT == BuildFileType.dds:
            # Without a param that asks for texture work the file is simply copied and
            # requires no tool. It is already a dds file.
            if BuildCopy.__HasCrunchParams(params):
                return self.__CopyToDDS
            else:
                return self.__CopyTo

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

        raise Exception(
            f"Source '{source}' of type '{sourceT.name}' cannot build target '{target}' of type '{targetT.name}', "
            f"because there is no conversion between these file types.")


    def __GetMultiCopyFunction(self, sources: list[str], target: str, targetT: BuildFileType) -> BuildMultiCopyFunctionT:
        """
        Selects the function that builds one target file from multiple source files.
        Symlinks are never taken here, because a merged file has no single source to link to.

        Whether the source files are of a type that can build this target at all is decided
        by SupportsMultiSource, which the Pre Build step applies to every bundle file, so
        that a bad configuration fails before the long running Build step and with the name
        of the bundle item in the message. It is not asked again here.
        """
        source: str

        if targetT == BuildFileType.csf:
            return self.__MergeToCSF

        if targetT == BuildFileType.str:
            # STR sources merge as text. A CSF source requires the tool to become text first.
            for source in sources:
                if GetFileType(source) == BuildFileType.csf:
                    return self.__MergeToSTR

        if (targetT == BuildFileType.ini or
            targetT == BuildFileType.wnd or
            targetT == BuildFileType.str):
            return self.__ConcatToTextFile

        raise Exception(
            f"Target '{target}' of type '{targetT.name}' cannot be built from multiple source files, "
            f"because there is no meaningful way to combine them into this file type.")


    def __CopyTo(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        if self.options & BuildCopyOption.EnableSymlinks:
            try:
                os.symlink(src=source, dst=target)
                return BuildCopyResult(success=True, printType=BuildCopyPrintType.Link)
            except OSError:
                pass

        shutil.copy(src=source, dst=target)
        return BuildCopyResult(success=True, printType=BuildCopyPrintType.Copy)


    @RequiresTool("gametextcompiler")
    def __CopySTRtoCSF(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        # The compiler cannot apply the text params, so they are applied to a temp file that
        # it reads in place of the source file.
        transform = TextTransform(params)
        toolSource: str = source

        if transform.IsRequired():
            toolSource = f"{target}.tmp.str"
            BuildCopy.__WriteTextFile([source], toolSource, transform)

        iparams = CaseInsensitiveDict(params)
        exec: str = self.__GetToolExePath("gametextcompiler")
        args: list[str] = [exec,
            "-LOAD_STR", toolSource,
            "-SAVE_CSF", target]

        language: str = iparams.get("language")
        if language:
            args.extend(["-LOAD_STR_LANGUAGES", language])

        swapAndSetLanguage: str = iparams.get("swapAndSetLanguage")
        if swapAndSetLanguage:
            args.extend(["-SWAP_AND_SET_LANGUAGE", swapAndSetLanguage])

        try:
            success: bool = util.RunProcess(args)
        finally:
            if toolSource != source:
                util.DeleteFile(toolSource)

        return BuildCopyResult(success=success, printType=BuildCopyPrintType.Make)


    @RequiresTool("gametextcompiler")
    def __CopyCSFtoSTR(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        iparams = CaseInsensitiveDict(params)
        exec: str = self.__GetToolExePath("gametextcompiler")

        # All params of a build file apply to the file that it builds, but the compiler can
        # apply none of the text ones, so it writes a temp file that they are applied to.
        transform = TextTransform(params)
        toolTarget: str = f"{target}.tmp.str" if transform.IsRequired() else target

        args: list[str] = [exec,
            "-LOAD_CSF", source,
            "-SAVE_STR", toolTarget]

        language: str = iparams.get("language")
        if language:
            args.extend(["-SAVE_STR_LANGUAGES", language])

        try:
            success: bool = util.RunProcess(args)

            if toolTarget != target:
                BuildCopy.__WriteTextFile([toolTarget], target, transform)
        finally:
            if toolTarget != target:
                util.DeleteFile(toolTarget)

        return BuildCopyResult(success=success, printType=BuildCopyPrintType.Make)


    @RequiresTool("gametextcompiler")
    def __MergeToCSF(self, sources: list[str], target: str, params: ParamsT) -> BuildCopyResult:
        return self.__MergeGameText(sources, target, params, BuildFileType.csf)


    @RequiresTool("gametextcompiler")
    def __MergeToSTR(self, sources: list[str], target: str, params: ParamsT) -> BuildCopyResult:
        return self.__MergeGameText(sources, target, params, BuildFileType.str)


    def __MergeGameText(self, sources: list[str], target: str, params: ParamsT, targetT: BuildFileType) -> BuildCopyResult:
        """
        Builds one game text file from multiple game text files.
        """
        exec: str = self.__GetToolExePath("gametextcompiler")

        # Text params cannot be applied by the compiler, so pre process each text source file into a temp file.
        tmpSources = list[str]()
        mergeSources = list(sources)
        transform = TextTransform(params)

        if transform.IsRequired():
            for index, source in enumerate(mergeSources):
                if GetFileType(source) == BuildFileType.str:
                    tmpSource: str = f"{target}.{index}.tmp.str"
                    result: BuildCopyResult = BuildCopy.__WriteTextFile([source], tmpSource, transform)
                    if result.success:
                        mergeSources[index] = tmpSource
                        tmpSources.append(tmpSource)

        args: list[str] = MakeGameTextMergeArgs(exec, mergeSources, target, params, targetT)

        try:
            success: bool = util.RunProcess(args)
        finally:
            for tmpSource in tmpSources:
                util.DeleteFile(tmpSource)

        return BuildCopyResult(success=success, printType=BuildCopyPrintType.Make)


    @RequiresTool("generalsbigcreator")
    def __CopyToBIG(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        exec: str = self.__GetToolExePath("generalsbigcreator")
        args: list[str] = [exec,
            "-source", source,
            "-dest", target]

        success: bool = util.RunProcess(args)
        return BuildCopyResult(success=success, printType=BuildCopyPrintType.Make)


    def __CopyToZIP(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        return BuildCopy.__MakeArchive(source, target, "zip")


    def __CopyToTAR(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        return BuildCopy.__MakeArchive(source, target, "tar")


    def __CopyToGZTAR(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        return BuildCopy.__MakeArchive(source, target, "gztar")


    @staticmethod
    def __MakeArchive(source: str, target: str, format: str) -> BuildCopyResult:
        """
        Packs the source directory into the target archive file.
        make_archive names the file it writes itself, by appending the suffix of its format
        to the name it is given, and that suffix is not always the extension of the target
        file: a gztar is written as .tar.gz, so a target called Mod.gz was written as
        Mod.tar.gz and the file that the build had promised was never there. The archive is
        therefore built beside the target and is then moved onto it.
        """
        archive: str = shutil.make_archive(base_name=target, format=format, root_dir=source)
        util.Verify(os.path.isfile(archive),
                    f"Archive '{archive}' of target '{target}' was not written")

        if archive != target:
            os.replace(src=archive, dst=target)

        return BuildCopyResult(success=True, printType=BuildCopyPrintType.Make)


    def __CopyToBMP(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        return BuildCopy.__CopyToImage(source, target, params)


    def __CopyToTGA(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        return BuildCopy.__CopyToImage(source, target, params)


    @staticmethod
    def __CopyToImage(source: str, target: str, params: ParamsT) -> BuildCopyResult:
        img: PILImage
        fileType: BuildFileType = GetFileType(source)

        if fileType == BuildFileType.psd:
            img = BuildCopy.__BuildImageFromPSD(source)
        elif fileType == BuildFileType.tiff:
            img = BuildCopy.__BuildImageFromTIFF(source)
        else:
            img = PIL.Image.open(fp=source)

        img = ResizeImageWithParams(img, params)
        img.save(target, compression=None)
        img.close()

        return BuildCopyResult(success=True, printType=BuildCopyPrintType.Make)


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

        # More than three channels, which the verify above has made certain of.
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

        # RGBA or RGBX, which the verify above has made certain of.
        # NOTE: No composite. Does not support more than one alpha channel and no transparent background.
        r, g, b, a = tif.split()
        img: PILImage = PIL.Image.merge("RGBA", (r, g, b, a))
        tif.close()
        return img


    @RequiresTool("crunch")
    def __CopyToDDS(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        tmpSourceType: BuildFileType = GetFileType(source)
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
            self.__CopyToTGA(source, tmpSource, params)

        textureFormat: str = ""

        if not HasCrunchTextureFormat(params):
            # Auto select the dds texture format depending on the source image.
            hasAlpha: bool = HasAlphaChannel(tmpSource, tmpSourceType)
            textureFormat = "-DXT5" if hasAlpha else "-DXT1"

        exec: str = self.__GetToolExePath("crunch")
        quiet: bool = not (self.options & BuildCopyOption.EnableLogging)
        args: list[str] = MakeCrunchArgs(exec, tmpSource, target, params, textureFormat, quiet)

        try:
            success: bool = util.RunProcess(args)
        finally:
            if tmpSource != source:
                util.DeleteFile(tmpSource)

        return BuildCopyResult(success=success, printType=BuildCopyPrintType.Make)


    @staticmethod
    def __HasResizeParams(params: ParamsT) -> bool:
        iparams = CaseInsensitiveDict(params)
        return (iparams.get("resize") != None) or (iparams.get("rescale") != None)


    @staticmethod
    def __HasCrunchParams(params: ParamsT) -> bool:
        """
        Tells whether any param asks for work that the crunch tool does.
        The params of a json entry are shared by every file that the entry builds, so a
        param that says nothing about textures must not compress an already compressed dds
        file a second time, with a texture format that nobody chose.
        """
        if BuildCopy.__HasResizeParams(params):
            return True

        iparams = CaseInsensitiveDict(params)
        if iparams.get("resampling") != None:
            return True

        # All command line arguments of crunch begin with a dash, which is also how
        # __CopyToDDS picks the params that it passes on to the tool.
        return any(key.startswith("-") for key in iparams)


    def __GetToolExePath(self, name: str) -> str:
        tool: Tool = self.tools.get(name)
        if tool == None:
            raise Exception(f"Tool '{name}' is required but does not exist or is disabled")
        return tool.GetExecutable()


    def __CopyToTextFile(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        transform = TextTransform(params)

        if transform.IsRequired():
            return BuildCopy.__WriteTextFile([source], target, transform)

        # No param changes the text, so the file is taken over as it is.
        return self.__CopyTo(source, target, params)


    @staticmethod
    def __WriteTextFile(sources: list[str], target: str, transform: TextTransform) -> BuildCopyResult:
        """
        Builds one text file from one or more text files in the order that they are listed in.
        Lines are read without their line ending and are written back with one, so the last line
        of a source file can never merge into the first line of the next one.
        """
        lines = list[TextLine]()
        source: str

        for source in sources:
            lines.extend(transform.ReadLines(source))

        lines = transform.TransformLines(lines, sources)
        transform.WriteLines(target, lines)

        return BuildCopyResult(success=True, printType=BuildCopyPrintType.Make)


    def __ConcatToTextFile(self, sources: list[str], target: str, params: ParamsT) -> BuildCopyResult:
        """
        Builds one text file from multiple text files in the order that they are listed in.
        Unlike the single source variant this always writes a new file, because there is
        no single source file that could simply be copied or linked instead.
        """
        return BuildCopy.__WriteTextFile(sources, target, TextTransform(params))


    @RequiresTool("blender")
    def __CopyToW3D(self, source: str, target: str, params: ParamsT) -> BuildCopyResult:
        # The type of every flag read here is verified where the params are parsed, so a
        # value that is present is a bool and can be written into the expression below.
        iparams = CaseInsensitiveDict(params)
        w3dExportHierarchy: bool = iparams.get("w3dExportHierarchy", True)
        w3dExportAnimation: bool = iparams.get("w3dExportAnimation", False)
        w3dExportMesh : bool = iparams.get("w3dExportMesh", True)
        w3dUseExistingSkeleton: bool = iparams.get("w3dUseExistingSkeleton", False)
        w3dCompressTimeCoded: bool = iparams.get("w3dCompressTimeCoded", False)
        w3dForceVertexMaterials: bool = iparams.get("w3dForceVertexMaterials", False)
        w3dCreateIndividualFiles: bool = iparams.get("w3dCreateIndividualFiles", False)
        w3dCreateTextureXmls: bool = iparams.get("w3dCreateTextureXmls", False)

        exportMode: str = MakeW3DExportMode(
            source, w3dExportHierarchy, w3dExportAnimation, w3dExportMesh)

        animationCompression: str = "TC" if w3dCompressTimeCoded else "U"

        expr = f"""
import bpy
bpy.ops.preferences.addon_enable(module='io_mesh_w3d')
bpy.ops.export_mesh.westwood_w3d(
    filepath=r'{target}',
    check_existing=False,
    file_format='W3D',
    export_mode='{exportMode}',
    use_existing_skeleton={w3dUseExistingSkeleton},
    animation_compression='{animationCompression}',
    force_vertex_materials={w3dForceVertexMaterials},
    individual_files={w3dCreateIndividualFiles},
    create_texture_xmls={w3dCreateTextureXmls})
"""

        exec: str = self.__GetToolExePath("blender")
        args: list[str] = [exec, source, "--background", "--python-expr", expr]

        success: bool = util.RunProcess(args)
        return BuildCopyResult(success=success, printType=BuildCopyPrintType.Make)



def CopyWithProcess(tools: ToolsT, options: BuildCopyOption, buildJob: BuildJob) -> BuildJob:
    buildCopy = BuildCopy(tools=tools, options=options)
    buildJob.result = buildCopy.Copy(buildJob.absSources, buildJob.absTarget, buildJob.params)
    return buildJob
