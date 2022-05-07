set ThisDir=%~dp0.

rd /s /q "%ThisDir%\ModBuilder\.build"
rd /s /q "%ThisDir%\ModBuilder\.pyinstaller"
rd /s /q "%ThisDir%\ModBuilder\.release"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\__pycache__"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\build\__pycache__"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\config\.tools"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\data\__pycache__"
rd /s /q "%ThisDir%\SampleProject\.Build"
rd /s /q "%ThisDir%\SampleProject\.Release"
rd /s /q "%ThisDir%\SampleProject\Scripts\Windows\.modbuilder"
rd /s /q "%ThisDir%\SampleProject\Scripts\Python\__pycache__"
