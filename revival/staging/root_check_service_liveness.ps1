param(
    [string]$Release = 'D:/神雕侠侣/revival/runtime/deployments/world-collision-20261023T204238Z',
    [string]$Report = 'D:/神雕侠侣/revival/evidence/root-service-liveness-current.json'
)
$ErrorActionPreference = 'Stop'
$serviceRoot = 'D:/神雕侠侣/revival'
$serviceRelease = (Resolve-Path -LiteralPath $Release).Path
$serviceExpectedRunner = Join-Path $serviceRelease 'run_release.py'
$serviceStartup = Get-Content -LiteralPath (Join-Path $serviceRoot 'runtime/deployment.json') -Raw | ConvertFrom-Json
$serviceRecordedPid = [int]$serviceStartup.pid
$serviceProcess = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $serviceRecordedPid)
$serviceListeners = @(Get-NetTCPConnection -LocalPort 28993 -State Listen -ErrorAction SilentlyContinue)
$serviceRunnerMatches = $false
if ($null -ne $serviceProcess) {
    $serviceRunnerMatches = $serviceProcess.CommandLine.IndexOf($serviceExpectedRunner, [StringComparison]::OrdinalIgnoreCase) -ge 0
}
$serviceHealthy = $null -ne $serviceProcess -and $serviceRunnerMatches -and $serviceListeners.Count -eq 1 -and $serviceListeners[0].OwningProcess -eq $serviceRecordedPid -and $serviceListeners[0].LocalAddress -eq '127.0.0.1'
$serviceObservation = [ordered]@{
    observed_utc = [DateTime]::UtcNow.ToString('o')
    healthy = [bool]$serviceHealthy
    expected_release = $serviceRelease
    startup_recorded_pid = $serviceRecordedPid
    process_exists = $null -ne $serviceProcess
    expected_runner_matches = [bool]$serviceRunnerMatches
    listener_count = $serviceListeners.Count
    listener_pids = @($serviceListeners | ForEach-Object { $_.OwningProcess })
    process_parent_pid = if ($null -ne $serviceProcess) { $serviceProcess.ParentProcessId } else { $null }
    root_live_socket_accessed = $false
    root_live_database_accessed = $false
    root_live_service_changed = $false
}
[IO.File]::WriteAllText($Report, ($serviceObservation | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
$serviceObservation | ConvertTo-Json -Depth 4 -Compress
if (-not $serviceHealthy) { throw 'Approved service is not running at its recorded PID and unique loopback listener' }
