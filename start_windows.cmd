@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows_launcher.ps1" -Action start
if errorlevel 1 echo Startup failed. Read the message above.
pause
