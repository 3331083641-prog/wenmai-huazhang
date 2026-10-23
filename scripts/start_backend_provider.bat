@echo off
set "PROJECT_ROOT=D:\wenmai-huazhang"
set "HF_HOME=D:\wenmai-huazhang\.cache\huggingface"
set "HF_HUB_CACHE=D:\wenmai-huazhang\.cache\huggingface\hub"
set "TRANSFORMERS_CACHE=D:\wenmai-huazhang\.cache\transformers"
set "TORCH_HOME=D:\wenmai-huazhang\.cache\torch"
set "XDG_CACHE_HOME=D:\wenmai-huazhang\.cache"
set "PIP_CACHE_DIR=D:\wenmai-huazhang\.cache\pip"
cd /d D:\wenmai-huazhang\backend
call venv\Scripts\activate.bat
uvicorn app:app --host 127.0.0.1 --port 8000 >> D:\wenmai-huazhang\logs\backend_provider.log 2>&1