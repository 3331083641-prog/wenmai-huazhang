#requires -Version 5.1
<#
.SYNOPSIS
    Prove the dsh bundle-patch mechanism offline: install the plugin into an
    isolated `wmtest` profile, compose the tree with `--dump-config`, and assert
    the plugin row is really there.

.DESCRIPTION
    This never touches the live `web` profile. It:

      1. checks preconditions (lib/index.js built, cordis.patch.yml present);
      2. refreshes an isolated profile (default name `wmtest`, optionally inside a
         throw-away DSH_HOME) so no stale plugin row can survive;
      3. installs the plugin (install-profile.ps1);
      4. runs `dsh --profile <name> --dump-config` and asserts:
           - exit code 0 and no error line in the output;
           - the composed YAML contains the plugin row id (`- id: <patchId>`);
           - the composed YAML contains the package name;
           - the row appears exactly once (no duplication);
      5. negative control: uninstall, then re-compose and assert the row is GONE
         (i.e. it came from this bundle, not from a leftover profile edit);
      6. removes the throw-away profile again and writes
         bundle-verify-<stamp>.json/.md evidence.

    Exit codes: 0 pass, 1 fail, 2 not ready (build/patch missing), 3 precondition.

.EXAMPLE
    powershell -File scripts/verify-bundle.ps1
    powershell -File scripts/verify-bundle.ps1 -DshHome D:\wenmai-huazhang\outputs\wenmai-3d\tests\dsh-home
#>
[CmdletBinding()]
param(
    [string]$Profile = 'wmtest',
    [string]$PluginPath = (Split-Path -Parent $PSScriptRoot),
    [string]$DshHome = '',
    [string]$DshCli = 'D:\deepseek\resources\runtime\cli\bin\dsh.cmd',
    [string]$ArtifactRoot = 'D:\wenmai-huazhang\outputs\wenmai-3d\tests',
    [switch]$KeepInstalled,
    [switch]$SkipRemoveCheck
)

# Native commands (dsh/pnpm) legitimately write progress to stderr; with
# ErrorActionPreference = Stop that becomes a terminating NativeCommandError.
# Every call below is captured to a temp file and judged by its exit code.
$ErrorActionPreference = 'Continue'

$script:checks = New-Object System.Collections.Generic.List[object]
$script:startedAt = (Get-Date).ToString('o')
$script:dshVersion = ''
$script:patchId = $null
$script:pluginName = $null
$script:installCode = $null
$script:dumpCode = $null
$script:dumpAfterUninstallCode = $null
$script:rowExcerpt = $null
$script:stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$script:liveHome = $false

function Write-Head([string]$text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }
function Write-Ok([string]$text) { Write-Host "   [ok] $text" -ForegroundColor Green }
function Write-Err2([string]$text) { Write-Host "   [fail] $text" -ForegroundColor Red }
function Write-Warn2([string]$text) { Write-Host "   [warn] $text" -ForegroundColor Yellow }

function Add-Check([string]$name, [bool]$ok, [string]$detail) {
    $script:checks.Add([pscustomobject]@{ name = $name; ok = $ok; detail = $detail })
    if ($ok) { Write-Ok "$name" } else { Write-Err2 "$name - $detail" }
}

