@echo off

set SetupDir=%~dp0.

set ModBuilderVer=1.1
set ModBuilderDir=%SetupDir%\.GeneralsModBuilder\v%ModBuilderVer%
set ModBuilderExe=%ModBuilderDir%\generalsmodbuilder.exe
set ModBuilderZip=%ModBuilderDir%\generalsmodbuilder.zip
set ModBuilderZipUrl=https://github.com/TheSuperHackers/GeneralsTools/raw/main/Tools/generalsmodbuilder/v%ModBuilderVer%/generalsmodbuilder_v%ModBuilderVer%.zip
set ModBuilderZipSha256=8d6338bfb41d7d4761c7c4bbac424bad7875a92a3af82492bf02b1d8ac036acc
set ModBuilderZipSize=7885084

set ConfigDir=%SetupDir%\..\..
set ConfigFiles=^
    "%ConfigDir%\ModBundleItems.json" ^
    "%ConfigDir%\ModBundlePacks.json" ^
    "%ConfigDir%\ModFolders.json" ^
    "%ConfigDir%\ModRunner.json"

if [%~1]==[print] (
    echo SETUP. Using Generals Mod Builder:
    echo ver... %ModBuilderVer%
    echo dir... %ModBuilderDir%
    echo exe... %ModBuilderExe%
    echo zip... %ModBuilderZip%
    echo zipurl %ModBuilderZipUrl%
    echo zipsha %ModBuilderZipSha256%
    echo zipsiz %ModBuilderZipSize%
    for %%f in (%ConfigFiles%) do (
        echo config %%f
    )
    echo SETUP END.
)
