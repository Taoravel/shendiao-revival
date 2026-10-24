$ErrorActionPreference = 'Stop'
$releaseRoot = 'D:/神雕侠侣/revival'
$releasePython = 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$releaseRecord = Join-Path $releaseRoot 'staging/npc-role-healing-candidate.json'
$releaseCandidate = Get-Content -LiteralPath $releaseRecord -Raw | ConvertFrom-Json
$releasePath = $releaseCandidate.release
if ((Split-Path -Leaf $releasePath) -ne 'npc-role-healing-20261023T125539Z') { throw 'Unexpected release candidate' }
$releasePreflight = Get-Content -LiteralPath (Join-Path $releasePath 'preflight.json') -Raw | ConvertFrom-Json
if ($releasePreflight.quick_check -ne 'ok' -or $releasePreflight.candidate_hashes_verified -ne 1429) { throw 'Preflight incomplete' }
$releaseReview = Get-Content -LiteralPath (Join-Path $releaseRoot 'evidence/reviews/npc-role-healing-release-20261023/REVIEW.md') -Raw
if ($releaseReview -notmatch '独立Standards与Spec各0项发现') { throw 'Independent exact-candidate review unavailable' }
if ($releaseCandidate.new_empty_tables.Count -ne 1 -or $releaseCandidate.new_empty_tables[0] -ne 'npc_role_healing_receipts') { throw 'Unexpected startup table allowlist' }
$releaseManifest = Get-Content -LiteralPath (Join-Path $releasePath 'manifest.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $releasePath 'run_release.py') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $releaseManifest.runner_sha256) { throw 'Immutable runner changed' }
$releaseListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen)
if ($releaseListener.Count -ne 1 -or $releaseListener[0].OwningProcess -ne 39796) { throw 'Current listener changed' }
$releaseCurrent = Get-CimInstance Win32_Process -Filter 'ProcessId=39796'
if ($releaseCurrent.ExecutablePath -ne (Get-Item -LiteralPath $releasePython).FullName -or $releaseCurrent.CommandLine -notlike '*npc-bound-shop-20261023T115742Z*run_release.py*') { throw 'Old process identity mismatch' }
if (@(Get-NetTCPConnection -LocalPort 28993 -State Established -ErrorAction SilentlyContinue).Count -ne 0) { throw 'A client connected; preserve its session and retry later' }
Copy-Item -LiteralPath (Join-Path $releaseRoot 'runtime/deployment.json') -Destination (Join-Path $releasePath 'previous-deployment.json')
Stop-Process -Id 39796
Wait-Process -Id 39796 -ErrorAction SilentlyContinue
& $releasePython -B (Join-Path $releaseRoot 'staging/verify_master_ready_deployment.py') --candidate-record $releaseRecord --at-stop
if ($LASTEXITCODE -ne 0) { throw 'At-stop backup failed; preserve logs' }
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
foreach ($releaseMetadataPath in @($releaseRecord,(Join-Path $releasePath 'candidate.json'))) {
    $releaseMetadata = Get-Content -LiteralPath $releaseMetadataPath -Raw | ConvertFrom-Json
    $releaseMetadata.started = $true
    $releaseMetadata | Add-Member -NotePropertyName status -NotePropertyValue 'deployed' -Force
    $releaseMetadata | Add-Member -NotePropertyName pid -NotePropertyValue $releaseStarted.Id -Force
    [System.IO.File]::WriteAllText($releaseMetadataPath, ($releaseMetadata | ConvertTo-Json -Depth 12), [System.Text.UTF8Encoding]::new($false))
}
