$ErrorActionPreference = 'Stop'
$collisionRoot = 'D:/神雕侠侣/revival'
$collisionPython = 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$collisionRecord = Join-Path $collisionRoot 'staging/world-collision-candidate.json'
$collisionCandidate = Get-Content -LiteralPath $collisionRecord -Raw | ConvertFrom-Json
$collisionPath = $collisionCandidate.release
if ((Split-Path -Leaf $collisionPath) -ne 'world-collision-20261023T204238Z') { throw 'Unexpected world collision candidate' }
$collisionPreflight = Get-Content -LiteralPath (Join-Path $collisionPath 'preflight.json') -Raw | ConvertFrom-Json
if ($collisionPreflight.quick_check -ne 'ok' -or $collisionPreflight.candidate_hashes_verified -ne 1442) { throw 'Startup preflight incomplete' }
if (@($collisionCandidate.changed_modules.PSObject.Properties).Count -ne 6) { throw 'Unexpected world collision production scope' }
if ($collisionCandidate.new_empty_tables.Count -ne 0) { throw 'No schema changes authorized' }
foreach ($collisionCheck in $collisionCandidate.checks_required) {
    $collisionResult = Get-Content -LiteralPath (Join-Path $collisionPath ('checks/' + $collisionCheck + '.result.json')) -Raw | ConvertFrom-Json
    if (-not $collisionResult.passed -or $collisionResult.acceptance_input_sha256 -ne $collisionCandidate.acceptance_input_sha256) { throw ('Exact-input acceptance missing: ' + $collisionCheck) }
}
$collisionReviewRoot = Join-Path $collisionRoot 'evidence/reviews/world-collision-root-20261024-r4'
$collisionAcceptance = Get-Content -LiteralPath (Join-Path $collisionReviewRoot 'acceptance-root.json') -Raw | ConvertFrom-Json
if ($collisionAcceptance.status -ne 'accepted_for_main_coordinated_deployment' -or $collisionAcceptance.release -ne $collisionPath -or $collisionAcceptance.base_release -ne $collisionCandidate.base_release -or $collisionAcceptance.expected_base_pid -ne 3396 -or $collisionAcceptance.acceptance_input_sha256 -ne $collisionCandidate.acceptance_input_sha256) { throw 'Independent acceptance identity mismatch' }
foreach ($collisionFinding in @('standards_hard','standards_heuristic','spec_missing','spec_extra','spec_wrong')) {
    if ($collisionAcceptance.$collisionFinding -ne 0) { throw ('Unresolved review finding: ' + $collisionFinding) }
}
if ((Get-FileHash -LiteralPath (Join-Path $collisionPath 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $collisionAcceptance.manifest_sha256) { throw 'Reviewed manifest changed' }
foreach ($collisionReviewedInput in $collisionAcceptance.production_sha256.PSObject.Properties) {
    if ($collisionCandidate.changed_modules.($collisionReviewedInput.Name) -ne $collisionReviewedInput.Value) { throw ('Reviewed input changed: ' + $collisionReviewedInput.Name) }
}
foreach ($collisionReviewedReport in $collisionAcceptance.review_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $collisionReviewRoot $collisionReviewedReport.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $collisionReviewedReport.Value) { throw ('Independent report changed: ' + $collisionReviewedReport.Name) }
}
$collisionManifest = Get-Content -LiteralPath (Join-Path $collisionPath 'manifest.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $collisionPath 'run_release.py') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $collisionManifest.runner_sha256) { throw 'Runner changed' }
foreach ($collisionInput in $collisionManifest.sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path (Join-Path $collisionPath 'source') $collisionInput.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $collisionInput.Value) { throw ('Frozen production changed: ' + $collisionInput.Name) }
}
$collisionListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen)
if ($collisionListener.Count -ne 1 -or $collisionListener[0].OwningProcess -ne 3396) { throw 'Current live process changed' }
$collisionCurrent = Get-CimInstance Win32_Process -Filter 'ProcessId=3396'
if ($collisionCurrent.ExecutablePath -ne (Get-Item -LiteralPath $collisionPython).FullName -or $collisionCurrent.CommandLine -notlike '*npc-loyalty-20261023T193742Z*run_release.py*') { throw 'Live executable/runner mismatch' }
Copy-Item -LiteralPath (Join-Path $collisionRoot 'runtime/deployment.json') -Destination (Join-Path $collisionPath 'previous-deployment.json')
# An immediate empty-server snapshot, not an atomic admission-drain protocol.
if (@(Get-NetTCPConnection -LocalPort 28993 -State Established -ErrorAction SilentlyContinue).Count -ne 0) { throw 'Player connected at final check; preserve session and retry later' }
Stop-Process -Id 3396
Wait-Process -Id 3396 -ErrorAction SilentlyContinue
& $collisionPython -B (Join-Path $collisionRoot 'staging/verify_master_ready_deployment.py') --candidate-record $collisionRecord --at-stop
if ($LASTEXITCODE -ne 0) { throw 'Consistent stopped-store backup failed' }
$collisionStarted = Start-Process -FilePath $collisionPython -ArgumentList @('-B', ('"' + (Join-Path $collisionPath 'run_release.py') + '"')) -WorkingDirectory 'D:/神雕侠侣' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $collisionPath 'server-stdout.log') -RedirectStandardError (Join-Path $collisionPath 'server-stderr.log') -PassThru
$collisionStarted.Id | Set-Content -LiteralPath (Join-Path $collisionRoot 'runtime/gateway.pid')
$collisionReady = $false
for ($collisionAttempt = 0; $collisionAttempt -lt 40; $collisionAttempt++) {
    Start-Sleep -Milliseconds 500
    if ($collisionStarted.HasExited) { throw 'Collision candidate exited; preserve logs and backup' }
    $collisionNewListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen -ErrorAction SilentlyContinue)
    if ($collisionNewListener.Count -eq 1 -and $collisionNewListener[0].OwningProcess -eq $collisionStarted.Id) { $collisionReady = $true; break }
}
if (-not $collisionReady) { throw 'Collision listener unavailable' }
& $collisionPython -B (Join-Path $collisionRoot 'staging/verify_master_ready_deployment.py') --candidate-record $collisionRecord --pid $collisionStarted.Id --previous-pid $collisionAcceptance.expected_base_pid
if ($LASTEXITCODE -ne 0) { throw 'Collision post-deployment verification failed' }
foreach ($collisionMetadataPath in @($collisionRecord, (Join-Path $collisionPath 'candidate.json'))) {
    $collisionMetadata = Get-Content -LiteralPath $collisionMetadataPath -Raw | ConvertFrom-Json
    $collisionMetadata.started = $true
    $collisionMetadata | Add-Member -NotePropertyName status -NotePropertyValue 'deployed' -Force
    $collisionMetadata | Add-Member -NotePropertyName pid -NotePropertyValue $collisionStarted.Id -Force
    [System.IO.File]::WriteAllText($collisionMetadataPath, ($collisionMetadata | ConvertTo-Json -Depth 12), [System.Text.UTF8Encoding]::new($false))
}
