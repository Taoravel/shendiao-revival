"""Prepare the approved-host coordinated repair switch, never execute it."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
candidate=json.loads((ROOT/'staging/npc-repair-candidate.json').read_text(encoding='utf-8'))
host_root=ROOT/'evidence/reviews/detached-service-host-root-20261024-r2'
host_hash=hashlib.sha256((host_root/'acceptance-root.json').read_bytes()).hexdigest()
text=(ROOT/'staging/deploy_world_collision_release.ps1').read_text(encoding='utf-8')
replacements=[('$collision','$repair'),
    ('staging/world-collision-candidate.json','staging/npc-repair-candidate.json'),
    ("'world-collision-20261023T204238Z'",repr(Path(candidate['release']).name)),
    ('evidence/reviews/world-collision-root-20261024-r4','evidence/reviews/npc-repair-root-20261024'),
    ('3396',str(candidate['base_pid_at_staging'])),('.Count -ne 6)', '.Count -ne 1)'),
    ('*npc-loyalty-20261023T193742Z*run_release.py*','*world-collision-20261023T204238Z*run_release.py*'),
    ('world collision','ordinary repair'),('Collision candidate','Repair candidate'),
    ('Collision post-deployment','Repair post-deployment')]
for old,new in replacements:
    if old not in text:raise ValueError('Deployer anchor missing: '+old)
    text=text.replace(old,new)
host_gate="""$repairHostRoot = Join-Path $repairRoot 'evidence/reviews/detached-service-host-root-20261024-r2'
$repairHostReceipt = Join-Path $repairHostRoot 'acceptance-root.json'
if ((Get-FileHash -LiteralPath $repairHostReceipt -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'HOST_HASH') { throw 'Detached host approval changed' }
$repairHostApproval = Get-Content -LiteralPath $repairHostReceipt -Raw | ConvertFrom-Json
if ($repairHostApproval.status -ne 'accepted_for_main_detached_launcher_use') { throw 'Detached host not approved' }
foreach ($repairHostInput in $repairHostApproval.files_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $repairRoot $repairHostInput.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $repairHostInput.Value) { throw ('Detached host input changed: ' + $repairHostInput.Name) }
}
foreach ($repairHostReport in $repairHostApproval.report_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $repairHostRoot $repairHostReport.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $repairHostReport.Value) { throw ('Detached host review changed: ' + $repairHostReport.Name) }
}
if ((Get-FileHash -LiteralPath (Join-Path $repairRoot 'staging/verify_windows_detached_lifetime.py') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $repairHostApproval.controlled_probe_sha256) { throw 'Controlled host lifetime probe changed' }
""".replace('HOST_HASH',host_hash)
anchor="$repairListener = @(Get-NetTCPConnection -LocalPort 28993 -State Listen)"
if text.count(anchor)!=1:raise ValueError('Final live gate missing')
text=text.replace(anchor,host_gate+anchor)
start=text.index('$repairStarted = Start-Process')
end=text.index('& $repairPython -B (Join-Path $repairRoot \'staging/verify_master_ready_deployment.py\') --candidate-record $repairRecord --pid',start)
detached="""& $repairPython -B (Join-Path $repairRoot 'staging/launch_detached_release.py') --release (Split-Path -Leaf $repairPath) --acceptance (Join-Path $repairReviewRoot 'acceptance-root.json')
if ($LASTEXITCODE -ne 0) { throw 'Approved detached repair host failed; preserve logs and backup' }
$repairActualPid = [int](Get-Content -LiteralPath (Join-Path $repairRoot 'runtime/gateway.pid') -Raw)
$repairStarted = [pscustomobject]@{ Id = $repairActualPid }
"""
text=text[:start]+detached+text[end:]
if 'Start-Process' in text:raise ValueError('Tool-bound launch must not enter this deployer')
path=ROOT/'staging/deploy_npc_repair_release.ps1';path.write_text(text,encoding='utf-8')
print(json.dumps(dict(deployer=str(path),host_approval_sha256=host_hash)))


if __name__=='__main__':pass
