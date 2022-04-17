setlocal

set ThisDir=%~dp0.

call "%ThisDir%\setupfolders.bat"

%PythonExe% -m venv "%VenvDir%"
%VenvExe% -m pip install wheel
%VenvExe% -m pip install -r "%ProjDir%\requirements.txt"
%VenvExe% -m pip install -r "%ProjDir%\requirements-dev.txt"

cd /D "%ProjDir%"

%VenvExe% "setup.py" sdist bdist_wheel --dist-dir ".dist"

cd /D "%WorkDir%"

endlocal
