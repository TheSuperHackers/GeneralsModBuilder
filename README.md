# Mod Builder for Generals: Zero Hour

This tool builds game Mod or Addon release files from flat game data source files. In its current release it is compatible with Windows 10 and above.

The [generalsmodbuilder](generalsmodbuilder) folder contains all program source files. It is relevant for tool developers, but not for mod developers.

The [GeneralsModBuilderSample](https://github.com/TheSuperHackers/GeneralsModBuilderSample) contains all scripts (.bat) and configurations (.json) for mod developers to get started with their own project. All tools associated with the Generals Mod Builder will automatically download and install.

## Install the Mod Builder

The Mod Builder needs nothing preinstalled on the machine. The [modbuilder.cmd](modbuilder.cmd) launcher installs [uv](https://docs.astral.sh/uv/) if it is missing, and uv then downloads a suitable Python and the locked dependencies into a `.venv` next to the launcher. This happens once; later runs start immediately.

Pick whichever of these suits the project:

**As a git submodule**, which is the recommended way and what the Sample Project does. The submodule commit pins the Mod Builder version, and `git submodule update --remote` upgrades it.

```
git submodule add https://github.com/TheSuperHackers/GeneralsModBuilder ThirdParty/GeneralsModBuilder
ThirdParty\GeneralsModBuilder\modbuilder.cmd --build --install --config-list MyMod.json
```

**As a plain copy.** Copy the contents of this repository anywhere into the project and commit them. Run `modbuilder.cmd` from wherever it landed.

**As an installed Python package**, for anyone who would rather have a `generalsmodbuilder` command on the PATH:

```
uv tool install git+https://github.com/TheSuperHackers/GeneralsModBuilder@v3.0
generalsmodbuilder --build --install --config-list MyMod.json
```

`pip install git+https://github.com/TheSuperHackers/GeneralsModBuilder@v3.0` works the same way in an existing environment. On a POSIX shell use `modbuilder.sh` in place of `modbuilder.cmd`.

The virtual environment is created inside the Mod Builder folder. Set the `UV_PROJECT_ENVIRONMENT` environment variable to put it somewhere else.

## Setup Mod files and configurations

In the [GeneralsModBuilderSample/Project](https://github.com/TheSuperHackers/GeneralsModBuilderSample/tree/main/Project), all game data source files are placed in the [GameFilesEdited](https://github.com/TheSuperHackers/GeneralsModBuilderSample/tree/main/Project/GameFilesEdited) folder and is referenced in the [ModBundleItems.json](https://github.com/TheSuperHackers/GeneralsModBuilderSample/tree/main/Project/ModBundleItems.json). The bundles configuration allows to define bundles aka .big archives and miscellaneous files. The [ModBundlePacks.json](https://github.com/TheSuperHackers/GeneralsModBuilderSample/tree/main/Project/ModBundlePacks.json) references the bundle items and packs them together as one entity. This allows to pack a project into different configurations, for example as **My_Textures_Pack_2k** and **My_Textures_Pack_4k**.

If a json file is misconfigured, the Mod Builder tool will halt execution early and print information about the problem. Once the configuration is properly set, it will start building.

Find more information about [Configuration Settings](SETTINGS.md).

## Supported file conversions

The following file conversions are supported:

**Since Release 1.0**

* Any to BIG (Game Archive)
* Any to ZIP (Archive), TAR (Archive), TAR.GZ (Archive)
* CSF to STR
* STR to CSF
* PSD (rgb) to BMP (24), DDS (DXT1 and DXT5), TGA
  * Can composite psd (since v2.2), otherwise uses baked psd composite (known as "Maximize Compatibility")
  * Supports transparent background and multiple alpha channels
  * Exports RGB as DXT1, RGBA as DXT5
* TGA to BMP (24), DDS (DXT1 and DXT5)
  * Exports RGB as DXT1, RGBA as DXT5

**Since Release 1.8**

* BLEND to W3D

**Since Release 2.2**

* TIFF (rgb) to BMP (24), DDS (DXT1 and DXT5), TGA
  * Supports Uncompressed, LZW RLE, LZW ZIP, ...
  * Supports no transparent background and no more than one alpha channel
  * Exports RGB as DXT1, RGBA as DXT5

**Since Release 2.3**

* DDS to DDS
  * Useful for exporting a source DDS texture to a new format, for example from DXT5 to DXT1 when omitting the alpha channel

**Since Release 2.4**

* Multiple sources to one INI, WND, STR, CSF
  * Allows to keep game data in several small files that are easier to maintain, and still ship them as the one file that the game expects
  * INI and WND files are appended in the order that their sources are listed in
  * STR and CSF files merge their string labels, where a label of a later file overwrites an earlier one
  * Configured with `multiSource`, see [Configuration Settings](SETTINGS.md)

## Run the Mod Builder

Batch scripts are available in [GeneralsModBuilderSample/Project/Scripts](https://github.com/TheSuperHackers/GeneralsModBuilderSample/tree/main/Project/Scripts) to build and run the project. The [BuildInstallRun.bat](https://github.com/TheSuperHackers/GeneralsModBuilderSample/tree/main/Project/Scripts/BuildInstallRun.bat) is helpful to build, install and run the game with the project in one go. After the game is closed, the project is automatically uninstalled. The [WindowsRunner.json](https://github.com/TheSuperHackers/GeneralsModBuilderSample/tree/main/Project/Scripts/Windows/WindowsRunner.json) can be customized to change game run behaviour.

Each of those scripts is a thin wrapper around the launcher, so the Mod Builder can equally be run by hand:

```
ThirdParty\GeneralsModBuilder\modbuilder.cmd --build --install --run --uninstall --config-list <your json files>
```

## Safety

The Mod Builder program will download and install a few executable files (.exe) from [GeneralsTools](https://github.com/TheSuperHackers/GeneralsTools). These are required to build .big or .dds files for example. Before any execution, all executable files are checked against sha256 hashes stored within the Mod Builder to verify correctness. This means once the configuration is placed in a Mod project, then no file change on the Internet can incur wrong or malicious program behaviour.

The Mod Builder itself is no longer distributed as a downloaded archive, so it needs no hash pinning of its own. A submodule is pinned to an exact commit, a copy is committed into the project, and a `uv tool install` is pinned to a tag. Its Python dependencies are pinned by [uv.lock](uv.lock), which records a hash for every package.

## Develop the Mod Builder

```
uv sync
uv run generalsmodbuilder --help
```

To release, bump `__version__` in [generalsmodbuilder/\_\_version\_\_.py](generalsmodbuilder/__version__.py), run `uv lock`, commit and tag `vX.Y`. There are no artifacts to build or upload; the tag is the release.
