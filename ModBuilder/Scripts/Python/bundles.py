import utils
from os.path import join as joinpath
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

    def Validate(self) -> None:
        utils.RelAssert(isinstance(self.absSourceFile, str), "source has incorrect type")
        utils.RelAssert(isinstance(self.relTargetFile, str), "target has incorrect type")
        utils.RelAssert(isinstance(self.language, str), "language has incorrect type")
        utils.RelAssert(isinstance(self.rescale, float), "rescale has incorrect type")


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

    def Validate(self) -> None:
        utils.RelAssert(isinstance(self.name, str), "name has incorrect type")
        utils.RelAssert(isinstance(self.isBig, bool), "big has incorrect type")
        utils.RelAssert(isinstance(self.files, list), "files has incorrect type")
        for file in self.files:
            utils.RelAssert(isinstance(file, BundleFile), "files has incorrect type")
            file.Validate()


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
                        bundleFile.absSourceFile = joinpath(parent, source)
                        bundleFile.relTargetFile = utils.GetSecondIfValid(source, jFile.get("target"))
                        bundleFile.language = utils.GetSecondIfValid(bundleFile.language, language)
                        bundleFile.rescale = utils.GetSecondIfValid(bundleFile.rescale, rescale)
                        bundle.files.append(bundleFile)

                    sourceList = jFile.get("sourceList")
                    if sourceList:
                        for item in sourceList:
                            bundleFile = BundleFile()
                            bundleFile.absSourceFile = joinpath(parent, item)
                            bundleFile.relTargetFile = item
                            bundleFile.language = utils.GetSecondIfValid(bundleFile.language, language)
                            bundleFile.rescale = utils.GetSecondIfValid(bundleFile.rescale, rescale)
                            bundle.files.append(bundleFile)

                    sourceTargetList = jFile.get("sourceTargetList")
                    if sourceTargetList:
                        for item in sourceTargetList:
                            bundleFile = BundleFile()
                            bundleFile.absSourceFile = joinpath(parent, item[0])
                            bundleFile.relTargetFile = item[1]
                            bundleFile.language = utils.GetSecondIfValid(bundleFile.language, language)
                            bundleFile.rescale = utils.GetSecondIfValid(bundleFile.rescale, rescale)
                            bundle.files.append(bundleFile)

            bundles.append(bundle)
   
    for bundle in bundles:
        bundle.Validate()
        bundle.Normalize()
        print("Created", bundle)

    return bundles
