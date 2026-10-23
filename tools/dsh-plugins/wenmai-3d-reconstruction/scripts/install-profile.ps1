#requires -Version 5.1
<#
.SYNOPSIS
    Install the wenmai-3d-reconstruction plugin into one DSH profile, safely.

.DESCRIPTION
    Order of operations (each step is idempotent):

      1. refuse the live `web` profile unless -AllowLive is passed;
      2. back up <profile>\package.json, cordis.patch.yml and pnpm-lock.yaml to
         <profile>\.backup\<yyyyMMdd-HHmmss>\ (plus manifest.json);
      3. run `dsh plugin --profile <name> add <pluginPath>` (this is the
         transactional install: dsh validates the bundle patch and rolls the
         profile back on failure);
      4. append the package to dsh.profile.bundles when the CLI did not, keeping
         the existing order and never duplicating;
      5. print a diff-style summary of exactly what changed.

.PARAMETER Profile
    Target profile name. Defaults to `wmtest`, the isolated verification profile.

.PARAMETER DshHome
    Override DSH_HOME (defaults to $env:DSH_HOME, else $HOME\.dsh). Use a scratch
    directory to prove the bundle path without touching the user's own profiles.

.PARAMETER AllowLive
    Permit installing into the live `web` profile. Off by default on purpose.

.NOTES
    Two activation routes exist and they are MUTUALLY EXCLUSIVE:

      * bundle entry  - the package name in <profile>\package.json
                        `dsh.profile.bundles`; needs a harness restart to take
                        effect (this script maintains it by default);
      * user patch    - an `- insert:` row for the plugin inside
                        <profile>\cordis.patch.yml; activates in-process.

    Listing the plugin in BOTH can mount it twice. The live `desktop` profile
    deliberately uses only the user-patch row, so install into it with
    `-SkipBundleAppend`; the script warns when it detects both.

.EXAMPLE
    powershell -File scripts/install-profile.ps1
    powershell -File scripts/install-profile.ps1 -DshHome D:\tmp\dsh-home
    powershell -File scripts/install-profile.ps1 -Profile desktop -SkipBundleAppend
#>
[CmdletBinding()]
param(
    [string]$Profile = 'wmtest',
    [string]$PluginPath = (Split-Path -Parent $PSScriptRoot),
    [string]$DshHome = '',
    [string]$DshCli = 'D:\deepseek\resources\runtime\cli\bin\dsh.cmd',
    [string]$ArtifactRoot = 'D:\wenmai-huazhang\outputs\wenmai-3d\tests',
    [switch]$AllowLive,
    [switch]$SkipBackup,
    [switch]$SkipBundleAppend
)

# Native commands (dsh/pnpm) legitimately write progress to stderr; with
# ErrorActionPreference = Stop that becomes a terminating NativeCommandError.
# Every dsh call is captured to a temp file and judged by its exit code.
$ErrorActionPreference = 'Continue'
$script:failed = $false

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
if (-not (Test-Path -LiteralPath $DshCli)) {
    Write-Err2 "dsh CLI not found: $DshCli"
    exit 3
}
$PluginPath = (Resolve-Path -LiteralPath $PluginPath).Path
$manifestPath = Join-Path $PluginPath 'package.json'
if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Err2 "not a plugin package (no package.json): $PluginPath"
    exit 3
}
$pluginManifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$pluginName = $pluginManifest.name
if (-not $pluginName) {
    Write-Err2 "package.json has no name"
    exit 3
}

$patchRel = $null
if ($pluginManifest.dsh -and $pluginManifest.dsh.bundle -and $pluginManifest.dsh.bundle.patch) {
    $patchRel = [string]$pluginManifest.dsh.bundle.patch
}
if (-not $patchRel) {
    Write-Err2 "package.json does not declare dsh.bundle.patch - dsh will reject this install"
    exit 3
}
$patchFile = Join-Path $PluginPath $patchRel
if (-not (Test-Path -LiteralPath $patchFile)) {
    Write-Err2 "bundle patch declared but missing: $patchFile"
    exit 3
}
$patchText = Get-Content -LiteralPath $patchFile -Raw
$patchId = $null
if ($patchText -match '(?m)^\s*-\s*id:\s*(?<id>[^\s#]+)') { $patchId = $Matches['id'] }
Write-Ok "plugin: $pluginName"
Write-Ok "bundle patch: $patchRel$(if ($patchId) { " (row id: $patchId)" } else { ' (no id found!)' })"
if (-not $patchId) { Write-Warn2 "the bundle patch has no 'id:' row; verify-bundle.ps1 will not be able to assert it" }

