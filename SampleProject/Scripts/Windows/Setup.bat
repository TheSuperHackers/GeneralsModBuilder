@echo off

set SetupDir=%~dp0.

set ModBuilderVer=1.2
set ModBuilderDir=%SetupDir%\.GeneralsModBuilder\v%ModBuilderVer%
set ModBuilderExe=%ModBuilderDir%\generalsmodbuilder.exe
set ModBuilderZip=%ModBuilderDir%\generalsmodbuilder.zip
set ModBuilderZipUrl=https://github.com/TheSuperHackers/GeneralsTools/raw/main/Tools/generalsmodbuilder/v%ModBuilderVer%/generalsmodbuilder_v%ModBuilderVer%.zip
set ModBuilderZipSha256=f30458985cf5925a67400da4241369ee23f12370a36e2bd8cfb04ada51c59672
set ModBuilderZipSize=7885115

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