# UTF-8 without BOM: composed YAML is read back by the dsh loader / graders.
function Write-Text([string]$Path, [string]$Text) {
    $dir = Split-Path -Parent $Path
    if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

function Invoke-Dsh {
    param([string[]]$DshArgs)
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
    if ($null -eq $text) { $text = '' }
    return [pscustomobject]@{ Code = $code; Text = [string]$text }
}

# Run one of the sibling profile scripts in its own PowerShell process and judge
# it by exit code (its stderr carries ordinary progress output).
function Invoke-ChildScript {
    param([string]$Path, [string[]]$ChildArgs)
    $tmp = [System.IO.Path]::GetTempFileName()
    try {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Path @ChildArgs *> $tmp
        $code = $LASTEXITCODE
        $text = if (Test-Path $tmp) { Get-Content -LiteralPath $tmp -Raw } else { '' }
    }
    finally {
        Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue
    }
    if ($null -eq $text) { $text = '' }
    return [pscustomobject]@{ Code = $code; Text = [string]$text }
}

function Save-Evidence([string]$status) {
    $payload = [ordered]@{
        kind                   = 'bundle-verify'
        status                 = $status
        startedAt              = $script:startedAt
        finishedAt             = (Get-Date).ToString('o')
        profile                = $Profile
        dshHome                = $DshHome
        liveHome               = $script:liveHome
        pluginPath             = $PluginPath
        dshCli                 = $DshCli
        dshVersion             = $script:dshVersion
        pluginName             = $script:pluginName
        patchId                = $script:patchId
        installCode            = $script:installCode
        dumpCode               = $script:dumpCode
        dumpAfterUninstallCode = $script:dumpAfterUninstallCode
        checks                 = $script:checks.ToArray()
        rowExcerpt             = $script:rowExcerpt
    }
    $jsonPath = Join-Path $ArtifactRoot "bundle-verify-$($script:stamp).json"
    $mdPath = Join-Path $ArtifactRoot "bundle-verify-$($script:stamp).md"
    Write-Text -Path $jsonPath -Text (($payload | ConvertTo-Json -Depth 8) + "`n")

    $md = New-Object System.Collections.Generic.List[string]
    $md.Add('# Bundle verification - wenmai-3d-reconstruction')
    $md.Add('')
    $md.Add("- status: **$status**")
    $md.Add("- at: $($script:startedAt) -> $($payload.finishedAt)")
    $md.Add("- profile: ``$Profile``")
    $md.Add("- DSH_HOME: ``$DshHome`` (live home: $($script:liveHome))")
    $md.Add("- dsh: ``$DshCli`` version ``$($script:dshVersion)``")
    $md.Add("- plugin: ``$($script:pluginName)``, patch row id ``$($script:patchId)``")
    $md.Add("- install exit: $($script:installCode); dump exit: $($script:dumpCode); dump-after-uninstall exit: $($script:dumpAfterUninstallCode)")
    $md.Add('')
    $md.Add('| check | result | detail |')
    $md.Add('|---|---|---|')
    foreach ($c in $script:checks) {
        $verdict = 'PASS'
        if (-not $c.ok) { $verdict = '**FAIL**' }
        $detail = ([string]$c.detail).Replace('|', '\|').Replace("`r", ' ').Replace("`n", ' ')
        $md.Add("| $($c.name) | $verdict | $detail |")
    }
    $md.Add('')
    if ($script:rowExcerpt) {
        $md.Add('## Plugin row found in the composed tree')
        $md.Add('')
        $md.Add('```yaml')
        $md.Add([string]$script:rowExcerpt)
        $md.Add('```')
        $md.Add('')
    }
    Write-Text -Path $mdPath -Text (($md -join "`n") + "`n")
    Write-Host ""
    Write-Host "   evidence: $jsonPath"
    Write-Host "   evidence: $mdPath"
}

function Fail-Exit([string]$status, [int]$code) {
    Save-Evidence $status
    Write-Host ""
    Write-Host "verify-bundle: $($status.ToUpper())" -ForegroundColor Red
    exit $code
}

# ------------------------------------------------------------------ preflight

Write-Head "preflight"
$PluginPath = (Resolve-Path -LiteralPath $PluginPath).Path
$manifestPath = Join-Path $PluginPath 'package.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { Write-Err2 "no package.json: $PluginPath"; exit 3 }
$pluginManifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$script:pluginName = $pluginManifest.name

$patchRel = $null
if ($pluginManifest.dsh -and $pluginManifest.dsh.bundle -and $pluginManifest.dsh.bundle.patch) {
    $patchRel = [string]$pluginManifest.dsh.bundle.patch
}
if (-not $patchRel) { Write-Err2 "package.json does not declare dsh.bundle.patch"; exit 3 }
$patchFile = Join-Path $PluginPath $patchRel
if (-not (Test-Path -LiteralPath $patchFile)) {
    Write-Warn2 "bundle patch missing: $patchFile"
    Save-Evidence 'not_ready'
    exit 2
}
if (-not (Test-Path -LiteralPath (Join-Path $PluginPath 'lib\index.js'))) {
    Write-Warn2 "lib/index.js is not built yet"
    Save-Evidence 'not_ready'
    exit 2
}
$patchText = Get-Content -LiteralPath $patchFile -Raw
if ($patchText -match '(?m)-\s*id:\s*(?<id>[^\s#]+)') { $script:patchId = $Matches['id'] }
if (-not $script:patchId) {
    Write-Warn2 "the bundle patch contains no '- id:' row"
    Save-Evidence 'fail'
    exit 1
}
Write-Ok "plugin: $($script:pluginName), patch row id: $($script:patchId)"

if ($Profile -eq 'web') { Write-Err2 "verify-bundle refuses the live web profile"; exit 3 }

$version = Invoke-Dsh -DshArgs @('--version')
$script:dshVersion = (($version.Text -split "`r?`n") | Where-Object { $_ -match '\S' } | Select-Object -First 1)
Write-Ok "dsh version: $($script:dshVersion)"

if ($DshHome) {
    $DshHome = [System.IO.Path]::GetFullPath($DshHome)
    $env:DSH_HOME = $DshHome
    Write-Ok "isolated DSH_HOME: $DshHome"
}
else {
    $DshHome = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $HOME '.dsh' }
    $script:liveHome = $true
    Write-Ok "DSH_HOME: $DshHome (live home)"
}
$ProfileDir = Join-Path (Join-Path $DshHome 'profiles') $Profile
$installScript = Join-Path (Join-Path $PluginPath 'scripts') 'install-profile.ps1'
$uninstallScript = Join-Path (Join-Path $PluginPath 'scripts') 'uninstall-profile.ps1'

