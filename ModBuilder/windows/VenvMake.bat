setlocal

set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"
call "%ThisDir%\GetPython.bat"

:: Remove existing venv dir
if exist "%VenvDir%\" (
    rmdir /s /q "%VenvDir%"
)

:: Create new venv
"%PythonExe%" -m venv "%VenvDir%"

:: Install requirements, if any
if exist "%PythonRequirements%" (
    "%VenvExe%" -m ensurepip
    "%VenvExe%" -m pip install -r "%PythonRequirements%"
    "%VenvExe%" -m pip list --local
)

endlocal
