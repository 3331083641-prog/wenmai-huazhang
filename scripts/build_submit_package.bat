@echo off
setlocal
set "ROOT=D:\wenmai-huazhang"
set "DEST=%ROOT%\release\wenmai-huazhang-submit"
set "ZIP=%ROOT%\release\wenmai-huazhang-submit.zip"
cd /d "%ROOT%\frontend"
call npm run build
if errorlevel 1 exit /b 1
if exist "%DEST%" rmdir /s /q "%DEST%"
if exist "%ZIP%" del /q "%ZIP%"
mkdir "%DEST%"
robocopy "%ROOT%\frontend" "%DEST%\frontend" /E /XD node_modules venv .git /XF .env .env.local *.log > nul
robocopy "%ROOT%\backend" "%DEST%\backend" /E /XD venv __pycache__ outputs .cache /XF .env *.pyc *.pyo *.log > nul
robocopy "%ROOT%\assets" "%DEST%\assets" /E > nul
robocopy "%ROOT%\docs" "%DEST%\docs" /E > nul
robocopy "%ROOT%\scripts" "%DEST%\scripts" /E > nul
copy "%ROOT%\README.md" "%DEST%\README.md" > nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%DEST%\*' -DestinationPath '%ZIP%' -Force"
echo Created %ZIP%
endlocal
