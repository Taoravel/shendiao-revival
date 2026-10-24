$ErrorActionPreference = 'Stop'
$damageRoot = 'D:/神雕侠侣/revival'
$damagePython = 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$damageRecord = Join-Path $damageRoot 'staging/battle-damage-candidate.json'
$damageCandidate = Get-Content -LiteralPath $damageRecord -Raw | ConvertFrom-Json
$damagePath = $damageCandidate.release
if ((Split-Path -Leaf $damagePath) -ne 'battle-damage-20261023T180731Z') { throw 'Unexpected candidate' }
$damagePreflight = Get-Content -LiteralPath (Join-Path $damagePath 'preflight.json') -Raw | ConvertFrom-Json
if ($damagePreflight.quick_check -ne 'ok' -or $damagePreflight.candidate_hashes_verified -ne 1429) { throw 'Incomplete preflight' }
if ($damageCandidate.new_empty_tables.Count -ne 0 -or @($damageCandidate.changed_modules.PSObject.Properties).Count -ne 2) { throw 'Unexpected scope' }
$damageReview = Get-Content -LiteralPath (Join-Path $damageRoot 'evidence/reviews/battle-damage-release-20261024/REVIEW.md') -Raw
if ($damageReview -notmatch '独立Standards与Spec各0项发现') { throw 'Exact candidate review unavailable' }
$damageManifest = Get-Content -LiteralPath (Join-Path $damagePath 'manifest.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $damagePath 'run_release.py') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $damageManifest.runner_sha256) { throw 'Runner changed' }
foreach ($damageInput in $damageManifest.sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path (Join-Path $damagePath 'source') $damageInput.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $damageInput.Value) { throw ('Frozen source changed: ' + $damageInput.Name) }
}
$damageListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen)
if ($damageListener.Count -ne 1 -or $damageListener[0].OwningProcess -ne 45272) { throw 'Current listener changed' }
$damageCurrent = Get-CimInstance Win32_Process -Filter 'ProcessId=45272'
if ($damageCurrent.ExecutablePath -ne (Get-Item -LiteralPath $damagePython).FullName -or $damageCurrent.CommandLine -notlike '*npc-role-healing-20261023T125539Z*run_release.py*') { throw 'Current process identity mismatch' }
Copy-Item -LiteralPath (Join-Path $damageRoot 'runtime/deployment.json') -Destination (Join-Path $damagePath 'previous-deployment.json')
# This is an empty-server snapshot immediately before stop, not atomic admission draining.
# A new connection attempted during the short restart may need to reconnect.
if (@(Get-NetTCPConnection -LocalPort 28993 -State Established -ErrorAction SilentlyContinue).Count -ne 0) { throw 'Player connected at final check; preserve the session and retry later' }
Stop-Process -Id 45272
Wait-Process -Id 45272 -ErrorAction SilentlyContinue
& $damagePython -B (Join-Path $damageRoot 'staging/verify_master_ready_deployment.py') --candidate-record $damageRecord --at-stop
if ($LASTEXITCODE -ne 0) { throw 'Consistent backup failed' }
$damageStarted = Start-Process -FilePath $damagePython -ArgumentList @('-B', ('"' + (Join-Path $damagePath 'run_release.py') + '"')) -WorkingDirectory 'D:/神雕侠侣' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $damagePath 'server-stdout.log') -RedirectStandardError (Join-Path $damagePath 'server-stderr.log') -PassThru
$damageStarted.Id | Set-Content -LiteralPath (Join-Path $damageRoot 'runtime/gateway.pid')
$damageReady = $false
for ($damageAttempt = 0; $damageAttempt -lt 40; $damageAttempt++) {
    Start-Sleep -Milliseconds 500
    if ($damageStarted.HasExited) { throw 'Candidate exited; inspect preserved logs' }
    $damageNewListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen -ErrorAction SilentlyContinue)
    if ($damageNewListener.Count -eq 1 -and $damageNewListener[0].OwningProcess -eq $damageStarted.Id) { $damageReady = $true; break }
}
if (-not $damageReady) { throw 'Candidate listener unavailable' }
& $damagePython -B (Join-Path $damageRoot 'staging/verify_master_ready_deployment.py') --candidate-record $damageRecord --pid $damageStarted.Id
if ($LASTEXITCODE -ne 0) { throw 'Post-deployment verification failed' }
foreach ($damageMetadataPath in @($damageRecord, (Join-Path $damagePath 'candidate.json'))) {
    $damageMetadata = Get-Content -LiteralPath $damageMetadataPath -Raw | ConvertFrom-Json
    $damageMetadata.started = $true
    $damageMetadata | Add-Member -NotePropertyName status -NotePropertyValue 'deployed' -Force
    $damageMetadata | Add-Member -NotePropertyName pid -NotePropertyValue $damageStarted.Id -Force
    [System.IO.File]::WriteAllText($damageMetadataPath, ($damageMetadata | ConvertTo-Json -Depth 12), [System.Text.UTF8Encoding]::new($false))
}
