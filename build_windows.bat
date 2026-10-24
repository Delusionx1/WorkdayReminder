@echo off
REM Build WorkdayReminder.exe with PyInstaller (run in the folder that contains main.py)
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name WorkdayReminder main.py
echo.
echo Done: dist\WorkdayReminder.exe
echo Move the exe to a permanent folder, run it, double-click the floating panel and tick autostart.
pause
