@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows_launcher.ps1" -Action setup
if errorlevel 1 echo Setup failed. Read the message above.
pause
