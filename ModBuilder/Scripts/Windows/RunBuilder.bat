setlocal

set ThisDir=%~dp0.
set ModBuilderPythonDir=%ThisDir%\..\Python

call "%ThisDir%\RunPython.bat" "%ModBuilderPythonDir%\main.py" %*

endlocal
