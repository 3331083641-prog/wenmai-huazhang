@echo off
setlocal
set PROJECT_ROOT=D:\wenmai-huazhang
echo [1/5] Python
python --version
echo.
echo [2/5] Node
node --version
echo.
echo [3/5] npm
npm --version
echo.
echo [4/5] Torch / CUDA
cd /d "%PROJECT_ROOT%\backend"
if exist venv\Scripts\python.exe (
  venv\Scripts\python.exe -c "import importlib.util; print('torchAvailable=', importlib.util.find_spec('torch') is not None); import torch; print('torchVersion=', torch.__version__); print('cudaAvailable=', torch.cuda.is_available()); print('cudaDevice=', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA')" 2^>nul || echo torch not installed or failed to import
) else (
  echo backend venv not found
)
echo.
echo [5/5] style_refs
for %%F in (zhuxianzhen.png bianxiu.png songhua.png qinghua.png jianzhi.png) do (
  if exist "%PROJECT_ROOT%\backend\style_refs\%%F" (echo OK backend\style_refs\%%F) else (echo MISSING backend\style_refs\%%F)
)
echo.
echo Start backend, then open http://127.0.0.1:8000/health
pause

