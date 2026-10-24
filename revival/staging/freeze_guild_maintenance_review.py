"""Immutable filesystem candidate; no Git repository is available."""
from pathlib import Path
from datetime import datetime,timezone
import ast,difflib,hashlib,json,shutil,sys

root=Path(__file__).resolve().parents[1]
previous=root/'evidence/reviews/guild-buildings-20261024T041930Z'
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
prior=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else None
review=Path(str(prior)+'-'+(sys.argv[2] if len(sys.argv)>2 else 'r2')) if prior else root/'evidence/reviews'/('guild-maintenance-'+stamp)
review.mkdir();(review/'source').mkdir();(review/'baseline').mkdir();(review/'results').mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
changed=('guild_maintenance.py','guild_maintenance_closure.py','guild_maintenance_runtime.py','guild_buildings.py',
    'guild_dissolution.py','faction_domain.py','faction_runtime.py','guild_runtime.py',
    'verify_guild_maintenance.py','verify_guild_maintenance_native.py')
for p in (prior/'source' if prior else root).glob('*.py'):(review/'source'/p.name).write_bytes(p.read_bytes())
for name in changed:(review/'source'/name).write_bytes((root/name).read_bytes())
(review/'source/design').mkdir();shutil.copy2((prior/'source' if prior else root)/'design/recovery-baseline.json',review/'source/design/recovery-baseline.json')
specs={'AGENTS.md':root.parent/'AGENTS.md','ARCHITECTURE.md':root/'ARCHITECTURE.md','DESIGN_AUTHORITY.md':root/'DESIGN_AUTHORITY.md'}
for name in ('GUILD_MAINTENANCE_CONTRACT.md','GUILD_MAINTENANCE_RESOURCE_BINDING.md','GUILD_BUILDING_CONTRACT.md',
    'GUILD_BUILDING_MAINTENANCE_SOURCES.md','GUILD_RESEARCH_GROWTH_SOURCES.md'):
    specs[name]=root/'evidence'/name
for name,p in specs.items():shutil.copy2(prior/name if prior and name!='GUILD_MAINTENANCE_CONTRACT.md' else p,review/name)
baselines={};diff=[]
for name in changed:
    before=previous/'source'/name;after=review/'source'/name
    if before.exists():
        shutil.copy2(before,review/'baseline'/name);baselines[name]=sha(before)
    old=before.read_text(encoding='utf-8').splitlines(True) if before.exists() else []
    diff.extend(difflib.unified_diff(old,after.read_text(encoding='utf-8').splitlines(True),fromfile='baseline/'+name,tofile='candidate/'+name))
(review/'since-guild-buildings.diff').write_text(''.join(diff),encoding='utf-8')
resources=set(json.loads(((prior or previous)/'resource-inputs.json').read_text(encoding='utf-8')))
if not prior:resources.update(p.relative_to(root).as_posix() for p in (root/'design').glob('*.json'))
resources.add('decoded/ui/layouts/gang.layout')
resource_root=prior/'source' if prior else root
write(review/'resource-inputs.json',{n:dict(sha256=sha(resource_root/n),size=(resource_root/n).stat().st_size) for n in sorted(resources)})
for name in resources:
    target=review/'source'/name;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(resource_root/name,target)
oldrunner=(previous/'verify_fixed_candidate.py').read_text(encoding='utf-8')
old_scripts=next(ast.literal_eval(node.value) for node in ast.parse(oldrunner).body
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='scripts' for t in node.targets))
scripts=('verify_guild_maintenance.py','verify_guild_maintenance_native.py',*old_scripts)
runner=oldrunner.replace('scripts='+repr(old_scripts),'scripts='+repr(scripts))
check="for name,record in resources.items():assert sha(root/name)==record['sha256'],name"
runner=runner.replace(check,check+"\nfor name,record in resources.items():assert sha(source/name)==record['sha256'],'Pinned resource alias: '+name")
assert runner!=oldrunner
(review/'verify_fixed_candidate.py').write_text(runner,encoding='utf-8')
manifest=dict(batch=25,created_utc=datetime.now(timezone.utc).isoformat(),
    scope='guild-owned hourly maintenance source, atomic fees/resources/research, downgrade/terminal handoff, overdue resume and bounded periodic execution; explicit optional fixture policy only',
    baseline_origin=str(previous/'source'),changed_files=changed,
    candidate_sha256={n:sha(review/'source'/n) for n in changed},baseline_sha256=baselines,
    dependency_source_sha256={p.relative_to(review/'source').as_posix():sha(p)
        for p in [*sorted((review/'source').glob('*.py')),review/'source/design/recovery-baseline.json']},
    specification_sha256={n:sha(review/n) for n in specs},
    resource_manifest_sha256=sha(review/'resource-inputs.json'),diff_sha256=sha(review/'since-guild-buildings.diff'),
    git_adaptation='No Git repository; exact accepted batch24 filesystem baseline unified diff; commit list not applicable')
write(review/'candidate.json',manifest)
print(json.dumps(dict(review=str(review),manifest_sha256=sha(review/'candidate.json'),source_count=len(manifest['dependency_source_sha256']),scripts=len(scripts))))
