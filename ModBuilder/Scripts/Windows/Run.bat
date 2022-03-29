setlocal
set ThisDir=%~dp0.
set PythonDir=%ThisDir%\..\Python
set RootDir=%~1

call "%ThisDir%\SetupFolders.bat" "%RootDir%"
call "%ThisDir%\VenvCheck.bat" "%RootDir%"

"%VenvExe%" "%PythonDir%\Main.py" %*

endlocal
