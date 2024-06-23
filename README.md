# Mod Builder for Generals: Zero Hour

This tool builds game Mod or Addon release files from flat game data source files. In its current release it is compatible with Windows 10 and above.

The [ModBuilder](ModBuilder) contains all program source files. It is relevant for tool developers, but not for mod developers.

The [GeneralsModBuilderSample](https://github.com/TheSuperHackers/GeneralsModBuilderSample) contains all scripts (.bat) and configurations (.json) for mod developers to get started with their own project. All tools associated with the Generals Mod Builder will automatically download and install.

## Customize the Mod Builder install

The [Setup.bat](https://github.com/TheSuperHackers/GeneralsModBuilderSample/tree/main/Project/Scripts/Windows/Setup.bat) allows to customize the Mod Builder install. When a new Mod Builder is released, it can be upgraded by modifying this script, or by replacing the script(s) with a new version from the Sample Project. It is possible to change the folder layouts, but for simplicity sake just use the same layout as presented in the Sample Project.

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

## Run the Mod Builder

Batch scripts are available in [GeneralsModBuilderSample/Project/Scripts](https://github.com/TheSuperHackers/GeneralsModBuilderSample/tree/main/Project/Scripts) to build and run the project. The [BuildInstallRun.bat](https://github.com/TheSuperHackers/GeneralsModBuilderSample/tree/main/Project/Scripts/BuildInstallRun.bat) is helpful to build, install and run the game with the project in one go. After the game is closed, the project is automatically uninstalled. The [WindowsRunner.json](https://github.com/TheSuperHackers/GeneralsModBuilderSample/tree/main/Project/Scripts/Windows/WindowsRunner.json) can be customized to change game run behaviour.

## Safety

The scripts and Mod Builder program will download and install a few executable files (.exe) from [GeneralsTools](https://github.com/TheSuperHackers/GeneralsTools). These are required to build .big or .dds files for example. Before any execution, all executable files are checked against sha256 hashes stored within the scripts and the Mod Builder to verify correctness. This means once the scripts are placed in a Mod project, then no file change on the Internet can incur wrong or malicious program behaviour.
