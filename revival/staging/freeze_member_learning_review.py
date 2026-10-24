"""Freeze batch26 against accepted25, retaining exact resource/code inputs."""
from pathlib import Path
from datetime import datetime,timezone
import ast,difflib,hashlib,json,shutil,sys

root=Path(__file__).resolve().parents[1]
previous=root/'evidence/reviews/guild-maintenance-20261024T051526Z-r3'
prior=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else None
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
review=Path(str(prior)+'-'+sys.argv[2]) if prior else root/'evidence/reviews'/('guild-member-learning-'+stamp)
review.mkdir();(review/'source').mkdir();(review/'baseline').mkdir();(review/'results').mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
changed=('role_life_skills.py','role_learning_costs.py','guild_member_learning.py','life_skill_protocol.py',
    'member_learning_npc.py','faction_domain.py','faction_runtime.py','guild_runtime.py',
    'guild_practice.py','faction_types.py','verify_guild_member_learning.py','verify_guild_member_learning_native.py')
for p in (prior/'source' if prior else root).glob('*.py'):(review/'source'/p.name).write_bytes(p.read_bytes())
for name in changed:shutil.copy2(root/name,review/'source'/name)
specs={'AGENTS.md':root.parent/'AGENTS.md','ARCHITECTURE.md':root/'ARCHITECTURE.md','DESIGN_AUTHORITY.md':root/'DESIGN_AUTHORITY.md'}
for name in ('GUILD_MEMBER_LEARNING_CONTRACT.md','GUILD_MEMBER_SKILL_NATIVE_RESEARCH.md','CURRENCY_DECISION.md',
    'NEWBIE_FIRST_SKILL_DECISION.md','GUILD_MAINTENANCE_CONTRACT.md','GUILD_INDIVIDUAL_TRAINING_RESEARCH.md'):
    specs[name]=root/'evidence'/name
for name,path in specs.items():shutil.copy2(root/'evidence'/name if prior and name=='GUILD_MEMBER_LEARNING_CONTRACT.md' else prior/name if prior else path,review/name)
diff=[];baselines={}
for name in changed:
    before=previous/'source'/name;after=review/'source'/name
    if before.exists():shutil.copy2(before,review/'baseline'/name);baselines[name]=sha(before)
    old=before.read_text(encoding='utf8').splitlines(True) if before.exists() else []
    diff.extend(difflib.unified_diff(old,after.read_text(encoding='utf8').splitlines(True),fromfile='baseline/'+name,tofile='candidate/'+name))
(review/'since-guild-maintenance.diff').write_text(''.join(diff),encoding='utf8')
resources=set(json.loads(((prior or previous)/'resource-inputs.json').read_text(encoding='utf8')))
if not prior:resources.update(p.relative_to(root).as_posix() for p in (root/'design').glob('*.json'))
resources.update(('catalogs/knight.gsp.skill.clifeskill.json','catalogs/knight.gsp.skill.clifeskillcost.json',
    'decoded/ui/layouts/assistskillstudyinfaction.layout','decoded/ui/layouts/assistskillstudy.layout','decoded/ui/layouts/workshop.layout',
    'evidence/world-recovery.json'))
resource_root=prior/'source' if prior else root
input_path=lambda name: resource_root/name if (resource_root/name).exists() else root/name
write(review/'resource-inputs.json',{name:dict(sha256=sha(input_path(name)),size=input_path(name).stat().st_size) for name in sorted(resources)})
for name in resources:
    target=review/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(input_path(name),target)
oldrunner=(previous/'verify_fixed_candidate.py').read_text(encoding='utf8')
old_scripts=next(ast.literal_eval(node.value) for node in ast.parse(oldrunner).body if isinstance(node,ast.Assign)
    and any(isinstance(t,ast.Name) and t.id=='scripts' for t in node.targets))
