$ErrorActionPreference = 'Stop'
$pveRoot = 'D:/神雕侠侣/revival'
$pvePython = 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$pveRelease = 'D:\神雕侠侣\revival\runtime\deployments\task-pve-20261024T053218Z'
$pveRecord = Join-Path $pveRelease 'candidate.json'
$pveReview = Join-Path $pveRoot 'evidence/reviews/task-pve-root-20261024-r1'
$pveReceipt = Join-Path $pveReview 'acceptance-root.json'
$pveCandidate = Get-Content -LiteralPath $pveRecord -Raw | ConvertFrom-Json
$pveApproval = Get-Content -LiteralPath $pveReceipt -Raw | ConvertFrom-Json
$pveManifest = Get-Content -LiteralPath (Join-Path $pveRelease 'manifest.json') -Raw | ConvertFrom-Json
$pvePreflight = Get-Content -LiteralPath (Join-Path $pveRelease 'preflight.json') -Raw | ConvertFrom-Json
if ($pveCandidate.release -ne $pveRelease -or $pveCandidate.file_count -ne 1454) { throw 'Unexpected exact P0 candidate' }
if ($pveApproval.status -ne 'accepted_for_main_coordinated_deployment' -or $pveApproval.release -ne $pveRelease -or $pveApproval.base_release -ne $pveCandidate.base_release -or $pveApproval.expected_base_pid -ne 7456 -or $pveApproval.acceptance_input_sha256 -ne $pveCandidate.acceptance_input_sha256) { throw 'Independent P0 approval identity mismatch' }
foreach ($pveField in @('standards_hard','spec_missing','spec_extra','spec_wrong')) {
    if ($pveApproval.$pveField -ne 0) { throw ('Blocking review finding: ' + $pveField) }
}
foreach ($pveFile in @('manifest.json','preflight.json')) {
    $pveField = if ($pveFile -eq 'manifest.json') { 'manifest_sha256' } else { 'preflight_sha256' }
    if ((Get-FileHash -LiteralPath (Join-Path $pveRelease $pveFile) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pveApproval.$pveField) { throw ('Reviewed deployment input changed: ' + $pveFile) }
}
if ($pvePreflight.quick_check -ne 'ok' -or $pvePreflight.candidate_hashes_verified -ne 1454 -or $pvePreflight.schema_and_all_existing_rows_preserved -ne 110 -or $pvePreflight.added_empty_tables.Count -ne 5) { throw 'P0 startup/data preflight incomplete' }
if (@($pveCandidate.changed_modules.PSObject.Properties).Count -ne 19 -or $pveCandidate.new_empty_tables.Count -ne 5) { throw 'Unexpected P0 source/schema scope' }
if ((($pveCandidate.new_empty_tables | Sort-Object) -join ',') -ne (($pveManifest.new_empty_tables | Sort-Object) -join ',')) { throw 'Candidate schema scope changed' }
foreach ($pveCheck in $pveCandidate.checks_required) {
    $pveResult = Get-Content -LiteralPath (Join-Path $pveRelease ('checks/' + $pveCheck + '.result.json')) -Raw | ConvertFrom-Json
    if (-not $pveResult.passed -or $pveResult.acceptance_input_sha256 -ne $pveCandidate.acceptance_input_sha256) { throw ('Exact P0 check missing: ' + $pveCheck) }
}
foreach ($pveInput in $pveManifest.sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path (Join-Path $pveRelease 'source') $pveInput.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pveInput.Value) { throw ('Frozen source changed: ' + $pveInput.Name) }
}
foreach ($pveReport in $pveApproval.review_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $pveReview $pveReport.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pveReport.Value) { throw ('Independent review changed: ' + $pveReport.Name) }
}
if (-not $pveApproval.deployment_tools_sha256) { throw 'Reviewed deployment tools are missing' }
foreach ($pveTool in $pveApproval.deployment_tools_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $pveRoot $pveTool.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pveTool.Value) { throw ('Reviewed deployment tool changed: ' + $pveTool.Name) }
}
$pveHostReceipt = Join-Path $pveRoot 'evidence/reviews/detached-service-host-root-20261024-r2/acceptance-root.json'
if ((Get-FileHash -LiteralPath $pveHostReceipt -Algorithm SHA256).Hash.ToLowerInvariant() -ne '2833d3f4b86436d71a2203045a5b1c6a8679cd619bd59b6266d6dfd2ab9f597b') { throw 'Original detached host approval changed' }
$pveHostApproval = Get-Content -LiteralPath $pveHostReceipt -Raw | ConvertFrom-Json
foreach ($pveHostInput in $pveHostApproval.files_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $pveRoot $pveHostInput.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pveHostInput.Value) { throw ('Approved host kernel input changed: ' + $pveHostInput.Name) }
}
$pveListeners = @(Get-NetTCPConnection -LocalPort 28993 -State Listen)
if ($pveListeners.Count -ne 1 -or $pveListeners[0].OwningProcess -ne 7456 -or $pveListeners[0].LocalAddress -ne '127.0.0.1') { throw 'Current exact server identity changed' }
$pveOld = Get-CimInstance Win32_Process -Filter 'ProcessId=7456'
if ($pveOld.ExecutablePath -ne (Get-Item -LiteralPath $pvePython).FullName -or $pveOld.CommandLine -notlike '*npc-repair-20261024T023920Z*run_release.py*') { throw 'Current executable or runner changed' }
if (@(Get-NetTCPConnection -LocalPort 28993 -State Established -ErrorAction SilentlyContinue).Count -ne 0) { throw 'Player connected; preserve the current session and retry the authorized empty-window switch' }
Copy-Item -LiteralPath (Join-Path $pveRoot 'runtime/deployment.json') -Destination (Join-Path $pveRelease 'previous-deployment.json')
Stop-Process -Id 7456
Wait-Process -Id 7456 -ErrorAction SilentlyContinue
& $pvePython -B (Join-Path $pveRoot 'staging/verify_master_ready_deployment.py') --candidate-record $pveRecord --at-stop
if ($LASTEXITCODE -ne 0) { throw 'Consistent at-stop P0 backup failed' }
& $pvePython -B (Join-Path $pveRoot 'staging/launch_detached_scoped_release.py') --release (Split-Path -Leaf $pveRelease) --acceptance $pveReceipt
if ($LASTEXITCODE -ne 0) { throw 'Scoped detached P0 startup failed; preserve its logs and stopped backup' }
$pveNewPid = [int](Get-Content -LiteralPath (Join-Path $pveRoot 'runtime/gateway.pid') -Raw)
$pveCurrent = @(Get-NetTCPConnection -LocalPort 28993 -State Listen)
if ($pveCurrent.Count -ne 1 -or $pveCurrent[0].OwningProcess -ne $pveNewPid) { throw 'Started server is not the unique expected listener' }
& $pvePython -B (Join-Path $pveRoot 'staging/verify_master_ready_deployment.py') --candidate-record $pveRecord --pid $pveNewPid --previous-pid 7456
if ($LASTEXITCODE -ne 0) { throw 'P0 post-deployment source/data/health verification failed' }
foreach ($pveMetadataPath in @($pveRecord,(Join-Path $pveRoot 'staging/task-pve-candidate.json'))) {
    $pveMetadata = Get-Content -LiteralPath $pveMetadataPath -Raw | ConvertFrom-Json
    $pveMetadata.started = $true
    $pveMetadata | Add-Member -NotePropertyName status -NotePropertyValue 'deployed' -Force
    $pveMetadata | Add-Member -NotePropertyName pid -NotePropertyValue $pveNewPid -Force
    [IO.File]::WriteAllText($pveMetadataPath,($pveMetadata | ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
}
