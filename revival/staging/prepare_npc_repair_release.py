"""One-function ordinary repair activation over approved collision production."""
from datetime import datetime,timezone
import difflib,hashlib,json,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/world-collision-20261023T204238Z'
CHECKS=['verify_npc_repair_resource_runtime.py','verify_resource_npc_care_runtime.py',
    'verify_npc_repair_resources.py','verify_npc_repair_transactions.py',
    'verify_npc_equipped_repair_runtime.py','verify_npc_pet_recovery_runtime.py',
    'verify_npc_loyalty_quote_runtime.py','verify_world_movement_delivery_boundaries.py',
    'verify_runtime_transfer_replays.py','verify_battle_damage_presentation.py','verify_prologue_touch_runtime.py']


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    previous=json.loads((BASE/'candidate.json').read_text(encoding='utf-8'))
    host=json.loads((ROOT/'evidence/detached-service-recovery.json').read_text(encoding='utf-8'))
    assert Path(host['release'])==BASE and not host['target_in_caller_job']
    for name,value in old['sha256'].items():assert digest(BASE/'source'/name)==value,name
    assert digest(BASE/'source/npc_repairs.py')=='3cc4ff7dc2a956946fd31debb18b1a3773d6ca472b93b218fcc257e5aaf86884'
    raw=(BASE/'source/runtime_storage.py').read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n'
    guard=b"    _require_unmigrated_operation(accounts,inventory,'repair resource contract awaits its receipt-aware Interface')"+nl
    call=b'    return npc_repairs.repair(accounts,inventory,intent,precommit)'
    assert raw.count(guard)==raw.count(call)==1
    changed=raw.replace(guard,b'',1).replace(call,call[:-1]+b','+nl+
        b'        resource_rules=accounts.resource_rules,equipment_rules=accounts.equipment_attribute_rules)',1)
    now=datetime.now(timezone.utc)
    release=ROOT/'runtime/deployments'/('npc-repair-'+now.strftime('%Y%m%dT%H%M%SZ'))
    source=release/'source';source.mkdir(parents=True,exist_ok=False)
    for name in old['sha256']:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/'source'/name,target)
    (source/'runtime_storage.py').write_bytes(changed)
    hashes={str(p.relative_to(source)).replace('\\','/'):digest(p) for p in source.rglob('*') if p.is_file()}
    delta={n:v for n,v in hashes.items() if old['sha256'].get(n)!=v}
    assert set(delta)=={'runtime_storage.py'}
    shutil.copy2(BASE/'run_release.py',release/'run_release.py')
    manifest=dict(created_utc=now.isoformat(),base_release=str(BASE),sha256=hashes,changed_modules=delta,
        runner_sha256=digest(release/'run_release.py'),scope='ordinary known-profile NPC repair receipt-aware rules injection')
    (release/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    diff=difflib.unified_diff(raw.decode('utf-8').splitlines(True),changed.decode('utf-8').splitlines(True),
        fromfile='live-collision/runtime_storage.py',tofile='repair/runtime_storage.py')
    (release/'changes.diff').write_text(''.join(diff),encoding='utf-8')
    harness=release/'harness';harness.mkdir()
    for p in (BASE/'harness').glob('*.py'):shutil.copy2(p,harness/p.name)
    shutil.copy2(ROOT/'verify_npc_repair_resource_runtime.py',harness/'verify_npc_repair_resource_runtime.py')
    shutil.copytree(BASE/'harness/evidence',harness/'evidence')
    workspace=harness/'workspace';shutil.copytree(BASE/'harness/workspace',workspace)
    (workspace/'runtime_storage.py').write_bytes(changed)
    shutil.copy2(harness/'verify_npc_repair_resource_runtime.py',workspace/'verify_npc_repair_resource_runtime.py')
    hh={p.name:digest(p) for p in harness.glob('*.py')}
    wh={**previous['workspace_sha256'],'runtime_storage.py':delta['runtime_storage.py'],
        'verify_npc_repair_resource_runtime.py':hh['verify_npc_repair_resource_runtime.py']}
    record=dict(release=str(release),base_release=str(BASE),base_pid_at_staging=host['pid'],file_count=len(hashes),
        changed_modules=delta,production_origins={'runtime_storage.py':'exact BASE only repair guard removal and paired startup rules'},
        started=False,checks_required=CHECKS,new_empty_tables=[],verification_name='npc-repair',scope=manifest['scope'],
        harness_sha256=hh,harness_sources={n:str(harness/n) for n in hh},
        harness_resource_sha256=previous['harness_resource_sha256'],workspace_sha256=wh,check_arguments={},
        verification_module_sources={str(workspace/Path(n).relative_to(BASE/'harness/workspace')):v
            for n,v in previous.get('verification_module_sources',{}).items()},native_gui_verified=False)
    bundle=dict(production=hashes,runner=manifest['runner_sha256'],harness=hh,
        resources=record['harness_resource_sha256'],workspace=wh,checks=CHECKS,arguments={})
    record['acceptance_input_sha256']=hashlib.sha256(json.dumps(bundle,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    text=json.dumps(record,indent=2)
    (release/'candidate.json').write_text(text,encoding='utf-8')
    (ROOT/'staging/npc-repair-candidate.json').write_text(text,encoding='utf-8')
    print(json.dumps(dict(release=str(release),changed=delta,checks=len(CHECKS),file_count=len(hashes))))


if __name__=='__main__':main()
