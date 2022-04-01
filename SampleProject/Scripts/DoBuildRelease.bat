setlocal
set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"
cd /D "%RootDir%"

call "%RunModBuilder%" --mod-build --mod-release ^
--mod-config="%ThisDir%\ModBundles.json" ^
--mod-config="%ThisDir%\ModFolders.json" ^
--mod-config="%ThisDir%\ModRunner.json"

cd /D "%ThisDir%"

endlocal
