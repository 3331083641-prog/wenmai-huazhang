@echo off
setlocal
set "ROOT=D:\wenmai-huazhang"
set "LOG=%ROOT%\logs\dashscope_retry_after_network_fix.log"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='D:\wenmai-huazhang\backend\.env'; $t=[IO.File]::ReadAllText($p,[Text.Encoding]::UTF8); $t=[regex]::Replace($t,'(?m)^GENERATION_PROVIDER=.*$','GENERATION_PROVIDER=dashscope_wanx'); [IO.File]::WriteAllText($p,$t,(New-Object Text.UTF8Encoding($false)))"
cd /d "%ROOT%\backend"
call venv\Scripts\activate.bat
(
  echo [%date% %time%] GENERATION_PROVIDER=dashscope_wanx
  echo Please ensure backend is running: uvicorn app:app --reload --port 8000
  python scripts\diagnose_dashscope_network.py
  python scripts\test_dashscope_minimal.py
  python scripts\test_generate_provider.py
) >> "%LOG%" 2>&1
endlocal