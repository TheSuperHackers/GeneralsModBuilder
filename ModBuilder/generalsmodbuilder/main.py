import argparse
import util
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
from util import JsonFile
from __version__ import __version__


def __CreateJsonFiles(configPaths: list[str]) -> list[JsonFile]:
    jsonFiles: list[JsonFile] = []
    for configPath in configPaths:
        if (util.HasFileExt(configPath, "json")):
            jsonFiles.append(JsonFile(configPath))

    return jsonFiles


def __CreateBuildStep(build: bool, release: bool, install: bool, uninstall: bool, run: bool) -> BuildStep:
    buildStep = BuildStep.Zero
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


def RunWithConfig(configPaths: list[str],
        build: bool=False,
        release: bool=False,
        install: bool=False,
        uninstall: bool=False,
        run: bool=False,
        printConfig: bool=False) -> None:

    jsonFiles: list[JsonFile] = __CreateJsonFiles(configPaths)
    buildStep: BuildStep = __CreateBuildStep(build, release, install, uninstall, run)

    folders: Folders = data.folders.MakeFoldersFromJsons(jsonFiles)
    runner: Runner = data.runner.MakeRunnerFromJsons(jsonFiles)
    bundles: Bundles = data.bundles.MakeBundlesFromJsons(jsonFiles)
    tools: ToolsT = data.tools.MakeToolsFromJsons(jsonFiles)

    setup = BuildSetup(
        step=buildStep,
        folders=folders,
        runner=runner,
        bundles=bundles,
        tools=tools,
        printConfig=printConfig)

    engine = BuildEngine()
    engine.Run(setup)


def Main(args=None):
    print(f"Generals Mod Builder v{__version__} by The Super Hackers")

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, action="append", help='Path to a configuration file (json). Multiples can be specified.')
    parser.add_argument('-l', '--config-list', type=str, nargs="*", help='Paths to any amount of configuration files (json).')
    parser.add_argument('-b', '--build', action='store_true')
    parser.add_argument('-z', '--release', action='store_true')
    parser.add_argument('-i', '--install', action='store_true')
    parser.add_argument('-u', '--uninstall', action='store_true')
    parser.add_argument('-r', '--run', action='store_true')
    parser.add_argument('--print-config', action='store_true')

    args, unknownargs = parser.parse_known_args(args=args)
    util.pprint(args)

    thisDir = util.GetAbsFileDir(__file__)
    configPaths: list[str] = []

    # Add default configurations first to list so readers can parse them first.
    configPaths.append(os.path.join(thisDir, "config", "DefaultRunner.json"))
    configPaths.append(os.path.join(thisDir, "config", "DefaultTools.json"))

    # Add custom configurations last so readers can write over default configurations last.
    if args.config_list:
        configPaths.extend(args.config_list)
    if args.config:
        configPaths.extend(args.config)

    for i in range(len(configPaths)):
        configPaths[i] = os.path.abspath(configPaths[i])

    RunWithConfig(
        configPaths=configPaths,
        build=bool(args.build),
        release=bool(args.release),
        install=bool(args.install),
        uninstall=bool(args.uninstall),
        run=bool(args.run),
        printConfig=bool(args.print_config))


if __name__ == "__main__":
    Main()