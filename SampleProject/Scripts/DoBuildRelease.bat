setlocal

set ThisDir=%~dp0.

call "%ThisDir%\SetupFolders.bat"

call "%ModBuilderExe%" --build --release ^
    --config "%ConfigDir%\ModBundleItems.json" ^
    --config "%ConfigDir%\ModBundlePacks.json" ^
    --config "%ConfigDir%\ModFolders.json" ^
    --config "%ConfigDir%\ModRunner.json" ^
    > "%LogDir%\%~n0.log"

endlocal
