# Offline regression: load only the identity helper, never execute launcher actions.
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Launcher=Join-Path $ProjectRoot 'scripts\windows_launcher.ps1'
$ParseErrors=@(); $ParseTokens=@()
$Ast=[System.Management.Automation.Language.Parser]::ParseFile($Launcher,[ref]$ParseTokens,[ref]$ParseErrors)
if ($ParseErrors.Count) { throw 'Launcher contains PowerShell syntax errors.' }
$Helper=$Ast.FindAll({param($Node) $Node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $Node.Name -eq 'Test-RecordedProcess'},$true)
if (@($Helper).Count -ne 1) { throw 'Expected one process identity helper.' }
Invoke-Expression $Helper[0].Extent.Text
$Utc=[DateTime]::Parse('2026-10-24T01:02:03.1234567Z',[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind)
$Running=[pscustomobject]@{ Id=42; StartTime=$Utc.ToLocalTime() }
$Checks=0
function Assert-Match([string]$Label,[object]$Record,[bool]$Expected) {
    $Actual=Test-RecordedProcess $Running $Record
    if ($Actual -ne $Expected) { throw ('Identity assertion failed: '+$Label) }
    $script:Checks++
}
Assert-Match 'ISO round-trip string' ([pscustomobject]@{id=42;started=$Utc.ToString('o')}) $true
Assert-Match 'UTC DateTime' ([pscustomobject]@{id=42;started=$Utc}) $true
Assert-Match 'local DateTime' ([pscustomobject]@{id=42;started=$Utc.ToLocalTime()}) $true
Assert-Match 'DateTimeOffset' ([pscustomobject]@{id=42;started=([DateTimeOffset]$Utc).ToOffset([TimeSpan]::FromHours(8))}) $true
$Json=@{processes=@(@{id=42;started=$Utc.ToString('o')})}|ConvertTo-Json -Depth 4
$Restored=$Json|ConvertFrom-Json
Assert-Match 'ConvertFrom-Json actual runtime type' $Restored.processes[0] $true
Assert-Match 'offset ISO string' ([pscustomobject]@{id=42;started='2026-10-24T09:02:03.1234567+08:00'}) $true
Assert-Match 'PID reused with different creation time' ([pscustomobject]@{id=42;started=$Utc.AddTicks(1).ToString('o')}) $false
Assert-Match 'wrong PID' ([pscustomobject]@{id=43;started=$Utc}) $false
Assert-Match 'invalid creation time' ([pscustomobject]@{id=42;started='invalid'}) $false
Assert-Match 'missing record' $null $false
if (Test-RecordedProcess $null ([pscustomobject]@{id=42;started=$Utc})) { throw 'Missing process matched.' }
$Checks++
$TreeHelper=$Ast.FindAll({param($Node) $Node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $Node.Name -eq 'Stop-RecordedProcessTree'},$true)
if (@($TreeHelper).Count -ne 1) { throw 'Expected one process tree helper.' }
Invoke-Expression $TreeHelper[0].Extent.Text
# These local mocks shadow system cmdlets: no real processes are queried/stopped.
function Get-Process {
    param([int]$Id,[string]$ErrorAction)
    if (-not $script:Calls.ContainsKey($Id)) { $script:Calls[$Id]=0 }
    $script:Calls[$Id]++
    if ($script:ReuseChild -and $Id -eq 43 -and $script:Calls[$Id] -ge 2) {
        return [pscustomobject]@{Id=43;StartTime=$Utc.AddHours(1)}
    }
    return $script:FakeProcesses[$Id]
}
function Get-CimInstance {
    param([string]$ClassName,[string[]]$Property,[string]$ErrorAction)
    return @(
        [pscustomobject]@{ProcessId=43;ParentProcessId=42},
        [pscustomobject]@{ProcessId=44;ParentProcessId=43},
        [pscustomobject]@{ProcessId=45;ParentProcessId=42},
        [pscustomobject]@{ProcessId=99;ParentProcessId=1}
    )
}
function Stop-Process {
    param([object]$InputObject,[string]$ErrorAction)
    $script:Stopped+=@($InputObject.Id)
}
function Reset-FakeTree {
    $script:Calls=@{}; $script:Stopped=@(); $script:ReuseChild=$false
    $script:FakeProcesses=@{
        42=[pscustomobject]@{Id=42;StartTime=$Utc}
        43=[pscustomobject]@{Id=43;StartTime=$Utc.AddSeconds(1)}
        44=[pscustomobject]@{Id=44;StartTime=$Utc.AddSeconds(2)}
        45=[pscustomobject]@{Id=45;StartTime=$Utc.AddSeconds(-1)}
        99=[pscustomobject]@{Id=99;StartTime=$Utc.AddSeconds(1)}
    }
}
Reset-FakeTree
Stop-RecordedProcessTree ([pscustomobject]@{id=42;started=$Utc.ToString('o')})
if (($Stopped -join ',') -ne '44,43,42') { throw 'Tree order or unrelated/older process protection failed.' }; $Checks++
Reset-FakeTree
Stop-RecordedProcessTree ([pscustomobject]@{id=42;started=$Utc.AddTicks(-1).ToString('o')})
if ($Stopped.Count) { throw 'Unverified root tree was stopped.' }; $Checks++
Reset-FakeTree; $script:ReuseChild=$true
Stop-RecordedProcessTree ([pscustomobject]@{id=42;started=$Utc})
if (($Stopped -join ',') -ne '44,42') { throw 'Reused child PID was not protected.' }; $Checks++
Reset-FakeTree; $script:FakeProcesses.Remove(43)
Stop-RecordedProcessTree ([pscustomobject]@{id=42;started=$Utc})
if (($Stopped -join ',') -ne '42') { throw 'Missing child allowed unverified grandchild traversal.' }; $Checks++
Write-Output ('PASS: '+$Checks+' process identity/tree checks; PowerShell '+$PSVersionTable.PSVersion+'; JSON started type '+$Restored.processes[0].started.GetType().Name)
