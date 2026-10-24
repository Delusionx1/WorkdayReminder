@echo off
chcp 65001 >nul
REM Build WorkdayReminder.exe with Nuitka (run in the folder that contains main.py)
REM First build downloads MinGW (~100-200 MB) and takes about 3-15 minutes.
cd /d "%~dp0"
python -m pip install --quiet --upgrade nuitka zstandard
python -m nuitka --mode=onefile --enable-plugin=pyside6 --windows-console-mode=disable --mingw64 --assume-yes-for-downloads --remove-output --output-dir=dist-nuitka --output-filename=WorkdayReminder.exe main.py
echo.
echo Done: dist-nuitka\WorkdayReminder.exe
echo Use --standalone --onefile instead of --mode=onefile on older Nuitka versions.
pause
