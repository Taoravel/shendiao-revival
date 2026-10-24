"""Stage authorized master/cart ready and ordinary exit initialization fixes."""
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/npc-20261023T102110Z'
PATCHES={
    'task_master_card.py':'7e28fe263d72683ef0c9e446ae1b7bf5e59e0f7d07f5949d9f139df5499f5888',
    'task_cart_dialogue.py':'c6d8d0bc6997e78f62e9403e592cb1d527cf28a3e64c53939accaf5af075f3f6'}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in before['sha256'].items():
        if digest(BASE/'source'/name)!=expected:raise ValueError('Base release hash changed: '+name)
    for name,expected in PATCHES.items():
        if digest(ROOT/name)!=expected:raise ValueError('Delivered task module changed: '+name)
    patch_bytes={name:(ROOT/name).read_bytes() for name in
        (*PATCHES,'role_protocol.py','design/role-exit-ui-v1.json')}
    # Reject accidental workspace battle/care integration. Only these three
    # exit initialization edits may accompany the frozen NPC runtime.
    expected=(BASE/'source/game_runtime.py').read_text(encoding='utf-8')
    expected=expected.replace('parse_enter,parse_delete,\n','parse_enter,parse_delete,load_exit_ui_message,\n',1)
    expected=expected.replace("            spawn=list(await self.rt.map(self.position.value[0]).mailbox.call('spawn',self.id,self.epoch))",
        "            # The original world reset disables both X and the system exit\n"
        "            # menu until this signed-mode notification initializes them.\n"
        "            spawn=[self.rt.exit_ui_message]\n"
        "            spawn.extend(await self.rt.map(self.position.value[0]).mailbox.call('spawn',self.id,self.epoch))",1)
    expected=expected.replace('    def __init__(self, accounts, prepared, io=None, logger=None, training=False):\n',
        '    def __init__(self, accounts, prepared, io=None, logger=None, training=False):\n'
        '        self.exit_ui_message=load_exit_ui_message()\n',1)
    base_runtime_bytes=(BASE/'source/game_runtime.py').read_bytes()
    patch_bytes['game_runtime.py']=(expected.replace('\n','\r\n') if b'\r\n' in base_runtime_bytes else expected).encode('utf-8')
    patches={name:hashlib.sha256(value).hexdigest() for name,value in patch_bytes.items()}
    base_hashes={str(p.relative_to(BASE/'source')).replace('\\','/'):digest(p)
        for p in (BASE/'source').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    now=datetime.now(timezone.utc)
    release=ROOT/'runtime/deployments'/('master-ready-exit-'+now.strftime('%Y%m%dT%H%M%SZ'))
    release.mkdir(exist_ok=False)
    source=release/'source'
    shutil.copytree(BASE/'source',source,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    changes=[]
    for name,expected in patches.items():
        (source/name).parent.mkdir(parents=True,exist_ok=True)
        (source/name).write_bytes(patch_bytes[name])
        if digest(source/name)!=expected:raise ValueError('Task copy changed: '+name)
        changes.extend(difflib.unified_diff(((BASE/'source'/name).read_text(encoding='utf-8') if (BASE/'source'/name).exists() else '').splitlines(True),
            (source/name).read_text(encoding='utf-8').splitlines(True),fromfile='base/'+name,tofile='ready/'+name))
    hashes={str(p.relative_to(source)).replace('\\','/'):digest(p) for p in source.rglob('*') if p.is_file()}
    actual={name for name,value in hashes.items() if value!=base_hashes.get(name)}
    if actual!=set(patches):raise ValueError('Release includes an unauthorized source change')
    if any(digest(BASE/'source'/name)!=value for name,value in base_hashes.items()):
        raise ValueError('Base source changed while copying')
    manifest={'created_utc':now.isoformat(),'base_release':str(BASE),
        'scope':'User-authorized first-master/cart ready fix and reported X/ordinary exit initialization only; frozen NPC baseline',
        'changed_modules':patches,'sha256':hashes,'runner_sha256':digest(BASE/'run_release.py'),
        'baseline_unlisted_inputs_captured':sorted(set(base_hashes)-set(before['sha256']))}
    (release/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(BASE/'run_release.py',release/'run_release.py')
    (release/'ready-changes.diff').write_text(''.join(changes),encoding='utf-8')
    record={'release':str(release),'base_release':str(BASE),'base_pid_at_staging':33072,
        'changed_modules':patches,'file_count':len(hashes),'started':False,
        'excluded':'all other workspace changes, including care/new creation/new wild/combat/task100106',
        'native_gui_verified':False,'real_roles_modified_by_staging':False,
        'game_runtime_derived_from_frozen_base':True}
    (release/'candidate.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'staging/master-ready-candidate.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=True))


if __name__=='__main__':main()
