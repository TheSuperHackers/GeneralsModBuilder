import os
from glob import glob
from generalsmodbuilder.build.engine import BuildEngine
from generalsmodbuilder.build.filehashregistry import FileHashRegistry
from generalsmodbuilder.build.setup import BuildStep, BuildSetup
from generalsmodbuilder.changelog.generator import FilterChangeLog, GenerateChangeLogDocuments, SortChangeList
from generalsmodbuilder.changelog.parser import ChangeLog, MakeChangelogFromChangeConfig
from generalsmodbuilder.data.buildfiles import BuildFiles, MakeBuildFilesFromJsons
from generalsmodbuilder.data.bundles import Bundles, BundlePack, MakeBundlesFromJsons
from generalsmodbuilder.data.changeconfig import ChangeConfig, MakeChangeConfigFromJsons
from generalsmodbuilder.data.folders import Folders, MakeFoldersFromJsons
from generalsmodbuilder.data.runner import Runner, MakeRunnerFromJsons
from generalsmodbuilder.data.tools import ToolsT, MakeToolsFromJsons, InstallTools
from generalsmodbuilder.util import JsonFile
from generalsmodbuilder import util


def CreateJsonFileList(configPaths: list[str]) -> list[JsonFile]:
    """
    Reads the given configuration files and every json file that they pull in through
    their build section, to any depth. A file that several of them list, or that is
    reached again through a cycle, is read once, so that including it twice does not
    build its bundle items twice.

    The files that were given keep their order and come first, because a later file
    overrides an earlier one and prefixes carry over from one file to the next.
    """
    jsonFiles: list[JsonFile] = []
    readPaths: set[str] = set()
    pendingPaths: list[str] = [path for path in configPaths if util.HasFileExt(path, "json")]

    while pendingPaths:
        path: str = pendingPaths.pop(0)

        # Identifies the file itself, so that two paths that reach it name it once.
        readPath: str = os.path.normcase(os.path.realpath(path))
        if readPath in readPaths:
            continue
        readPaths.add(readPath)

        jsonFile = JsonFile(path)
        jsonFiles.append(jsonFile)

        buildFiles: BuildFiles = MakeBuildFilesFromJsons([jsonFile])
        pendingPaths.extend(buildFiles.absFiles)

    return jsonFiles


def CreateBuildStep(clean: bool, build: bool, release: bool, install: bool, uninstall: bool, run: bool) -> BuildStep:
    buildStep = BuildStep.Zero
    if clean:
        buildStep |= BuildStep.Clean
    if build:
        buildStep |= BuildStep.Build
    if release:
        buildStep |= BuildStep.Release
    if install:
        buildStep |= BuildStep.Install
    if uninstall:
        buildStep |= BuildStep.Uninstall
    if run:
        buildStep |= BuildStep.Run

    return buildStep


def PatchBundlesInstall(bundles: Bundles, installList: list[str]) -> None:
    pack: BundlePack
    for pack in bundles.packs:
        if pack.name in installList:
            pack.allowInstall = True


def PatchBundlesBuild(bundles: Bundles, buildList: list[str]) -> None:
    pack: BundlePack
    for pack in bundles.packs:
        if pack.name in buildList:
            pack.allowBuild = True


def RunWithConfig(
        configPaths: list[str]=list[str](),
        installList: list[str]=list[str](),
        buildList: list[str]=list[str](),
        makeChangeLog: bool=False,
        clean: bool=False,
        build: bool=False,
        release: bool=False,
        install: bool=False,
        uninstall: bool=False,
        run: bool=False,
        printConfig: bool=False,
        verboseLogging: bool=False,
        multiProcessing: bool=False,
        toolsRootDir: str=None,
        engine: BuildEngine=None) -> None:

    timer = util.Timer()
    print("Run Build Job ...")

    util.ResetFileHashCount()

    jsonFiles: list[JsonFile] = CreateJsonFileList(configPaths)
    buildStep: BuildStep = CreateBuildStep(clean, build, release, install, uninstall, run)

    if makeChangeLog:
        changeConfig: ChangeConfig = MakeChangeConfigFromJsons(jsonFiles)
        changeLog: ChangeLog = MakeChangelogFromChangeConfig(changeConfig)
        changeLog = FilterChangeLog(changeLog)
        changeLog = SortChangeList(changeLog)
        GenerateChangeLogDocuments(changeLog)

    if buildStep != BuildStep.Zero:
        folders: Folders = MakeFoldersFromJsons(jsonFiles)
        runner: Runner = MakeRunnerFromJsons(jsonFiles) if (install or uninstall or run) else Runner()
        bundles: Bundles = MakeBundlesFromJsons(jsonFiles)
        tools: ToolsT = MakeToolsFromJsons(jsonFiles, rootDir=toolsRootDir)

        InstallTools(tools)

        if not bool(installList) and not bundles.HasPackToInstall():
            for pack in bundles.packs:
                pack.allowInstall = True
        else:
            PatchBundlesInstall(bundles, installList)

        if not bool(buildList) and not bundles.HasPackToBuild():
            for pack in bundles.packs:
                pack.allowBuild = True
        else:
            PatchBundlesBuild(bundles, buildList)

        setup = BuildSetup(
            step=buildStep,
            folders=folders,
            runner=runner,
            bundles=bundles,
            tools=tools,
            printConfig=printConfig,
            verboseLogging=verboseLogging,
            multiProcessing=multiProcessing)

        if engine == None:
            with BuildEngine() as engine:
                engine.Run(setup)
        else:
            engine.Run(setup)

    if timer.GetElapsedSeconds() > util.PERFORMANCE_TIMER_THRESHOLD:
        print(f"Build Job completed in {timer.GetElapsedSecondsString()} s")


def BuildFileHashRegistry(inputPaths: list[str], outputPath: str, outputName: str) -> None:
    registry = FileHashRegistry()
    registry.lowerPath = False

    for inputPath in inputPaths:
        cleanInputPath: str = inputPath.split("*", 1)[0]
        cleanInputPath = os.path.normpath(cleanInputPath)
        inputFiles: list[str] = glob(inputPath, recursive=True)
        for inputFile in inputFiles:
            relFile = inputFile.removeprefix(cleanInputPath)
            relFile = relFile.removeprefix("/")
            relFile = relFile.removeprefix("\\")
            registry.AddFile(
                relFile=relFile,
                size=util.GetFileSize(inputFile),
                md5=util.GetFileMd5(inputFile),
                sha256=util.GetFileSha256(inputFile))

    registry.SaveRegistry(outputPath, outputName)
