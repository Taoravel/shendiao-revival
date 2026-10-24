"""Freeze the tested P0 combination and its exact acceptance inputs."""
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/npc-repair-20261024T023920Z'
DEV=ROOT/'staging/candidates/task-pve-development-20261024T051247429662Z'
FIXTURE=ROOT/'evidence/fixtures/task-pve-existing-role4-20261024T051401532220Z/accounts.sqlite3'
TABLES=['role_other_skill_baseline_migrations','role_other_skills','task_battle_admissions',
        'task_first_skills','task_pve_runtime_battles']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    baseline=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    previous=json.loads((BASE/'candidate.json').read_text(encoding='utf-8'))
    development=json.loads((DEV/'manifest.json').read_text(encoding='utf-8'))
    for name,value in development['source_sha256'].items():
        if sha(DEV/'source'/name)!=value:raise ValueError('Tested development input changed: '+name)
    if sha(FIXTURE)!='964b5d52ca0022f7a3049e885de632d7088ce822e10628a2786de4a91430a92d':
        raise ValueError('Sealed existing-role QA fixture changed')
    release=ROOT/'runtime/deployments'/('task-pve-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    release.mkdir(parents=True,exist_ok=False)
    source=release/'source';harness=release/'harness'
    shutil.copytree(DEV/'source',source)
    # Sole post-development production change: paid replies no longer require
    # a formerly participating pet after its legitimate rest/release.
    shutil.copyfile(ROOT/'task_pve_runtime_storage.py',source/'task_pve_runtime_storage.py')
    shutil.copytree(DEV/'harness',harness)
    shutil.copyfile(ROOT/'verify_task_pve_current_role.py',harness/'verify_task_pve_current_role.py')
    shutil.copyfile(ROOT/'verify_runtime_member_join_admission.py',harness/'verify_runtime_member_join_admission.py')
    shutil.copyfile(FIXTURE,harness/'evidence/task-pve-role4-fixture.sqlite3')
    for mode in ('win','recover','late-recover','source-drift','notice','defeat','paid-pet'):
        code=('"""Exact existing-role copy QA, never production account access."""\n'
            'from pathlib import Path\nimport runpy,sys\n'
            'root=Path(__file__).resolve().parent\n'
            'sys.argv=[str(root/"verify_task_pve_current_role.py"),"--source",str(root.parent/"source"),'
            '"--seed-db",str(root/"evidence/task-pve-role4-fixture.sqlite3"),"--role-id","4",'
            '"--case",'+repr(mode)+',"--report",str(root/"workspace/evidence"/'+repr('task-pve-role4-'+mode+'.json')+')]\n'
            'runpy.run_path(str(root/"verify_task_pve_current_role.py"),run_name="__main__")\n')
        (harness/('verify_task_pve_role4_'+mode.replace('-','_')+'.py')).write_text(code,encoding='utf-8')
    shutil.copyfile(BASE/'run_release.py',release/'run_release.py')
    source_hashes={str(p.relative_to(source)).replace('\\','/'):sha(p)
        for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    delta={name:value for name,value in source_hashes.items() if baseline['sha256'].get(name)!=value}
    diff=[]
    for name in sorted(delta):
        before=(BASE/'source'/name).read_text(encoding='utf-8').splitlines(True) if name in baseline['sha256'] else []
        after=(source/name).read_text(encoding='utf-8').splitlines(True)
        diff.extend(difflib.unified_diff(before,after,fromfile='BASE/'+name,tofile='P0/'+name))
    (release/'changes.diff').write_text(''.join(diff),encoding='utf-8')
    workspace=harness/'workspace'
    for name in delta:
        target=workspace/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source/name,target)
    (harness/'design').mkdir(exist_ok=True)
    resources=dict(previous['harness_resource_sha256'])
    for name in ('task-pve-ai8001-v1.json','newbie-first-skill-v1.json',
                 'local-prologue-other-skills-baseline-v1.json'):
        shutil.copyfile(source/'design'/name,harness/'design'/name)
        resources['design/'+name]=sha(harness/'design'/name)
    resources['evidence/task-pve-role4-fixture.sqlite3']=sha(FIXTURE)
    checks=['verify_task_pve_engine.py','verify_task_pve_storage.py','verify_task_pve_recovery.py',
        'verify_task_dream_resources.py']+['verify_task_pve_role4_'+mode+'.py' for mode in
        ('win','recover','late_recover','source_drift','notice','defeat','paid_pet')]+[
        'verify_battle_owner.py','verify_battle_damage_presentation.py','verify_runtime_member_join_admission.py',
        'verify_world_movement_delivery_boundaries.py','verify_runtime_transfer_replays.py',
        'verify_npc_repair_resource_runtime.py','verify_resource_npc_care_runtime.py',
        'verify_role_lifecycle_runtime.py','verify_exit_initialization_runtime.py']
    hh={p.name:sha(p) for p in harness.glob('*.py')}
    wh={name:sha(workspace/name) for name in previous['workspace_sha256']}
    wh.update({name:sha(workspace/name) for name in delta})
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),base_release=str(BASE),
        tested_development=str(DEV),sha256=source_hashes,changed_modules=delta,
        runner_sha256=sha(release/'run_release.py'),new_empty_tables=TABLES,
        scope='Real first dream Task PVE, atomic resource/reward recovery, existing-role first teaching and local visible refusal')
    (release/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    record=dict(release=str(release),base_release=str(BASE),base_pid_at_staging=7456,
        file_count=len(source_hashes),changed_modules=delta,production_origins=development['selected_origins'],
        started=False,checks_required=checks,new_empty_tables=TABLES,verification_name='task-pve',
        scope=manifest['scope'],harness_sha256=hh,harness_sources={name:str(harness/name) for name in hh},
        harness_resource_sha256=resources,workspace_sha256=wh,check_arguments={},
        verification_module_sources={str(workspace/Path(name).relative_to(BASE/'harness/workspace')):value
            for name,value in previous.get('verification_module_sources',{}).items()},
        native_gui_verified=False,real_database_role_or_task_migration=False)
    record['production_origins']['task_pve_runtime_storage.py']=dict(path=str(ROOT/'task_pve_runtime_storage.py'),
        sha256=delta['task_pve_runtime_storage.py'],post_development_change='only paid released-pet omission; fresh strict')
    bundle=dict(production=source_hashes,runner=manifest['runner_sha256'],harness=hh,
        resources=resources,workspace=wh,checks=checks,arguments={})
    record['acceptance_input_sha256']=hashlib.sha256(json.dumps(bundle,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    text=json.dumps(record,indent=2)
    (release/'candidate.json').write_text(text,encoding='utf-8')
    (ROOT/'staging/task-pve-candidate.json').write_text(text,encoding='utf-8')
    print(json.dumps(dict(release=str(release),source=len(source_hashes),harness=len(hh),
        delta=len(delta),checks=len(checks),seal=record['acceptance_input_sha256'])))


if __name__=='__main__':main()
