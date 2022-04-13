import utils
import os.path
from glob import glob
from dataclasses import dataclass
from data.common import ParamsT, VerifyParamsType
from utils import JsonFile


@dataclass(init=False)
class BundleFile:
    absSourceFile: str
    relTargetFile: str
    params: ParamsT

    def __init__(self):
        pass

    def VerifyTypes(self) -> None:
        utils.RelAssertType(self.absSourceFile, str, "BundleFile.absSourceFile")
        utils.RelAssertType(self.relTargetFile, str, "BundleFile.relTargetFile")
        VerifyParamsType(self.params, "BundleFile.params")

    def VerifyValues(self) -> None:
        utils.RelAssert(os.path.isfile(self.absSourceFile), f"BundleFile.absSourceFile '{self.absSourceFile}' is not a valid file")
        utils.RelAssert(not os.path.isabs(self.relTargetFile), f"BundleFile.relTargetFile '{self.relTargetFile}' is not a relative path")

    def Normalize(self) -> None:
        self.absSourceFile = utils.NormalizePath(self.absSourceFile)
        self.relTargetFile = utils.NormalizePath(self.relTargetFile)


@dataclass(init=False)
class BundleItem:
    name: str
    namePrefix: str
    nameSuffix: str
    isBig: bool
    files: list[BundleFile]

    def __init__(self):
        self.namePrefix = ""
        self.nameSuffix = ""
        self.isBig = True

    def VerifyTypes(self) -> None:
        utils.RelAssertType(self.name, str, "BundleItem.name")
        utils.RelAssertType(self.namePrefix, str, "BundleItem.namePrefix")
        utils.RelAssertType(self.nameSuffix, str, "BundleItem.nameSuffix")
        utils.RelAssertType(self.isBig, bool, "BundleItem.isBig")
        utils.RelAssertType(self.files, list, "BundleItem.files")
        for file in self.files:
            utils.RelAssertType(file, BundleFile, "BundleItem.files.value")
            file.VerifyTypes()

    def VerifyValues(self) -> None:
        for file in self.files:
            file.VerifyValues()

    def Normalize(self) -> None:
        for file in self.files:
            file.Normalize()

    def ResolveWildcards(self) -> None:
        newFiles: list[BundleFile] = []
        curFile: BundleFile

        for curFile in self.files:
            if not os.path.isfile(curFile.absSourceFile) and "*" in curFile.absSourceFile:
                globFiles = glob(curFile.absSourceFile, recursive=True)
                utils.RelAssert(bool(globFiles), f"Wildcard '{curFile.absSourceFile}' matches nothing")

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
    namePrefix: str
    nameSuffix: str
    install: bool
    itemNames: list[str]

    def __init__(self):
        self.namePrefix = ""
        self.nameSuffix = ""
        self.install = False

    def VerifyTypes(self) -> None:
        utils.RelAssertType(self.name, str, "BundlePack.name")
        utils.RelAssertType(self.namePrefix, str, "BundlePack.namePrefix")
        utils.RelAssertType(self.nameSuffix, str, "BundlePack.nameSuffix")
        utils.RelAssertType(self.install, bool, "BundlePack.install")
        utils.RelAssertType(self.itemNames, list, "BundlePack.itemNames")
        for itemName in self.itemNames:
            utils.RelAssertType(itemName, str, "BundlePack.itemNames.value")


@dataclass(init=False)
class Bundles:
    items: list[BundleItem]
    packs: list[BundlePack]

    def __init__(self):
        pass

    def VerifyTypes(self) -> None:
        utils.RelAssertType(self.items, list, "Bundles.items")
        utils.RelAssertType(self.packs, list, "Bundles.packs")
        for item in self.items:
            utils.RelAssertType(item, BundleItem, "Bundles.items.value")
            item.VerifyTypes()
        for pack in self.packs:
            utils.RelAssertType(pack, BundlePack, "Bundles.packs.value")
            pack.VerifyTypes()

    def VerifyValues(self) -> None:
        for item in self.items:
            item.VerifyValues()
        self.__VerifyUniqueItemNames()
        self.__VerifyKnownItemsinPacks()

    def __VerifyUniqueItemNames(self) -> None:
        itemLen = len(self.items)
        for a in range(itemLen):
            for b in range(a + 1, itemLen):
                nameA: str = self.items[a].name
                nameB: str = self.items[b].name
                utils.RelAssert(nameA != nameB, f"Bundles.items has items with duplicate name '{nameA}'")

    def __VerifyKnownItemsinPacks(self) -> None:
        for pack in self.packs:
            for packItemName in pack.itemNames:
                found: bool = False
                for item in self.items:
                    if packItemName == item.name:
                        found = True
                        break
                utils.RelAssert(found, f"Bundles.packs with pack '{pack.name}' references unknown bundle item '{packItemName}'")

    def Normalize(self) -> None:
        for item in self.items:
            item.Normalize()

    def ResolveWildcards(self) -> None:
        for item in self.items:
            item.ResolveWildcards()


