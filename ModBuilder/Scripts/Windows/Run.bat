setlocal

set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"
call "%ThisDir%\VenvCheck.bat"

set ModBuilderPythonDir=%ThisDir%\..\Python

"%VenvExe%" "%ModBuilderPythonDir%\main.py" %*

endlocal
