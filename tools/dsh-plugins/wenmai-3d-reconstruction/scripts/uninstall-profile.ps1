#requires -Version 5.1
<#
.SYNOPSIS
    Uninstall the wenmai-3d-reconstruction plugin from a DSH profile and restore
    the backups that install-profile.ps1 made.

.DESCRIPTION
    1. refuse the live `web` profile unless -AllowLive is passed;
    2. drop the package from dsh.profile.bundles (preserving every other entry);
    3. run `dsh plugin --profile <name> remove <pkg>` so pnpm removes the
       dependency and the node_modules link;
    4. restore package.json / cordis.patch.yml / pnpm-lock.yaml from the chosen
       backup directory (or the newest one), and say which files were restored;
    5. report every changed item; -Purge also deletes the (now plugin-free)
       profile directory so the next install starts from a clean slate.

.PARAMETER BackupDir
    Explicit backup folder. Defaults to the newest directory under
    <profile>\.backup\ that contains a manifest.json.

.NOTES
    Use -KeepDependency to restore the profile files from a backup while keeping
    the `link:`/`file:` dependency and its node_modules link in place — that is
    the right mode when a live profile is activated through a user-patch
    `insert` row (bundle entry and user-patch row are mutually exclusive; see
    install-profile.ps1 -SkipBundleAppend).

.EXAMPLE
    powershell -File scripts/uninstall-profile.ps1
    powershell -File scripts/uninstall-profile.ps1 -Profile wmtest -Purge
    powershell -File scripts/uninstall-profile.ps1 -Profile desktop -KeepDependency
#>
[CmdletBinding()]
param(
    [string]$Profile = 'wmtest',
    [string]$PluginPath = (Split-Path -Parent $PSScriptRoot),
    [string]$DshHome = '',
    [string]$DshCli = 'D:\deepseek\resources\runtime\cli\bin\dsh.cmd',
    [string]$ArtifactRoot = 'D:\wenmai-huazhang\outputs\wenmai-3d\tests',
    [string]$BackupDir = '',
    [switch]$AllowLive,
    [switch]$Purge,
    [switch]$KeepDependency
)

$ErrorActionPreference = 'Stop'
$changed = New-Object System.Collections.Generic.List[string]
$failed = $false

function Write-Head([string]$text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }
function Write-Ok([string]$text) { Write-Host "   [ok] $text" -ForegroundColor Green }
function Write-Warn2([string]$text) { Write-Host "   [warn] $text" -ForegroundColor Yellow }
function Write-Err2([string]$text) { Write-Host "   [fail] $text" -ForegroundColor Red; $script:failed = $true }

# UTF-8 without BOM: profile package.json must stay parseable by Node's JSON.parse.
function Write-Text([string]$Path, [string]$Text) {
    $dir = Split-Path -Parent $Path
    if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

function Invoke-Dsh {
    param([string[]]$DshArgs, [string]$LogFile)
    $tmp = [System.IO.Path]::GetTempFileName()
    $env:ELECTRON_RUN_AS_NODE = '1'
    try {
        & $DshCli @DshArgs *> $tmp
        $code = $LASTEXITCODE
        $text = if (Test-Path $tmp) { Get-Content -LiteralPath $tmp -Raw } else { '' }
    }
    finally {
        Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue
    }
    if ($LogFile) {
        Write-Text -Path $LogFile -Text $text
    }
    return [pscustomobject]@{ Code = $code; Text = $text }
}

# ------------------------------------------------------------------ preflight

Write-Head "preflight"
if ($Profile -eq 'web' -and -not $AllowLive) {
    Write-Err2 "refusing to touch the live 'web' profile without -AllowLive"
    exit 3
}
if (-not $DshHome) {
    $DshHome = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $HOME '.dsh' }
}
$DshHome = [System.IO.Path]::GetFullPath($DshHome)
$ProfileDir = Join-Path (Join-Path $DshHome 'profiles') $Profile
$pluginName = $null
$manifestPath = Join-Path $PluginPath 'package.json'
if (Test-Path -LiteralPath $manifestPath) {
    $pluginName = (Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json).name
}
$pkgPath = Join-Path $ProfileDir 'package.json'
$bundlesNow = @()
if (Test-Path -LiteralPath $pkgPath) {
    $pkg = Get-Content -LiteralPath $pkgPath -Raw | ConvertFrom-Json
    if ($pkg.dsh -and $pkg.dsh.profile -and $pkg.dsh.profile.bundles) { $bundlesNow = @($pkg.dsh.profile.bundles) }
}
if (-not $pluginName) {
    # fall back to whatever bundle name install left behind
    $candidate = @($bundlesNow | Where-Object { $_ -like 'wenmai*' }) | Select-Object -First 1
    if ($candidate) { $pluginName = $candidate }
}
Write-Ok "profile: $Profile  ->  $ProfileDir"
Write-Ok "plugin : $(if ($pluginName) { $pluginName } else { '<unknown>' })"

