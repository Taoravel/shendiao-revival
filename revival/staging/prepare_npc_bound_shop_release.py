"""Freeze only the four reviewed bound-shop inputs over the actual live base."""
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/npc-close-master-commit-20261023T113819Z'
EXPECTED={
    'npc_gameplay.py':'e5d70e181a18dd13ff29ed0c9302bb65f980e8b498160c5eb8a444a15d344bfa',
    'npc_shop_payments.py':'874f6f02e3f154b32f408d61c853bc9cea07236d3f5db812c769e9de91d72450',
    'design/npc-shop-payments-v1.json':'e5575ee1c4e8718e862efec8cca25769416660ab417373a971b62393addca386',
    'design/currency-v1.json':'13a573af54597eee1ff6fdae3389a51615e5d8a24738713755b362900a79523d',
}
CHECKS=['verify_currency_bound_shop.py','verify_npc_bound_shop_runtime.py',
        'verify_npc_bound_shop_sources.py','verify_npc_shop_runtime.py',
        'verify_npc_services.py','verify_npc_pet_recovery_runtime.py',
        'verify_master_commit_card_runtime.py','verify_exit_initialization_runtime.py',
        'verify_npc_depot_close.py','verify_npc_depot_money_runtime.py']


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ready=json.loads((ROOT/'evidence/npc-bound-shop-ready.json').read_text(encoding='utf-8'))
    if ready['files']!=EXPECTED or ready['base_pid']!=44084:
        raise ValueError('Bound shop handoff changed')
    before=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in before['sha256'].items():
        if digest(BASE/'source'/name)!=expected:raise ValueError('Immutable live baseline changed: '+name)
    if digest(BASE/'run_release.py')!=before['runner_sha256']:
        raise ValueError('Immutable runner changed')
    for name,expected in EXPECTED.items():
        if digest(ROOT/name)!=expected:raise ValueError('Reviewed production input changed: '+name)
    now=datetime.now(timezone.utc)
    release=ROOT/'runtime/deployments'/('npc-bound-shop-'+now.strftime('%Y%m%dT%H%M%SZ'))
    release.mkdir(exist_ok=False);source=release/'source';source.mkdir()
    for name in before['sha256']:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(BASE/'source'/name,target)
    changes=[]
    for name in EXPECTED:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,target)
        old=BASE/'source'/name
        changes.extend(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True) if old.exists() else [],
            target.read_text(encoding='utf-8').splitlines(True),fromfile='live-base/'+name,tofile='bound-shop/'+name))
    hashes={str(p.relative_to(source)).replace('\\','/'):digest(p) for p in source.rglob('*') if p.is_file()}
    delta={name for name,value in hashes.items() if before['sha256'].get(name)!=value}
    if delta!=set(EXPECTED):raise ValueError('Candidate changes outside the approved four inputs')
    scope='ordinary NPC mode1 bound-silver payment and binding1 output only; preserve cash mode0 receipts'
    manifest={'created_utc':now.isoformat(),'base_release':str(BASE),'sha256':hashes,
              'changed_modules':EXPECTED,'scope':scope,'runner_sha256':digest(BASE/'run_release.py')}
    (release/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(BASE/'run_release.py',release/'run_release.py')
    (release/'changes.diff').write_text(''.join(changes),encoding='utf-8')
    harness=release/'harness';harness.mkdir()
    for name in CHECKS:shutil.copy2(ROOT/name,harness/name)
    record={'release':str(release),'base_release':str(BASE),'base_pid_at_staging':44084,
            'changed_modules':EXPECTED,'file_count':len(hashes),'started':False,
            'scope':scope,'checks_required':CHECKS,'verification_name':'npc-bound-shop',
            'harness_sources':{name:str(harness/name) for name in CHECKS},
            'harness_sha256':{name:digest(harness/name) for name in CHECKS},
            'shared_modules_unchanged':True,'native_gui_verified':False,
            'excluded':'lifecycle/care/new creation/v2/world/story instance and all other workspace changes'}
    data=json.dumps(record,ensure_ascii=False,indent=2)
    (release/'candidate.json').write_text(data,encoding='utf-8')
    (ROOT/'staging/npc-bound-shop-candidate.json').write_text(data,encoding='utf-8')
    print(json.dumps(record,ensure_ascii=True))


if __name__=='__main__':main()