# ------------------------------------------------------------------ refresh

Write-Head "refresh the isolated profile"
if (Test-Path -LiteralPath $ProfileDir) {
    $refresh = Invoke-ChildScript -Path $uninstallScript -ChildArgs @('-Profile', $Profile, '-PluginPath', $PluginPath, '-DshHome', $DshHome, '-DshCli', $DshCli, '-ArtifactRoot', $ArtifactRoot, '-Purge')
    ($refresh.Text -split "`r?`n") | Where-Object { $_ -match '\S' } | ForEach-Object { Write-Host "   $_" }
    if ($refresh.Code -ne 0) { Write-Warn2 "uninstall exited $($refresh.Code) during refresh" }
    if (Test-Path -LiteralPath $ProfileDir) {
        Write-Warn2 "profile dir still present after purge; deleting it directly"
        Remove-Item -LiteralPath $ProfileDir -Recurse -Force
    }
}
Write-Ok "no pre-existing profile state: $ProfileDir"

# ------------------------------------------------------------------ install

Write-Head "install"
$install = Invoke-ChildScript -Path $installScript -ChildArgs @('-Profile', $Profile, '-PluginPath', $PluginPath, '-DshHome', $DshHome, '-DshCli', $DshCli, '-ArtifactRoot', $ArtifactRoot)
$script:installCode = $install.Code
($install.Text -split "`r?`n") | Where-Object { $_ -match '\S' } | ForEach-Object { Write-Host "   $_" }
Add-Check 'install-profile.ps1 exits 0' ($script:installCode -eq 0) "exit=$($script:installCode)"

$profilePkg = Join-Path $ProfileDir 'package.json'
if (Test-Path -LiteralPath $profilePkg) {
    $pkg = Get-Content -LiteralPath $profilePkg -Raw | ConvertFrom-Json
    $bundles = @()
    if ($pkg.dsh -and $pkg.dsh.profile -and $pkg.dsh.profile.bundles) { $bundles = @($pkg.dsh.profile.bundles) }
    Add-Check 'profile manifest lists the plugin bundle' ($bundles -contains $script:pluginName) "bundles=[$($bundles -join ', ')]"
    $spec = $null
    if ($pkg.dependencies) { $spec = [string]$pkg.dependencies.($script:pluginName) }
    Add-Check 'profile depends on the plugin (link/file spec)' ([bool]$spec) "spec=$spec"
}
else {
    Add-Check 'profile manifest exists after install' $false $profilePkg
}
if ($script:installCode -ne 0) { Fail-Exit 'fail' 1 }

# --------------------------------------------------------------------- dump

Write-Head "dsh --profile $Profile --dump-config (after install)"
$dump = Invoke-Dsh -DshArgs @('--profile', $Profile, '--dump-config')
$script:dumpCode = $dump.Code
$dumpPath = Join-Path $ArtifactRoot "dump-config-$Profile-$($script:stamp).yml"
Write-Text -Path $dumpPath -Text $dump.Text
$dumpLines = @($dump.Text -split "`r?`n")
Write-Ok "dump written to $dumpPath ($($dumpLines.Count) lines)"
Add-Check '--dump-config exits 0' ($dump.Code -eq 0) "exit=$($dump.Code)"
if ($dump.Code -ne 0) {
    ($dumpLines | Where-Object { $_ -match '\S' } | Select-Object -Last 12) | ForEach-Object { Write-Host "        $_" }
    Fail-Exit 'fail' 1
}

