"""Six reviewed healing inputs plus three owner-route lines over actual live."""
from datetime import datetime,timezone
import difflib,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/npc-bound-shop-20261023T115742Z'
EXPECTED={
 'npc_gameplay.py':'7212aa304509721bf82c4e5d6545212a5cc8c21b26bfbbf3901ed3c946c83387',
 'npc_role_healing.py':'1f9e6a594e666545d51db37806ffa6f2c5ec513e80aa0eab6da6ae014f95e160',
 'design/npc-role-healing-v1.json':'6f232df5c36dbb0f37aa2530670d2f7c38c65e6fbfc065bff116e24dacbbbaff',
 'role_resource_plan.py':'bc70cadabe5d214b95691e75cce2d7295f9781f56909d53200324e95305820c8',
 'design/role-resources-v1.json':'8be230cb69403f4eeefc2c72610e628035e802ab7777beaf3296abb8c4ff67a8',
 'design/currency-v1.json':'6a702ba9831a6ec99254ac4d4732f8d6c62ac4a6835157ead5df9de9c286e1cb',
}
CHECKS=['verify_role_resource_healing.py','verify_npc_role_healing.py',
 'verify_npc_role_healing_runtime.py','verify_npc_role_healing_guards.py',
 'verify_npc_bound_shop_runtime.py','verify_npc_bound_shop_sources.py',
 'verify_npc_transport_runtime.py','verify_master_commit_card_runtime.py',
 'verify_exit_initialization_runtime.py','verify_npc_pet_recovery_runtime.py']


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ready=json.loads((ROOT/'evidence/npc-role-healing-ready.json').read_text(encoding='utf-8'))
    if ready['files']!=EXPECTED or ready['base_pid']!=39796:raise ValueError('Healing handoff changed')
    before=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in before['sha256'].items():
        if digest(BASE/'source'/name)!=expected:raise ValueError('Immutable live baseline changed: '+name)
    if digest(BASE/'run_release.py')!=before['runner_sha256']:raise ValueError('Immutable runner changed')
    patch={}
    for name,expected in EXPECTED.items():
        if digest(ROOT/name)!=expected:raise ValueError('Reviewed healing input changed: '+name)
        patch[name]=(ROOT/name).read_bytes()
    raw=(BASE/'source/game_runtime.py').read_bytes();newline='\r\n' if b'\r\n' in raw else '\n'
    code=raw.decode('utf-8').replace('\r\n','\n')
    anchor='import npc_recovery\n'
    service="                if command.handler=='items.sell':\n                    return await self.io(npc_shop_sales.cache_messages,self.rt.accounts,self.inventory,proof.npc_id)\n"
    if code.count(anchor)!=1 or code.count(service)!=1:raise ValueError('Expected NPC routing seam changed')
    code=code.replace(anchor,anchor+'import npc_role_healing\n',1)
    code=code.replace(service,service+"                if command.handler=='role.heal':\n                    return await self.io(npc_role_healing.settle,self.rt.accounts,self.inventory,command)\n",1)
    patch['game_runtime.py']=code.replace('\n',newline).encode('utf-8')
    now=datetime.now(timezone.utc)
    release=ROOT/'runtime/deployments'/('npc-role-healing-'+now.strftime('%Y%m%dT%H%M%SZ'))
    release.mkdir(exist_ok=False);source=release/'source';source.mkdir()
    for name in before['sha256']:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/'source'/name,target)
    changes=[]
    for name,data in patch.items():
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        old=BASE/'source'/name
        changes.extend(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True) if old.exists() else [],
            target.read_text(encoding='utf-8').splitlines(True),fromfile='live-base/'+name,tofile='healing/'+name))
    hashes={str(p.relative_to(source)).replace('\\','/'):digest(p) for p in source.rglob('*') if p.is_file()}
    delta={name for name,value in hashes.items() if before['sha256'].get(name)!=value}
    if delta!=set(patch):raise ValueError('Candidate changes outside the approved seven production files')
    patched={name:hashes[name] for name in patch}
    scope='dedicated ordinary NPC10380 service294 healing with explicit known resource profile and cash fee only'
    manifest={'created_utc':now.isoformat(),'base_release':str(BASE),'sha256':hashes,
        'changed_modules':patched,'scope':scope,'runner_sha256':digest(BASE/'run_release.py')}
    (release/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(BASE/'run_release.py',release/'run_release.py')
    (release/'changes.diff').write_text(''.join(changes),encoding='utf-8')
    harness=release/'harness';harness.mkdir()
    for name in CHECKS:shutil.copy2(ROOT/name,harness/name)
    record={'release':str(release),'base_release':str(BASE),'base_pid_at_staging':39796,'changed_modules':patched,
        'file_count':len(hashes),'started':False,'scope':scope,'checks_required':CHECKS,
        'new_empty_tables':['npc_role_healing_receipts'],
        'verification_name':'npc-role-healing','harness_sources':{name:str(harness/name) for name in CHECKS},
        'harness_sha256':{name:digest(harness/name) for name in CHECKS},'game_runtime_derived_from_frozen_base':True,
        'native_gui_verified':False,'excluded':'private factory/role/story/touch/lifecycle/NPC interaction distance/social scene scope/care/creation/v2 and all other workspace changes'}
    data=json.dumps(record,ensure_ascii=False,indent=2)
    (release/'candidate.json').write_text(data,encoding='utf-8')
    (ROOT/'staging/npc-role-healing-candidate.json').write_text(data,encoding='utf-8')
    print(json.dumps(record,ensure_ascii=True))


if __name__=='__main__':main()
