@echo off
REM Builds MagicKit.exe on Windows.
REM Run this FROM Windows (not WSL/Linux) - .exe files have to be built on
REM the OS they'll run on, PyInstaller does not cross-compile.

setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo.
    echo  ERROR: Python was not found on this PC.
    echo.
    echo  Building the .exe requires Python ^(the finished .exe itself will
    echo  NOT need Python - only this one-time build step does^).
    echo.
    echo  Install it from https://www.python.org/downloads/
    echo  and tick "Add python.exe to PATH" during setup, then re-run this
    echo  script.
    echo.
    echo  Alternative: push this repo to GitHub and let the included
    echo  GitHub Actions workflow build the .exe for you on GitHub's own
    echo  Windows machine - no Python install needed on this PC at all.
    echo.
    pause
    exit /b 1
)

echo === MagicKit build: creating clean virtual environment ===
py -3 -m venv build_venv
call build_venv\Scripts\activate.bat

echo === Installing dependencies ===
python -m pip install --upgrade pip
pip install -r requirements.txt

echo === Building MagicKit.exe ===
pyinstaller --noconfirm --clean MagicKit.spec

echo.
echo === Done ===
echo Your .exe is at: dist\MagicKit\MagicKit.exe
echo Zip the whole "dist\MagicKit" folder if you want to share it -
echo the .exe needs the files next to it in that folder to run.
pause
