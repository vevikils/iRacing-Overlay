@echo off
setlocal
title iRacing HUD Overlay Suite v3.5 Supreme - Instalador y Lanzador Portable (by vevi)
cd /d "%~dp0"

echo ============================================================================
echo   iRACING HUD OVERLAY SUITE v3.5 SUPREME - BLENDER 3D PBR EDITION
echo   Autor: vevi (VEVIkils556@gmail.com)
echo ============================================================================
echo.

:: 1. Ruta rapida si existe el entorno virtual del creador o local
if exist "C:\Users\alfaswz\.venv\Scripts\python.exe" (
    set "PY_EXE=C:\Users\alfaswz\.venv\Scripts\python.exe"
    set "PYW_EXE=C:\Users\alfaswz\.venv\Scripts\pythonw.exe"
    goto :CHECK_DEPS
)

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
    set "PYW_EXE=%~dp0.venv\Scripts\pythonw.exe"
    goto :CHECK_DEPS
)

:: 2. Buscar Python en el sistema y crear entorno virtual portable (.venv)
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Creando entorno virtual portable en .venv ...
    python -m venv "%~dp0.venv"
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
    set "PYW_EXE=%~dp0.venv\Scripts\pythonw.exe"
    goto :INSTALL_DEPS
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Creando entorno virtual portable con py launcher en .venv ...
    py -3 -m venv "%~dp0.venv"
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
    set "PYW_EXE=%~dp0.venv\Scripts\pythonw.exe"
    goto :INSTALL_DEPS
)

echo [ERROR] No se encontro Python 3 instalado en este equipo.
echo Descarga Python 3.10+ desde https://www.python.org/downloads/ (marca "Add Python to PATH").
pause
exit /b 1

:CHECK_DEPS
"%PY_EXE%" -c "import PyQt5, irsdk" >nul 2>nul
if %ERRORLEVEL% NEQ 0 goto :INSTALL_DEPS
goto :LAUNCH

:INSTALL_DEPS
echo [INFO] Instalando dependencias necesarias (PyQt5, pyirsdk, PyYAML)...
"%PY_EXE%" -m pip install --upgrade pip >nul 2>nul
"%PY_EXE%" -m pip install -r "%~dp0requirements.txt"

:LAUNCH
echo [OK] Iniciando iRacing HUD Overlay Suite v3.5 Supreme (Blender 3D Edition)...
start "" "%PYW_EXE%" "%~dp0main.py" --autostart
exit /b 0
