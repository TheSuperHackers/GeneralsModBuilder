setlocal

set ThisDir=%~dp0.

call "%ThisDir%\RequestAdmin.bat" "%~s0" %*

if %errorlevel% EQU 123 (
    exit /B
)

call "%ThisDir%\SetupFolders.bat"

call "%ModBuilderExe%" --build --install ^
    --config "%ConfigDir%\ModBundleItems.json" ^
    --config "%ConfigDir%\ModBundlePacks.json" ^
    --config "%ConfigDir%\ModFolders.json" ^
    --config "%ConfigDir%\ModRunner.json" ^
    > "%LogDir%\%~n0.log"

endlocal
