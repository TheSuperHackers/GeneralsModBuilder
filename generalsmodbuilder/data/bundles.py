import os
import zlib
from copy import copy
from glob import glob
from dataclasses import dataclass
from enum import Enum, auto
from generalsmodbuilder.data.common import (
    FinalizeParsedData, ParamsT, ParsedData, VerifyBuildFileParams, VerifyFormatVersion)
from generalsmodbuilder.util import JsonNode, JsonFile
from generalsmodbuilder import util


class BundleEventType(Enum):
    OnPreBuild = auto()
    OnBuild = auto()
    OnPostBuild = auto()
    OnRelease = auto()
    OnInstall = auto()
    OnRun = auto()
    OnUninstall = auto()
    OnStartBuildRawBundleItem = auto()
    OnStartBuildBigBundleItem = auto()
    OnStartBuildRawBundlePack = auto()
    OnStartBuildReleaseBundlePack = auto()
    OnStartBuildInstallBundlePack = auto()
    OnFinishBuildRawBundleItem = auto()
    OnFinishBuildBigBundleItem = auto()
    OnFinishBuildRawBundlePack = auto()
    OnFinishBuildReleaseBundlePack = auto()
    OnFinishBuildInstallBundlePack = auto()


def GetJsonBundleEventName(type: BundleEventType) -> str:
    return type.name[:1].lower() + type.name[1:]


def IsBundleBuildEvent(type: BundleEventType) -> bool:
    return (type == BundleEventType.OnPreBuild or
            type == BundleEventType.OnBuild or
            type == BundleEventType.OnPostBuild or
            type == BundleEventType.OnRelease or
            type == BundleEventType.OnStartBuildRawBundleItem or
            type == BundleEventType.OnStartBuildBigBundleItem or
            type == BundleEventType.OnStartBuildRawBundlePack or
            type == BundleEventType.OnStartBuildReleaseBundlePack or
            type == BundleEventType.OnFinishBuildRawBundleItem or
            type == BundleEventType.OnFinishBuildBigBundleItem or
            type == BundleEventType.OnFinishBuildRawBundlePack or
            type == BundleEventType.OnFinishBuildReleaseBundlePack)


def IsBundleInstallEvent(type: BundleEventType) -> bool:
    return (type == BundleEventType.OnInstall or
            type == BundleEventType.OnRun or
            type == BundleEventType.OnUninstall or
            type == BundleEventType.OnStartBuildInstallBundlePack or
            type == BundleEventType.OnFinishBuildInstallBundlePack)


# The json name of every event type, built once instead of per item and per pack.
g_bundleEventTypeByJsonName: dict[str, BundleEventType] = {
    GetJsonBundleEventName(eventType): eventType for eventType in BundleEventType
}


LATEST_BUNDLES_VERSION = 1

BUNDLES_KEYS = {
    "version",
    "items",
    "itemsPrefix",
    "itemsSuffix",
    "packs",
    "packsPrefix",
    "packsSuffix"
}

BUNDLE_EVENT_KEYS = {
    "script",
    "function",
    "kwargs"
}

BUNDLE_ITEM_KEYS = {
    "name",
    "files",
    "namePrefix",
    "nameSuffix",
    "big",
    "bigSuffix",
    "setGameLanguageOnInstall",
} | set(g_bundleEventTypeByJsonName)

BUNDLE_PACK_KEYS = {
    "name",
    "itemNames",
    "namePrefix",
    "nameSuffix",
    "install",
    "build",
    "setGameLanguageOnInstall",
} | set(g_bundleEventTypeByJsonName)

BUNDLE_FILE_KEYS = {
    "sourceParent",
    "parent",
    "source",
    "target",
    "params",
    "sourceList",
    "sourceTargetList",
    "multiSource",
    "multiSourceTargetList",
    "registryList",
}

# params is documented but is not implemented on an element of a sourceTargetList. It
# stays a known key so that a configuration that carries it keeps working.
BUNDLE_SOURCE_TARGET_KEYS = {
    "source",
    "target",
    "params"
}

