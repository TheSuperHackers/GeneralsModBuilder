setlocal
set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"

cd /D "%PythonDir%"

call "%RunModBuilder%" --uninstall ^
--mod-config="%ConfigDir%\ModBundles.json" ^
--mod-config="%ConfigDir%\ModFolders.json" ^
--mod-config="%ConfigDir%\ModRunner.json"

cd /D "%ThisDir%"

endlocal
