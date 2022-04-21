setlocal

set ThisDir=%~dp0.
set WasDownloaded=0
set WasInstalled=0

call "%ThisDir%\Setup.bat"

echo Hash Generals Mod Builder Exe ...
Certutil -hashfile "%ModBuilderExe%" SHA256 | findstr /c:%ModBuilderExeSha256%

if %errorlevel% NEQ 0 (
    echo Installing Generals Mod Builder at '%ModBuilderDir%'

    if not exist "%ModBuilderDir%" (
        echo Create folder '%ModBuilderDir%'
        mkdir "%ModBuilderDir%"
    )

    echo Download '%ModBuilderZipUrl%'
    curl --location "%ModBuilderZipUrl%" --output "%ModBuilderZip%" --max-filesize %ModBuilderZipSize%

    set WasDownloaded=1
)

if %WasDownloaded% NEQ 0 (
    if exist "%ModBuilderZip%" (
        echo Hash Generals Mod Builder archive ...
        Certutil -hashfile "%ModBuilderZip%" SHA256 | findstr /c:%ModBuilderZipSha256%

        if %errorlevel% EQU 0 (
            echo Extract archive '%ModBuilderZip%'
            tar.exe -x -k -f "%ModBuilderZip%" -C "%ModBuilderDir%" --strip-components=1

            echo Delete archive '%ModBuilderZip%'
            del /q "%ModBuilderZip%"

            set WasInstalled=1
        ) else (
            echo File '%ModBuilderZip%' does not have expected hash '%ModBuilderZipSha256%'
            exit /B 222
        )
    ) else (
        echo File '%ModBuilderZip%' failed to download
        exit /B 222
    )
)

if %WasInstalled% NEQ 0 (
    if not exist "%ModBuilderExe%" (
        echo File '%ModBuilderExe%' failed to install
        exit /B 222
    )

    echo Hashing Generals Mod Builder ...
    Certutil -hashfile "%ModBuilderExe%" SHA256 | findstr /c:%ModBuilderExeSha256%

    if %errorlevel% NEQ 0 (
        echo File '%ModBuilderExe%' does not have expected hash '%ModBuilderExeSha256%'
        exit /B 222
    )
)

echo Check Generals Mod Builder exe ...
for /F %%I in ("%ModBuilderExe%") do (
    if %%~zI NEQ %ModBuilderExeSize% (
        echo File '%ModBuilderExe%' does not have expected size %ModBuilderExeSize%
        exit /B 222
    )
)

endlocal
