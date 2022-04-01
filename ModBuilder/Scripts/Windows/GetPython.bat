setlocal

set ThisDir=%~dp0.
call "%ThisDir%\SetupFolders.bat" %1

set PythonZip=%PythonDir%\python.zip

if not exist "%PythonExe%" (
    :: Create directory
    if not exist "%PythonDir%" mkdir "%PythonDir%"
    :: Download archive
    if not exist "%PythonZip%" (
        curl -L %PythonUrl% -o "%PythonZip%"
    )
    :: Extract archive
    if exist "%PythonZip%" (
        tar -x -k -f "%PythonZip%" -C "%PythonDir%"
        del /q "%PythonZip%"
    )
)

endlocal
