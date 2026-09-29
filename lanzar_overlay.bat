@echo off
:: Comprobar si tenemos permisos de administrador
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"

if '%errorlevel%' NEQ '0' (
    echo Solicitando permisos de administrador...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params = %*:"=""
    echo UAC.ShellExecute "cmd.exe", "/c %~s0 %params%", "", "runas", 1 >> "%temp%\getadmin.vbs"

    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    pushd "%~dp0"
    echo Lanzando iRacing Overlays como Administrador...
    
    :: Ejecutar panel de control (priorizar ejecutable compilado v3.0 RaceLab Pro)
    if exist ".\dist\iRacingRaceLabPro.exe" (
        start "" ".\dist\iRacingRaceLabPro.exe"
    ) else if exist ".\iRacingRaceLabPro.exe" (
        start "" ".\iRacingRaceLabPro.exe"
    ) else if exist ".\dist\iRacingOverlay.exe" (
        start "" ".\dist\iRacingOverlay.exe"
    ) else if exist ".\iRacingOverlay.exe" (
        start "" ".\iRacingOverlay.exe"
    ) else (
        start "" ".\.venv\Scripts\pythonw.exe" "main.py"
    )
    
    echo Panel de control de Overlays iniciado en segundo plano.
    exit