def __MakeBundleFilesFromDict(jFile: dict, jsonDir: str) -> list[BundleFile]:
    files: list[BundleFile] = list()

    parent = utils.JoinPathIfValid(jsonDir, jsonDir, jFile.get("parent"))
    params: ParamsT = jFile.get("params")
    if params == None:
        params = ParamsT()

    jSource: str = jFile.get("source")
    jSourceList: list = jFile.get("sourceList")
    jSourceTargetList: list = jFile.get("sourceTargetList")

    if jSource:
        bundleFile = BundleFile()
        bundleFile.absSourceFile = utils.JoinPathIfValid(None, parent, jSource)
        bundleFile.relTargetFile = utils.GetSecondIfValid(jSource, jFile.get("target"))
        bundleFile.params = params
        files.append(bundleFile)

    if jSourceList:
        jElement: str
        for jElement in jSourceList:
            bundleFile = BundleFile()
            bundleFile.absSourceFile = utils.JoinPathIfValid(None, parent, jElement)
            bundleFile.relTargetFile = jElement
            bundleFile.params = params
            files.append(bundleFile)

    if jSourceTargetList:
        jElement: dict[str, str]
        for jElement in jSourceTargetList:
            jElementSource: str = jElement.get("source")
            bundleFile = BundleFile()
            bundleFile.absSourceFile = utils.JoinPathIfValid(None, parent, jElementSource)
            bundleFile.relTargetFile = utils.GetSecondIfValid(jElementSource, jElement.get("target"))
            bundleFile.params = params
            files.append(bundleFile)

    return files


def __MakeBundleItemFromDict(jItem: dict, jsonDir: str) -> BundleItem:
    item = BundleItem()
    item.name = utils.GetSecondIfValid("Undefined", jItem.get("name"))
    item.isBig = utils.GetSecondIfValid(False, jItem.get("big"))
    item.files = list()

    jFiles = jItem.get("files")
    if jFiles:
        jFile: dict
        for jFile in jFiles:
            item.files.extend(__MakeBundleFilesFromDict(jFile, jsonDir))

    return item


def __MakeBundlePackFromDict(jPack: dict) -> BundlePack:
    pack = BundlePack()
    pack.name = jPack.get("name")
    pack.install = utils.GetSecondIfValid(pack.install, jPack.get("install"))
    pack.itemNames = jPack.get("itemNames")

    return pack


def MakeBundlesFromJsons(jsonFiles: list[JsonFile]) -> Bundles:
    bundles = Bundles()
    bundles.items = list()
    bundles.packs = list()

    for jsonFile in jsonFiles:
        jsonDir: str = utils.GetFileDir(jsonFile.path)
        jBundles: dict = jsonFile.data.get("bundles")

        if jBundles:
            jItemsPrefix: str = jBundles.get("itemsPrefix")
            jItemsSuffix: str = jBundles.get("itemsSuffix")
            jItems: dict = jBundles.get("items")

            if jItems:
                jItem: dict
                for jItem in jItems:
                    bundleItem: BundleItem = __MakeBundleItemFromDict(jItem, jsonDir)
                    bundleItem.namePrefix = utils.GetSecondIfValid(bundleItem.namePrefix, jItemsPrefix)
                    bundleItem.nameSuffix = utils.GetSecondIfValid(bundleItem.nameSuffix, jItemsSuffix)
                    bundles.items.append(bundleItem)

            jPacksPrefix: str = jBundles.get("packsPrefix")
            jPacksSuffix: str = jBundles.get("packsSuffix")
            jPacks: dict = jBundles.get("packs")
            if jPacks:
                jPack: dict
                for jPack in jPacks:
                    bundlePack: BundlePack = __MakeBundlePackFromDict(jPack)
                    bundlePack.namePrefix = utils.GetSecondIfValid(bundlePack.namePrefix, jPacksPrefix)
                    bundlePack.nameSuffix = utils.GetSecondIfValid(bundlePack.nameSuffix, jPacksSuffix)
                    bundles.packs.append(bundlePack)

    bundles.VerifyTypes()
    bundles.Normalize()
    bundles.ResolveWildcards()
    bundles.VerifyValues()

    return bundles
