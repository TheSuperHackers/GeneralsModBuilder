import sys
import argparse
import builder
import bundles
import folders
import runner
import tools
import utils
from os.path import join as joinpath
from os.path import normpath as normpath
from builder import Builder
from utils import JsonFile


def __CreateJsonFiles(jsonFilePaths: list[str]) -> list[JsonFile]:
   jsonFiles: list[JsonFile] = []
   for jsonFilePath in jsonFilePaths:
       jsonFiles.append(JsonFile(jsonFilePath))

   return jsonFiles


def __StartBuild(jsonFilePaths: list[str]) -> None:
    jsonFiles = __CreateJsonFiles(jsonFilePaths)

    builder = Builder()
    builder.SetFolders(folders.MakeFoldersFromJsons(jsonFiles))
    builder.SetRunner(runner.MakeRunnerFromJsons(jsonFiles))
    builder.SetBundles(bundles.MakeBundlesFromJsons(jsonFiles))
    builder.SetTools(tools.MakeToolsFromJsons(jsonFiles))


def __PrintArgs(args):
    for arg in vars(args):
        print("Arg:", arg, getattr(args, arg))


def Main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', type=str, action="append", help='Path to any json configuration file. Multiples can be specified.')

    args, unknownargs = parser.parse_known_args(args=args)

    __PrintArgs(args)

    thisDir = utils.GetFileDir(__file__)
    jsonFilePaths: list[str] = []

    jsonFilePaths.append(joinpath(thisDir, "..", "DefaultFolders.json"))
    jsonFilePaths.append(joinpath(thisDir, "..", "DefaultRunner.json"))
    jsonFilePaths.append(joinpath(thisDir, "..", "DefaultTools.json"))

    if args.json:
        jsonFilePaths.extend(args.json)

    __StartBuild(jsonFilePaths)


if __name__ == "__main__":
    print(sys.version_info)
    utils.RelAssert(sys.version_info >= (3,10), f"Python version must be 3.10 or higher")

    Main()
