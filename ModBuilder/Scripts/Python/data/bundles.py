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
        utils.RelAssert(isinstance(self.absSourceFile, str), "BundleFile.absSourceFile has incorrect type")
        utils.RelAssert(isinstance(self.relTargetFile, str), "BundleFile.relTargetFile has incorrect type")
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
        utils.RelAssert(isinstance(self.name, str), "BundleItem.name has incorrect type")
        utils.RelAssert(isinstance(self.namePrefix, str), "BundleItem.namePrefix has incorrect type")
        utils.RelAssert(isinstance(self.nameSuffix, str), "BundleItem.nameSuffix has incorrect type")
        utils.RelAssert(isinstance(self.isBig, bool), "BundleItem.isBig has incorrect type")
        utils.RelAssert(isinstance(self.files, list), "BundleItem.files has incorrect type")
        for file in self.files:
            utils.RelAssert(isinstance(file, BundleFile), "BundleItem.files has incorrect type")
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
        utils.RelAssert(isinstance(self.name, str), "BundlePack.name has incorrect type")
        utils.RelAssert(isinstance(self.namePrefix, str), "BundlePack.namePrefix has incorrect type")
        utils.RelAssert(isinstance(self.nameSuffix, str), "BundlePack.nameSuffix has incorrect type")
        utils.RelAssert(isinstance(self.install, bool), "BundlePack.install has incorrect type")
        utils.RelAssert(isinstance(self.itemNames, list), "BundlePack.itemNames has incorrect type")
        for itemName in self.itemNames:
            utils.RelAssert(isinstance(itemName, str), "BundlePack.itemNames has incorrect type")


@dataclass(init=False)
class Bundles:
    items: list[BundleItem]
    packs: list[BundlePack]

    def __init__(self):
        pass

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.items, list), "Bundles.items has incorrect type")
        utils.RelAssert(isinstance(self.packs, list), "Bundles.packs has incorrect type")
        for item in self.items:
            utils.RelAssert(isinstance(item, BundleItem), "Bundles.items has incorrect type")
            item.VerifyTypes()
        for pack in self.packs:
            utils.RelAssert(isinstance(pack, BundlePack), "Bundles.packs has incorrect type")
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

    source = jFile.get("source")
    if source:
        bundleFile = BundleFile()
        bundleFile.absSourceFile = os.path.join(parent, source)
        bundleFile.relTargetFile = utils.GetSecondIfValid(source, jFile.get("target"))
        bundleFile.params = params
        files.append(bundleFile)

    sourceList = jFile.get("sourceList")
    if sourceList:
        element: str
        for element in sourceList:
            bundleFile = BundleFile()
            bundleFile.absSourceFile = os.path.join(parent, element)
            bundleFile.relTargetFile = element
            bundleFile.params = params
            files.append(bundleFile)

    sourceTargetList = jFile.get("sourceTargetList")
    if sourceTargetList:
        element: list[str]
        for element in sourceTargetList:
            source2: str = element.get("source")
            bundleFile = BundleFile()
            bundleFile.absSourceFile = os.path.join(parent, source2)
            bundleFile.relTargetFile = utils.GetSecondIfValid(source2, element.get("target"))
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
            itemsPrefix: str = jBundles.get("itemsPrefix")
            itemsSuffix: str = jBundles.get("itemsSuffix")
            jItems: dict = jBundles.get("items")

            if jItems:
                jItem: dict
                for jItem in jItems:
                    bundleItem: BundleItem = __MakeBundleItemFromDict(jItem, jsonDir)
                    bundleItem.namePrefix = utils.GetSecondIfValid(bundleItem.namePrefix, itemsPrefix)
                    bundleItem.nameSuffix = utils.GetSecondIfValid(bundleItem.nameSuffix, itemsSuffix)
                    bundles.items.append(bundleItem)

            packsPrefix: str = jBundles.get("packsPrefix")
            packsSuffix: str = jBundles.get("packsSuffix")
            jPacks: dict = jBundles.get("packs")
            if jPacks:
                jPack: dict
                for jPack in jPacks:
                    bundlePack: BundlePack = __MakeBundlePackFromDict(jPack)
                    bundlePack.namePrefix = utils.GetSecondIfValid(bundlePack.namePrefix, packsPrefix)
                    bundlePack.nameSuffix = utils.GetSecondIfValid(bundlePack.nameSuffix, packsSuffix)
                    bundles.packs.append(bundlePack)

    bundles.VerifyTypes()
    bundles.Normalize()
    bundles.ResolveWildcards()
    bundles.VerifyValues()

    return bundles
