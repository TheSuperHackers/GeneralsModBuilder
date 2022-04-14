import enum
import util
import os.path
from glob import glob
from dataclasses import dataclass
from data.common import ParamsT, VerifyParamsType
from util import JsonFile


class BundleEventType(enum.Enum):
    PRE_BUILD = 0

g_jsonBundleEventNames: list[str] = [""] * len(BundleEventType)
g_jsonBundleEventNames[BundleEventType.PRE_BUILD.value] = "onPreBuild"


@dataclass(init=False)
class BundleEvent:
    type: BundleEventType
    absScript: str
    funcName: str
    kwargs: dict

    def __init__(self):
        self.funcName = "OnEvent"
        self.kwargs = dict()

    def GetScriptDir(self) -> str:
        return os.path.dirname(self.absScript)

    def GetScriptName(self) -> str:
        base: str = os.path.basename(self.absScript)
        name, ext = os.path.splitext(base)
        return name

    def VerifyTypes(self) -> None:
        util.RelAssertType(self.type, BundleEventType, "BundleEvent.type")
        util.RelAssertType(self.absScript, str, "BundleEvent.absScript")
        util.RelAssertType(self.funcName, str, "BundleEvent.functionName")
        util.RelAssertType(self.kwargs, dict, "BundleEvent.kwargs")

    def VerifyValues(self) -> None:
        util.RelAssert(os.path.isfile(self.absScript), f"BundleEvent.absScript '{self.absScript}' is not a valid file")
        util.RelAssert(len(self.funcName) > 0, f"BundleEvent.functionName cannot be empty")

    def Normalize(self) -> None:
        self.absScript = util.NormalizePath(self.absScript)


BundleEventsT = dict[BundleEventType, BundleEvent]


@dataclass(init=False)
class BundleFile:
    absSourceFile: str
    relTargetFile: str
    params: ParamsT

    def __init__(self):
        pass

    def VerifyTypes(self) -> None:
        util.RelAssertType(self.absSourceFile, str, "BundleFile.absSourceFile")
        util.RelAssertType(self.relTargetFile, str, "BundleFile.relTargetFile")
        VerifyParamsType(self.params, "BundleFile.params")

    def VerifyValues(self) -> None:
        util.RelAssert(os.path.isfile(self.absSourceFile), f"BundleFile.absSourceFile '{self.absSourceFile}' is not a valid file")
        util.RelAssert(not os.path.isabs(self.relTargetFile), f"BundleFile.relTargetFile '{self.relTargetFile}' is not a relative path")

    def Normalize(self) -> None:
        self.absSourceFile = util.NormalizePath(self.absSourceFile)
        self.relTargetFile = util.NormalizePath(self.relTargetFile)


@dataclass(init=False)
class BundleItem:
    name: str
    files: list[BundleFile]
    namePrefix: str
    nameSuffix: str
    isBig: bool
    events: BundleEventsT

    def __init__(self):
        self.namePrefix = ""
        self.nameSuffix = ""
        self.isBig = True
        self.events = BundleEventsT()

    def VerifyTypes(self) -> None:
        util.RelAssertType(self.name, str, "BundleItem.name")
        util.RelAssertType(self.files, list, "BundleItem.files")
        util.RelAssertType(self.namePrefix, str, "BundleItem.namePrefix")
        util.RelAssertType(self.nameSuffix, str, "BundleItem.nameSuffix")
        util.RelAssertType(self.isBig, bool, "BundleItem.isBig")
        util.RelAssertType(self.events, dict, "BundleItem.events")
        for file in self.files:
            util.RelAssertType(file, BundleFile, "BundleItem.files.value")
            file.VerifyTypes()
        for type,event in self.events.items():
            util.RelAssertType(type, BundleEventType, "BundleItem.events.key")
            util.RelAssertType(event, BundleEvent, "BundleItem.events.value")
            event.VerifyTypes()

    def VerifyValues(self) -> None:
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
                util.RelAssert(bool(globFiles), f"Wildcard '{curFile.absSourceFile}' matches nothing")

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

        # TODO: Implement ** target folder support?

        newTarget = os.path.join(targetPath, newName + newExtn)
        return newTarget


