@echo off
cd /d D:\wenmai-huazhang\backend
set "PIP_CACHE_DIR=D:\wenmai-huazhang\.cache\pip"
set "HF_HOME=D:\wenmai-huazhang\.cache\huggingface"
set "HF_HUB_CACHE=D:\wenmai-huazhang\.cache\huggingface\hub"
set "TRANSFORMERS_CACHE=D:\wenmai-huazhang\.cache\transformers"
set "TORCH_HOME=D:\wenmai-huazhang\.cache\torch"
set "XDG_CACHE_HOME=D:\wenmai-huazhang\.cache"
set "LOCALAPPDATA=D:\wenmai-huazhang\.cache\localappdata"
set "TEMP=D:\wenmai-huazhang\.cache\temp"
set "TMP=D:\wenmai-huazhang\.cache\temp"
if not exist "D:\wenmai-huazhang\.cache\localappdata" mkdir "D:\wenmai-huazhang\.cache\localappdata"
if not exist "D:\wenmai-huazhang\.cache\temp" mkdir "D:\wenmai-huazhang\.cache\temp"
call venv\Scripts\activate
uvicorn app:app --host 127.0.0.1 --port 8000
