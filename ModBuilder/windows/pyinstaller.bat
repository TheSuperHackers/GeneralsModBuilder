setlocal

set ThisDir=%~dp0.

call "%ThisDir%\setupfolders.bat"

%PythonExe% -m venv "%VenvDir%"
%VenvExe% -m pip install pyinstaller
%VenvExe% -m pip install -r "%ProjDir%\requirements.txt"
%VenvExe% -m pip install -r "%ProjDir%\requirements-dev.txt"

cd "%CodeDir%"

%VenvExe% -m PyInstaller "main.py" ^
    --name generalsmodbuilder ^
    --distpath "%ProjDir%\.dist" ^
    --workpath "%ProjDir%\.build" ^
    --specpath "%ProjDir%" ^
    --add-data "%CodeDir%\config\*.json";config ^
    --clean ^
    --onefile ^
    --noconfirm

cd "%WorkDir%"

endlocal
