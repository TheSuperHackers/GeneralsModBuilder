setlocal

set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"
call "%VenvActivate%"

endlocal
