import sys
import argparse
import data.bundles
import data.folders
import data.runner
import data.tools
import utils
import os
from build.engine import BuildStep
from build.engine import BuildSetup
from build.engine import BuildEngine
from utils import JsonFile


def __CreateJsonFiles(configPaths: list[str]) -> list[JsonFile]:
    jsonFiles: list[JsonFile] = []
    for configPath in configPaths:
        if (utils.HasFileExt(configPath, "json")):
            jsonFiles.append(JsonFile(configPath))

    return jsonFiles


def __Initialize(buildType: BuildStep, configPaths: list[str]) -> None:
    jsonFiles = __CreateJsonFiles(configPaths)

    folders = data.folders.MakeFoldersFromJsons(jsonFiles)
    runner = data.runner.MakeRunnerFromJsons(jsonFiles)
    bundles = data.bundles.MakeBundlesFromJsons(jsonFiles)
    tools = data.tools.MakeToolsFromJsons(jsonFiles)

    setup = BuildSetup(step=buildType, folders=folders, runner=runner, bundles=bundles, tools=tools)

    engine = BuildEngine()
    engine.Run(setup)


def Main(args=None):
    utils.RelAssert(sys.version_info >= (3,10), f"Python version must be 3.10 or higher")

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
    configPaths.append(os.path.join(configPath, "DefaultFolders.json"))
    configPaths.append(os.path.join(configPath, "DefaultRunner.json"))
    configPaths.append(os.path.join(configPath, "DefaultTools.json"))

    # Add custom configurations last so readers can write over default configurations last.
    if args.mod_config:
        configPaths.extend(args.mod_config)

    buildType = BuildStep.NONE
    if args.mod_build:
        buildType |= BuildStep.BUILD
    if args.mod_release:
        buildType |= BuildStep.RELEASE
    if args.mod_install:
        buildType |= BuildStep.INSTALL
    if args.mod_uninstall:
        buildType |= BuildStep.UNINSTALL
    if args.mod_run:
        buildType |= BuildStep.RUN

    __Initialize(buildType=buildType, configPaths=configPaths)


if __name__ == "__main__":
    print(sys.version_info)
    Main()