BUNDLE_MULTI_SOURCE_TARGET_KEYS = {
    "multiSource",
    "target"
}


@dataclass(init=False)
class BundleEvent(ParsedData):
    type: BundleEventType
    absScript: str
    funcName: str
    kwargs: dict

    def __init__(self):
        self.type = None
        self.absScript = None
        self.funcName = "OnEvent"
        self.kwargs = dict()

    def GetScriptDir(self) -> str:
        return os.path.dirname(self.absScript)

    def GetScriptName(self) -> str:
        base: str = os.path.basename(self.absScript)
        name, ext = os.path.splitext(base)
        return name

    def VerifyValues(self) -> None:
        eventName: str = GetJsonBundleEventName(self.type)
        util.Verify(os.path.isfile(self.absScript), f"bundles {eventName}.script '{self.absScript}' is not a valid file")
        util.Verify(len(self.funcName) > 0, f"bundles {eventName}.function cannot be empty")

    def Normalize(self) -> None:
        self.absScript = os.path.normpath(self.absScript)


BundleEventsT = dict[BundleEventType, BundleEvent]


@dataclass(init=False)
class BundleRegistryDefinition:
    paths: list[str]
    crc32: int

    def __init__(self, absPaths: list[str]):
        # One definition is shared by every bundle file of the entry that declares it,
        # and a wildcard entry can expand into very many of those. It is therefore
        # normalized and verified here, once, instead of once per file through the
        # phases that the other data objects run.
        self.paths = [os.path.normpath(path) for path in absPaths]
        for path in self.paths:
            util.Verify(os.path.isfile(path), f"bundles.items.files.registryList '{path}' is not a valid file")

        # Identifies the set of registry files, so it is built from the normalized paths.
        pathsBytes = bytes("".join(self.paths), encoding="utf-8")
        self.crc32 = zlib.crc32(pathsBytes)


@dataclass(init=False)
class BundleFile(ParsedData):
    absSourceParent: str
    absSourceFiles: list[str]
    isMultiSource: bool
    relTargetFile: str
    # params and registryDef are shared with every other file that the same json entry
    # builds, which includes every file that a wildcard in that entry expands into.
    # Neither of them may be modified after parsing.
    params: ParamsT
    registryDef: BundleRegistryDefinition

    def __init__(self):
        self.absSourceParent = None
        self.absSourceFiles = None # Expected to contain 1..N
        self.isMultiSource = False
        self.relTargetFile = None
        self.params = None
        self.registryDef = None

    def HasMultiSourceFile(self) -> bool:
        """
        Tells whether all source files build one target file together.
        This is not the same as having more than one source file, because a multi source
        file can be written with a single wildcard that resolves to any number of files.
        """
        return self.isMultiSource

    def GetFirstAbsSourceFile(self) -> str:
        return self.absSourceFiles[0]

    def GetFirstRelSourceFile(self) -> str:
        absSourceFile: str = self.absSourceFiles[0]
        return absSourceFile.removeprefix(self.absSourceParent).removeprefix("\\").removeprefix("/")

    def VerifyTypes(self) -> None:
        VerifyBuildFileParams(self.params, "bundles.items.files.params")

    def VerifyValues(self) -> None:
        util.Verify(util.IsValidPathName(self.relTargetFile), f"bundles.items.files.target '{self.relTargetFile}' is not a valid file name")
        util.Verify(not os.path.isabs(self.relTargetFile), f"bundles.items.files.target '{self.relTargetFile}' is not a relative path")

    def Normalize(self) -> None:
        self.absSourceParent = os.path.normpath(self.absSourceParent)
        for i, absSourceFile in enumerate(self.absSourceFiles):
            self.absSourceFiles[i] = os.path.normpath(absSourceFile)
        self.relTargetFile = os.path.normpath(self.relTargetFile)


