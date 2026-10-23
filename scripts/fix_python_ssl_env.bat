@echo off
setlocal
set "ROOT=D:\wenmai-huazhang"
set "LOG=%ROOT%\logs\fix_python_ssl_env.log"
cd /d "%ROOT%\backend"
call venv\Scripts\activate.bat
(
  echo [%date% %time%] Upgrade pip/certifi/requests/urllib3
  python -m pip install --upgrade pip
  pip install --upgrade certifi requests urllib3
  echo [%date% %time%] Install truststore optional
  pip install truststore
  if errorlevel 1 echo truststore install failed, continuing
  echo [%date% %time%] Install python-certifi-win32 optional
  pip install python-certifi-win32
  if errorlevel 1 echo python-certifi-win32 install failed, continuing
  echo [%date% %time%] Run DashScope network diagnosis
  python scripts\diagnose_dashscope_network.py
  echo [%date% %time%] Run DashScope minimal test
  python scripts\test_dashscope_minimal.py
) >> "%LOG%" 2>&1
endlocal