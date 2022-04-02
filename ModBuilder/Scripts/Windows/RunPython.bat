setlocal

set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"
call "%ThisDir%\VenvCheck.bat"

if exist "%VenvExe%" (
    "%VenvExe%" %*
) else (
    if exist "%PythonExe%" (
        "%PythonExe%" %*
    )
)

endlocal