if (-not $DshHome) {
    $DshHome = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $HOME '.dsh' }
}
$DshHome = [System.IO.Path]::GetFullPath($DshHome)
$ProfileDir = Join-Path (Join-Path $DshHome 'profiles') $Profile
Write-Ok "profile: $Profile  ->  $ProfileDir"

# ------------------------------------------------------------------- backup

$backupDir = $null
$bundlesBefore = @()
if (Test-Path -LiteralPath $ProfileDir) {
    $pkgPath = Join-Path $ProfileDir 'package.json'
    if (Test-Path -LiteralPath $pkgPath) {
        $existing = Get-Content -LiteralPath $pkgPath -Raw | ConvertFrom-Json
        if ($existing.dsh -and $existing.dsh.profile -and $existing.dsh.profile.bundles) {
            $bundlesBefore = @($existing.dsh.profile.bundles)
        }
    }
    if (-not $SkipBackup) {
        Write-Head "backup"
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $backupDir = Join-Path (Join-Path $ProfileDir '.backup') $stamp
        New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
        $saved = @()
        foreach ($name in @('package.json', 'cordis.patch.yml', 'pnpm-lock.yaml')) {
            $src = Join-Path $ProfileDir $name
            if (Test-Path -LiteralPath $src) {
                Copy-Item -LiteralPath $src -Destination (Join-Path $backupDir $name) -Force
                $saved += $name
            }
        }
        $manifest = [ordered]@{
            profile     = $Profile
            profileDir  = $ProfileDir
            pluginName  = $pluginName
            pluginPath  = $PluginPath
            createdAt   = (Get-Date).ToString('o')
            savedFiles  = $saved
            bundlesBefore = $bundlesBefore
        }
        $manifest | ConvertTo-Json -Depth 8 | ForEach-Object { Write-Text -Path (Join-Path $backupDir 'manifest.json') -Text $_ }
        Write-Text -Path (Join-Path (Join-Path $ProfileDir '.backup') 'latest.txt') -Text $stamp
        Write-Ok "backed up $($saved.Count) file(s) to $backupDir"
    }
    else {
        Write-Warn2 "-SkipBackup: profile files are NOT backed up"
    }
}
else {
    Write-Warn2 "profile does not exist yet; dsh will initialise it (nothing to back up)"
}

# ------------------------------------------------------------------ install

Write-Head "dsh plugin add"
$logDir = Join-Path $ArtifactRoot 'install-logs'
$stampLog = Get-Date -Format 'yyyyMMdd-HHmmss'
$logFile = Join-Path $logDir "install-$Profile-$stampLog.log"
$result = Invoke-Dsh -DshArgs @('plugin', '--profile', $Profile, 'add', $PluginPath) -LogFile $logFile
$cliApplied = ($result.Code -eq 0)
if ($cliApplied) { Write-Ok "dsh plugin add succeeded (log: $logFile)" }
else {
    Write-Err2 "dsh plugin add failed with exit code $($result.Code)"
    ($result.Text -split "`r?`n" | Where-Object { $_ -match '\S' } | Select-Object -Last 12) | ForEach-Object { Write-Host "        $_" }
}

# -------------------------------------------------------- bundle reconcile

