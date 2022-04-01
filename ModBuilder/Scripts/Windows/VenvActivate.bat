setlocal

set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat" %1
call "%VenvActivate%"

endlocal