# --------------------------------------------------------------- choose backup

function Find-LatestBackup([string]$dir) {
    if (-not (Test-Path -LiteralPath $dir)) { return $null }
    $candidates = Get-ChildItem -LiteralPath $dir -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'manifest.json') } |
        Sort-Object Name -Descending
    return ($candidates | Select-Object -First 1)
}

$backupRoot = Join-Path $ProfileDir '.backup'
$backup = $null
if ($BackupDir) {
    if (Test-Path -LiteralPath $BackupDir) { $backup = Get-Item -LiteralPath $BackupDir }
    else { Write-Err2 "backup dir not found: $BackupDir" }
}
elseif (Test-Path -LiteralPath (Join-Path $backupRoot 'latest.txt')) {
    $latestName = (Get-Content -LiteralPath (Join-Path $backupRoot 'latest.txt') -Raw).Trim()
    $candidate = Join-Path $backupRoot $latestName
    if (Test-Path -LiteralPath $candidate) { $backup = Get-Item -LiteralPath $candidate }
}
if (-not $backup) { $backup = Find-LatestBackup $backupRoot }

if ($backup) { Write-Ok "backup : $($backup.FullName)" }
else { Write-Warn2 "no backup found; only the bundle entry and dependency will be removed" }

# ---------------------------------------------------------- remove the bundle

Write-Head "dsh.profile.bundles"
if ($pluginName -and (Test-Path -LiteralPath $pkgPath)) {
    $pkg = Get-Content -LiteralPath $pkgPath -Raw | ConvertFrom-Json
    $bundles = @()
    if ($pkg.dsh -and $pkg.dsh.profile -and $pkg.dsh.profile.bundles) { $bundles = @($pkg.dsh.profile.bundles) }
    if ($bundles -contains $pluginName) {
        $filtered = @($bundles | Where-Object { $_ -ne $pluginName })
        $pkg.dsh.profile | Add-Member -NotePropertyName bundles -NotePropertyValue $filtered -Force
        Write-Text -Path $pkgPath -Text (($pkg | ConvertTo-Json -Depth 20) + "`n")
        $changed.Add("bundle entry removed: $pluginName")
        Write-Ok "removed '$pluginName' from dsh.profile.bundles"
        Write-Host "   before: [$($bundles -join ', ')]"
        Write-Host "   after : [$($filtered -join ', ')]"
    }
    else {
        Write-Warn2 "'$pluginName' is not in dsh.profile.bundles (nothing to remove)"
    }
}
else {
    Write-Warn2 "no profile package.json / plugin name; skipping bundle edit"
}

# ---------------------------------------------------------- remove dependency

