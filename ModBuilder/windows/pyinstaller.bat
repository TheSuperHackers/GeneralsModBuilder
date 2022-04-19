setlocal

set ThisDir=%~dp0.

call "%ThisDir%\setup.bat"

%PythonExe% -m venv "%VenvDir%"
%VenvExe% -m pip install pyinstaller==4.10
%VenvExe% -m pip install -r "%ProjDir%\requirements.txt"
%VenvExe% -m pip install -r "%ProjDir%\requirements-dev.txt"

cd /D "%CodeDir%"

%VenvExe% -m PyInstaller "main.py" ^
    --name %ProjName% ^
    --distpath "%PyInstallerDir%" ^
    --workpath "%BuildDir%" ^
    --specpath "%ProjDir%" ^
    --add-data "%CodeDir%\config\*.json";"config" ^
    --clean ^
    --onedir ^
    --noconfirm

cd /D "%WorkDir%"

if not exist %ReleaseDir% (
    mkdir %ReleaseDir%
)

tar.exe -a -c -C "%PyInstallerDir%" -f "%ReleaseDir%\%ProjName%.zip" *.*

endlocal
