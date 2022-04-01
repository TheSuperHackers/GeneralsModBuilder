:: Command line argument 1 expects project root folder. Some folders will be created there.

set VenvDir=%~1\.venv
set VenvExe=%VenvDir%\Scripts\python.exe
set VenvActivate=%VenvDir%\Scripts\activate.bat

set PythonDir=%~1\.tools\python-3.10.4-amd64
set PythonExe=%PythonDir%\python.exe
set PythonUrl="https://github.com/TheSuperHackers/GeneralsTools/raw/main/Tools/Python/python-3.10.4-amd64.zip"
