# Mod Builder for Generals: Zero Hour

This tool builds game Mod or Addon release files from flat game data source files. In its current release it is compatible with Windows 10 and above.

The [ModBuilder](ModBuilder) contains all program source files. It is relevant for tool developers, but not for mod developers.

The [SampleProject](SampleProject) contains all scripts (.bat) and configurations (.json) for mod developers to get started with their own project. All tools associated with the Generals Mod Builder will automatically download and install.

## Customize the Mod Builder install

The [Setup.bat](SampleProject/Scripts/Windows/Setup.bat) allows to customize the Mod Builder install. When a new Mod Builder is released, it can be upgraded by modifying this script, or by replacing the script(s) with a new version from the Sample Project. It is possible to change the folder layouts, but for simplicity sake just use the same layout as presented in the Sample Project.

## Setup Mod files and configurations

In the given [SampleProject](SampleProject), all game data source files are placed in the [GameFilesEdited](SampleProject/GameFilesEdited) folder and is referenced in the [ModBundleItems.json](SampleProject/ModBundleItems.json). The bundles configuration allows to define bundles aka .big archives and miscellaneous files. The [ModBundlePacks.json](SampleProject/ModBundlePacks.json) references the bundle items and packs them together as one entity. This allows to pack a project into different configurations, for example as **My_Textures_Pack_2k** and **My_Textures_Pack_4k**.

If a json file is misconfigured, the Mod Builder tool will halt execution early and print information about the problem. Once the configuration is properly set, it will start building.

Find more information about configuration settings down below.

## Supported file conversions

As of Release 1.0, the following file conversions are supported:

* Any to BIG (Game Archive)
* Any to ZIP (Archive)
* Any to TAR (Archive)
* Any to TAR.GZ (Archive)
* CSF to STR
* STR to CSF
* PSD to TGA
* PSD to DDS (DXT1 and DXT5)
* PSD to BMP (24)
* TGA to DDS (DXT1 and DXT5)
* TGA to BMP (24)

## Run the Mod Builder

Batch scripts are available in [SampleProject/Scripts](SampleProject/Scripts) to build and run the project. The [BuildInstallRun.bat](SampleProject/Scripts/BuildInstallRun.bat) is helpful to build, install and run the game with the project in one go. After the game is closed, the project is automatically uninstalled. The [ModRunner.json](SampleProject/ModRunner.json) can be customized to change game run behaviour.

## Safety

The scripts and Mod Builder program will download and install a few executable files (.exe) from [github](https://github.com/TheSuperHackers/GeneralsTools). These are required to build .big or .dds files for example. Before any execution, all executable files are checked against sha256 hashes stored within the scripts and the Mod Builder to verify correctness. This means once the scripts are placed in a Mod project, then no file change on the Internet can incur wrong or malicious program behaviour.

## Configuration settings

### Bundle Items

| Setting                                           | Mandatory | Default | Description                                                                                                         |
|---------------------------------------------------|-----------|---------|---------------------------------------------------------------------------------------------------------------------|
| bundles.version                                   | no        | 1       | json Format version                                                                                                 |
| bundles.itemsPrefix                               | no        |         | A prefix added to all generated .big file names                                                                     |
| bundles.itemsSuffix                               | no        |         | A suffix added to all generated .big file names                                                                     |
| bundles.items                                     | no        |         | Item list                                                                                                           |
| bundles.items[].name                              | yes       |         | Item name                                                                                                           |
| bundles.items[].big                               | no        | True    | Item is a .big file?                                                                                                |
| bundles.items[].files                             | no        |         | Item file list                                                                                                      |
| bundles.items[].files[].parent                    | no        |         | Source file(s) parent folder                                                                                        |
| bundles.items[].files[].source                    | no        |         | Source file(s), accepts wild cards \*.\* or A.\* or \*.B                                                            |
| bundles.items[].files[].target                    | no        |         | Target file(s), accepts wild cards \*.\* or A.\* or \*.B                                                            |
| bundles.items[].files[].params                    | no        |         | File params, see Sample Project for examples                                                                        |
| bundles.items[].files[].sourceList                | no        |         | List of source file(s), target file is automatic, alternative to 'source', accepts wild cards \*.\* or A.\* or \*.B |
| bundles.items[].files[].sourceTargetList          | no        |         | List of source and target file(s), alternative to 'source' and 'target', accepts wild cards \*.\* or A.\* or \*.B   |
| bundles.items[].files[].sourceTargetList[].source | yes       |         | Source file as part of the list                                                                                     |
| bundles.items[].files[].sourceTargetList[].target | yes       |         | Target file as part of the list                                                                                     |
| bundles.items[].files[].sourceTargetList[].params | no        |         | Not implemented                                                                                                     |
| bundles.items[].onPreBuild                        | no        |         | Special callback event that is executed before build. Used to inject custom script logic                            |
| bundles.items[].onPreBuild.script                 | yes       |         | Python script called on event                                                                                       |
| bundles.items[].onPreBuild.function               | no        | OnEvent | Python script function called                                                                                       |
| bundles.items[].onPreBuild.kwargs                 | no        |         | Arbitrary keyword arguments passed to Python script function                                                        |

### Bundle Packs

| Setting                             | Mandatory | Default | Description                                                                              |
|-------------------------------------|-----------|---------|------------------------------------------------------------------------------------------|
| bundles.version                     | no        | 1       | json Format version                                                                      |
| bundles.packsPrefix                 | no        |         | A prefix added to all generated .zip file names                                          |
| bundles.packsSuffix                 | no        |         | A suffix added to all generated .zip file names                                          |
| bundles.packs                       | no        |         | Pack list                                                                                |
| bundles.packs[].install             | no        | False   | Pack is installed by Mod Builder for testing?                                            |
| bundles.packs[].name                | yes       |         | Pack name                                                                                |
| bundles.packs[].itemNames           | yes       |         | Item name list                                                                           |
| bundles.packs[].onPreBuild          | no        |         | Special callback event that is executed before build. Used to inject custom script logic |
| bundles.items[].onPreBuild.script   | yes       |         | Python script called on event                                                            |
| bundles.items[].onPreBuild.function | no        | OnEvent | Python script function called                                                            |
| bundles.items[].onPreBuild.kwargs   | no        |         | Arbitrary keyword arguments passed to Python script function                             |
