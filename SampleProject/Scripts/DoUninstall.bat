setlocal
set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"
call "%RunModBuilder%" "%RootDir%" --uninstall ^
--mod-config="%ThisDir%\ModBundles.json" ^
--mod-config="%ThisDir%\ModFolders.json" ^
--mod-config="%ThisDir%\ModRunner.json"

endlocal
