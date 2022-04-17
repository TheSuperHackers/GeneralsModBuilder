@echo off

set ScriptDir=%~dp0.

set ModBuilderVer=1.0
set ModBuilderDir=%ScriptDir%\.generalsmodbuilder\v%ModBuilderVer%
set ModBuilderExe=%ModBuilderDir%\generalsmodbuilder.exe
set ModBuilderUrl=https://github.com/TheSuperHackers/GeneralsTools/raw/main/Tools/generalsmodbuilder/v%ModBuilderVer%/generalsmodbuilder.exe
set ModBuilderSha256=4a212a70e646b8604d254f7849a1cb5088fa615bc60503b03ed10b9933b77381

set ConfigDir=%ScriptDir%\..
set ConfigFiles=^
    "%ConfigDir%\ModBundleItems.json" ^
    "%ConfigDir%\ModBundlePacks.json" ^
    "%ConfigDir%\ModFolders.json" ^
    "%ConfigDir%\ModRunner.json"

set LogDir=%ScriptDir%\.log

if [%~1]==[print] (
    echo SETUP. Using Generals Mod Builder:
    echo ver... %ModBuilderVer%
    echo dir... %ModBuilderDir%
    echo exe... %ModBuilderExe%
    echo sha256 %ModBuilderSha256%
    echo url... %ModBuilderUrl%
    for %%f in (%ConfigFiles%) do (
        echo config %%f
    )
    echo SETUP END.
)
