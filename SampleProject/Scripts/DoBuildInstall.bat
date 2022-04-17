@echo off

setlocal

set ThisDir=%~dp0.

call "%ThisDir%\RequestAdmin.bat" "%~s0" %*

if %errorlevel% EQU 111 (
    exit /B %errorlevel%
)

call "%ThisDir%\InstallModBuilder.bat"

if %errorlevel% EQU 222 (
    exit /B %errorlevel%
)

call "%ThisDir%\Setup.bat" print

call "%ModBuilderExe%" --build --install --config-list %ConfigFiles%

endlocal
