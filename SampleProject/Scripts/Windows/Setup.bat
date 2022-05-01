@echo off

set SetupDir=%~dp0.

:: Version, size and hash. Sets which Mod Builder is used.
set ModBuilderVer=1.4
set ModBuilderArcSize=30082750
set ModBuilderArcSha256=9f0659d75db8b1aac77c8a3fc13289e99282849a4d23dea92c53f528f78d8608

:: The mod config files. Relative to this setup file.
set ConfigFiles=^
    "%SetupDir%\..\..\ModBundleItems.json" ^
    "%SetupDir%\..\..\ModBundlePacks.json" ^
    "%SetupDir%\..\..\ModFolders.json" ^
    "%SetupDir%\..\..\ModRunner.json"

:: Misc path setup.
set ModBuilderDir=%SetupDir%\.modbuilder\v%ModBuilderVer%
set ModBuilderExe=%ModBuilderDir%\generalsmodbuilder\generalsmodbuilder.exe
set ModBuilderArc=%ModBuilderDir%\generalsmodbuilder.7z
set ModBuilderArcUrl=https://github.com/TheSuperHackers/GeneralsTools/raw/main/Tools/generalsmodbuilder/v%ModBuilderVer%/generalsmodbuilder_v%ModBuilderVer%.7z

:: Print setup info.
echo SETUP.BAT
echo modver %ModBuilderVer%
echo arcsiz %ModBuilderArcSize%
echo arcsha %ModBuilderArcSha256%
for %%f in (%ConfigFiles%) do (
    echo config %%f
)
echo moddir %ModBuilderDir%
echo modexe %ModBuilderExe%
echo arcfil %ModBuilderArc%
echo arcurl %ModBuilderArcUrl%
