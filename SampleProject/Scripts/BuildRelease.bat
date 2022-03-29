setlocal
set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"
call "%RunModBuilder%" "%RootDir%" --json="%ThisDir%\ModBundles.json" --json="%ThisDir%\ModFolders.json" --json="%ThisDir%\ModRunner.json"

endlocal
