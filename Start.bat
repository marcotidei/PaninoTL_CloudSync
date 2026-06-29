@echo off
setlocal
cd /d "%~dp0"

call :create_shortcut

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON=python"
    ) else (
        echo Python 3 was not found.
        echo Install it from https://www.python.org/downloads/ and try again.
        echo During setup, check the box labeled "Add Python to PATH".
        pause
        exit /b 1
    )
)

echo Checking Python...
%PYTHON% -c "import sys; print('Python {}.{}.{}'.format(*sys.version_info[:3]))"

%PYTHON% main.py
set "APP_EXIT=%errorlevel%"

echo.
if %APP_EXIT% equ 0 (
    echo PaninoTL Cloud Sync has finished.
) else (
    echo PaninoTL Cloud Sync stopped because of an error.
)
echo.
powershell -NoProfile -Command "Write-Host 'NEXT TIME YOU WANT TO RUN PANINOTL CLOUD SYNC:' -ForegroundColor Cyan; Write-Host 'Open the PaninoTL Cloud Sync folder and double-click Start.bat.' -ForegroundColor Cyan; Write-Host 'Keep this folder; you do not need to repeat the installation command.' -ForegroundColor Cyan"
echo.
pause
exit /b %APP_EXIT%

:create_shortcut
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP=%%D"
set "SHORTCUT_PATH=%DESKTOP%\PaninoTL Cloud Sync.lnk"
if exist "%SHORTCUT_PATH%" exit /b 0
if not exist "%~dp0icons\icon.ico" exit /b 0

set "CREATE_SHORTCUT="
set /p "CREATE_SHORTCUT=Create a PaninoTL Cloud Sync shortcut on your Desktop? [Y/n]: "
if /I "%CREATE_SHORTCUT%"=="n" exit /b 0
if /I "%CREATE_SHORTCUT%"=="no" exit /b 0

set "SHORTCUT_TARGET=%~f0"
set "SHORTCUT_ICON=%~dp0icons\icon.ico"
set "SHORTCUT_WORKDIR=%~dp0"
powershell -NoProfile -Command "$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($env:SHORTCUT_PATH); $shortcut.TargetPath = $env:SHORTCUT_TARGET; $shortcut.WorkingDirectory = $env:SHORTCUT_WORKDIR; $shortcut.IconLocation = $env:SHORTCUT_ICON; $shortcut.Save()"
if %errorlevel% equ 0 (
    echo Desktop shortcut created.
    echo.
) else (
    echo The desktop shortcut could not be created.
    echo.
)
exit /b 0
