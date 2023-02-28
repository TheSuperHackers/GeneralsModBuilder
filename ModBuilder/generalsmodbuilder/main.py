import os
import traceback
from argparse import ArgumentParser
from generalsmodbuilder.__version__ import __version__
from generalsmodbuilder.buildfunctions import RunWithConfig, BuildFileHashRegistry
from generalsmodbuilder import util


def Main(args=None):
    print(f"Generals Mod Builder v{__version__} by The Super Hackers")

    parser = ArgumentParser()
    parser.add_argument('-c', '--config', type=str, action="append", help='Path to a configuration file (json). Multiples can be specified.')
    parser.add_argument('-l', '--config-list', type=str, nargs="*", help='Paths to any amount of configuration files (json).')
    parser.add_argument('-a', '--clean', action='store_true')
    parser.add_argument('-b', '--build', action='store_true')
    parser.add_argument('-z', '--release', action='store_true')
    parser.add_argument('-i', '--install', type=str, nargs="?", const="_default_", action='append', help='Can specify bundle pack name to install. Multiples can be specified.')
    parser.add_argument('-o', '--install-list', type=str, nargs="*", help='Installs specified bundle pack names.')
    parser.add_argument('-u', '--uninstall', action='store_true')
    parser.add_argument('-r', '--run', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--print-config', action='store_true')
    parser.add_argument('--file-hash-registry-input', type=str, action="append", help='Path to generate file hash registry from. Multiples can be specified.')
    parser.add_argument('--file-hash-registry-output', type=str, help='Path to save file hash registry to.')
    parser.add_argument('--file-hash-registry-name', type=str, default="FileHashRegistry", help='Name of the file hash registry.')

    args, unknownargs = parser.parse_known_args(args=args)

    if args.file_hash_registry_input and args.file_hash_registry_output:
        BuildFileHashRegistry(
            args.file_hash_registry_input,
            args.file_hash_registry_output,
            args.file_hash_registry_name)
        return

    # Build install pack name list.
    installList = list[str]()
    if args.install_list:
        installList.extend(args.install_list)
    if args.install:
        installList.extend(args.install)

    # Set main tool commands.
    clean = bool(args.clean)
    build = bool(args.build)
    release = bool(args.release)
    install = bool(installList)
    uninstall = bool(args.uninstall)
    run = bool(args.run)

    # Check if any work needs to be done.
    if (not build) and (not release) and (not install) and (not uninstall) and (not run):
        parser.print_help()
        return

    util.pprint(args)

    thisDir = util.GetAbsFileDir(__file__)
    configPaths = list[str]()

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

    debug = bool(args.debug)
    printConfig = bool(args.print_config)

    if debug:
        RunWithConfig(
            configPaths=configPaths,
            installList=installList,
            clean=clean,
            build=build,
            release=release,
            install=install,
            uninstall=uninstall,
            run=run,
            printConfig=printConfig)
    else:
        try:
            RunWithConfig(
                configPaths=configPaths,
                installList=installList,
                clean=clean,
                build=build,
                release=release,
                install=install,
                uninstall=uninstall,
                run=run,
                printConfig=printConfig)
        except Exception:
            print("ERROR CALLSTACK")
            traceback.print_exc()
            input("Press any key to continue...")


if __name__ == "__main__":
    Main()
