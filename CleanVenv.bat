set ThisDir=%~dp0.

rd /s /q "%ThisDir%\ModBuilder\.venv"
rd /s /q "%ThisDir%\ModBuilder\.venv-poetry"
rd /s /q "%ThisDir%\ModBuilder\.venv-pyinstaller"
