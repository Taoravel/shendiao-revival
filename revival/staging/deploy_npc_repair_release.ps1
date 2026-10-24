$ErrorActionPreference = 'Stop'
$repairRoot = 'D:/神雕侠侣/revival'
$repairPython = 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$repairRecord = Join-Path $repairRoot 'staging/npc-repair-candidate.json'
$repairCandidate = Get-Content -LiteralPath $repairRecord -Raw | ConvertFrom-Json
$repairPath = $repairCandidate.release
if ((Split-Path -Leaf $repairPath) -ne 'npc-repair-20261024T023920Z') { throw 'Unexpected ordinary repair candidate' }
$repairPreflight = Get-Content -LiteralPath (Join-Path $repairPath 'preflight.json') -Raw | ConvertFrom-Json
if ($repairPreflight.quick_check -ne 'ok' -or $repairPreflight.candidate_hashes_verified -ne 1442) { throw 'Startup preflight incomplete' }
if (@($repairCandidate.changed_modules.PSObject.Properties).Count -ne 1) { throw 'Unexpected ordinary repair production scope' }
if ($repairCandidate.new_empty_tables.Count -ne 0) { throw 'No schema changes authorized' }
foreach ($repairCheck in $repairCandidate.checks_required) {
    $repairResult = Get-Content -LiteralPath (Join-Path $repairPath ('checks/' + $repairCheck + '.result.json')) -Raw | ConvertFrom-Json
    if (-not $repairResult.passed -or $repairResult.acceptance_input_sha256 -ne $repairCandidate.acceptance_input_sha256) { throw ('Exact-input acceptance missing: ' + $repairCheck) }
}
$repairReviewRoot = Join-Path $repairRoot 'evidence/reviews/npc-repair-root-20261024'
$repairAcceptance = Get-Content -LiteralPath (Join-Path $repairReviewRoot 'acceptance-root.json') -Raw | ConvertFrom-Json
if ($repairAcceptance.status -ne 'accepted_for_main_coordinated_deployment' -or $repairAcceptance.release -ne $repairPath -or $repairAcceptance.base_release -ne $repairCandidate.base_release -or $repairAcceptance.expected_base_pid -ne 16276 -or $repairAcceptance.acceptance_input_sha256 -ne $repairCandidate.acceptance_input_sha256) { throw 'Independent acceptance identity mismatch' }
foreach ($repairFinding in @('standards_hard','standards_heuristic','spec_missing','spec_extra','spec_wrong')) {
    if ($repairAcceptance.$repairFinding -ne 0) { throw ('Unresolved review finding: ' + $repairFinding) }
}
if ((Get-FileHash -LiteralPath (Join-Path $repairPath 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $repairAcceptance.manifest_sha256) { throw 'Reviewed manifest changed' }
foreach ($repairReviewedInput in $repairAcceptance.production_sha256.PSObject.Properties) {
    if ($repairCandidate.changed_modules.($repairReviewedInput.Name) -ne $repairReviewedInput.Value) { throw ('Reviewed input changed: ' + $repairReviewedInput.Name) }
}
foreach ($repairReviewedReport in $repairAcceptance.review_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $repairReviewRoot $repairReviewedReport.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $repairReviewedReport.Value) { throw ('Independent report changed: ' + $repairReviewedReport.Name) }
}
$repairManifest = Get-Content -LiteralPath (Join-Path $repairPath 'manifest.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $repairPath 'run_release.py') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $repairManifest.runner_sha256) { throw 'Runner changed' }
foreach ($repairInput in $repairManifest.sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path (Join-Path $repairPath 'source') $repairInput.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $repairInput.Value) { throw ('Frozen production changed: ' + $repairInput.Name) }
}
$repairHostRoot = Join-Path $repairRoot 'evidence/reviews/detached-service-host-root-20261024-r2'
$repairHostReceipt = Join-Path $repairHostRoot 'acceptance-root.json'
if ((Get-FileHash -LiteralPath $repairHostReceipt -Algorithm SHA256).Hash.ToLowerInvariant() -ne '2833d3f4b86436d71a2203045a5b1c6a8679cd619bd59b6266d6dfd2ab9f597b') { throw 'Detached host approval changed' }
$repairHostApproval = Get-Content -LiteralPath $repairHostReceipt -Raw | ConvertFrom-Json
if ($repairHostApproval.status -ne 'accepted_for_main_detached_launcher_use') { throw 'Detached host not approved' }
foreach ($repairHostInput in $repairHostApproval.files_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $repairRoot $repairHostInput.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $repairHostInput.Value) { throw ('Detached host input changed: ' + $repairHostInput.Name) }
}
foreach ($repairHostReport in $repairHostApproval.report_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $repairHostRoot $repairHostReport.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $repairHostReport.Value) { throw ('Detached host review changed: ' + $repairHostReport.Name) }
}
if ((Get-FileHash -LiteralPath (Join-Path $repairRoot 'staging/verify_windows_detached_lifetime.py') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $repairHostApproval.controlled_probe_sha256) { throw 'Controlled host lifetime probe changed' }
$repairListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen)
if ($repairListener.Count -ne 1 -or $repairListener[0].OwningProcess -ne 16276) { throw 'Current live process changed' }
$repairCurrent = Get-CimInstance Win32_Process -Filter 'ProcessId=16276'
if ($repairCurrent.ExecutablePath -ne (Get-Item -LiteralPath $repairPython).FullName -or $repairCurrent.CommandLine -notlike '*world-collision-20261023T204238Z*run_release.py*') { throw 'Live executable/runner mismatch' }
Copy-Item -LiteralPath (Join-Path $repairRoot 'runtime/deployment.json') -Destination (Join-Path $repairPath 'previous-deployment.json')
# An immediate empty-server snapshot, not an atomic admission-drain protocol.
if (@(Get-NetTCPConnection -LocalPort 28993 -State Established -ErrorAction SilentlyContinue).Count -ne 0) { throw 'Player connected at final check; preserve session and retry later' }
Stop-Process -Id 16276
Wait-Process -Id 16276 -ErrorAction SilentlyContinue
& $repairPython -B (Join-Path $repairRoot 'staging/verify_master_ready_deployment.py') --candidate-record $repairRecord --at-stop
if ($LASTEXITCODE -ne 0) { throw 'Consistent stopped-store backup failed' }
& $repairPython -B (Join-Path $repairRoot 'staging/launch_detached_release.py') --release (Split-Path -Leaf $repairPath) --acceptance (Join-Path $repairReviewRoot 'acceptance-root.json')
if ($LASTEXITCODE -ne 0) { throw 'Approved detached repair host failed; preserve logs and backup' }
$repairActualPid = [int](Get-Content -LiteralPath (Join-Path $repairRoot 'runtime/gateway.pid') -Raw)
$repairStarted = [pscustomobject]@{ Id = $repairActualPid }
& $repairPython -B (Join-Path $repairRoot 'staging/verify_master_ready_deployment.py') --candidate-record $repairRecord --pid $repairStarted.Id --previous-pid $repairAcceptance.expected_base_pid
if ($LASTEXITCODE -ne 0) { throw 'Repair post-deployment verification failed' }
foreach ($repairMetadataPath in @($repairRecord, (Join-Path $repairPath 'candidate.json'))) {
    $repairMetadata = Get-Content -LiteralPath $repairMetadataPath -Raw | ConvertFrom-Json
    $repairMetadata.started = $true
    $repairMetadata | Add-Member -NotePropertyName status -NotePropertyValue 'deployed' -Force
    $repairMetadata | Add-Member -NotePropertyName pid -NotePropertyValue $repairStarted.Id -Force
    [System.IO.File]::WriteAllText($repairMetadataPath, ($repairMetadata | ConvertTo-Json -Depth 12), [System.Text.UTF8Encoding]::new($false))
}
