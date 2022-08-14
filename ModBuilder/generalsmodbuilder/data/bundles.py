import enum
import os.path
from glob import glob
from dataclasses import dataclass
from enum import Enum, auto
from generalsmodbuilder.data.common import ParamsT, VerifyParamsType
from generalsmodbuilder.util import JsonFile
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


@dataclass(init=False)
class BundleEvent:
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

    def VerifyTypes(self) -> None:
        util.VerifyType(self.type, BundleEventType, "BundleEvent.type")
        util.VerifyType(self.absScript, str, "BundleEvent.absScript")
        util.VerifyType(self.funcName, str, "BundleEvent.functionName")
        util.VerifyType(self.kwargs, dict, "BundleEvent.kwargs")

    def VerifyValues(self) -> None:
        util.Verify(os.path.isfile(self.absScript), f"BundleEvent.absScript '{self.absScript}' is not a valid file")
        util.Verify(len(self.funcName) > 0, f"BundleEvent.functionName cannot be empty")

    def Normalize(self) -> None:
        self.absScript = os.path.normpath(self.absScript)


BundleEventsT = dict[BundleEventType, BundleEvent]


@dataclass(init=False)
class BundleFile:
    absSourceFile: str
    relTargetFile: str
    params: ParamsT

    def __init__(self):
        self.absSourceFile = None
        self.relTargetFile = None
        self.params = ParamsT()

    def VerifyTypes(self) -> None:
        util.VerifyType(self.absSourceFile, str, "BundleFile.absSourceFile")
        util.VerifyType(self.relTargetFile, str, "BundleFile.relTargetFile")
        VerifyParamsType(self.params, "BundleFile.params")

    def VerifyValues(self) -> None:
        util.Verify(os.path.isfile(self.absSourceFile), f"BundleFile.absSourceFile '{self.absSourceFile}' is not a valid file")
        util.Verify(util.IsValidPathName(self.relTargetFile), f"BundleFile.relTargetFile '{self.relTargetFile}' is not a valid file name")
        util.Verify(not os.path.isabs(self.relTargetFile), f"BundleFile.relTargetFile '{self.relTargetFile}' is not a relative path")

    def Normalize(self) -> None:
        self.absSourceFile = os.path.normpath(self.absSourceFile)
        self.relTargetFile = os.path.normpath(self.relTargetFile)


