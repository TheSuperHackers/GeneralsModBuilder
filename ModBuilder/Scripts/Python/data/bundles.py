import copy
import utils
import os.path
import glob
from utils import JsonFile
from dataclasses import dataclass


@dataclass(init=False)
class BundleFile:
    absSourceFile: str
    relTargetFile: str
    language: str = ""
    rescale: float = 1.0

    def __init__(self):
        pass

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.absSourceFile, str), "BundleFile.absSourceFile has incorrect type")
        utils.RelAssert(isinstance(self.relTargetFile, str), "BundleFile.relTargetFile has incorrect type")
        utils.RelAssert(isinstance(self.language, str), "BundleFile.language has incorrect type")
        utils.RelAssert(isinstance(self.rescale, float), "BundleFile.rescale has incorrect type")

    def VerifyValues(self) -> None:
        utils.RelAssert(os.path.isabs(self.absSourceFile), "BundleFile.absSourceFile is not an absolute path")
        utils.RelAssert(not os.path.isabs(self.relTargetFile), "BundleFile.absSourceFile is not a relative path")

    def Normalize(self) -> None:
        self.absSourceFile = utils.NormalizePath(self.absSourceFile)
        self.relTargetFile = utils.NormalizePath(self.relTargetFile)


@dataclass(init=False)
class BundleItem:
    name: str
    isBig: bool = True
    files: list[BundleFile]

    def __init__(self):
        pass


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
                globFiles = glob.glob(file.absSourceFile)
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
class BundleContainer:
    name: str
    namePrefix: str = ""
    nameSuffix: str = ""
    items: list[BundleItem]

    def __init__(self):
        pass

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.name, str), "BundleContainer.name has incorrect type")
        utils.RelAssert(isinstance(self.namePrefix, str), "BundleContainer.namePrefix has incorrect type")
        utils.RelAssert(isinstance(self.nameSuffix, str), "BundleContainer.nameSuffix has incorrect type")
        for item in self.items:
            utils.RelAssert(isinstance(item, BundleItem), "BundleContainer.items has incorrect type")
            item.VerifyTypes()

    def VerifyValues(self) -> None:
        for item in self.items:
            item.VerifyValues()

    def Normalize(self) -> None:
        for item in self.items:
            item.Normalize()

    def ResolveWildcards(self) -> None:
        for item in self.items:
            item.ResolveWildcards()


def MakeBundlesFromJsons(jsonFiles: list[JsonFile]) -> list[BundleContainer]:
    containers = list()
    
    for jsonFile in jsonFiles:
        jsonDir: str = utils.GetFileDir(jsonFile.path)
        jBundles: dict = jsonFile.data.get("bundles")
        jBundleContainer: dict
        jBundleItem: dict
        jBundleFile: dict

        if not jBundles:
            continue

        containersPrefix: str = jBundles.get("containersPrefix")
        containersSuffix: str = jBundles.get("containersSuffix")
        jBundleContainers: dict = jBundles.get("containers")

        if not jBundleContainers:
            continue

        for jBundleContainer in jBundleContainers:
            container = BundleContainer()
            container.name = jBundleContainer.get("name")
            container.namePrefix = utils.GetSecondIfValid(container.namePrefix, containersPrefix)
            container.nameSuffix = utils.GetSecondIfValid(container.nameSuffix, containersSuffix)
            container.items = list()

            jBundleItems: dict = jBundleContainer.get("items")

            if not jBundleItems:
                continue

            for jBundleItem in jBundleItems:
                item = BundleItem()
                item.name = utils.GetSecondIfValid("Undefined", jBundleItem.get("name"))
                item.isBig = utils.GetSecondIfValid(False, jBundleItem.get("big"))
                item.files = []
                jFiles = jBundleItem.get("files")

                if jFiles:
                    for jBundleFile in jFiles:
                        parent = utils.JoinPathIfValid(jsonDir, jsonDir, jBundleFile.get("parent"))
                        language = jBundleFile.get("language")
                        rescale = jBundleFile.get("rescale")
                        if type(rescale) is int:
                            rescale = float(rescale)

                        source = jBundleFile.get("source")
                        if source:
                            bundleFile = BundleFile()
                            bundleFile.absSourceFile = os.path.join(parent, source)
                            bundleFile.relTargetFile = utils.GetSecondIfValid(source, jBundleFile.get("target"))
                            bundleFile.language = utils.GetSecondIfValid(bundleFile.language, language)
                            bundleFile.rescale = utils.GetSecondIfValid(bundleFile.rescale, rescale)
                            item.files.append(bundleFile)

                        sourceList = jBundleFile.get("sourceList")
                        if sourceList:
                            for element in sourceList:
                                bundleFile = BundleFile()
                                bundleFile.absSourceFile = os.path.join(parent, element)
                                bundleFile.relTargetFile = element
                                bundleFile.language = utils.GetSecondIfValid(bundleFile.language, language)
                                bundleFile.rescale = utils.GetSecondIfValid(bundleFile.rescale, rescale)
                                item.files.append(bundleFile)

                        sourceTargetList = jBundleFile.get("sourceTargetList")
                        if sourceTargetList:
                            for element in sourceTargetList:
                                bundleFile = BundleFile()
                                bundleFile.absSourceFile = os.path.join(parent, element[0])
                                bundleFile.relTargetFile = element[1]
                                bundleFile.language = utils.GetSecondIfValid(bundleFile.language, language)
                                bundleFile.rescale = utils.GetSecondIfValid(bundleFile.rescale, rescale)
                                item.files.append(bundleFile)

                container.items.append(item)

            containers.append(container)
   
    container: BundleContainer
    for container in containers:
        container.VerifyTypes()
        container.ResolveWildcards()
        container.Normalize()
        container.VerifyValues()

    return containers
