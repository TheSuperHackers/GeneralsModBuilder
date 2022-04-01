import sys
import argparse
import data.bundles
import data.folders
import data.runner
import data.tools
import utils
import os.path
from build.engine import BuildType
from build.engine import BuildSetup
from build.engine import Engine
from utils import JsonFile
from pprint import pprint


def __CreateJsonFiles(configPaths: list[str]) -> list[JsonFile]:
    jsonFiles: list[JsonFile] = []
    for configPath in configPaths:
        if (utils.GetFileExt(configPath) == ".json"):
            jsonFiles.append(JsonFile(configPath))

    return jsonFiles


def __Initialize(buildType: BuildType, configPaths: list[str]) -> None:
    jsonFiles = __CreateJsonFiles(configPaths)

    folders = data.folders.MakeFoldersFromJsons(jsonFiles)
    runner = data.runner.MakeRunnerFromJsons(jsonFiles)
    bundles = data.bundles.MakeBundlesFromJsons(jsonFiles)
    tools = data.tools.MakeToolsFromJsons(jsonFiles)

    pprint(folders)
    pprint(runner)
    pprint(bundles)
    pprint(tools)

    setup = BuildSetup(type=buildType, folders=folders, runner=runner, bundles=bundles, tools=tools)

    engine = Engine()
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
    pprint(args)

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

    buildType = BuildType.NONE
    if args.mod_build:
        buildType |= BuildType.BUILD
    if args.mod_release:
        buildType |= BuildType.RELEASE
    if args.mod_install:
        buildType |= BuildType.INSTALL
    if args.mod_uninstall:
        buildType |= BuildType.UNINSTALL
    if args.mod_run:
        buildType |= BuildType.RUN

    __Initialize(buildType=buildType, configPaths=configPaths)


if __name__ == "__main__":
    print(sys.version_info)
    Main()