@dataclass(init=False)
class BundlePack:
    name: str
    itemNames: list[str]
    namePrefix: str
    nameSuffix: str
    install: bool
    events: BundleEventsT

    def __init__(self):
        self.namePrefix = ""
        self.nameSuffix = ""
        self.install = False
        self.events = BundleEventsT()

    def VerifyTypes(self) -> None:
        util.RelAssertType(self.name, str, "BundlePack.name")
        util.RelAssertType(self.itemNames, list, "BundlePack.itemNames")
        util.RelAssertType(self.namePrefix, str, "BundlePack.namePrefix")
        util.RelAssertType(self.nameSuffix, str, "BundlePack.nameSuffix")
        util.RelAssertType(self.install, bool, "BundlePack.install")
        util.RelAssertType(self.events, dict, "BundlePack.events")
        for itemName in self.itemNames:
            util.RelAssertType(itemName, str, "BundlePack.itemNames.value")
        for type,event in self.events.items():
            util.RelAssertType(type, BundleEventType, "BundlePack.events.key")
            util.RelAssertType(event, BundleEvent, "BundlePack.events.value")
            event.VerifyTypes()

    def VerifyValues(self) -> None:
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
        pass

    def VerifyTypes(self) -> None:
        util.RelAssertType(self.items, list, "Bundles.items")
        util.RelAssertType(self.packs, list, "Bundles.packs")
        for item in self.items:
            util.RelAssertType(item, BundleItem, "Bundles.items.value")
            item.VerifyTypes()
        for pack in self.packs:
            util.RelAssertType(pack, BundlePack, "Bundles.packs.value")
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
                util.RelAssert(nameA != nameB, f"Bundles.items has items with duplicate name '{nameA}'")

    def __VerifyKnownItemsInPacks(self) -> None:
        for pack in self.packs:
            for packItemName in pack.itemNames:
                found: bool = False
                for item in self.items:
                    if packItemName == item.name:
                        found = True
                        break
                util.RelAssert(found, f"Bundles.packs with pack '{pack.name}' references unknown bundle item '{packItemName}'")

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
        bundleFile.relTargetFile = util.GetSecondIfValid(jSource, jFile.get("target"))
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
            bundleFile.relTargetFile = util.GetSecondIfValid(jElementSource, jElement.get("target"))
            bundleFile.params = params
            files.append(bundleFile)

    return files


def __MakeBundleEventsFromDict(jThing: dict, jsonDir: str) -> BundleEventsT:
    events = BundleEventsT()
    eventType: BundleEventType

    for eventType in BundleEventType:
        eventName: str = g_jsonBundleEventNames[eventType.value]
        jEvent: dict = jThing.get(eventName)
        if jEvent:
            event = BundleEvent()
            event.type = eventType
            event.absScript = util.JoinPathIfValid(None, jsonDir, jEvent.get("script"))
            event.funcName = util.GetSecondIfValid(event.funcName, jEvent.get("function"))
            event.kwargs = util.GetSecondIfValid(event.kwargs, jEvent.get("kwargs"))
            events[event.type] = event

    return events


def __MakeBundleItemFromDict(jItem: dict, jsonDir: str) -> BundleItem:
    item = BundleItem()
    item.name = util.GetSecondIfValid("Undefined", jItem.get("name"))
    item.isBig = util.GetSecondIfValid(False, jItem.get("big"))
    item.files = list()

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
    pack.install = util.GetSecondIfValid(pack.install, jPack.get("install"))
    pack.itemNames = jPack.get("itemNames")
    pack.events = __MakeBundleEventsFromDict(jPack, jsonDir)

    return pack


def MakeBundlesFromJsons(jsonFiles: list[JsonFile]) -> Bundles:
    bundles = Bundles()
    bundles.items = list()
    bundles.packs = list()

    for jsonFile in jsonFiles:
        jsonDir: str = util.GetFileDir(jsonFile.path)
        jBundles: dict = jsonFile.data.get("bundles")

        if jBundles:
            jItemsPrefix: str = jBundles.get("itemsPrefix")
            jItemsSuffix: str = jBundles.get("itemsSuffix")
            jItems: dict = jBundles.get("items")

            if jItems:
                jItem: dict
                for jItem in jItems:
                    bundleItem: BundleItem = __MakeBundleItemFromDict(jItem, jsonDir)
                    bundleItem.namePrefix = util.GetSecondIfValid(bundleItem.namePrefix, jItemsPrefix)
                    bundleItem.nameSuffix = util.GetSecondIfValid(bundleItem.nameSuffix, jItemsSuffix)
                    bundles.items.append(bundleItem)

            jPacksPrefix: str = jBundles.get("packsPrefix")
            jPacksSuffix: str = jBundles.get("packsSuffix")
            jPacks: dict = jBundles.get("packs")
            if jPacks:
                jPack: dict
                for jPack in jPacks:
                    bundlePack: BundlePack = __MakeBundlePackFromDict(jPack, jsonDir)
                    bundlePack.namePrefix = util.GetSecondIfValid(bundlePack.namePrefix, jPacksPrefix)
                    bundlePack.nameSuffix = util.GetSecondIfValid(bundlePack.nameSuffix, jPacksSuffix)
                    bundles.packs.append(bundlePack)

    bundles.VerifyTypes()
    bundles.Normalize()
    bundles.ResolveWildcards()
    bundles.VerifyValues()

    return bundles
