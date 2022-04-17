@echo off

set __ThisDir=%~dp0.

:: Mod configuration folder (json)
set ConfigDir=%__ThisDir%\..

:: Generals Mod Builder tool
set ModBuilderDir=%__ThisDir%\.generalsmodbuilder\v1.0
set ModBuilderExe=%ModBuilderDir%\generalsmodbuilder.exe

:: Log Folder
set LogDir=%__ThisDir%\.log

if not exist "%LogDir%" mkdir "%LogDir%"