$errorLines = @($dumpLines | Where-Object { $_ -match '^\s*(Error|error|ERR!|TypeError|SyntaxError)\b' })
Add-Check 'no error line in the composed output' ($errorLines.Count -eq 0) ($errorLines -join ' | ')

$idPattern = "id:\s*['`"]?" + [regex]::Escape([string]$script:patchId) + "['`"]?\s*$"
$idMatches = @($dumpLines | Where-Object { $_ -match $idPattern })
Add-Check "composed tree contains the plugin row id ($($script:patchId))" ($idMatches.Count -ge 1) "matches=$($idMatches.Count)"
Add-Check 'the plugin row appears exactly once' ($idMatches.Count -eq 1) "matches=$($idMatches.Count)"

$namePattern = "name:\s*['`"]?" + [regex]::Escape([string]$script:pluginName) + "['`"]?"
$nameMatches = @($dumpLines | Where-Object { $_ -match $namePattern })
Add-Check "composed tree references the package ($($script:pluginName))" ($nameMatches.Count -ge 1) "matches=$($nameMatches.Count)"

if ($idMatches.Count -ge 1) {
    $idx = [array]::IndexOf($dumpLines, $idMatches[0])
    $from = [Math]::Max(0, $idx - 1)
    $to = [Math]::Min($dumpLines.Count - 1, $idx + 8)
    $script:rowExcerpt = (($dumpLines[$from..$to]) -join "`n")
    Write-Host ""
    Write-Host "   composed row:" -ForegroundColor Cyan
    ($script:rowExcerpt -split "`n") | ForEach-Object { Write-Host "     $_" }
}

# --------------------------------------------------- prove the row can vanish

if (-not $SkipRemoveCheck -and -not $KeepInstalled) {
    Write-Head "negative control: uninstall, then re-compose"
    # No -Purge here: the profile must still exist so the second dump can compose.
    $uninstall = Invoke-ChildScript -Path $uninstallScript -ChildArgs @('-Profile', $Profile, '-PluginPath', $PluginPath, '-DshHome', $DshHome, '-DshCli', $DshCli, '-ArtifactRoot', $ArtifactRoot)
    ($uninstall.Text -split "`r?`n") | Where-Object { $_ -match '\S' } | ForEach-Object { Write-Host "   $_" }
    Add-Check 'uninstall-profile.ps1 exits 0' ($uninstall.Code -eq 0) "exit=$($uninstall.Code)"

    $dump2 = Invoke-Dsh -DshArgs @('--profile', $Profile, '--dump-config')
    $script:dumpAfterUninstallCode = $dump2.Code
    $dump2Path = Join-Path $ArtifactRoot "dump-config-$Profile-after-uninstall-$($script:stamp).yml"
    Write-Text -Path $dump2Path -Text $dump2.Text
    Add-Check '--dump-config still composes after uninstall' ($dump2.Code -eq 0) "exit=$($dump2.Code); dump: $dump2Path"
    $stillThere = ([string]$dump2.Text) -match [regex]::Escape([string]$script:patchId)
    Add-Check 'plugin row is gone after uninstall (it came from this bundle)' (-not $stillThere) "dump exit=$($dump2.Code), row present=$stillThere"

    Write-Head "cleanup"
    if (Test-Path -LiteralPath $ProfileDir) {
        Remove-Item -LiteralPath $ProfileDir -Recurse -Force
        Write-Ok "removed the throw-away profile: $ProfileDir"
    }
    else {
        Write-Ok "profile already absent: $ProfileDir"
    }
}
elseif ($KeepInstalled) {
    Write-Warn2 "-KeepInstalled: leaving the profile installed for manual inspection"
}

# ------------------------------------------------------------------ verdict

# PowerShell 5.1: @() around a generic List breaks [ordered]@{ } casts, so count
# with a plain loop.
$failedCount = 0
foreach ($c in $script:checks) { if (-not $c.ok) { $failedCount++ } }
if ($failedCount -gt 0) { Fail-Exit 'fail' 1 }
Save-Evidence 'pass'
Write-Host ""
Write-Host "verify-bundle: PASS ($($script:checks.Count) checks)" -ForegroundColor Green
exit 0
