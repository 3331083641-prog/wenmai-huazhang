@echo off
setlocal
set PROJECT_ROOT=D:\wenmai-huazhang
set HF_HOME=%PROJECT_ROOT%\.cache\huggingface
set HF_HUB_CACHE=%PROJECT_ROOT%\.cache\huggingface\hub
set HUGGINGFACE_HUB_CACHE=%PROJECT_ROOT%\.cache\huggingface\hub
set TRANSFORMERS_CACHE=%PROJECT_ROOT%\.cache\transformers
set TORCH_HOME=%PROJECT_ROOT%\.cache\torch
set XDG_CACHE_HOME=%PROJECT_ROOT%\.cache
set PIP_CACHE_DIR=%PROJECT_ROOT%\.cache\pip
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"
cd /d "%PROJECT_ROOT%\backend"
call venv\Scripts\activate.bat
uvicorn app:app --reload --port 8000 >> "%PROJECT_ROOT%\logs\backend_real_instantstyle.log" 2>&1