@dataclass(init=False)
class BundleItem:
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

    def VerifyTypes(self) -> None:
        util.VerifyType(self.name, str, "BundleItem.name")
        util.VerifyType(self.files, list, "BundleItem.files")
        util.VerifyType(self.namePrefix, str, "BundleItem.namePrefix")
        util.VerifyType(self.nameSuffix, str, "BundleItem.nameSuffix")
        util.VerifyType(self.isBig, bool, "BundleItem.isBig")
        util.VerifyType(self.bigSuffix, str, "BundleItem.bigSuffix")
        util.VerifyType(self.setGameLanguageOnInstall, str, "BundleItem.setGameLanguageOnInstall")
        util.VerifyType(self.events, dict, "BundleItem.events")
        for file in self.files:
            util.VerifyType(file, BundleFile, "BundleItem.files.value")
            file.VerifyTypes()
        for type,event in self.events.items():
            util.VerifyType(type, BundleEventType, "BundleItem.events.key")
            util.VerifyType(event, BundleEvent, "BundleItem.events.value")
            event.VerifyTypes()

    def VerifyValues(self) -> None:
        util.Verify(util.IsValidPathName(self.name), f"BundleItem.name '{self.name}' has invalid name")
        util.Verify(not self.namePrefix or util.IsValidPathName(self.namePrefix), f"BundleItem.namePrefix '{self.namePrefix}' has invalid name")
        util.Verify(not self.nameSuffix or util.IsValidPathName(self.nameSuffix), f"BundleItem.nameSuffix '{self.nameSuffix}' has invalid name")
        util.Verify(not self.bigSuffix or util.IsValidPathName(self.bigSuffix), f"BundleItem.bigSuffix '{self.bigSuffix}' has invalid name")
        for file in self.files:
            file.VerifyValues()
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
            if not os.path.isfile(curFile.absSourceFile) and "*" in curFile.absSourceFile:
                globFiles = glob(curFile.absSourceFile, recursive=True)
                util.Verify(bool(globFiles), f"Wildcard '{curFile.absSourceFile}' matches nothing")

                for globFile in globFiles:
                    if os.path.isfile(globFile):
                        newFile = BundleFile()
                        newFile.absSourceFile = globFile
                        newFile.relTargetFile = curFile.relTargetFile
                        newFile.params = curFile.params
                        newFiles.append(newFile)
            else:
                newFiles.append(curFile)

        for curFile in newFiles:
            curFile.relTargetFile = BundleItem.__ResolveTargetWildcard(curFile.absSourceFile, curFile.relTargetFile)

        self.files = newFiles
        return newFiles

    @staticmethod
    def __ResolveTargetWildcard(source: str, target: str) -> str:
        sourcePath, sourceFile = os.path.split(source)
        targetPath, targetFile = os.path.split(target)
        sourceName, sourceExtn = os.path.splitext(sourceFile)
        targetName, targetExtn = os.path.splitext(targetFile)

        if targetFile == "*":
            newName = sourceName
            newExtn = sourceExtn
        else:
            newName = sourceName if targetName == "*" else targetName
            newExtn = sourceExtn if targetExtn == ".*" else targetExtn

        if "**" in targetPath:
            basePathPair: list[str] = targetPath.split("**", 1)
            basePath = os.path.dirname(basePathPair[0])
            sourceExtraPathPair: list[str] = source.split(basePath)
            if len(sourceExtraPathPair) > 1:
                sourceExtraPath = os.path.dirname(sourceExtraPathPair[-1])
                sourceExtraPath = util.RemoveLeadingString(sourceExtraPath, "/")
                sourceExtraPath = util.RemoveLeadingString(sourceExtraPath, "\\")
            else:
                sourceExtraPath = ""
            newPath = targetPath.replace("**", sourceExtraPath)
            newPath = os.path.normpath(newPath)
        else:
            newPath = os.path.normpath(targetPath)

        newTarget = os.path.join(newPath, newName + newExtn)
        newTarget = util.RemoveLeadingString(newTarget, "./")
        newTarget = util.RemoveLeadingString(newTarget, ".\\")
        return newTarget


@dataclass(init=False)
class BundlePack:
    name: str
    itemNames: list[str]
    namePrefix: str
    nameSuffix: str
    install: bool
    setGameLanguageOnInstall: str
    events: BundleEventsT

    def __init__(self):
        self.name = None
        self.itemNames = list[str]()
        self.namePrefix = ""
        self.nameSuffix = ""
        self.install = False
        self.setGameLanguageOnInstall = ""
        self.events = BundleEventsT()

    def VerifyTypes(self) -> None:
        util.VerifyType(self.name, str, "BundlePack.name")
        util.VerifyType(self.itemNames, list, "BundlePack.itemNames")
        util.VerifyType(self.namePrefix, str, "BundlePack.namePrefix")
        util.VerifyType(self.nameSuffix, str, "BundlePack.nameSuffix")
        util.VerifyType(self.install, bool, "BundlePack.install")
        util.VerifyType(self.setGameLanguageOnInstall, str, "BundlePack.setGameLanguageOnInstall")
        util.VerifyType(self.events, dict, "BundlePack.events")
        for itemName in self.itemNames:
            util.VerifyType(itemName, str, "BundlePack.itemNames.value")
        for type,event in self.events.items():
            util.VerifyType(type, BundleEventType, "BundlePack.events.key")
            util.VerifyType(event, BundleEvent, "BundlePack.events.value")
            event.VerifyTypes()

    def VerifyValues(self) -> None:
        util.Verify(util.IsValidPathName(self.name), f"BundlePack.name '{self.name}' has invalid name")
        util.Verify(not self.namePrefix or util.IsValidPathName(self.namePrefix), f"BundlePack.namePrefix '{self.namePrefix}' has invalid name")
        util.Verify(not self.nameSuffix or util.IsValidPathName(self.nameSuffix), f"BundlePack.nameSuffix '{self.nameSuffix}' has invalid name")
        for event in self.events.values():
            event.VerifyValues()

    def Normalize(self) -> None:
        for event in self.events.values():
            event.Normalize()