Write-Head "dsh.profile.bundles"
$pkgPath = Join-Path $ProfileDir 'package.json'
if (-not (Test-Path -LiteralPath $pkgPath)) {
    Write-Err2 "profile package.json not found after install: $pkgPath"
}
else {
    $pkg = Get-Content -LiteralPath $pkgPath -Raw | ConvertFrom-Json
    $bundlesNow = @()
    if ($pkg.dsh -and $pkg.dsh.profile -and $pkg.dsh.profile.bundles) {
        $bundlesNow = @($pkg.dsh.profile.bundles)
    }
    $cliAdded = $bundlesNow -contains $pluginName
    if ($SkipBundleAppend) {
        if ($cliAdded) {
            Write-Warn2 "-SkipBundleAppend: dsh already appended '$pluginName'; leaving it"
        }
        else {
            Write-Warn2 "-SkipBundleAppend: dsh.profile.bundles left untouched (activate via a user-layer patch row)"
        }
    }
    elseif ($cliAdded) {
        Write-Ok "dsh already appended '$pluginName' to dsh.profile.bundles"
    }
    else {
        $updated = @($bundlesNow) + $pluginName
        if (-not $pkg.dsh) {
            $pkg | Add-Member -NotePropertyName dsh -NotePropertyValue ([pscustomobject]@{}) -Force
        }
        if (-not $pkg.dsh.profile) {
            $pkg.dsh | Add-Member -NotePropertyName profile -NotePropertyValue ([pscustomobject]@{}) -Force
        }
        $pkg.dsh.profile | Add-Member -NotePropertyName bundles -NotePropertyValue $updated -Force
        Write-Text -Path $pkgPath -Text (($pkg | ConvertTo-Json -Depth 20) + "`n")
        $bundlesNow = $updated
        Write-Ok "appended '$pluginName' to dsh.profile.bundles"
    }
    $dupes = @($bundlesNow | Group-Object | Where-Object Count -gt 1 | ForEach-Object Name)
    if ($dupes.Count -gt 0) { Write-Err2 "duplicate bundle entries: $($dupes -join ', ')" }
    else { Write-Ok "bundle list has no duplicates" }

    Write-Host ""
    Write-Host "   diff: dsh.profile.bundles" -ForegroundColor Cyan
    Write-Host "   before: [$($bundlesBefore -join ', ')]"
    Write-Host "   after : [$($bundlesNow -join ', ')]"
}

# A profile user patch that already inserts this plugin plus a bundle entry means
# the plugin can mount twice (duplicate ids). The two activation routes are
# mutually exclusive - pick exactly one.
$userPatch = Join-Path $ProfileDir 'cordis.patch.yml'
if (Test-Path -LiteralPath $userPatch) {
    $patchText2 = Get-Content -LiteralPath $userPatch -Raw
    $patchMentions = $patchText2 -match [regex]::Escape($pluginName)
    $inBundles = $false
    if (Test-Path -LiteralPath $pkgPath) {
        $check = Get-Content -LiteralPath $pkgPath -Raw | ConvertFrom-Json
        if ($check.dsh -and $check.dsh.profile -and $check.dsh.profile.bundles) {
            $inBundles = @($check.dsh.profile.bundles) -contains $pluginName
        }
    }
    if ($patchMentions -and $inBundles) {
        Write-Warn2 "DUPLICATE ACTIVATION RISK: '$pluginName' is listed in dsh.profile.bundles AND referenced by $userPatch."
        Write-Warn2 "  The two routes are mutually exclusive: keep the bundle entry (needs a harness restart)"
        Write-Warn2 "  or remove the user-patch insert row (activates in-process). Remove one before starting the GUI."
        Write-Warn2 "  Re-run with -SkipBundleAppend to keep only the user-layer row."
    }
    elseif ($patchMentions) {
        Write-Ok "user patch already activates the plugin; consider -SkipBundleAppend to avoid a second row"
    }
}

# ------------------------------------------------------------------ summary

$dependency = $null
if (Test-Path -LiteralPath $pkgPath) {
    $finalPkg = Get-Content -LiteralPath $pkgPath -Raw | ConvertFrom-Json
    if ($finalPkg.dependencies -and $finalPkg.dependencies.$pluginName) {
        $dependency = [string]$finalPkg.dependencies.$pluginName
    }
}
$nodeModulesLink = Join-Path (Join-Path $ProfileDir 'node_modules') $pluginName

Write-Head "summary"
Write-Host "   profile          : $Profile"
Write-Host "   profile dir      : $ProfileDir"
Write-Host "   plugin           : $pluginName"
Write-Host "   dependency spec  : $(if ($dependency) { $dependency } else { '<not in dependencies>' })"
Write-Host "   node_modules link: $(if (Test-Path -LiteralPath $nodeModulesLink) { 'present' } else { 'MISSING' })"
Write-Host "   backup dir       : $(if ($backupDir) { $backupDir } else { '<none>' })"
Write-Host "   pnpm log         : $logFile"

if (-not $cliApplied) { exit 1 }
if (-not (Test-Path -LiteralPath $nodeModulesLink)) { Write-Err2 "package link missing after install"; exit 1 }
Write-Host ""
Write-Host "install: PASS" -ForegroundColor Green
exit 0