@dataclass(init=False)
class BundleItem(ParsedData):
    name: str
    files: list[BundleFile]
    namePrefix: str
    nameSuffix: str
    isBig: bool
    bigSuffix: str
    setGameLanguageOnInstall: str
    events: BundleEventsT

    def __init__(self):
        self.name = None
        self.files = list[BundleFile]()
        self.namePrefix = ""
        self.nameSuffix = ""
        self.isBig = True
        self.bigSuffix = ""
        self.setGameLanguageOnInstall = ""
        self.events = BundleEventsT()

    def GetBigFileName(self) -> str:
        """
        Returns the name of the big file that is built from this item.
        Is only meaningful when this item is built as big file.
        """
        return self.namePrefix + self.name + self.nameSuffix + ".big"

    def GetPackTargetFileNames(self) -> list[str]:
        """
        Returns the names of the files that this item contributes to a bundle pack that lists it.
        A big item contributes its big file. Any other item contributes all of its target files.
        """
        if self.isBig:
            return [self.GetBigFileName() + self.bigSuffix]
        else:
            return [file.relTargetFile for file in self.files]

    def VerifyTypes(self) -> None:
        for file in self.files:
            file.VerifyTypes()

    def VerifyValues(self) -> None:
        util.Verify(util.IsValidPathName(self.name), f"bundles.items.name '{self.name}' has invalid name")
        util.Verify(not self.namePrefix or util.IsValidPathName(self.namePrefix), f"bundles.items.namePrefix '{self.namePrefix}' has invalid name")
        util.Verify(not self.nameSuffix or util.IsValidPathName(self.nameSuffix), f"bundles.items.nameSuffix '{self.nameSuffix}' has invalid name")
        util.Verify(not self.bigSuffix or util.IsValidPathName(self.bigSuffix), f"bundles.items.bigSuffix '{self.bigSuffix}' has invalid name")
        for file in self.files:
            file.VerifyValues()
        # All files of an item are built into the same item directory or big file.
        util.VerifyUniqueNames([file.relTargetFile for file in self.files], f"bundles.items '{self.name}' target file")
        for event in self.events.values():
            event.VerifyValues()

    def Normalize(self) -> None:
        for file in self.files:
            file.Normalize()
        for event in self.events.values():
            event.Normalize()

    def ResolveWildcards(self) -> None:
        newFiles: list[BundleFile] = []
        curFile: BundleFile

        for curFile in self.files:

            if curFile.HasMultiSourceFile():
                # All source files build the same target file. Wildcard matches add more source files to it.
                curFile.absSourceFiles = util.ResolveFileWildcards(curFile.absSourceFiles, sortWildcardMatches=True)
                if curFile.absSourceFiles:
                    newFiles.append(curFile)
                continue

            absSourceFile: str = curFile.GetFirstAbsSourceFile()

            if "*" in absSourceFile and not os.path.isfile(absSourceFile):
                globFiles = glob(absSourceFile, recursive=True)
                if not bool(globFiles):
                    print(f"Note: Wildcard '{absSourceFile}' currently matches nothing")

                for globFile in globFiles:
                    if os.path.isfile(globFile):
                        newFile: BundleFile = copy(curFile)
                        newFile.absSourceFiles = [globFile]
                        newFiles.append(newFile)
            else:
                util.Verify(os.path.isfile(absSourceFile), f"BundleFile.absSourceFiles.value '{absSourceFile}' is not a valid file")
                newFiles.append(curFile)

        for curFile in newFiles:
            # A multi source file has no single source file name to substitute a target wildcard with.
            if not curFile.HasMultiSourceFile():
                curFile.relTargetFile = BundleItem.__ResolveTargetWildcard(curFile.GetFirstRelSourceFile(), curFile.relTargetFile)

        self.files = newFiles

    @staticmethod
    def __ResolveTargetWildcard(source: str, target: str) -> str:
        sourcePath, sourceFile = os.path.split(source)
        targetPath, targetFile = os.path.split(target)
        sourceName, sourceExtn = os.path.splitext(sourceFile)
        targetName, targetExtn = os.path.splitext(targetFile)

        # Substitute wildcard file name.
        if targetFile == "*":
            newName = sourceName
            newExtn = sourceExtn
        else:
            newName = sourceName if targetName == "*" else targetName
            newExtn = sourceExtn if targetExtn == ".*" else targetExtn

        # Substitute wildcard file path.
        if "**" in targetPath:
            sourcePathList: list[str] = sourcePath.split(os.sep)
            targetPathList: list[str] = targetPath.split(os.sep)
            pathLevel = 0
            while pathLevel < len(targetPathList):
                if "**" in targetPathList[pathLevel]:
                    if pathLevel < len(sourcePathList):
                        # Take folder from source path on same level.
                        targetPathList[pathLevel] = sourcePathList[pathLevel]
                        if pathLevel == len(targetPathList) - 1:
                            # Is last element, take all remaining folders from source path.
                            # Do this, because glob.glob also takes all subfolders with a single ** folder.
                            pathLevel += 1
                            while pathLevel < len(sourcePathList):
                                targetPathList.append(sourcePathList[pathLevel])
                                pathLevel += 1
                            break
                    else:
                        # Has no matching source path, make empty.
                        targetPathList[pathLevel] = ""
                pathLevel += 1

            newTargetPath = os.path.join(*targetPathList)
        else:
            newTargetPath = targetPath

        # Build final path.
        newTarget = os.path.join(newTargetPath, newName + newExtn)
        return newTarget


