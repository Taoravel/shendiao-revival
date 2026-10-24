"""Freeze the reviewed loyalty recipe over the actual private-story release."""
import argparse
from datetime import datetime,timezone
import difflib,hashlib,json,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/private-story-20261023T190051Z'
CHECKS=['verify_npc_loyalty_quote.py','verify_npc_loyalty_quote_runtime.py',
    'verify_npc_pet_recovery_runtime.py','verify_npc_inn_resources.py',
    'verify_prologue_touch_runtime.py','verify_battle_damage_presentation.py']


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--enable-known-profile',action='store_true')
    args=parser.parse_args()
    ready=json.loads((ROOT/'evidence/npc-pet-loyalty-v2-ready.json').read_text(encoding='utf-8'))
    before=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    for name,value in before['sha256'].items():
        if digest(BASE/'source'/name)!=value:raise ValueError('BASE changed: '+name)
    patch={};origins={}
    for name,value in ready['production_inputs'].items():
        if digest(ROOT/name)!=value:raise ValueError('Reviewed loyalty source changed: '+name)
        patch[name]=(ROOT/name).read_bytes();origins[name]=str(ROOT/name)
    if args.enable_known_profile:
        raw=(BASE/'source/runtime_storage.py').read_bytes()
        newline=b'\r\n' if b'\r\n' in raw else b'\n'
        guard=newline.join((b'    if intent.kind!=1:',
            b"        _require_unmigrated_operation(accounts,inventory,'Pet recovery awaits inventory resource-source integration')"))+newline
        if raw.count(guard)!=1:raise ValueError('Expected shared pet-recovery guard changed')
        patch['runtime_storage.py']=raw.replace(guard,b'',1)
        origins['runtime_storage.py']='BASE only pet-recovery guard removal; repair guard and every other source unchanged'
    now=datetime.now(timezone.utc)
    release=ROOT/'runtime/deployments'/('npc-loyalty-'+now.strftime('%Y%m%dT%H%M%SZ'))
    source=release/'source';source.mkdir(parents=True,exist_ok=False)
    for name in before['sha256']:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/'source'/name,target)
    changes=[]
    for name,data in patch.items():
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        old=BASE/'source'/name
        changes.extend(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True) if old.exists() else [],
            target.read_text(encoding='utf-8').splitlines(True),fromfile='live-base/'+name,tofile='loyalty/'+name))
    hashes={str(path.relative_to(source)).replace('\\','/'):digest(path) for path in source.rglob('*') if path.is_file()}
    changed={name:value for name,value in hashes.items() if before['sha256'].get(name)!=value}
    if set(changed)!=set(patch):raise ValueError('Unexpected loyalty scope')
    shutil.copy2(BASE/'run_release.py',release/'run_release.py')
    manifest=dict(created_utc=now.isoformat(),base_release=str(BASE),sha256=hashes,
        changed_modules=changed,runner_sha256=digest(release/'run_release.py'),
        scope='known ordinary pet blood remainder loyalty quote; historical paid receipts remain current-only')
    (release/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (release/'changes.diff').write_text(''.join(changes),encoding='utf-8')
    harness=release/'harness';(harness/'evidence').mkdir(parents=True)
    for path in (BASE/'harness').glob('*.py'):shutil.copy2(path,harness/path.name)
    for name in ('diagnose_npc_loyalty_quote.py','verify_npc_loyalty_quote.py','verify_npc_loyalty_quote_runtime.py'):
        data=(ROOT/name).read_bytes()
        if name=='verify_npc_loyalty_quote.py':
            data=data.replace(b"Path(__file__).parent/'evidence/reviews/npc-loyalty-quote-20261024/base/npc_recovery.py'",
                b"OUT/'evidence/reviews/npc-loyalty-quote-20261024/base/npc_recovery.py'")
            data=data.replace(b'(Path(__file__).parent/name)',b'(OUT/name)')
        (harness/name).write_bytes(data)
    shutil.copy2(source/'evidence/native-image.bin',harness/'evidence/native-image.bin')
    workspace=harness/'workspace';workspace.mkdir()
    for name in hashes:
        target=workspace/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,target)
    harness_hashes={path.name:digest(path) for path in harness.glob('*.py')}
    for name in harness_hashes:shutil.copy2(harness/name,workspace/name)
    fixtures=('evidence/npc-loyalty-quote-native.json',
        'evidence/reviews/npc-loyalty-quote-20261024/base/npc_recovery.py')
    workspace_hashes={name:value for name,value in hashes.items()
        if not name.startswith('evidence/') or name.endswith('.bin') or name=='evidence/newbie-birth-sites-audit.json'}
    workspace_hashes.update(harness_hashes)
    for name in fixtures:
        target=workspace/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
        workspace_hashes[name]=digest(target)
    record=dict(release=str(release),base_release=str(BASE),base_pid_at_staging=14480,
        file_count=len(hashes),changed_modules=changed,production_origins=origins,started=False,
        checks_required=CHECKS,new_empty_tables=[],verification_name='npc-loyalty',scope=manifest['scope'],
        harness_sha256=harness_hashes,harness_sources={name:str(harness/name) for name in harness_hashes},
        harness_resource_sha256={'evidence/native-image.bin':digest(harness/'evidence/native-image.bin')},
        workspace_sha256=workspace_hashes,check_arguments={},
        verification_module_sources={str(workspace/fixtures[1]):digest(workspace/fixtures[1])},
        harness_adaptation='loyalty verifier report/hash and old-module file roots redirect to bound OUT; gameplay imports immutable source',
        known_profile_guard_removed=args.enable_known_profile,native_gui_verified=False)
    bundle=dict(production=hashes,runner=manifest['runner_sha256'],harness=harness_hashes,
        resources=record['harness_resource_sha256'],workspace=workspace_hashes,checks=CHECKS,arguments={})
    record['acceptance_input_sha256']=hashlib.sha256(json.dumps(bundle,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    text=json.dumps(record,indent=2)
    (release/'candidate.json').write_text(text,encoding='utf-8')
    (ROOT/'staging/npc-loyalty-candidate.json').write_text(text,encoding='utf-8')
    print(json.dumps(dict(release=str(release),changed=changed,file_count=len(hashes),known_profile=args.enable_known_profile)))


if __name__=='__main__':main()
