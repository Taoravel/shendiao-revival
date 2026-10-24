"""Freeze exactly the movement lifecycle slice over verified loyalty production.

This creates a candidate only. No live DB, PID, listener or client is touched.
"""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/npc-loyalty-20261023T193742Z'
from prepare_private_story_release import CHECKS as PRIVATE_CHECKS
CHECKS=list(dict.fromkeys(PRIVATE_CHECKS+[
    'verify_runtime_movement_lifecycle.py','verify_world_encrypted_collision.py',
    'verify_runtime_movement_terminals.py',
    'verify_world_movement_delivery_boundaries.py','verify_runtime_movement_battle.py',
    'verify_runtime_movement_intro_race.py',
    'verify_world_late_finalize_membership.py','verify_runtime_transfer_replays.py',
    'verify_world_current_cell_collision.py','verify_world_current_cell_maps.py',
    'verify_world_resource_runtime.py','verify_world_movement_state_lifecycle_native.py',
    'verify_world_movement_reconciliation_native.py',
    'verify_npc_loyalty_quote.py','verify_npc_loyalty_quote_runtime.py',
    'verify_npc_pet_recovery_runtime.py','verify_npc_inn_resources.py']))


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    previous=json.loads((BASE/'candidate.json').read_text(encoding='utf-8'))
    old=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    for name,value in old['sha256'].items():
        if digest(BASE/'source'/name)!=value:raise ValueError('BASE hash changed: '+name)
    for name in CHECKS:
        if not (ROOT/name).exists() and not (BASE/'harness'/name).exists():
            raise ValueError('Missing verification input: '+name)
    patch={name:(ROOT/name).read_bytes() for name in (
        'game_runtime.py','runtime_movement.py','world_movement.py','world_owner.py',
        'design/world-movement-state-v1.json')}
    world=json.loads((ROOT/'evidence/world-current-cell-collision-current-interface.json').read_text(encoding='utf-8'))
    for name,value in world['production_files'].items():
        if hashlib.sha256(patch[name]).hexdigest()!=value:raise ValueError('World handoff changed: '+name)
    raw=(BASE/'source/runtime_storage.py').read_bytes()
    nl=b'\r\n' if b'\r\n' in raw else b'\n'
    import_anchor=b'from dataclasses import asdict,dataclass,replace'+nl
    grid_anchor=b'    grids=maze_grids()'+nl
    if raw.count(import_anchor)!=1 or raw.count(grid_anchor)!=1:raise ValueError('Storage startup anchor changed')
    raw=raw.replace(import_anchor,import_anchor+b'from types import MappingProxyType'+nl,1)
    raw=raw.replace(grid_anchor,grid_anchor+nl.join((
        b'    accounts.movement_grids=MappingProxyType(dict(grids))',
        b'    from runtime_movement import load_movement_policy',
        b'    accounts.movement_policy=load_movement_policy()'))+nl,1)
    patch['runtime_storage.py']=raw
    now=datetime.now(timezone.utc)
    release=ROOT/'runtime/deployments'/('world-collision-'+now.strftime('%Y%m%dT%H%M%SZ'))
    source=release/'source';source.mkdir(parents=True,exist_ok=False)
    changes=[]
    for name in old['sha256']:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(BASE/'source'/name,target)
    for name,data in patch.items():
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        before=BASE/'source'/name
        changes.extend(difflib.unified_diff(before.read_text(encoding='utf-8').splitlines(True) if before.exists() else [],
            target.read_text(encoding='utf-8').splitlines(True),fromfile='live-base/'+name,tofile='collision/'+name))
    hashes={str(p.relative_to(source)).replace('\\','/'):digest(p) for p in source.rglob('*') if p.is_file()}
    changed={n:v for n,v in hashes.items() if old['sha256'].get(n)!=v}
    if set(changed)!=set(patch):raise ValueError('Unexpected collision delta')
    shutil.copy2(BASE/'run_release.py',release/'run_release.py')
    manifest=dict(created_utc=now.isoformat(),base_release=str(BASE),sha256=hashes,changed_modules=changed,
        runner_sha256=digest(release/'run_release.py'),scope='original current-cell maze with exact delivered normal-state lifecycle')
    (release/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (release/'changes.diff').write_text(''.join(changes),encoding='utf-8')
    harness=release/'harness';harness.mkdir()
    for p in (BASE/'harness').glob('*.py'):shutil.copy2(p,harness/p.name)
    # Only collision verification and its deliberately updated Peer assertion.
    names=['verify_runtime.py','verify_runtime_movement_lifecycle.py','verify_runtime_movement_terminals.py',
        'verify_world_movement_delivery_boundaries.py','verify_runtime_movement_battle.py',
        'verify_runtime_movement_intro_race.py',
        'verify_world_late_finalize_membership.py','verify_runtime_transfer_replays.py',
        'verify_runtime_private_map_factory.py','research_world_scene_delivery_abandonment.py','verify_world_encrypted_collision.py',
        'verify_world_resource_runtime.py','verify_world_current_cell_collision.py','verify_world_current_cell_maps.py',
        'verify_world_movement_state_lifecycle_native.py','verify_world_scene_movement_state_native.py',
        'verify_world_movement_state_transitions_native.py','verify_world_movement_reconciliation_native.py']
    for name in names:shutil.copy2(ROOT/name,harness/name)
    workspace=harness/'workspace';shutil.copytree(BASE/'harness/workspace',workspace)
    for name in hashes:
        target=workspace/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,target)
    harness_hashes={p.name:digest(p) for p in harness.glob('*.py')}
    for name in harness_hashes:shutil.copy2(harness/name,workspace/name)
    shutil.copytree(BASE/'harness/evidence',harness/'evidence')
    workspace_hashes=dict(previous['workspace_sha256'])
    for name,value in hashes.items():
        if name in workspace_hashes or not name.startswith('evidence/'):
            workspace_hashes[name]=value
    workspace_hashes.update(harness_hashes)
    private=ROOT/'runtime/deployments/private-story-20261023T190051Z'
    private_record=json.loads((private/'candidate.json').read_text(encoding='utf-8'))
    for name in ('evidence/npc-client-visit-root-red.json','evidence/npc-interaction-compatibility-audit.json'):
        original=private/'harness/workspace'/name
        expected=private_record['workspace_sha256'][name]
        if digest(original)!=expected:raise ValueError('Private original fixture changed: '+name)
        shutil.copy2(original,workspace/name);workspace_hashes[name]=expected
    record=dict(release=str(release),base_release=str(BASE),base_pid_at_staging=48572,
        file_count=len(hashes),changed_modules=changed,production_origins={n:str(ROOT/n) for n in patch},
        started=False,checks_required=CHECKS,new_empty_tables=[],verification_name='world-collision',
        scope=manifest['scope'],harness_sha256=harness_hashes,
        harness_sources={n:str(harness/n) for n in harness_hashes},
        harness_resource_sha256=previous['harness_resource_sha256'],workspace_sha256=workspace_hashes,
        check_arguments={**private_record.get('check_arguments',{}),
            'verify_world_late_finalize_membership.py':['--report',str(workspace/'evidence/world-late-finalize-membership.json')],
            'verify_world_resource_runtime.py':['--runtime-source',str(source),'--runtime-harness',str(harness),
            '--client-root',str(ROOT.parent),'--report',str(workspace/'evidence/world-collision-all302-runtime.json')]},
        verification_module_sources={str(workspace/'evidence/reviews/npc-loyalty-quote-20261024/base/npc_recovery.py'):
            previous['verification_module_sources'][str(BASE/'harness/workspace/evidence/reviews/npc-loyalty-quote-20261024/base/npc_recovery.py')]},
        native_gui_verified=False)
    record['production_origins']['runtime_storage.py']='exact live BASE plus startup frozen maze/policy only; repair guard retained'
    bundle=dict(production=hashes,runner=manifest['runner_sha256'],harness=harness_hashes,
        resources=record['harness_resource_sha256'],workspace=workspace_hashes,
        checks=CHECKS,arguments=record['check_arguments'])
    record['acceptance_input_sha256']=hashlib.sha256(json.dumps(bundle,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    text=json.dumps(record,indent=2)
    (release/'candidate.json').write_text(text,encoding='utf-8')
    (ROOT/'staging/world-collision-candidate.json').write_text(text,encoding='utf-8')
    print(json.dumps(dict(release=str(release),delta=list(changed),checks=len(CHECKS),file_count=len(hashes))))


if __name__=='__main__':main()
