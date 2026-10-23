@echo off
setlocal enabledelayedexpansion
set PROJECT_ROOT=D:\wenmai-huazhang
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set TODAY=%%a%%b%%c
for /f "tokens=1-3 delims=:., " %%a in ("%time%") do set NOW=%%a%%b%%c
set TRASH=%PROJECT_ROOT%\_trash_backup\cleanup_!TODAY!_!NOW!
mkdir "!TRASH!" 2>nul
for /d /r "%PROJECT_ROOT%" %%D in (__pycache__) do if exist "%%D" move "%%D" "!TRASH!\" >nul
for /r "%PROJECT_ROOT%" %%F in (*.pyc) do move "%%F" "!TRASH!\" >nul
if exist "%PROJECT_ROOT%\frontend\dist" move "%PROJECT_ROOT%\frontend\dist" "!TRASH!\frontend_dist" >nul
echo Safe cleanup complete. Trash backup: !TRASH!
pause

