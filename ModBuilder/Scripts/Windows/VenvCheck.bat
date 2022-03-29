setlocal
set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat" "%~1"
if not exist "%VenvExe%" (
    call "%ThisDir%\VenvMake.bat" "%~1"
)

endlocal
