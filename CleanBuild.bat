set ThisDir=%~dp0.

rd /s /q "%ThisDir%\ModBuilder\.build"
rd /s /q "%ThisDir%\ModBuilder\.pyinstaller"
rd /s /q "%ThisDir%\ModBuilder\.release"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\__pycache__"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\changelog\__pycache__"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\build\__pycache__"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\config\.tools"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\data\__pycache__"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\gui\__pycache__"