@dataclass(init=False)
class Bundles:
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
                assert(item != None)
                if item.setGameLanguageOnInstall:
                    return item.setGameLanguageOnInstall

        return ""

    def VerifyTypes(self) -> None:
        util.VerifyType(self.items, list, "Bundles.items")
        util.VerifyType(self.packs, list, "Bundles.packs")
        for item in self.items:
            util.VerifyType(item, BundleItem, "Bundles.items.value")
            item.VerifyTypes()
        for pack in self.packs:
            util.VerifyType(pack, BundlePack, "Bundles.packs.value")
            pack.VerifyTypes()

    def VerifyValues(self) -> None:
        for item in self.items:
            item.VerifyValues()
        for pack in self.packs:
            pack.VerifyValues()
        self.__VerifyUniqueItemNames()
        self.__VerifyKnownItemsInPacks()

    def __VerifyUniqueItemNames(self) -> None:
        itemLen = len(self.items)
        for a in range(itemLen):
            for b in range(a + 1, itemLen):
                nameA: str = self.items[a].name
                nameB: str = self.items[b].name
                util.Verify(nameA != nameB, f"Bundles.items has items with duplicate name '{nameA}'")

    def __VerifyKnownItemsInPacks(self) -> None:
        for pack in self.packs:
            for packItemName in pack.itemNames:
                found: bool = False
                for item in self.items:
                    if packItemName == item.name:
                        found = True
                        break
                util.Verify(found, f"Bundles.packs with pack '{pack.name}' references unknown bundle item '{packItemName}'")

    def Normalize(self) -> None:
        for item in self.items:
            item.Normalize()
        for pack in self.packs:
            pack.Normalize()

    def ResolveWildcards(self) -> None:
        for item in self.items:
            item.ResolveWildcards()


def __MakeBundleFilesFromDict(jFile: dict, jsonDir: str) -> list[BundleFile]:
    files: list[BundleFile] = list()

    parent = util.JoinPathIfValid(jsonDir, jsonDir, jFile.get("parent"))
    params: ParamsT = jFile.get("params")
    if params == None:
        params = ParamsT()

    jSource: str = jFile.get("source")
    jSourceList: list = jFile.get("sourceList")
    jSourceTargetList: list = jFile.get("sourceTargetList")

    if jSource:
        bundleFile = BundleFile()
        bundleFile.absSourceFile = util.JoinPathIfValid(None, parent, jSource)
        bundleFile.relTargetFile = jFile.get("target", jSource)
        bundleFile.params = params
        files.append(bundleFile)

    if jSourceList:
        jElement: str
        for jElement in jSourceList:
            bundleFile = BundleFile()
            bundleFile.absSourceFile = util.JoinPathIfValid(None, parent, jElement)
            bundleFile.relTargetFile = jElement
            bundleFile.params = params
            files.append(bundleFile)

    if jSourceTargetList:
        jElement: dict[str, str]
        for jElement in jSourceTargetList:
            jElementSource: str = jElement.get("source")
            bundleFile = BundleFile()
            bundleFile.absSourceFile = util.JoinPathIfValid(None, parent, jElementSource)
            bundleFile.relTargetFile = jElement.get("target", jElementSource)
            bundleFile.params = params
            files.append(bundleFile)

    return files


