"""Only the authorized carried-depot close, trainer menu and master commit fixes."""
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/wild-20261023T110855Z'
MENU_SNAPSHOT=ROOT/'evidence/npc-menu-close-ready-20261023'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in before['sha256'].items():
        if digest(BASE/'source'/name)!=expected:raise ValueError('Immutable live baseline changed: '+name)
    if digest(ROOT/'task_master_card.py')!='07bcfa4cb63086ac18f14a419ecb90a30c339e6db5186d581e9a30028c8ea100':
        raise ValueError('Delivered master commit module changed')
    policy=(ROOT/'design/newbie-master-card-v1.json').read_text(encoding='utf-8')
    if 'matching CCommitScenarioQuest may acknowledge' in policy:
        raise ValueError('Central master policy still requires the obsolete DialogEnd trigger')
    menu_manifest=json.loads((MENU_SNAPSHOT/'manifest.json').read_text(encoding='utf-8'))['files']
    for name,expected in menu_manifest.items():
        if digest(MENU_SNAPSHOT/name)!=expected:raise ValueError('Frozen NPC handoff changed: '+name)
    patch_bytes={name:(MENU_SNAPSHOT/name).read_bytes() for name in ('npc_services.py','npc_gameplay.py')}
    patch_bytes.update({name:(ROOT/name).read_bytes() for name in
        ('task_master_card.py','design/newbie-master-card-v1.json')})
    raw=(BASE/'source/game_runtime.py').read_bytes()
    text=raw.decode('utf-8');newline='\r\n' if b'\r\n' in raw else '\n'
    normalized=text.replace('\r\n','\n');anchor='        kind,body = cmd.args\n'
    if normalized.count(anchor)!=1:raise ValueError('Unexpected owner receive seam')
    normalized=normalized.replace(anchor,anchor+
        '        if kind==npc_depot.CLOSE_DEPOT:\n'
        '            npc_depot.decode_close(body)\n'
        '            self.npc_depot_ticket=None\n'
        '            return []\n',1)
    patch_bytes['game_runtime.py']=normalized.replace('\n',newline).encode('utf-8')
    now=datetime.now(timezone.utc)
    release=ROOT/'runtime/deployments'/('npc-close-master-commit-'+now.strftime('%Y%m%dT%H%M%SZ'))
    release.mkdir(exist_ok=False)
    source=release/'source';source.mkdir()
    # Copy exactly the frozen live manifest, excluding verifier outputs added
    # later to its source/evidence directory. Required static inputs are hashed.
    for name in before['sha256']:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(BASE/'source'/name,target)
    changes=[]
    for name,raw in patch_bytes.items():
        (source/name).write_bytes(raw)
        changes.extend(difflib.unified_diff((BASE/'source'/name).read_text(encoding='utf-8').splitlines(True),
            (source/name).read_text(encoding='utf-8').splitlines(True),fromfile='live-base/'+name,tofile='npc-card/'+name))
    hashes={str(p.relative_to(source)).replace('\\','/'):digest(p) for p in source.rglob('*') if p.is_file()}
    delta={name for name,value in hashes.items() if before['sha256'].get(name)!=value}
    if delta!=set(patch_bytes):raise ValueError('Candidate has changes outside the authorized five files')
    patched={name:hashes[name] for name in patch_bytes}
    manifest={'created_utc':now.isoformat(),'base_release':str(BASE),'sha256':hashes,'changed_modules':patched,
        'scope':'master Start CCommit card fix, trainer local menu grouping and empty depot close only',
        'runner_sha256':digest(BASE/'run_release.py')}
    (release/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(BASE/'run_release.py',release/'run_release.py')
    (release/'changes.diff').write_text(''.join(changes),encoding='utf-8')
    record={'release':str(release),'base_release':str(BASE),'base_pid_at_staging':10076,'changed_modules':patched,
        'file_count':len(hashes),'started':False,'game_runtime_derived_from_frozen_base':True,
        'excluded':'lifecycle/npc_state/npc_change/new care/creation/v2/other task or wild workspace changes',
        'native_gui_verified':False,'real_roles_modified_by_staging':False,'verification_name':'npc-close-master-commit',
        'checks_required':['research_first_master_dialogue_end.py','verify_master_commit_card_runtime.py',
            'verify_first_master_runtime.py','verify_task_master_card.py','verify_newbie_cart_runtime.py',
            'verify_npc_services.py','verify_npc_depot_close.py','verify_npc_pet_recovery_runtime.py',
            'verify_exit_initialization_runtime.py','verify_npc_shop_runtime.py','verify_npc_depot_money_runtime.py'],
        'harness_sources':{name:str(MENU_SNAPSHOT/name) for name in menu_manifest if name.startswith('verify_')}}
    data=json.dumps(record,ensure_ascii=False,indent=2)
    (release/'candidate.json').write_text(data,encoding='utf-8')
    (ROOT/'staging/npc-menu-card-candidate.json').write_text(data,encoding='utf-8')
    print(json.dumps(record,ensure_ascii=True))


if __name__=='__main__':main()
