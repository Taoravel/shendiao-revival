"""Freeze a Task-only delivery; no gameplay, server, DB or validation rerun."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

root=Path(__file__).resolve().parents[1]
bundle=root/'evidence/reviews/task-second-battle-20261024-r1'
source=bundle/'source';inputs=bundle/'inputs'
source.mkdir(exist_ok=False);inputs.mkdir(exist_ok=False)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=root/'evidence/task-second-battle-verification.json'
verified=json.loads(report.read_text(encoding='utf8'))
base=Path(verified['base'])
files=('task_first_skill_proof.py','task_second_battle.py','verify_task_second_battle.py','verify_local_prologue_teaching.py')
production=files[:2]
records={};patch=[]
for name in files:
    shutil.copy2(root/name,source/name)
    if name in verified['candidate_sources']:
        assert digest(source/name)==verified['candidate_sources'][name]
    baseline=bundle/'baseline'/name
    old=baseline.read_text(encoding='utf8') if baseline.is_file() else ''
    records[name]={'baseline_sha256':digest(baseline) if baseline.is_file() else hashlib.sha256(b'').hexdigest(),
        'sha256':digest(source/name),'production':name in production}
    patch.extend(difflib.unified_diff(old.splitlines(True),(source/name).read_text(encoding='utf8').splitlines(True),
        fromfile='baseline/'+name,tofile='source/'+name))
dependencies={}
for name,expected in verified['candidate_sources'].items():
    if name in files:continue
    origins=(base/name,root/name)
    origin=next((p for p in origins if p.is_file() and digest(p)==expected),None)
    assert origin is not None,name
    target=inputs/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(origin,target)
    dependencies[name]={'sha256':digest(target),'origin':str(origin)}
for name in ('verify_task_first_battle.py','diagnose_growth_first_battle_runtime.py'):
    origin=base/name if (base/name).is_file() else root/name
    shutil.copy2(origin,inputs/name);dependencies[name]={'sha256':digest(inputs/name),'origin':str(origin),
        'reason':'static import companion of snapshot helper; no main executed'}
shutil.copy2(report,bundle/'verification.json')
(bundle/'candidate.patch').write_text(''.join(patch),encoding='utf8')
manifest={'baseline':'Published053218 immutable BASE; two new production modules absent; existing teaching verifier bytes saved before edit',
    'base':str(base),'base_manifest_sha256':digest(base.parent/'manifest.json'),'files':records,
    'selected_dependencies':dependencies,'selected_dependencies_are_full_import_closure':False,
    'verification_sha256':digest(bundle/'verification.json'),'patch_sha256':digest(bundle/'candidate.patch'),
    'checks_repeated_by_freezer':False}
(bundle/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
delivery={'scope':'AI8027 Task-only second-battle gate and pure original teaching proof',
    'production_sources':{name:records[name]['sha256'] for name in production},
    'bundle':str(bundle),'manifest_sha256':digest(bundle/'manifest.json'),
    'integration':'evidence/TASK_SECOND_BATTLE_INTEGRATION.md','verification':'evidence/task-second-battle-verification.json',
    'necessary_public_chain_passed':True,'base':str(base),
    'second_battle_engine_executed':False,'shared_wired':False,'deployed':False,'native_gui_verified':False,
    'live_database_or_client_operated':False,'whole_goal_complete':False,
    'review':'No duplicated multi-round reviews after user requested minimal necessary checks; main integration remains separate',
    'red_cycles':['actual missing read_completed_first_skill_proof ImportError after natural teaching',
        'actual missing load_second_battle_rules/open_second_battle_transaction ImportError after natural teaching',
        'actual missing admit_second_battle_transaction ImportError after natural teaching'],
    'harness_repair':'FencedConnection has no total_changes; readonly authorizer check uses raw disposable store connection, production still enforces lease',
    'not_repeated':['old first-battle/teaching broad regressions','parallel independent review rounds','human role or GUI replay']}
(root/'evidence/task-second-battle-delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(delivery,ensure_ascii=False))
