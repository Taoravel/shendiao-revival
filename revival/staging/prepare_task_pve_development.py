"""Build a disposable exact BASE combination for the natural P0 feedback.

Never a release/deployment approval. Task source comes from fixed reviewed
slices, shared source from the explicitly named main files only. No hot NPC,
Inventory, World or whole workspace copies are admitted.
"""
import hashlib
import json
from pathlib import Path
import shutil
import ast
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/npc-repair-20261024T023920Z'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=ROOT/'staging/candidates'/('task-pve-development-'+stamp)
    target.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in manifest['sha256'].items():
        if sha(BASE/'source'/name)!=expected:raise ValueError('Published BASE source drift: '+name)
    shutil.copytree(BASE/'source',target/'source')
    shutil.copytree(BASE/'harness',target/'harness')
    selected={}
    main_files=('accounts.py','game_runtime.py','runtime_storage.py','battle_owner.py',
        'role_resource_storage.py','task_pve.py','task_pve_runtime_storage.py',
        'task_pve_recovery.py','task_dream_resources.py',
        'design/task-pve-ai8001-v1.json','design/newbie-first-skill-v1.json')
    for name in main_files:selected[name]=ROOT/name
    task_slices={
        'task-first-skill-20261024-r3':('task_domain.py',),
        'local-prologue-first-skill-20261024-r2':('role_skills.py','task_first_skill.py',
            'design/local-prologue-other-skills-baseline-v1.json'),
        'visible-notice-20261024T042625Z':('visible_notice.py',),
        'task-first-battle-20261024-r1':('task_first_battle.py',),
        'task-battle-terminal-recovery-20261024-r2':('task_battle.py',),
        'task-dream-return-settlement-20261024-r4':('task_prologue_puzzle.py',),
    }
    for review,names in task_slices.items():
        for name in names:selected[name]=ROOT/'evidence/reviews'/review/'source'/name
    # New notice depends only on the existing chat codec, not the rest of the
    # current Social/organization workspace. Pin the actual used statements.
    def chat_contract(path):
        nodes=[]
        for node in ast.parse(path.read_text(encoding='utf-8')).body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in ('text','chat_message'):
                nodes.append(ast.dump(node,include_attributes=False))
            elif isinstance(node,ast.Assign):
                names={item.id for item in ast.walk(node) if isinstance(item,ast.Name) and isinstance(item.ctx,ast.Store)}
                if names.intersection(('CHAT_RECEIVE','CURRENT_CHANNEL')):
                    nodes.append(ast.dump(node,include_attributes=False))
        if len(nodes)!=4:raise ValueError('Chat dependency contract shape changed')
        return nodes
    notice_review=ROOT/'evidence/reviews/visible-notice-20261024T042625Z/source'
    if chat_contract(BASE/'source/social_protocol.py')!=chat_contract(notice_review/'social_protocol.py'):
        raise ValueError('Published chat codec differs from the verified notice dependency')
    origins={}
    for name,source in selected.items():
        destination=target/'source'/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
        origins[name]=dict(path=str(source),sha256=sha(source))
        if sha(destination)!=origins[name]['sha256']:raise ValueError('Selected input changed while copying')
    tests=('diagnose_growth_first_battle_runtime.py','verify_task_pve_engine.py',
           'verify_task_pve_storage.py','verify_task_pve_recovery.py','verify_task_dream_resources.py',
           'verify_task_pve_current_role.py')
    for name in tests:
        shutil.copyfile(ROOT/name,target/'harness'/name)
    shutil.copyfile(ROOT/'evidence/reviews/task-first-skill-20261024-r3/source/research_other_skill_snapshot.py',
                    target/'harness/research_other_skill_snapshot.py')
    # The diagnostic normally lives directly under revival and derives the
    # original artres root from its own depth. This frozen copy is deeper; use
    # the SAME explicit asset root as the actual immutable run_release.py.
    probe=target/'harness/diagnose_growth_first_battle_runtime.py'
    original=probe.read_text(encoding='utf-8')
    old='inspect_client.ROOT=Path(__file__).resolve().parents[1]'
    if original.count(old)!=1:raise ValueError('Natural probe asset binding changed')
    probe.write_text(original.replace(old,"inspect_client.ROOT=Path('D:/神雕侠侣')"),encoding='utf-8')
    source_hashes={str(path.relative_to(target/'source')).replace('\\','/'):sha(path)
        for path in (target/'source').rglob('*') if path.is_file() and '__pycache__' not in path.parts}
    harness_hashes={str(path.relative_to(target/'harness')).replace('\\','/'):sha(path)
        for path in (target/'harness').rglob('*') if path.is_file() and '__pycache__' not in path.parts}
    record=dict(base=str(BASE),source=str(target/'source'),harness=str(target/'harness'),
        selected_origins=origins,source_sha256=source_hashes,harness_sha256=harness_hashes,
        scope='offline development only; not reviewed for full runtime activation or deployment',
        harness_resource_binding=dict(original_probe=str(ROOT/'diagnose_growth_first_battle_runtime.py'),
            original_sha256=sha(ROOT/'diagnose_growth_first_battle_runtime.py'),
            actual_game_root=str(ROOT.parent),change='only test artres root binding, matching actual release runner'),
        live_server_changed=False,live_database_opened=False,client_operated=False)
    (target/'manifest.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    (ROOT/'staging/task-pve-development-current.json').write_text(json.dumps(dict(candidate=str(target)),indent=2),encoding='utf-8')
    print(json.dumps(dict(candidate=str(target),source_inputs=len(source_hashes),selected=len(selected))))


if __name__=='__main__':main()