@dataclass(init=False)
class BundlePack(ParsedData):
    name: str
    itemNames: list[str]
    namePrefix: str
    nameSuffix: str
    allowBuild: bool
    allowInstall: bool
    setGameLanguageOnInstall: str
    events: BundleEventsT

    def __init__(self):
        self.name = None
        self.itemNames = list[str]()
        self.namePrefix = ""
        self.nameSuffix = ""
        self.allowBuild = False
        self.allowInstall = False
        self.setGameLanguageOnInstall = ""
        self.events = BundleEventsT()

    def GetReleaseFileName(self) -> str:
        """
        Returns the name of the release zip file that is built from this pack.
        """
        return self.namePrefix + self.name + self.nameSuffix + ".zip"

    def VerifyValues(self) -> None:
        util.Verify(util.IsValidPathName(self.name), f"bundles.packs.name '{self.name}' has invalid name")
        util.Verify(not self.namePrefix or util.IsValidPathName(self.namePrefix), f"bundles.packs.namePrefix '{self.namePrefix}' has invalid name")
        util.Verify(not self.nameSuffix or util.IsValidPathName(self.nameSuffix), f"bundles.packs.nameSuffix '{self.nameSuffix}' has invalid name")
        util.VerifyUniqueNames(self.itemNames, f"bundles.packs '{self.name}' item name")
        for event in self.events.values():
            event.VerifyValues()

    def Normalize(self) -> None:
        for event in self.events.values():
            event.Normalize()


