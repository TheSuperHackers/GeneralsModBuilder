import argparse
import utils
import os
import data.folders
import data.runner
import data.bundles
import data.tools
from build.engine import BuildEngine
from build.setup import BuildStep
from build.setup import BuildSetup
from data.bundles import Bundles
from data.folders import Folders
from data.runner import Runner
from data.tools import ToolsT
from utils import JsonFile


def __CreateJsonFiles(configPaths: list[str]) -> list[JsonFile]:
    jsonFiles: list[JsonFile] = []
    for configPath in configPaths:
        if (utils.HasFileExt(configPath, "json")):
            jsonFiles.append(JsonFile(configPath))

    return jsonFiles


def __CreateBuildStep(build: bool, release: bool, install: bool, uninstall: bool, run: bool) -> BuildStep:
    buildStep = BuildStep.NONE
    if build:
        buildStep |= BuildStep.BUILD
    if release:
        buildStep |= BuildStep.RELEASE
    if install:
        buildStep |= BuildStep.INSTALL
    if uninstall:
        buildStep |= BuildStep.UNINSTALL
    if run:
        buildStep |= BuildStep.RUN

    return buildStep


def RunWithConfig(configPaths: list[str],
        build: bool=False,
        release: bool=False,
        install: bool=False,
        uninstall: bool=False,
        run: bool=False) -> None:

    jsonFiles: list[JsonFile] = __CreateJsonFiles(configPaths)
    buildStep: BuildStep = __CreateBuildStep(build, release, install, uninstall, run)

    folders: Folders = data.folders.MakeFoldersFromJsons(jsonFiles)
    runner: Runner = data.runner.MakeRunnerFromJsons(jsonFiles)
    bundles: Bundles = data.bundles.MakeBundlesFromJsons(jsonFiles)
    tools: ToolsT = data.tools.MakeToolsFromJsons(jsonFiles)

    setup = BuildSetup(step=buildStep, folders=folders, runner=runner, bundles=bundles, tools=tools)

    engine = BuildEngine()
    engine.Run(setup)


def Main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--mod-config', type=str, action="append", help='Path to a configuration file (json). Multiples can be specified.')
    parser.add_argument('-b', '--mod-build', action='store_true')
    parser.add_argument('-rel', '--mod-release', action='store_true')
    parser.add_argument('-i', '--mod-install', action='store_true')
    parser.add_argument('-u', '--mod-uninstall', action='store_true')
    parser.add_argument('-run', '--mod-run', action='store_true')

    args, unknownargs = parser.parse_known_args(args=args)
    utils.pprint(args)

    thisDir = utils.GetFileDir(__file__)
    configPaths: list[str] = []

    # Add default configurations first to list so readers can parse them first.
    configPath: str = os.path.join(thisDir, "..", "..")
    configPaths.append(os.path.join(configPath, "DefaultRunner.json"))
    configPaths.append(os.path.join(configPath, "DefaultTools.json"))

    # Add custom configurations last so readers can write over default configurations last.
    if args.mod_config:
        configPaths.extend(args.mod_config)

    RunWithConfig(
        configPaths=configPaths,
        build=bool(args.mod_build),
        release=bool(args.mod_release),
        install=bool(args.mod_install),
        uninstall=bool(args.mod_uninstall),
        run=bool(args.mod_run))


if __name__ == "__main__":
    Main()
