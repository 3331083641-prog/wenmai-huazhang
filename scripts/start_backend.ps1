$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot 'backend/venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) { throw '先按 README 创建 backend/venv 并安装依赖。' }
Set-Location (Join-Path $projectRoot 'backend')
& $python -m uvicorn app:app --host 127.0.0.1 --port 8000