@dataclass(init=False)
class Bundles(ParsedData):
    items: list[BundleItem]
    packs: list[BundlePack]

    def __init__(self):
        self.items = list[BundleItem]()
        self.packs = list[BundlePack]()

    def FindItemByName(self, name: str) -> BundleItem:
        item: BundleItem
        for item in self.items:
            if item.name == name:
                return item
        return None

    def FindPackByName(self, name: str) -> BundlePack:
        pack: BundlePack
        for pack in self.packs:
            if pack.name == name:
                return pack
        return None

    def FindFirstGameLanguageForInstall(self, name: str) -> str:
        item: BundleItem = self.FindItemByName(name)
        if item != None:
            return item.setGameLanguageOnInstall

        pack: BundlePack = self.FindPackByName(name)
        if pack != None:
            itemName: str
            for itemName in pack.itemNames:
                item = self.FindItemByName(itemName)
                assert item != None
                if item.setGameLanguageOnInstall:
                    return item.setGameLanguageOnInstall

        return ""

    def GetPackListContainingItem(self, itemName: str) -> list[BundlePack]:
        pack: BundlePack
        packItemName: str
        packs = list[BundlePack]()
        for pack in self.packs:
            for packItemName in pack.itemNames:
                if packItemName == itemName:
                    packs.append(pack)
        return packs

    def GetPackListToBuild(self) -> list[BundlePack]:
        pack: BundlePack
        packs = list[BundlePack]()
        for pack in self.packs:
            if pack.allowBuild:
                packs.append(pack)
        return packs

    def GetPackListToInstall(self) -> list[BundlePack]:
        pack: BundlePack
        packs = list[BundlePack]()
        for pack in self.packs:
            if pack.allowInstall:
                packs.append(pack)
        return packs

    def IsItemAllowedToBuild(self, itemName: str) -> bool:
        pack: BundlePack
        packs: list[BundlePack] = self.GetPackListContainingItem(itemName)
        for pack in packs:
            if pack.allowBuild:
                return True
        return False
    
    def IsItemAllowedToInstall(self, itemName: str) -> bool:
        pack: BundlePack
        packs: list[BundlePack] = self.GetPackListContainingItem(itemName)
        for pack in packs:
            if pack.allowInstall:
                return True
        return False

    def HasPackToBuild(self) -> bool:
        packs: list[BundlePack] = self.GetPackListToBuild()
        return bool(packs)

    def HasPackToInstall(self) -> bool:
        packs: list[BundlePack] = self.GetPackListToInstall()
        return bool(packs)

    def VerifyTypes(self) -> None:
        for item in self.items:
            item.VerifyTypes()

    def VerifyValues(self) -> None:
        timer = util.Timer()
        for item in self.items:
            item.VerifyValues()
        for pack in self.packs:
            pack.VerifyValues()
        self.__VerifyUniqueItemNames()
        self.__VerifyUniqueItemBigFileNames()
        self.__VerifyUniquePackNames()
        self.__VerifyUniquePackReleaseFileNames()
        self.__VerifyKnownItemsInPacks()
        self.__VerifyUniquePackTargetFileNames()
        if timer.GetElapsedSeconds() > util.PERFORMANCE_TIMER_THRESHOLD:
            print(f"Bundles.VerifyValues completed in {timer.GetElapsedSecondsString()} s")

    def __VerifyUniqueItemNames(self) -> None:
        # Each item is built into its own directory that is named after the item.
        util.VerifyUniqueNames([item.name for item in self.items], "bundles.items item name")

    def __VerifyUniqueItemBigFileNames(self) -> None:
        # The big files of all items are built into the same directory.
        util.VerifyUniqueNames([item.GetBigFileName() for item in self.items if item.isBig], "bundles.items big file name")

    def __VerifyUniquePackNames(self) -> None:
        # Each pack is built into its own directory that is named after the pack.
        util.VerifyUniqueNames([pack.name for pack in self.packs], "bundles.packs pack name")

    def __VerifyUniquePackReleaseFileNames(self) -> None:
        # The release files of all packs are built into the same directory.
        util.VerifyUniqueNames([pack.GetReleaseFileName() for pack in self.packs], "bundles.packs release file name")

    def __VerifyUniquePackTargetFileNames(self) -> None:
        # All items of a pack are built into the same pack directory.
        # Is verified after __VerifyKnownItemsInPacks, so that every listed item is known to exist.
        pack: BundlePack
        itemName: str
        for pack in self.packs:
            targetFileNames = list[str]()
            for itemName in pack.itemNames:
                item: BundleItem = self.FindItemByName(itemName)
                assert item != None
                targetFileNames.extend(item.GetPackTargetFileNames())
            util.VerifyUniqueNames(targetFileNames, f"bundles.packs '{pack.name}' target file")

    def __VerifyKnownItemsInPacks(self) -> None:
        for pack in self.packs:
            for packItemName in pack.itemNames:
                found: bool = False
                for item in self.items:
                    if packItemName == item.name:
                        found = True
                        break
                util.Verify(found, f"bundles.packs '{pack.name}' references unknown bundle item '{packItemName}'")

    def Normalize(self) -> None:
        for item in self.items:
            item.Normalize()
        for pack in self.packs:
            pack.Normalize()

    def ResolveWildcards(self) -> None:
        for item in self.items:
            item.ResolveWildcards()


