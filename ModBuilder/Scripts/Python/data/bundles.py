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

    def Normalize(self) -> None:
        self.absSourceFile = utils.NormalizePath(self.absSourceFile)
        self.relTargetFile = utils.NormalizePath(self.relTargetFile)

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.absSourceFile, str), "BundleFile.absSourceFile has incorrect type")
        utils.RelAssert(isinstance(self.relTargetFile, str), "BundleFile.relTargetFile has incorrect type")
        utils.RelAssert(isinstance(self.language, str), "BundleFile.language has incorrect type")
        utils.RelAssert(isinstance(self.rescale, float), "BundleFile.rescale has incorrect type")
        
    def VerifyValues(self) -> None:
        utils.RelAssert(os.path.isabs(self.absSourceFile), "BundleFile.absSourceFile is not an absolute path")
        utils.RelAssert(not os.path.isabs(self.relTargetFile), "BundleFile.absSourceFile is not a relative path")

    def GetSourceExt(self) -> str:
        path, ext = os.path.splitext(self.absSourceFile)
        return ext

    def GetTargetExt(self) -> str:
        path, ext = os.path.splitext(self.relTargetFile)
        return ext


@dataclass(init=False)
class Bundle:
    name: str
    isBig: bool = True
    files: list[BundleFile]

    def __init__(self):
        pass

    def Normalize(self) -> None:
        for file in self.files:
            file.Normalize()

    def VerifyTypes(self) -> None:
        utils.RelAssert(isinstance(self.name, str), "Bundle.name has incorrect type")
        utils.RelAssert(isinstance(self.isBig, bool), "Bundle.isBig has incorrect type")
        utils.RelAssert(isinstance(self.files, list), "Bundle.files has incorrect type")
        for file in self.files:
            utils.RelAssert(isinstance(file, BundleFile), "Bundle.files has incorrect type")
            file.VerifyTypes()

    def VerifyValues(self) -> None:
        for file in self.files:
            file.VerifyValues()

    def ResolveWildcards(self) -> None:
        newFiles: list[BundleFile] = []
        file: BundleFile

        for file in self.files:
            if not os.path.isfile(file.absSourceFile):
                globFiles = glob.glob(file.absSourceFile)
                utils.RelAssert(bool(globFiles), f"Bundle file '{file.absSourceFile}' matches nothing")
                for globFile in globFiles:
                    utils.RelAssert(os.path.isfile(globFile), f"Bundle file '{globFile}' is not a file")
                    newFile: BundleFile = copy.copy(file)
                    newFile.absSourceFile = globFile
                    newFiles.append(newFile)
            else:
                newFiles.append(file)

        for file in newFiles:
            file.relTargetFile = Bundle.__ResolveTargetWildcard(file.absSourceFile, file.relTargetFile)

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


def MakeBundlesFromJsons(jsonFiles: list[JsonFile]) -> list[Bundle]:
    bundles = list()
    bundle: Bundle

    for jsonFile in jsonFiles:
        jsonDir: str = utils.GetFileDir(jsonFile.path)
        jBundles: dict = jsonFile.data.get("bundles")
        jBundle: dict
        jFile: dict

        if not jBundles:
            continue

        jList: dict = jBundles.get("list")

        if not jList:
            continue

        for jBundle in jList:
            bundle = Bundle()
            bundle.name = utils.GetSecondIfValid("Undefined", jBundle.get("name"))
            bundle.isBig = utils.GetSecondIfValid(False, jBundle.get("big"))
            bundle.files = []
            jFiles = jBundle.get("files")

            if jFiles:
                for jFile in jFiles:
                    parent = utils.JoinPathIfValid(jsonDir, jsonDir, jFile.get("parent"))
                    language = jFile.get("language")
                    rescale = jFile.get("rescale")
                    if type(rescale) is int:
                        rescale = float(rescale)

                    source = jFile.get("source")
                    if source:
                        bundleFile = BundleFile()
                        bundleFile.absSourceFile = os.path.join(parent, source)
                        bundleFile.relTargetFile = utils.GetSecondIfValid(source, jFile.get("target"))
                        bundleFile.language = utils.GetSecondIfValid(bundleFile.language, language)
                        bundleFile.rescale = utils.GetSecondIfValid(bundleFile.rescale, rescale)
                        bundle.files.append(bundleFile)

                    sourceList = jFile.get("sourceList")
                    if sourceList:
                        for item in sourceList:
                            bundleFile = BundleFile()
                            bundleFile.absSourceFile = os.path.join(parent, item)
                            bundleFile.relTargetFile = item
                            bundleFile.language = utils.GetSecondIfValid(bundleFile.language, language)
                            bundleFile.rescale = utils.GetSecondIfValid(bundleFile.rescale, rescale)
                            bundle.files.append(bundleFile)

                    sourceTargetList = jFile.get("sourceTargetList")
                    if sourceTargetList:
                        for item in sourceTargetList:
                            bundleFile = BundleFile()
                            bundleFile.absSourceFile = os.path.join(parent, item[0])
                            bundleFile.relTargetFile = item[1]
                            bundleFile.language = utils.GetSecondIfValid(bundleFile.language, language)
                            bundleFile.rescale = utils.GetSecondIfValid(bundleFile.rescale, rescale)
                            bundle.files.append(bundleFile)

            bundles.append(bundle)
   
    for bundle in bundles:
        bundle.VerifyTypes()
        bundle.ResolveWildcards()
        bundle.Normalize()
        bundle.VerifyValues()

    return bundles
