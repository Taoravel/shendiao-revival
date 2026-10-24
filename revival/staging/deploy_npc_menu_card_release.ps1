$ErrorActionPreference = 'Stop'
$releaseRoot = 'D:/神雕侠侣/revival'
$releasePython = 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$releaseRecord = Join-Path $releaseRoot 'staging/npc-menu-card-candidate.json'
$releaseCandidate = Get-Content -LiteralPath $releaseRecord -Raw | ConvertFrom-Json
$releasePath = $releaseCandidate.release
if ((Split-Path -Leaf $releasePath) -ne 'npc-close-master-commit-20261023T113819Z') { throw 'Unexpected release candidate' }
$releasePreflight = Get-Content -LiteralPath (Join-Path $releasePath 'preflight.json') -Raw | ConvertFrom-Json
if ($releasePreflight.quick_check -ne 'ok') { throw 'Preflight not complete' }
$releaseReview = Get-Content -LiteralPath (Join-Path $releaseRoot 'evidence/reviews/npc-close-master-commit-20261023/REVIEW.md') -Raw
if ($releaseReview -notmatch '(?s)## Standards\s+0项.*?## Spec\s+0项') { throw 'Independent review result unavailable' }
$releaseListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen)
if ($releaseListener.Count -ne 1 -or $releaseListener[0].OwningProcess -ne 10076) { throw 'Current listener changed' }
$releaseCurrent = Get-CimInstance Win32_Process -Filter 'ProcessId=10076'
if ($releaseCurrent.ExecutablePath -ne (Get-Item -LiteralPath $releasePython).FullName -or $releaseCurrent.CommandLine -notlike '*wild-20261023T110855Z*run_release.py*') { throw 'Old process identity mismatch' }
if (@(Get-NetTCPConnection -LocalPort 28993 -State Established -ErrorAction SilentlyContinue).Count -ne 0) { throw 'A client connected; preserve its session and retry later' }
Copy-Item -LiteralPath (Join-Path $releaseRoot 'runtime/deployment.json') -Destination (Join-Path $releasePath 'previous-deployment.json')
Stop-Process -Id 10076
Wait-Process -Id 10076 -ErrorAction SilentlyContinue
& $releasePython -B (Join-Path $releaseRoot 'staging/verify_master_ready_deployment.py') --candidate-record $releaseRecord --at-stop
if ($LASTEXITCODE -ne 0) { throw 'At-stop backup failed; do not start unverified release' }
$releaseStarted = Start-Process -FilePath $releasePython -ArgumentList @('-B',('"'+(Join-Path $releasePath 'run_release.py')+'"')) -WorkingDirectory 'D:/神雕侠侣' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $releasePath 'server-stdout.log') -RedirectStandardError (Join-Path $releasePath 'server-stderr.log') -PassThru
$releaseStarted.Id | Set-Content -LiteralPath (Join-Path $releaseRoot 'runtime/gateway.pid')
$releaseReady = $false
for ($releaseAttempt=0; $releaseAttempt -lt 40; $releaseAttempt++) {
    Start-Sleep -Milliseconds 500
    if ($releaseStarted.HasExited) { throw 'Candidate exited; inspect preserved release logs' }
    $releaseNewListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen -ErrorAction SilentlyContinue)
    if ($releaseNewListener.Count -eq 1 -and $releaseNewListener[0].OwningProcess -eq $releaseStarted.Id) { $releaseReady=$true; break }
}
if (-not $releaseReady) { throw 'Candidate listener not ready' }
& $releasePython -B (Join-Path $releaseRoot 'staging/verify_master_ready_deployment.py') --candidate-record $releaseRecord --pid $releaseStarted.Id
if ($LASTEXITCODE -ne 0) { throw 'Post-deployment verification failed; keep logs and backups' }