def __MakeRegistryDefinition(node: JsonNode, jsonDir: str) -> BundleRegistryDefinition:
    jRegistryList: list = node.GetOptional("registryList", list, elementType=str)
    if not jRegistryList:
        return None

    # Builds a new list, so that the parsed json data of the caller is left untouched.
    return BundleRegistryDefinition([os.path.join(jsonDir, jPath) for jPath in jRegistryList])


def __MakeBundleFilesFromDict(node: JsonNode, jsonDir: str) -> list[BundleFile]:
    files: list[BundleFile] = list()
    node.VerifyKnownKeys(BUNDLE_FILE_KEYS)

    jSourceParent: str = node.GetOptional("sourceParent", str)
    if jSourceParent == None:
        jSourceParent = node.GetOptional("parent", str) # Legacy name
    sourceParent: str = util.JoinPathIfValid(jsonDir, jsonDir, jSourceParent)

    params: ParamsT = node.GetOptional("params", dict, default=ParamsT())
    registryDef: BundleRegistryDefinition = __MakeRegistryDefinition(node, jsonDir)

    # A key that is only read stays a plain read. A key whose elements are walked below
    # is descended into once here, so that its name is written a single time.
    jSource: str = node.GetOptional("source", str)
    jTarget: str = node.GetOptional("target", str)
    jMultiSource: list = node.GetOptional("multiSource", list, elementType=str)
    sourceListNode: JsonNode = node.SubOptional("sourceList", list, elementType=str)
    sourceTargetListNode: JsonNode = node.SubOptional("sourceTargetList", list, elementType=dict)
    multiSourceTargetListNode: JsonNode = node.SubOptional("multiSourceTargetList", list, elementType=dict)

    # Is tested first, so that an entry naming both keeps being reported as that.
    util.Verify(not (jSource and jMultiSource), "Bundle file cannot specify 'source' and 'multiSource' together, because both would build the same 'target' file")

    # An entry that names no source key at all builds nothing, which is never intended
    # and hides a misspelled key. An empty source collection does the same.
    jSourceKeys: dict = {
        "source": jSource,
        "sourceList": sourceListNode.data,
        "sourceTargetList": sourceTargetListNode.data,
        "multiSource": jMultiSource,
        "multiSourceTargetList": multiSourceTargetListNode.data,
    }
    jPresentKeys: list[str] = [key for key, value in jSourceKeys.items() if value != None]
    node.Verify(bool(jPresentKeys),
               "must name at least one of 'source', 'sourceList', 'sourceTargetList', "
               "'multiSource' or 'multiSourceTargetList', otherwise it builds no file at all")
    for key in jPresentKeys:
        node.Verify(bool(jSourceKeys[key]), "must not be empty, otherwise it builds no file at all", key=key)

    # The targets of a sourceList and of a sourceTargetList are derived from their own
    # source files, so a target next to them alone would be silently ignored.
    if jTarget != None:
        node.Verify(jSource != None or jMultiSource != None,
                    "is only used together with 'source' or 'multiSource'", key="target")

    def MakeSourceFile(fileNode: JsonNode, jElement: str, key: str) -> str:
        fileNode.Verify(bool(jElement), "must not be empty", key=key)
        return os.path.join(sourceParent, jElement)

    def MakeMultiSourceBundleFile(multiNode: JsonNode, jMultiSourceElement: list, jMultiTarget: str) -> BundleFile:
        multiNode.Verify(bool(jMultiSourceElement), "must not be empty, otherwise it builds no file at all", key="multiSource")
        multiNode.Verify(bool(jMultiTarget), "is mandatory with 'multiSource', because it cannot be derived from a single source file name", key="target")
        multiNode.Verify(not "*" in jMultiTarget, f"'{jMultiTarget}' cannot contain a wildcard with 'multiSource', because it cannot be derived from a single source file name", key="target")

        bundleFile = BundleFile()
        bundleFile.absSourceParent = sourceParent
        bundleFile.absSourceFiles = [MakeSourceFile(multiNode, jElement, "multiSource")
                                     for jElement in jMultiSourceElement]
        bundleFile.isMultiSource = True
        bundleFile.relTargetFile = jMultiTarget
        bundleFile.params = params
        bundleFile.registryDef = registryDef
        return bundleFile

    if jSource:
        bundleFile = BundleFile()
        bundleFile.absSourceParent = sourceParent
        bundleFile.absSourceFiles = [MakeSourceFile(node, jSource, "source")]
        bundleFile.relTargetFile = jTarget if jTarget != None else jSource
        bundleFile.params = params
        bundleFile.registryDef = registryDef
        files.append(bundleFile)

    elementNode: JsonNode
    for elementNode in sourceListNode.Elements():
        bundleFile = BundleFile()
        bundleFile.absSourceParent = sourceParent
        bundleFile.absSourceFiles = [MakeSourceFile(elementNode, elementNode.data, "")]
        bundleFile.relTargetFile = elementNode.data
        bundleFile.params = params
        bundleFile.registryDef = registryDef
        files.append(bundleFile)

    for elementNode in sourceTargetListNode.Elements():
        elementNode.VerifyKnownKeys(BUNDLE_SOURCE_TARGET_KEYS)
        jElementSource: str = elementNode.GetMandatory("source", str)
        bundleFile = BundleFile()
        bundleFile.absSourceParent = sourceParent
        bundleFile.absSourceFiles = [MakeSourceFile(elementNode, jElementSource, "source")]
        bundleFile.relTargetFile = elementNode.GetOptional("target", str, default=jElementSource)
        bundleFile.params = params
        bundleFile.registryDef = registryDef
        files.append(bundleFile)

    # Tested against None, so that an empty list is reported as a bad configuration
    # instead of silently building no target file at all.
    if jMultiSource != None:
        files.append(MakeMultiSourceBundleFile(node, jMultiSource, jTarget))

    for elementNode in multiSourceTargetListNode.Elements():
        elementNode.VerifyKnownKeys(BUNDLE_MULTI_SOURCE_TARGET_KEYS)
        files.append(MakeMultiSourceBundleFile(
            elementNode,
            elementNode.GetMandatory("multiSource", list, elementType=str),
            elementNode.GetOptional("target", str)))

    return files


