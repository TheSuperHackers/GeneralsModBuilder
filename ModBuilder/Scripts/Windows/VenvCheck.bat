setlocal

set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"

set makeVenv=0

if not exist "%PythonExe%" (
    set makeVenv=1
)

if not exist "%VenvExe%" (
    set makeVenv=1
)

if %makeVenv%==1 (
    call "%ThisDir%\VenvMake.bat" %1
)

endlocal
