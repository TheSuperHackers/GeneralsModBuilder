import os
import bpy
import sys
import argparse

class ArgumentParser(argparse.ArgumentParser):
    """
    This class is identical to its superclass, except for the parse_args
    method (see docstring). It resolves the ambiguity generated when calling
    Blender from the CLI with a python script, and both Blender and the script
    have arguments. E.g., the following call will make Blender crash because
    it will try to process the script's -a and -b flags:
    >>> blender --python my_script.py -a 1 -b 2

    To bypass this issue this class uses the fact that Blender will ignore all
    arguments given after a double-dash ('--'). The approach is that all
    arguments before '--' go to Blender, arguments after go to the script.
    The following calls work fine:
    >>> blender --python my_script.py -- -a 1 -b 2
    >>> blender --python my_script.py --
    """

    def _get_argv_after_doubledash(self):
        try:
            idx = sys.argv.index("--")
            return sys.argv[idx+1:]
        except ValueError as e:
            return []

    def parse_args(self):
        return super().parse_args(args=self._get_argv_after_doubledash())

    def parse_known_args(self):
        return super().parse_known_args(args=self._get_argv_after_doubledash())


def main():
    print("Install blender addon/plugin ...")

    parser = ArgumentParser()
    parser.add_argument('-n', '--name', type=str, help='Name of the addon/plugin')
    parser.add_argument('-f', '--file', type=str, help='Absolute file path to the addon/plugin')

    args, unknownargs = parser.parse_known_args()

    print(f"Name: {args.name}")
    print(f"File: {args.file}")

    if args.file:
        bpy.ops.preferences.addon_install(overwrite=True, filepath=args.file)

    if args.name:
        bpy.ops.preferences.addon_enable(module=args.name)


if __name__ == '__main__': 
    main()