def __MakeBundleEventsFromDict(node: JsonNode, jsonDir: str) -> BundleEventsT:
    events = BundleEventsT()
    eventName: str
    eventType: BundleEventType

    for eventName, eventType in g_bundleEventTypeByJsonName.items():
        if eventNode := node.SubOptional(eventName):
            eventNode.VerifyKnownKeys(BUNDLE_EVENT_KEYS)
            event = BundleEvent()
            event.type = eventType
            event.absScript = os.path.join(jsonDir, eventNode.GetMandatory("script", str))
            event.funcName = eventNode.GetOptional("function", str, event.funcName)
            event.kwargs = eventNode.GetOptional("kwargs", dict, event.kwargs)
            events[event.type] = event

    return events


def __MakeBundleItemFromDict(node: JsonNode, jsonDir: str) -> BundleItem:
    item = BundleItem()
    node.VerifyKnownKeys(BUNDLE_ITEM_KEYS)
    item.name = node.GetMandatory("name", str)
    item.namePrefix = node.GetOptional("namePrefix", str, item.namePrefix)
    item.nameSuffix = node.GetOptional("nameSuffix", str, item.nameSuffix)
    item.isBig = node.GetOptional("big", bool, item.isBig)
    item.bigSuffix = node.GetOptional("bigSuffix", str, item.bigSuffix)
    item.setGameLanguageOnInstall = node.GetOptional(
        "setGameLanguageOnInstall", str, item.setGameLanguageOnInstall)

    fileNode: JsonNode
    for fileNode in node.Elements("files", dict):
        item.files.extend(__MakeBundleFilesFromDict(fileNode, jsonDir))

    item.events = __MakeBundleEventsFromDict(node, jsonDir)

    return item


