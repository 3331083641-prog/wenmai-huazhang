@echo off
setlocal enabledelayedexpansion
set "PROJECT_ROOT=D:\wenmai-huazhang"
set "LOG=%PROJECT_ROOT%\logs\frontend_backend_connection.log"
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"
echo ==== %date% %time% ====>> "%LOG%"
echo [1] netstat :8000>> "%LOG%"
netstat -ano | findstr :8000 >> "%LOG%" 2>&1
echo [2] curl /health>> "%LOG%"
curl -s -S http://127.0.0.1:8000/health >> "%LOG%" 2>&1
echo.>> "%LOG%"
echo [3] frontend .env.local>> "%LOG%"
type "%PROJECT_ROOT%\frontend\.env.local" >> "%LOG%" 2>&1
echo.>> "%LOG%"
for /f "tokens=1,* delims==" %%A in ('findstr /b "VITE_INSTANTSTYLE_API_URL=" "%PROJECT_ROOT%\frontend\.env.local"') do set "API_URL=%%B"
echo Current VITE_INSTANTSTYLE_API_URL=!API_URL!
echo Current VITE_INSTANTSTYLE_API_URL=!API_URL!>> "%LOG%"
echo Please restart frontend after changing .env.local: %PROJECT_ROOT%\scripts\start_frontend.bat
echo Please restart frontend after changing .env.local: %PROJECT_ROOT%\scripts\start_frontend.bat>> "%LOG%"
echo Log saved to %LOG%
