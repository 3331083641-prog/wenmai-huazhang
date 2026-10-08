param([ValidateSet('setup','start','stop','check')][string]$Action='check', [switch]$NoBrowser)
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path -Parent $PSScriptRoot
$Runtime=Join-Path $ProjectRoot '.cache\windows_launcher'
$PythonExe=Join-Path $ProjectRoot 'backend\venv\Scripts\python.exe'
$StateFile=Join-Path $Runtime 'processes.json'
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
$env:NPM_CONFIG_CACHE=Join-Path $ProjectRoot '.cache\npm'
$env:PIP_CACHE_DIR=Join-Path $ProjectRoot '.cache\pip'
Set-Location -LiteralPath $ProjectRoot

function Port-Free([int]$Port) {
    return -not (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}
function Find-Port([int]$First,[int]$Last) {
    foreach ($Candidate in $First..$Last) { if (Port-Free $Candidate) { return $Candidate } }
    throw 'No free project service port. Please close only the conflicting application yourself.'
}
function Environment-Check {
    if (Get-Command python -ErrorAction SilentlyContinue) { & python --version } else { Write-Host 'Python missing: install Python 3.10+.' }
    if (Get-Command node -ErrorAction SilentlyContinue) { & node --version } else { Write-Host 'Node missing: install Node 20.19+ or 22.12+.' }
    Write-Host ('Python dependencies: '+(Test-Path $PythonExe))
    Write-Host ('Frontend dependencies: '+(Test-Path 'frontend\node_modules'))
    # Output only configuration presence. Never print environment values.
    $Config=Join-Path $ProjectRoot 'backend\.env'
    $KeyReady=$false
    if (Test-Path $Config) {
        $KeyReady=[bool](Get-Content -LiteralPath $Config | Where-Object { $_ -match '^DASHSCOPE_API_KEY\s*=\s*[^\s#]+' })
    }
    Write-Host ('Personal DashScope key configured: '+$KeyReady)
    if (-not $KeyReady) { Write-Host 'Saved cases remain available. Real generation requires YOUR paid DashScope service and personal API key.' }
    try {
        $Models=Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3
        Write-Host ('Local Qwen3-VL installed: '+[bool]($Models.models.name -contains 'qwen3-vl:4b-instruct-q4_K_M'))
    } catch { Write-Host 'Ollama not reachable. Saved cases remain available; live image analysis is unavailable.' }
}

if ($Action -eq 'check') { Environment-Check; exit 0 }
if ($Action -eq 'setup') {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Install Python 3.10+ first.' }
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Install Node 20.19+ or 22.12+ first.' }
    & python -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'"
    if ($LASTEXITCODE -ne 0) { throw 'Unsupported Python version.' }
    & node -e "let [a,b]=process.versions.node.split('.').map(Number);if(!((a===20&&b>=19)||(a===22&&b>=12)||a>22))process.exit(1)"
    if ($LASTEXITCODE -ne 0) { throw 'Unsupported Node version.' }
    if (-not (Test-Path $PythonExe)) { & python -m venv backend\venv; if ($LASTEXITCODE -ne 0) { throw 'Cannot create Python venv.' } }
    & $PythonExe -m pip install -r backend\requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency install failed.' }
    Push-Location frontend
    try { & npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' } } finally { Pop-Location }
    if (-not (Test-Path 'backend\.env')) { Copy-Item -LiteralPath 'backend\.env.example' -Destination 'backend\.env' }
    & $PythonExe scripts\prepare_style_assets.py
    if ($LASTEXITCODE -ne 0) { throw 'Style asset preparation failed.' }
    Environment-Check
    Write-Host 'Setup complete. Configure backend/.env privately, then double-click start_windows.cmd. No models were downloaded.'
    exit 0
}
if ($Action -eq 'stop') {
    if (-not (Test-Path $StateFile)) { Write-Host 'No recorded project processes.'; exit 0 }
    $State=Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
    foreach ($Recorded in $State.processes) {
        $Running=Get-Process -Id $Recorded.id -ErrorAction SilentlyContinue
        # Creation time prevents stopping an unrelated process if a PID was reused.
        if ($Running -and $Running.StartTime.ToUniversalTime().ToString('o') -eq $Recorded.started) {
            Stop-Process -Id $Recorded.id
            Write-Host ('Stopped project process '+$Recorded.id)
        }
    }
    Remove-Item -LiteralPath $StateFile
    Write-Host 'Ollama and other projects were not stopped.'
    exit 0
}
if (Test-Path $StateFile) {
    $Prior=Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
    $Alive=@($Prior.processes | Where-Object { $P=Get-Process -Id $_.id -ErrorAction SilentlyContinue; $P -and $P.StartTime.ToUniversalTime().ToString('o') -eq $_.started })
    if ($Alive.Count) { Write-Host 'This launcher already has running project services. Use stop_windows.cmd first.'; exit 0 }
}
if (-not (Test-Path $PythonExe) -or -not (Test-Path 'frontend\node_modules')) { throw 'Run setup_windows.cmd first.' }
$ApiPort=Find-Port 8000 8010
$WebPort=Find-Port 5173 5174
$Processes=@()
try {
    $Backend=Start-Process -FilePath $PythonExe -ArgumentList @('-m','uvicorn','app:app','--host','127.0.0.1','--port',"$ApiPort") -WorkingDirectory (Join-Path $ProjectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Runtime 'backend.out.log') -RedirectStandardError (Join-Path $Runtime 'backend.err.log')
    $Processes+=@{id=$Backend.Id;started=$Backend.StartTime.ToUniversalTime().ToString('o')}
    $Ready=$false
    for ($Attempt=0;$Attempt -lt 12;$Attempt++) {
        try { $Health=Invoke-RestMethod "http://127.0.0.1:$ApiPort/health" -TimeoutSec 10; $Ready=$true; break } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $Ready) { throw 'Backend health check failed. See project launcher logs.' }
    $env:VITE_API_BASE_URL="http://127.0.0.1:$ApiPort"
    # Run Vite directly to track its real PID, not a transient npm/cmd parent.
    $Frontend=Start-Process -FilePath (Get-Command node).Source -ArgumentList @('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',"$WebPort",'--strictPort') -WorkingDirectory (Join-Path $ProjectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Runtime 'frontend.out.log') -RedirectStandardError (Join-Path $Runtime 'frontend.err.log')
    $Processes+=@{id=$Frontend.Id;started=$Frontend.StartTime.ToUniversalTime().ToString('o')}
    $WebReady=$false
    for ($Attempt=0;$Attempt -lt 25;$Attempt++) {
        try { $null=Invoke-WebRequest "http://127.0.0.1:$WebPort" -UseBasicParsing -TimeoutSec 3; $WebReady=$true; break } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $WebReady) { throw 'Frontend startup failed. See project launcher logs.' }
    @{processes=$Processes;apiPort=$ApiPort;webPort=$WebPort}|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $StateFile -Encoding UTF8
    Write-Host "Product ready: http://127.0.0.1:$WebPort/gallery"
    Write-Host ('Qwen Image configuration ready: '+$Health.providers.dashscope_qwen_image.available)
    Write-Host ('Qwen3-VL local ready: '+$Health.localVisionAnalysis.available)
    if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$WebPort/gallery" }
} catch {
    foreach ($Recorded in $Processes) { $P=Get-Process -Id $Recorded.id -ErrorAction SilentlyContinue; if ($P -and $P.StartTime.ToUniversalTime().ToString('o') -eq $Recorded.started) { Stop-Process -Id $Recorded.id } }
    throw
}
