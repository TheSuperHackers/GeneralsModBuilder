@echo off
:: Runs the Generals Mod Builder, installing everything it needs on first use.
::
:: This requires nothing on the machine but this script. It installs uv if it is
:: missing, and uv then downloads a suitable Python and the locked dependencies
:: into a virtual environment next to this script. Later runs reuse both.
::
:: All arguments are forwarded to the mod builder, for example:
::   modbuilder.cmd --build --install --config-list MyMod.json

setlocal

set ThisDir=%~dp0.

where uv >nul 2>nul
if errorlevel 1 (
    echo Installing uv ...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

where uv >nul 2>nul
if errorlevel 1 (
    echo Failed to install uv. See https://docs.astral.sh/uv/getting-started/installation/
    exit /B 1
)

uv run --project "%ThisDir%" generalsmodbuilder %*

exit /B %errorlevel%