scripts=('verify_guild_member_learning.py','verify_guild_member_learning_native.py',*old_scripts)
runner=oldrunner.replace('scripts='+repr(old_scripts),'scripts='+repr(scripts));assert runner!=oldrunner
runner=runner.replace('inspect_client.OUT=root','inspect_client.OUT=source')
runner=runner.replace("assert sha(root/'design/recovery-baseline.json')==sha(source/'design/recovery-baseline.json'),'Resource policy changed'",'')
runner=runner.replace("for name,record in resources.items():assert sha(root/name)==record['sha256'],name",'')
(review/'external-inputs.json').write_text('{}\n',encoding='utf8')
def stream_sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while block:=stream.read(1024*1024):digest.update(block)
    return digest.hexdigest()
external=root.parent/'artres/map.pfs'
write(review/'external-inputs.json',{str(external):dict(sha256=stream_sha(external),size=external.stat().st_size)})
runner=runner.replace('sys.path.insert(0,str(source))',"""external=json.loads((review/'external-inputs.json').read_text(encoding='utf8'))
def stream_sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while block:=stream.read(1024*1024):digest.update(block)
    return digest.hexdigest()
for name,record in external.items():assert stream_sha(Path(name))==record['sha256'],name
input_reads=set()
sys.dont_write_bytecode=True
def audit_open(event,args):
    if event!='open' or not isinstance(args[0],(str,bytes)):return
    name,mode,flags=args
    if (isinstance(mode,str) and 'r' not in mode and '+' not in mode) or (mode is None and flags&3):return
    path=Path(name.decode() if isinstance(name,bytes) else name).resolve()
    if path.suffix.lower() not in ('.py','.pyc') and (path.is_relative_to(root) or path.is_relative_to(root.parent/'artres')):
        input_reads.add(path)
sys.addaudithook(audit_open)
sys.path.insert(0,str(source))""")
runner+='''
actual_inputs={}
for path in sorted(tuple(input_reads)):
    if path.is_relative_to(review/'results'):continue
    if path.is_relative_to(source):
        name=path.relative_to(source).as_posix()
        assert name in resources,'Unenumerated frozen read: '+name
        digest=sha(path);assert digest==resources[name]['sha256'],name
    else:
        assert str(path) in external,'Unpinned external read: '+str(path)
        digest=stream_sha(path);assert digest==external[str(path)]['sha256'],str(path)
    actual_inputs[str(path)]={'sha256':digest,'size':path.stat().st_size}
for name,record in external.items():assert stream_sha(Path(name))==record['sha256'],name
write(review/'results/actual-input-reads.json',{'files':actual_inputs,'unlisted_workspace_or_original_asset_read':False,
    'mutable_workspace_resources_used':False,'frozen_resource_root':str(source)})
write(review/'results/runner-completed.json',{'scripts':len(results),'all_exit_zero':True,
    'source_and_resource_hashes_verified':True,'actual_input_read_audit_complete':True})
print(json.dumps({'audited_actual_inputs':len(actual_inputs),'external_archives':len(external)}))
'''
(review/'verify_fixed_candidate.py').write_text(runner,encoding='utf8')
manifest=dict(batch=26,created_utc=datetime.now(timezone.utc).isoformat(),
    scope='member life-skill source reservation, role-owned expenses/learning/receipts, guild compensation, service121 Adapter/current original panel and login recovery; explicit optional policy only, shared raw purchase routing and production policies not activated',
    baseline_origin=str(previous/'source'),changed_files=changed,candidate_sha256={n:sha(review/'source'/n) for n in changed},baseline_sha256=baselines,
    dependency_source_sha256={p.relative_to(review/'source').as_posix():sha(p) for p in [*sorted((review/'source').glob('*.py')),review/'source/design/recovery-baseline.json']},
    specification_sha256={name:sha(review/name) for name in specs},resource_manifest_sha256=sha(review/'resource-inputs.json'),
    external_input_manifest_sha256=sha(review/'external-inputs.json'),
    diff_sha256=sha(review/'since-guild-maintenance.diff'),git_adaptation='No Git repository; exact accepted25 filesystem source baseline/diff, commit list not applicable')
write(review/'candidate.json',manifest)
print(json.dumps(dict(review=str(review),manifest_sha256=sha(review/'candidate.json'),dependencies=len(manifest['dependency_source_sha256']),resources=len(resources),scripts=len(scripts))))
