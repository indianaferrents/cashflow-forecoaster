@echo off

:: === Создание ярлыка на рабочем столе (только если его нет) ===
set "shortcut=%USERPROFILE%\Desktop\CashFlow Forecaster.lnk"
if not exist "%shortcut%" (
    powershell -command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\CashFlow Forecaster.lnk'); $s.TargetPath = '%~dp0cashflow_forecaster.bat'; $s.IconLocation = '%~dp0dashboard/icon.ico, 0'; $s.Save()"
)

:: === Запуск основного скрипта ===
powershell.exe -ExecutionPolicy Bypass -File "%~dp0cashflow_forecaster.ps1"
pause
