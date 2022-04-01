setlocal

set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat" %1
call "%ThisDir%\VenvCheck.bat" %1

set ModBuilderPythonDir=%ThisDir%\..\Python

"%VenvExe%" "%ModBuilderPythonDir%\main.py" %*

endlocal
