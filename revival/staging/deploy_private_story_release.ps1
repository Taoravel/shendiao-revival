$ErrorActionPreference = 'Stop'
$storyRoot = 'D:/神雕侠侣/revival'
$storyPython = 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$storyRecord = Join-Path $storyRoot 'staging/private-story-candidate.json'
$storyCandidate = Get-Content -LiteralPath $storyRecord -Raw | ConvertFrom-Json
$storyPath = $storyCandidate.release
if ((Split-Path -Leaf $storyPath) -ne 'private-story-20261023T190051Z') { throw 'Unexpected private story candidate' }
$storyPreflight = Get-Content -LiteralPath (Join-Path $storyPath 'preflight.json') -Raw | ConvertFrom-Json
if ($storyPreflight.quick_check -ne 'ok' -or $storyPreflight.candidate_hashes_verified -ne 1439) { throw 'Startup preflight incomplete' }
if (@($storyCandidate.changed_modules.PSObject.Properties).Count -ne 18) { throw 'Unexpected private production scope' }
if ((($storyCandidate.new_empty_tables | Sort-Object) -join ',') -ne 'task_prologue_touches,world_story_instances') { throw 'Unexpected new table allowlist' }
foreach ($storyCheck in $storyCandidate.checks_required) {
    $storyResult = Get-Content -LiteralPath (Join-Path $storyPath ('checks/' + $storyCheck + '.result.json')) -Raw | ConvertFrom-Json
    if (-not $storyResult.passed -or $storyResult.acceptance_input_sha256 -ne $storyCandidate.acceptance_input_sha256) { throw ('Exact-input acceptance missing: ' + $storyCheck) }
}
$storyRecovery = Get-Content -LiteralPath (Join-Path $storyPath 'checks/private-transfer-recovery-extra.json') -Raw | ConvertFrom-Json
if ($storyRecovery.production_inputs -ne 1439 -or $storyRecovery.passed.Count -ne 2) { throw 'Transfer recovery feedback incomplete' }
$storyReview = Get-Content -LiteralPath (Join-Path $storyRoot 'evidence/reviews/private-story-release-20261024/REVIEW-root.md') -Raw
if ($storyReview -notmatch 'Standards：硬性违规0，heuristic判断项0' -or $storyReview -notmatch 'Spec：缺失0、额外范围0、错误0') { throw 'Exact candidate independent review unavailable' }
$storyManifest = Get-Content -LiteralPath (Join-Path $storyPath 'manifest.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $storyPath 'run_release.py') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $storyManifest.runner_sha256) { throw 'Runner changed' }
foreach ($storyInput in $storyManifest.sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path (Join-Path $storyPath 'source') $storyInput.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $storyInput.Value) { throw ('Frozen production changed: ' + $storyInput.Name) }
}
$storyListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen)
if ($storyListener.Count -ne 1 -or $storyListener[0].OwningProcess -ne 12336) { throw 'Current live process changed' }
$storyCurrent = Get-CimInstance Win32_Process -Filter 'ProcessId=12336'
if ($storyCurrent.ExecutablePath -ne (Get-Item -LiteralPath $storyPython).FullName -or $storyCurrent.CommandLine -notlike '*wild-auto-20261023T181143Z*run_release.py*') { throw 'Live executable/runner mismatch' }
Copy-Item -LiteralPath (Join-Path $storyRoot 'runtime/deployment.json') -Destination (Join-Path $storyPath 'previous-deployment.json')
# An immediate empty-server snapshot, not an atomic admission-drain protocol.
if (@(Get-NetTCPConnection -LocalPort 28993 -State Established -ErrorAction SilentlyContinue).Count -ne 0) { throw 'Player connected at final check; preserve session and retry later' }
Stop-Process -Id 12336
Wait-Process -Id 12336 -ErrorAction SilentlyContinue
& $storyPython -B (Join-Path $storyRoot 'staging/verify_master_ready_deployment.py') --candidate-record $storyRecord --at-stop
if ($LASTEXITCODE -ne 0) { throw 'Consistent stopped-store backup failed' }
$storyStarted = Start-Process -FilePath $storyPython -ArgumentList @('-B', ('"' + (Join-Path $storyPath 'run_release.py') + '"')) -WorkingDirectory 'D:/神雕侠侣' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $storyPath 'server-stdout.log') -RedirectStandardError (Join-Path $storyPath 'server-stderr.log') -PassThru
$storyStarted.Id | Set-Content -LiteralPath (Join-Path $storyRoot 'runtime/gateway.pid')
$storyReady = $false
for ($storyAttempt = 0; $storyAttempt -lt 40; $storyAttempt++) {
    Start-Sleep -Milliseconds 500
    if ($storyStarted.HasExited) { throw 'Private candidate exited; preserve logs and backup' }
    $storyNewListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen -ErrorAction SilentlyContinue)
    if ($storyNewListener.Count -eq 1 -and $storyNewListener[0].OwningProcess -eq $storyStarted.Id) { $storyReady = $true; break }
}
if (-not $storyReady) { throw 'Private listener unavailable' }
& $storyPython -B (Join-Path $storyRoot 'staging/verify_master_ready_deployment.py') --candidate-record $storyRecord --pid $storyStarted.Id
if ($LASTEXITCODE -ne 0) { throw 'Private post-deployment verification failed' }
foreach ($storyMetadataPath in @($storyRecord, (Join-Path $storyPath 'candidate.json'))) {
    $storyMetadata = Get-Content -LiteralPath $storyMetadataPath -Raw | ConvertFrom-Json
    $storyMetadata.started = $true
    $storyMetadata | Add-Member -NotePropertyName status -NotePropertyValue 'deployed' -Force
    $storyMetadata | Add-Member -NotePropertyName pid -NotePropertyValue $storyStarted.Id -Force
    [System.IO.File]::WriteAllText($storyMetadataPath, ($storyMetadata | ConvertTo-Json -Depth 12), [System.Text.UTF8Encoding]::new($false))
}
