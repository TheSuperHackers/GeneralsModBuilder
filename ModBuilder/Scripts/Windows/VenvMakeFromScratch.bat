setlocal
set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat" "%~1"

:: Remove existing venv dir
if exist "%VenvDir%\" (
    rmdir /s /q "%VenvDir%"
)

:: Create new venv
python -m venv "%VenvDir%"

:: Activate venv
call "%VenvActivate%"

:: Install pip
python -m pip install --upgrade pip

:: Install requirements
:: pip install libname
pip freeze > "%ThisDir%\requirements.txt"
pip list --local

:: Exit
deactivate

endlocal
