<#
.SYNOPSIS
    Stops all running Actions/Orca processes.

.DESCRIPTION
    Kills all processes related to Actions/Orca system to prevent file locking
    during builds. This is critical before building to avoid "file in use" errors.

.OUTPUTS
    [PSCustomObject] with properties:
    - ProcessesKilled: Number of processes stopped
    - ProcessNames: Array of process names that were stopped

.EXAMPLE
    & .\Stop-ActionsProcesses.ps1
    # Stops all Orca/Actions processes

.NOTES
    Embedded from resolve.dev.resources/scripts/Actions Manager Utils.ps1
#>

[CmdletBinding()]
param()

Write-Host "Stopping Actions/Orca processes..." -ForegroundColor Yellow

$processNames = @(
    "Orca.AppHost",
    "dotnet",
    "eyeShareComm",
    "eyeShareCommServerRemote",
    "eyeShareEngine",
    "eyeShareExecutor",
    "eyeShareScheduler",
    "w3wp"  # IIS worker process
)

$killedProcesses = @()
$killedCount = 0

foreach ($processName in $processNames) {
    $processes = Get-Process -Name $processName -ErrorAction SilentlyContinue

    foreach ($proc in $processes) {
        try {
            Write-Verbose "Killing process: $processName (PID: $($proc.Id))"
            Stop-Process -Id $proc.Id -Force -ErrorAction Stop
            $killedProcesses += $processName
            $killedCount++
        } catch {
            Write-Verbose "Failed to kill $processName (PID: $($proc.Id)): $_"
        }
    }
}

if ($killedCount -gt 0) {
    Write-Host "  [OK] Stopped $killedCount process(es)" -ForegroundColor Green

    # Wait for processes to fully terminate
    Write-Verbose "Waiting 2 seconds for processes to terminate..."
    Start-Sleep -Seconds 2
} else {
    Write-Host "  [OK] No processes running" -ForegroundColor Green
}

return [PSCustomObject]@{
    ProcessesKilled = $killedCount
    ProcessNames = ($killedProcesses | Select-Object -Unique)
}
