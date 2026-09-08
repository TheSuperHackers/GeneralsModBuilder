import os
import platformdirs
import traceback
from argparse import ArgumentParser
from generalsmodbuilder.__version__ import VERSIONSTR
from generalsmodbuilder.build.engine import BuildEngine
from generalsmodbuilder.buildfunctions import RunWithConfig, BuildFileHashRegistry
from generalsmodbuilder.data.runner import UserRunner, SplitGameExeArgs
from generalsmodbuilder.gui.gui import Gui
from generalsmodbuilder import util


def GetDefaultToolsRootDir() -> str:
    return os.path.join(platformdirs.user_cache_dir("GeneralsModBuilder", "TheSuperHackers"), "tools")


def MakeUserRunnerFromArgs(args) -> UserRunner:
    userRunner = UserRunner()

    if args.game_install_path:
        userRunner.absGameInstallDir = os.path.abspath(args.game_install_path)
    if args.game_exe_file:
        userRunner.relGameExeFile = args.game_exe_file
    if args.game_exe_args != None:
        userRunner.gameExeArgs = SplitGameExeArgs(args.game_exe_args)

    return userRunner


def MakeArgumentParser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument('-c', '--config', type=str, action="append", help='Path to a configuration file (json). Multiples can be specified.')
    parser.add_argument('-l', '--config-list', type=str, nargs="*", help='Paths to any amount of configuration files (json).')
    parser.add_argument('-a', '--clean', action='store_true')
    parser.add_argument('-b', '--build', action='store_true')
    parser.add_argument(      '--build-pack', type=str, nargs="?", const="_default_", action='append', help='If specified, then only builds the bundle pack by name. Multiples can be specified.')
    parser.add_argument(      '--build-pack-list', type=str, nargs="*", help='If specified, then only builds the bundle packs by name.')
    parser.add_argument('-z', '--release', action='store_true')
    parser.add_argument('-i', '--install', type=str, nargs="?", const="_default_", action='append', help='Installs the specified bundle pack by name. Multiples can be specified.')
    parser.add_argument('-o', '--install-list', type=str, nargs="*", help='Installs the specified bundle packs by name.')
    parser.add_argument('-u', '--uninstall', action='store_true')
    parser.add_argument('-r', '--run', action='store_true')
    parser.add_argument('-g', '--gui', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--print-config', action='store_true')
    parser.add_argument('--verbose-logging', action='store_true')
    parser.add_argument('--multi-processing', action='store_true')
    parser.add_argument('--tools-root-dir', type=str, default=None, help='The root directory of tools. By default the directory of the tools json file is used as the root directory for its specified tools.')
    parser.add_argument('--file-hash-registry-input', type=str, action="append", help='Path to generate file hash registry from. Multiples can be specified.')
    parser.add_argument('--file-hash-registry-output', type=str, help='Path to save file hash registry to.')
    parser.add_argument('--file-hash-registry-name', type=str, default="FileHashRegistry", help='Name of the file hash registry.')
    parser.add_argument('--load-default-runner', action='store_true', help='Loads the built-in runner json configuration. Is loaded before custom configurations from --config and --config-list.')
    parser.add_argument('--load-default-tools', action='store_true', help='Loads the built-in tools json configuration. Is loaded before custom configurations from --config and --config-list.')
    parser.add_argument('--make-change-log', action='store_true', help='Generates change log(s) according to the given change log json setup')
    parser.add_argument('--game-install-path', type=str, help='Custom game installation directory. Overrides the runner configuration.')
    parser.add_argument('--game-exe-file', type=str, help='Custom game executable, relative to the game installation directory. Overrides the runner configuration.')
    parser.add_argument('--game-exe-args', type=str, help='Custom game executable arguments as one string, for example --game-exe-args="-win -quickstart". Replaces the arguments of the runner configuration.')

    return parser


def Main(args=None):
    print(f"Generals Mod Builder v{VERSIONSTR} by The Super Hackers")

    parser: ArgumentParser = MakeArgumentParser()
    args, unknownargs = parser.parse_known_args(args=args)

    if args.file_hash_registry_input and args.file_hash_registry_output:
        BuildFileHashRegistry(
            args.file_hash_registry_input,
            args.file_hash_registry_output,
            args.file_hash_registry_name)
        return

    # Populate install pack name list.
    installList = list[str]()
    if args.install_list:
        installList.extend(args.install_list)
    if args.install:
        installList.extend(args.install)

    # Populate build pack name list.
    buildList = list[str]()
    if args.build_pack_list:
        buildList.extend(args.build_pack_list)
    if args.build_pack:
        buildList.extend(args.build_pack)

    # Set main tool commands.
    clean = bool(args.clean)
    build = bool(args.build) or bool(buildList)
    release = bool(args.release)
    install = bool(installList)
    uninstall = bool(args.uninstall)
    run = bool(args.run)
    makeChangeLog = bool(args.make_change_log)

    # Check if any work needs to be done.
    if (not build and
        not release and
        not install and
        not uninstall and
        not run and
        not makeChangeLog):
        parser.print_help()
        return

    util.pprint(args)

    configPaths = list[str]()

    # Add default configurations first to list so readers can parse them first.
    if args.load_default_runner:
        configPaths.append(os.path.join(util.g_appDir, "config", "DefaultRunner.json"))
    if args.load_default_tools:
        configPaths.append(os.path.join(util.g_appDir, "config", "DefaultTools.json"))

    # Add custom configurations last so readers can write over default configurations last.
    if args.config_list:
        configPaths.extend(args.config_list)
    if args.config:
        configPaths.extend(args.config)

    for i, path in enumerate(configPaths):
        configPaths[i] = os.path.abspath(path)

    useGui = bool(args.gui)
    debug = bool(args.debug)
    printConfig = bool(args.print_config)
    verboseLogging = bool(args.verbose_logging)
    multiProcessing = bool(args.multi_processing)
    toolsRootDir = args.tools_root_dir
    userRunner: UserRunner = MakeUserRunnerFromArgs(args)

    if toolsRootDir:
        toolsRootDir = os.path.normpath(toolsRootDir)
    elif args.load_default_tools:
        # The built-in tools configuration would otherwise download tools next to itself,
        # which is inside the installed package. Use a per-user cache directory instead.
        toolsRootDir = GetDefaultToolsRootDir()

    if useGui:
        gui: Gui = Gui()
        gui.RunWithConfig(
            configPaths=configPaths,
            installList=installList,
            buildList=buildList,
            makeChangeLog=makeChangeLog,
            clean=clean,
            build=build,
            release=release,
            install=install,
            uninstall=uninstall,
            run=run,
            debug=debug,
            printConfig=printConfig,
            verboseLogging=verboseLogging,
            multiProcessing=multiProcessing,
            toolsRootDir=toolsRootDir,
            userRunner=userRunner)
    else:
        def RunWithConfigWrapper():
            RunWithConfig(
                configPaths=configPaths,
                installList=installList,
                buildList=buildList,
                makeChangeLog=makeChangeLog,
                clean=clean,
                build=build,
                release=release,
                install=install,
                uninstall=uninstall,
                run=run,
                printConfig=printConfig,
                verboseLogging=verboseLogging,
                multiProcessing=multiProcessing,
                toolsRootDir=toolsRootDir,
                userRunner=userRunner)
        if debug:
            RunWithConfigWrapper()
        else:
            try:
                RunWithConfigWrapper()
            except Exception:
                print("ERROR CALLSTACK")
                traceback.print_exc()
                input("Press any key to continue...")


if __name__ == "__main__":
    Main()
