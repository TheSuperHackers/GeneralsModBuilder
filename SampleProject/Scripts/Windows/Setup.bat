@echo off

set SetupDir=%~dp0.

set ModBuilderVer=1.3
set ModBuilderDir=%SetupDir%\.modbuilder\v%ModBuilderVer%
set ModBuilderExe=%ModBuilderDir%\generalsmodbuilder\generalsmodbuilder.exe
set ModBuilderArc=%ModBuilderDir%\generalsmodbuilder.7z
set ModBuilderArcUrl=https://github.com/TheSuperHackers/GeneralsTools/raw/main/Tools/generalsmodbuilder/v%ModBuilderVer%/generalsmodbuilder_v%ModBuilderVer%.7z
set ModBuilderArcSha256=65424774ffc3ea51f0796485e32846e873ee2fa0a9fe595f7d328704363e8d7a
set ModBuilderArcSize=36570350

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
    echo archiv %ModBuilderArc%
    echo arcurl %ModBuilderArcUrl%
    echo arcsha %ModBuilderArcSha256%
    echo arcsiz %ModBuilderArcSize%
    for %%f in (%ConfigFiles%) do (
        echo config %%f
    )
    echo SETUP END.
)
