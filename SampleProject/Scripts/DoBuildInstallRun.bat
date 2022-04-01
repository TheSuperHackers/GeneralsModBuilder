setlocal
set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"
cd /D "%PythonDir%"

call "%RunModBuilder%" --mod-build --mod-install --mod-run --mod-uninstall ^
--mod-config="%ConfigDir%\ModBundles.json" ^
--mod-config="%ConfigDir%\ModFolders.json" ^
--mod-config="%ConfigDir%\ModRunner.json"

cd /D "%ThisDir%"

endlocal
