set __ThisDir=%~dp0.

:: Directory to where python is or will be installed
set PythonDir=%__ThisDir%\..\..

:: Directory to Mod configuration files (json)
set ConfigDir=%__ThisDir%\..

:: Directory to the Mod Builder tool
set ModBuilderDir=%__ThisDir%\..\..\ModBuilder
set RunModBuilder=%ModBuilderDir%\Scripts\Windows\Run.bat
