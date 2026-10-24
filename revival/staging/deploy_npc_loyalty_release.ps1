$ErrorActionPreference = 'Stop'
$loyaltyRoot = 'D:/神雕侠侣/revival'
$loyaltyPython = 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$loyaltyRecord = Join-Path $loyaltyRoot 'staging/npc-loyalty-candidate.json'
$loyaltyCandidate = Get-Content -LiteralPath $loyaltyRecord -Raw | ConvertFrom-Json
$loyaltyPath = $loyaltyCandidate.release
if ((Split-Path -Leaf $loyaltyPath) -ne 'npc-loyalty-20261023T193742Z') { throw 'Unexpected private story candidate' }
$loyaltyPreflight = Get-Content -LiteralPath (Join-Path $loyaltyPath 'preflight.json') -Raw | ConvertFrom-Json
if ($loyaltyPreflight.quick_check -ne 'ok' -or $loyaltyPreflight.candidate_hashes_verified -ne 1440) { throw 'Startup preflight incomplete' }
if (@($loyaltyCandidate.changed_modules.PSObject.Properties).Count -ne 3) { throw 'Unexpected private production scope' }
if ($loyaltyCandidate.new_empty_tables.Count -ne 0) { throw 'No schema changes authorized' }
foreach ($loyaltyCheck in $loyaltyCandidate.checks_required) {
    $loyaltyResult = Get-Content -LiteralPath (Join-Path $loyaltyPath ('checks/' + $loyaltyCheck + '.result.json')) -Raw | ConvertFrom-Json
    if (-not $loyaltyResult.passed -or $loyaltyResult.acceptance_input_sha256 -ne $loyaltyCandidate.acceptance_input_sha256) { throw ('Exact-input acceptance missing: ' + $loyaltyCheck) }
}
$loyaltyReviewRoot = Join-Path $loyaltyRoot 'evidence/reviews/npc-loyalty-release-20261024-r2'
$loyaltyAcceptance = Get-Content -LiteralPath (Join-Path $loyaltyReviewRoot 'acceptance-root.json') -Raw | ConvertFrom-Json
if ($loyaltyAcceptance.status -ne 'accepted_for_main_coordinated_deployment' -or $loyaltyAcceptance.release -ne $loyaltyPath -or $loyaltyAcceptance.base_release -ne $loyaltyCandidate.base_release -or $loyaltyAcceptance.expected_base_pid -ne 14480 -or $loyaltyAcceptance.acceptance_input_sha256 -ne $loyaltyCandidate.acceptance_input_sha256) { throw 'Independent acceptance identity mismatch' }
foreach ($loyaltyFinding in @('standards_hard','standards_heuristic','spec_missing','spec_extra','spec_wrong')) {
    if ($loyaltyAcceptance.$loyaltyFinding -ne 0) { throw ('Unresolved review finding: ' + $loyaltyFinding) }
}
if ((Get-FileHash -LiteralPath (Join-Path $loyaltyPath 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $loyaltyAcceptance.manifest_sha256) { throw 'Reviewed manifest changed' }
foreach ($loyaltyReviewedInput in $loyaltyAcceptance.production_sha256.PSObject.Properties) {
    if ($loyaltyCandidate.changed_modules.($loyaltyReviewedInput.Name) -ne $loyaltyReviewedInput.Value) { throw ('Reviewed input changed: ' + $loyaltyReviewedInput.Name) }
}
foreach ($loyaltyReviewedReport in $loyaltyAcceptance.review_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $loyaltyReviewRoot $loyaltyReviewedReport.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $loyaltyReviewedReport.Value) { throw ('Independent report changed: ' + $loyaltyReviewedReport.Name) }
}
$loyaltyManifest = Get-Content -LiteralPath (Join-Path $loyaltyPath 'manifest.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $loyaltyPath 'run_release.py') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $loyaltyManifest.runner_sha256) { throw 'Runner changed' }
foreach ($loyaltyInput in $loyaltyManifest.sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path (Join-Path $loyaltyPath 'source') $loyaltyInput.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $loyaltyInput.Value) { throw ('Frozen production changed: ' + $loyaltyInput.Name) }
}
$loyaltyListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen)
if ($loyaltyListener.Count -ne 1 -or $loyaltyListener[0].OwningProcess -ne 14480) { throw 'Current live process changed' }
$loyaltyCurrent = Get-CimInstance Win32_Process -Filter 'ProcessId=14480'
if ($loyaltyCurrent.ExecutablePath -ne (Get-Item -LiteralPath $loyaltyPython).FullName -or $loyaltyCurrent.CommandLine -notlike '*private-story-20261023T190051Z*run_release.py*') { throw 'Live executable/runner mismatch' }
Copy-Item -LiteralPath (Join-Path $loyaltyRoot 'runtime/deployment.json') -Destination (Join-Path $loyaltyPath 'previous-deployment.json')
# An immediate empty-server snapshot, not an atomic admission-drain protocol.
if (@(Get-NetTCPConnection -LocalPort 28993 -State Established -ErrorAction SilentlyContinue).Count -ne 0) { throw 'Player connected at final check; preserve session and retry later' }
Stop-Process -Id 14480
Wait-Process -Id 14480 -ErrorAction SilentlyContinue
& $loyaltyPython -B (Join-Path $loyaltyRoot 'staging/verify_master_ready_deployment.py') --candidate-record $loyaltyRecord --at-stop
if ($LASTEXITCODE -ne 0) { throw 'Consistent stopped-store backup failed' }
$loyaltyStarted = Start-Process -FilePath $loyaltyPython -ArgumentList @('-B', ('"' + (Join-Path $loyaltyPath 'run_release.py') + '"')) -WorkingDirectory 'D:/神雕侠侣' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $loyaltyPath 'server-stdout.log') -RedirectStandardError (Join-Path $loyaltyPath 'server-stderr.log') -PassThru
$loyaltyStarted.Id | Set-Content -LiteralPath (Join-Path $loyaltyRoot 'runtime/gateway.pid')
$loyaltyReady = $false
for ($loyaltyAttempt = 0; $loyaltyAttempt -lt 40; $loyaltyAttempt++) {
    Start-Sleep -Milliseconds 500
    if ($loyaltyStarted.HasExited) { throw 'Private candidate exited; preserve logs and backup' }
    $loyaltyNewListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen -ErrorAction SilentlyContinue)
    if ($loyaltyNewListener.Count -eq 1 -and $loyaltyNewListener[0].OwningProcess -eq $loyaltyStarted.Id) { $loyaltyReady = $true; break }
}
if (-not $loyaltyReady) { throw 'Private listener unavailable' }
& $loyaltyPython -B (Join-Path $loyaltyRoot 'staging/verify_master_ready_deployment.py') --candidate-record $loyaltyRecord --pid $loyaltyStarted.Id
if ($LASTEXITCODE -ne 0) { throw 'Private post-deployment verification failed' }
foreach ($loyaltyMetadataPath in @($loyaltyRecord, (Join-Path $loyaltyPath 'candidate.json'))) {
    $loyaltyMetadata = Get-Content -LiteralPath $loyaltyMetadataPath -Raw | ConvertFrom-Json
    $loyaltyMetadata.started = $true
    $loyaltyMetadata | Add-Member -NotePropertyName status -NotePropertyValue 'deployed' -Force
    $loyaltyMetadata | Add-Member -NotePropertyName pid -NotePropertyValue $loyaltyStarted.Id -Force
    [System.IO.File]::WriteAllText($loyaltyMetadataPath, ($loyaltyMetadata | ConvertTo-Json -Depth 12), [System.Text.UTF8Encoding]::new($false))
}
