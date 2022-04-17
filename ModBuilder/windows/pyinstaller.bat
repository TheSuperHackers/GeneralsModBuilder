setlocal

set ThisDir=%~dp0.

call "%ThisDir%\setupfolders.bat"

%PythonExe% -m venv "%VenvDir%"
%VenvExe% -m pip install pyinstaller==4.10
%VenvExe% -m pip install -r "%ProjDir%\requirements.txt"
%VenvExe% -m pip install -r "%ProjDir%\requirements-dev.txt"

cd /D "%CodeDir%"

%VenvExe% -m PyInstaller "main.py" ^
    --name generalsmodbuilder ^
    --distpath "%ProjDir%\.dist" ^
    --workpath "%ProjDir%\.build" ^
    --specpath "%ProjDir%" ^
    --add-data "%CodeDir%\config\*.json";config ^
    --clean ^
    --onefile ^
    --noconfirm

cd /D "%WorkDir%"

endlocal
