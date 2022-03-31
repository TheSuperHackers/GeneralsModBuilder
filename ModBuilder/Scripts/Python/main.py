import sys
import argparse
import data.bundles
import data.folders
import data.runner
import data.tools
import utils
import os.path
from build.engine import Engine
from utils import JsonFile
from pprint import pprint


def __CreateJsonFiles(jsonFilePaths: list[str]) -> list[JsonFile]:
   jsonFiles: list[JsonFile] = []
   for jsonFilePath in jsonFilePaths:
       jsonFiles.append(JsonFile(jsonFilePath))

   return jsonFiles


def __StartBuild(jsonFilePaths: list[str]) -> None:
    jsonFiles = __CreateJsonFiles(jsonFilePaths)

    folders = data.folders.MakeFoldersFromJsons(jsonFiles)
    runner = data.runner.MakeRunnerFromJsons(jsonFiles)
    bundles = data.bundles.MakeBundlesFromJsons(jsonFiles)
    tools = data.tools.MakeToolsFromJsons(jsonFiles)

    pprint(folders)
    pprint(runner)
    pprint(bundles)
    pprint(tools)

    engine = Engine(folders=folders, runner=runner, bundles=bundles, tools=tools)
    engine.VerifyTypes()
    engine.VerifyValues()


def Main(args=None):
    utils.RelAssert(sys.version_info >= (3,10), f"Python version must be 3.10 or higher")

    parser = argparse.ArgumentParser()
    parser.add_argument('--json', type=str, action="append", help='Path to any json configuration file. Multiples can be specified.')

    args, unknownargs = parser.parse_known_args(args=args)
    pprint(args)

    thisDir = utils.GetFileDir(__file__)
    jsonFilePaths: list[str] = []

    jsonFilePaths.append(os.path.join(thisDir, "..", "DefaultFolders.json"))
    jsonFilePaths.append(os.path.join(thisDir, "..", "DefaultRunner.json"))
    jsonFilePaths.append(os.path.join(thisDir, "..", "DefaultTools.json"))

    if args.json:
        jsonFilePaths.extend(args.json)

    __StartBuild(jsonFilePaths)


if __name__ == "__main__":
    print(sys.version_info)
    Main()
