setlocal
set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"

cd /D "%PythonDir%"

call "%RunModBuilder%" --mod-build --mod-release ^
--mod-config="%ConfigDir%\ModBundleItems.json" ^
--mod-config="%ConfigDir%\ModBundlePacks.json" ^
--mod-config="%ConfigDir%\ModFolders.json" ^
--mod-config="%ConfigDir%\ModRunner.json"

cd /D "%ThisDir%"

endlocal
