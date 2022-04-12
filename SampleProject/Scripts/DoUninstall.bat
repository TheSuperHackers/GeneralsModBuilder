setlocal
set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"

cd /D "%PythonDir%"

call "%RunModBuilder%" --uninstall ^
--config="%ConfigDir%\ModBundleItems.json" ^
--config="%ConfigDir%\ModBundlePacks.json" ^
--config="%ConfigDir%\ModFolders.json" ^
--config="%ConfigDir%\ModRunner.json"

cd /D "%ThisDir%"

endlocal