def __MakeBundleEventsFromDict(jThing: dict, jsonDir: str) -> BundleEventsT:
    events = BundleEventsT()
    eventType: BundleEventType

    for eventType in BundleEventType:
        eventName: str = GetJsonBundleEventName(eventType)
        jEvent: dict = jThing.get(eventName)
        if jEvent:
            event = BundleEvent()
            event.type = eventType
            event.absScript = util.JoinPathIfValid(None, jsonDir, jEvent.get("script"))
            event.funcName = jEvent.get("function", event.funcName)
            event.kwargs = jEvent.get("kwargs", event.kwargs)
            events[event.type] = event

    return events


def __MakeBundleItemFromDict(jItem: dict, jsonDir: str) -> BundleItem:
    item = BundleItem()
    item.name = jItem.get("name")
    item.namePrefix = jItem.get("namePrefix", item.namePrefix)
    item.nameSuffix = jItem.get("nameSuffix", item.nameSuffix)
    item.isBig = jItem.get("big", item.isBig)
    item.bigSuffix = jItem.get("bigSuffix", item.bigSuffix)
    item.setGameLanguageOnInstall = jItem.get("setGameLanguageOnInstall", item.setGameLanguageOnInstall)

    jFiles = jItem.get("files")
    if jFiles:
        jFile: dict
        for jFile in jFiles:
            item.files.extend(__MakeBundleFilesFromDict(jFile, jsonDir))

    item.events = __MakeBundleEventsFromDict(jItem, jsonDir)

    return item


def __MakeBundlePackFromDict(jPack: dict, jsonDir: str) -> BundlePack:
    pack = BundlePack()
    pack.name = jPack.get("name")
    pack.namePrefix = jPack.get("namePrefix", pack.namePrefix)
    pack.nameSuffix = jPack.get("nameSuffix", pack.nameSuffix)
    pack.itemNames = jPack.get("itemNames")
    pack.install = jPack.get("install", pack.install)
    pack.setGameLanguageOnInstall = jPack.get("setGameLanguageOnInstall", pack.setGameLanguageOnInstall)
    pack.events = __MakeBundleEventsFromDict(jPack, jsonDir)

    return pack


def MakeBundlesFromJsons(jsonFiles: list[JsonFile]) -> Bundles:
    bundles = Bundles()

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetAbsSmartFileDir(jsonFile.path)
        jBundles: dict = jsonFile.data.get("bundles")

        if jBundles:
            jItemsPrefix: str = jBundles.get("itemsPrefix")
            jItemsSuffix: str = jBundles.get("itemsSuffix")
            jItems: dict = jBundles.get("items")

            if jItems:
                jItem: dict
                for jItem in jItems:
                    bundleItem: BundleItem = __MakeBundleItemFromDict(jItem, jsonDir)

                    if not bundleItem.namePrefix and jItemsPrefix != None:
                        bundleItem.namePrefix = jItemsPrefix
                    if not bundleItem.nameSuffix and jItemsSuffix != None:
                        bundleItem.nameSuffix = jItemsSuffix

                    bundles.items.append(bundleItem)

            jPacksPrefix: str = jBundles.get("packsPrefix")
            jPacksSuffix: str = jBundles.get("packsSuffix")
            jPacks: dict = jBundles.get("packs")
            if jPacks:
                jPack: dict
                for jPack in jPacks:
                    bundlePack: BundlePack = __MakeBundlePackFromDict(jPack, jsonDir)

                    if not bundlePack.namePrefix and jPacksPrefix != None:
                        bundlePack.namePrefix = jPacksPrefix
                    if not bundlePack.nameSuffix and jPacksSuffix != None:
                        bundlePack.nameSuffix = jPacksSuffix

                    bundles.packs.append(bundlePack)

    bundles.VerifyTypes()
    bundles.Normalize()
    bundles.ResolveWildcards()
    bundles.VerifyValues()

    return bundles