def __MakeBundlePackFromDict(node: JsonNode, jsonDir: str) -> BundlePack:
    pack = BundlePack()
    node.VerifyKnownKeys(BUNDLE_PACK_KEYS)
    pack.name = node.GetMandatory("name", str)
    pack.namePrefix = node.GetOptional("namePrefix", str, pack.namePrefix)
    pack.nameSuffix = node.GetOptional("nameSuffix", str, pack.nameSuffix)
    pack.itemNames = node.GetMandatory("itemNames", list, elementType=str)
    pack.allowInstall = node.GetOptional("install", bool, pack.allowInstall)
    pack.allowBuild = node.GetOptional("build", bool, pack.allowBuild)
    pack.setGameLanguageOnInstall = node.GetOptional(
        "setGameLanguageOnInstall", str, pack.setGameLanguageOnInstall)
    pack.events = __MakeBundleEventsFromDict(node, jsonDir)

    return pack


def AddBundlePacksFromJsons(jsonFiles: list[JsonFile], bundles: Bundles) -> None:
    """
    Parses bundle packs from all json files where present.
    """
    jPacksPrefix: str = ""
    jPacksSuffix: str = ""

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsFileDir(jsonFile.path)
        root = util.JsonNode(jsonFile.path, jsonFile.data)

        if node := root.SubOptional("bundles"):
            node.VerifyKnownKeys(BUNDLES_KEYS)
            VerifyFormatVersion(node, LATEST_BUNDLES_VERSION)

            # The prefixes are deliberately not reset per json file. A prefix declared
            # in one file keeps applying to the packs of the following files.
            jPacksPrefix: str = node.GetOptional("packsPrefix", str, jPacksPrefix)
            jPacksSuffix: str = node.GetOptional("packsSuffix", str, jPacksSuffix)
            packNode: JsonNode
            for packNode in node.Elements("packs", dict, nameKey="name"):
                bundlePack: BundlePack = __MakeBundlePackFromDict(packNode, jsonDir)

                if not bundlePack.namePrefix and jPacksPrefix:
                    bundlePack.namePrefix = jPacksPrefix
                if not bundlePack.nameSuffix and jPacksSuffix:
                    bundlePack.nameSuffix = jPacksSuffix

                bundles.packs.append(bundlePack)
    return


def AddBundleItemsFromJsons(jsonFiles: list[JsonFile], bundles: Bundles) -> None:
    """
    Parses bundle items from all json files where present.
    """
    jItemsPrefix: str = ""
    jItemsSuffix: str = ""

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsFileDir(jsonFile.path)
        root = util.JsonNode(jsonFile.path, jsonFile.data)

        if node := root.SubOptional("bundles"):
            node.VerifyKnownKeys(BUNDLES_KEYS)
            VerifyFormatVersion(node, LATEST_BUNDLES_VERSION)

            # The prefixes are deliberately not reset per json file. A prefix declared
            # in one file keeps applying to the items of the following files.
            jItemsPrefix: str = node.GetOptional("itemsPrefix", str, jItemsPrefix)
            jItemsSuffix: str = node.GetOptional("itemsSuffix", str, jItemsSuffix)
            itemNode: JsonNode
            for itemNode in node.Elements("items", dict, nameKey="name"):
                bundleItem: BundleItem = __MakeBundleItemFromDict(itemNode, jsonDir)

                if not bundleItem.namePrefix and jItemsPrefix:
                    bundleItem.namePrefix = jItemsPrefix
                if not bundleItem.nameSuffix and jItemsSuffix:
                    bundleItem.nameSuffix = jItemsSuffix

                bundles.items.append(bundleItem)
    return


def MakeBundlesFromJsons(jsonFiles: list[JsonFile]) -> Bundles:
    bundles = Bundles()

    AddBundleItemsFromJsons(jsonFiles, bundles)
    AddBundlePacksFromJsons(jsonFiles, bundles)

    FinalizeParsedData(bundles)

    return bundles
