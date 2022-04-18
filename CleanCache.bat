set ThisDir=%~dp0.

del "%ThisDir%\ModBuilder\MANIFEST"
rd /s /q "%ThisDir%\ModBuilder\.build"
rd /s /q "%ThisDir%\ModBuilder\.dist"
rd /s /q "%ThisDir%\ModBuilder\__pycache__"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder.egg-info"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\__pycache__"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\build\__pycache__"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\config\.tools"
rd /s /q "%ThisDir%\ModBuilder\generalsmodbuilder\data\__pycache__"
rd /s /q "%ThisDir%\ModBuilder\SampleProject\Scripts\Python\__pycache__"
