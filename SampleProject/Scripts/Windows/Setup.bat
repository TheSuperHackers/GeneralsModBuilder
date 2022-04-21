@echo off

set SetupDir=%~dp0.

set ModBuilderVer=1.1
set ModBuilderDir=%SetupDir%\.GeneralsModBuilder\v%ModBuilderVer%
set ModBuilderExe=%ModBuilderDir%\generalsmodbuilder.exe
set ModBuilderZip=%ModBuilderDir%\generalsmodbuilder.zip
set ModBuilderZipUrl=https://github.com/TheSuperHackers/GeneralsTools/raw/main/Tools/generalsmodbuilder/v%ModBuilderVer%/generalsmodbuilder_v%ModBuilderVer%.zip
set ModBuilderZipSha256=e8f30276d0895b34d17d8c5b5cd2e0c7e75ec6c7f4e3fa897ca175464241294e
set ModBuilderZipSize=7885060

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
