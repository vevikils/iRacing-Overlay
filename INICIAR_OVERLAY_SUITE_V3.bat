@echo off
setlocal
cd /d "%~dp0"
if exist "C:\Users\alfaswz\.venv\Scripts\pythonw.exe" (
    start "" "C:\Users\alfaswz\.venv\Scripts\pythonw.exe" "%~dp0main.py" --autostart
    exit /b 0
)
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py" --autostart
    exit /b 0
)
call "%~dp0INSTALAR_Y_EJECUTAR.bat"
