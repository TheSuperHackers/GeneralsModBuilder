setlocal

set ThisDir=%~dp0.
set ModBuilderPythonDir=%ThisDir%\..\generalsmodbuilder

call "%ThisDir%\RunPython.bat" "%ModBuilderPythonDir%\main.py" %*

endlocal