Write-Head "dsh plugin remove"
$dependencyRemoved = $false
if ($pluginName -and -not $KeepDependency) {
    $stampLog = Get-Date -Format 'yyyyMMdd-HHmmss'
    $logFile = Join-Path (Join-Path $ArtifactRoot 'install-logs') "uninstall-$Profile-$stampLog.log"
    $result = Invoke-Dsh -DshArgs @('plugin', '--profile', $Profile, 'remove', $pluginName) -LogFile $logFile
    if ($result.Code -eq 0) {
        Write-Ok "dsh plugin remove succeeded (log: $logFile)"
        $changed.Add("dependency removed: $pluginName")
        $dependencyRemoved = $true
    }
    else {
        Write-Warn2 "dsh plugin remove exited $($result.Code); continuing (backup restore may supersede it)"
        ($result.Text -split "`r?`n" | Where-Object { $_ -match '\S' } | Select-Object -Last 8) | ForEach-Object { Write-Host "        $_" }
    }
}
else {
    Write-Warn2 "-KeepDependency: leaving node_modules and the dependency entry alone"
}

# ---------------------------------------------------------------- restore

Write-Head "restore"
if ($backup) {
    $restored = @()
    foreach ($name in @('package.json', 'cordis.patch.yml', 'pnpm-lock.yaml')) {
        $src = Join-Path $backup.FullName $name
        if (-not (Test-Path -LiteralPath $src)) { continue }
        $dst = Join-Path $ProfileDir $name
        $same = $false
        if (Test-Path -LiteralPath $dst) {
            $same = (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash
        }
        if ($same) {
            Write-Ok "$name already identical to the backup"
        }
        else {
            Copy-Item -LiteralPath $src -Destination $dst -Force
            $restored += $name
            $changed.Add("restored: $name")
            Write-Ok "restored $name"
        }
    }
    if ($restored.Count -eq 0) { Write-Warn2 "nothing needed restoring" }
}
else {
    Write-Warn2 "no backup to restore"
}

# ------------------------------------------------------------------- purge

if ($Purge) {
    Write-Head "purge"
    if (Test-Path -LiteralPath $ProfileDir) {
        $leftovers = @()
        if ($pluginName) {
            $link = Join-Path (Join-Path $ProfileDir 'node_modules') $pluginName
            if (Test-Path -LiteralPath $link) { $leftovers += $link }
        }
        Remove-Item -LiteralPath $ProfileDir -Recurse -Force
        $changed.Add("profile directory deleted: $ProfileDir")
        Write-Ok "deleted $ProfileDir"
    }
    else {
        Write-Warn2 "profile directory already gone"
    }
}

# ------------------------------------------------------------------ summary

Write-Head "summary"
if ($changed.Count -eq 0) { Write-Host "   no changes were required" }
else { foreach ($item in $changed) { Write-Host "   - $item" } }
Write-Host "   profile dir: $ProfileDir"
Write-Host "   backup used: $(if ($backup) { $backup.FullName } else { '<none>' })"

$link = if ($pluginName) { Join-Path (Join-Path $ProfileDir 'node_modules') $pluginName } else { $null }
if (-not $dependencyRemoved -and $link -and (Test-Path -LiteralPath $link)) {
    # -KeepDependency (or a failed pnpm step): leave the link exactly as it was.
    Write-Warn2 "-KeepDependency: the node_modules link was left in place: $link"
}
elseif ($link -and (Test-Path -LiteralPath $link)) {
    # pnpm can leave the hoisted link/junction behind after `remove`. Deleting a
    # reparse point with .NET removes the LINK only (never the plugin sources);
    # a real directory copy is reported instead of deleted.
    $item = Get-Item -LiteralPath $link -Force -ErrorAction SilentlyContinue
    $isLink = $item -and (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
    if ($isLink) {
        try {
            [System.IO.Directory]::Delete($link, $false)
            $changed.Add("stale node_modules link removed: $link")
            Write-Ok "removed the stale node_modules link (reparse point only)"
        }
        catch {
            Write-Warn2 "could not remove the stale link: $($_.Exception.Message)"
        }
    }
    else {
        Write-Warn2 "plugin path is a real directory (not a link) and was left in place: $link"
    }
}

if ($failed) {
    Write-Host ""
    Write-Host "uninstall: FAIL" -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "uninstall: PASS" -ForegroundColor Green
exit 0
