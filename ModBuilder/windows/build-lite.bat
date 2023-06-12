set RootDir=%~dp0.\..

python.exe "%RootDir%\build.py" --build-definition-file "%RootDir%\build-lite.json"
