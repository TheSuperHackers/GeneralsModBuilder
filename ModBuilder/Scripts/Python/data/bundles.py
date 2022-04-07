import copy
import utils
import os.path
from typing import Any, Union
from glob import glob
from dataclasses import dataclass
from utils import JsonFile


ParamsT = dict[str, Union[str, int, float, bool, list[Union[str, int, float, bool]]]]


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
        utils.RelAssert(isinstance(self.params, dict), "BundleFile.params has incorrect type")
        
        for key,value in self.params.items():
            utils.RelAssert(isinstance(key, str), "BundleFile.params has incorrect type")
            utils.RelAssert(isinstance(value, str) or
                isinstance(value, int) or
                isinstance(value, float) or
                isinstance(value, bool) or
                isinstance(value, list), "BundleFile.params has incorrect type")

            if isinstance(value, list):
                for subValue in value:
                    utils.RelAssert(
                        isinstance(subValue, str) or
                        isinstance(subValue, int) or
                        isinstance(subValue, float) or
                        isinstance(subValue, bool), "BundleFile.params has incorrect type")

    def VerifyValues(self) -> None:
        utils.RelAssert(os.path.isabs(self.absSourceFile), "BundleFile.absSourceFile is not an absolute path")
        utils.RelAssert(not os.path.isabs(self.relTargetFile), "BundleFile.absSourceFile is not a relative path")

    def Normalize(self) -> None:
        self.absSourceFile = utils.NormalizePath(self.absSourceFile)
        self.relTargetFile = utils.NormalizePath(self.relTargetFile)


@dataclass(init=False)
class BundleItem:
    name: str
    isBig: bool
    files: list[BundleFile]

    def __init__(self):
        self.isBig = True

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.name, str), "BundleItem.name has incorrect type")
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
        file: BundleFile

        for file in self.files:
            if not os.path.isfile(file.absSourceFile):
                globFiles = glob(file.absSourceFile, recursive=True)
                utils.RelAssert(bool(globFiles), f"BundleItem.absSourceFile '{file.absSourceFile}' matches nothing")
                for globFile in globFiles:
                    utils.RelAssert(os.path.isfile(globFile), f"BundleItem file '{globFile}' is not a file")
                    newFile: BundleFile = copy.copy(file)
                    newFile.absSourceFile = globFile
                    newFiles.append(newFile)
            else:
                newFiles.append(file)

        for file in newFiles:
            file.relTargetFile = BundleItem.__ResolveTargetWildcard(file.absSourceFile, file.relTargetFile)

        self.files = newFiles
        return newFiles

    @staticmethod
    def __ResolveTargetWildcard(source: str, target: str) -> str:
        if utils.IsPathSyntax(target):
            sourcePath, sourceFile = os.path.split(source)
            newTarget = os.path.join(target, sourceFile)
            return newTarget
        else:
            sourcePath, sourceFile = os.path.split(source)
            targetPath, targetFile = os.path.split(target)
            sourceName, sourceExtn = os.path.splitext(sourceFile)
            targetName, targetExtn = os.path.splitext(targetFile)
            newName = sourceName if targetName == "*" else targetName
            newExtn = sourceExtn if targetExtn == ".*" else targetExtn
            newTarget = os.path.join(targetPath, newName + newExtn)
            return newTarget


@dataclass(init=False)
class BundlePack:
    name: str
    namePrefix: str
    nameSuffix: str
    runDefault: bool
    itemNames: list[str]

    def __init__(self):
        self.namePrefix = ""
        self.nameSuffix = ""
        self.runDefault = False

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.name, str), "BundlePack.name has incorrect type")
        utils.RelAssert(isinstance(self.namePrefix, str), "BundlePack.namePrefix has incorrect type")
        utils.RelAssert(isinstance(self.nameSuffix, str), "BundlePack.nameSuffix has incorrect type")
        utils.RelAssert(isinstance(self.runDefault, bool), "BundlePack.runDefault has incorrect type")
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
            bundleFile = BundleFile()
            bundleFile.absSourceFile = os.path.join(parent, element[0])
            bundleFile.relTargetFile = element[1]
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
    pack.runDefault = utils.GetSecondIfValid(pack.runDefault, jPack.get("runDefault"))
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
            jItems: dict = jBundles.get("items")
            if jItems:
                jItem: dict
                for jItem in jItems:
                    bundleItem: BundleItem = __MakeBundleItemFromDict(jItem, jsonDir)
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
    bundles.ResolveWildcards()
    bundles.Normalize()
    bundles.VerifyValues()

    return bundles
