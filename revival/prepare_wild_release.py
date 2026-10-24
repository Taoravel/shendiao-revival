"""Build a frozen wild fix release atop the exact currently published source.

No listener/process/real database mutation. Only enumerated wild/resource files
are overlaid; unrelated in-progress workspace changes never enter this release.
"""
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parent
BASE=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'runtime/deployments/npc-20261023T102110Z'
OVERLAY_ROOT=Path(sys.argv[2]).resolve()/'source' if len(sys.argv)>2 else ROOT
BASE_INPUTS=('evidence/world-recovery.json',)
OVERLAYS=(
    'wild_runtime_storage.py','wild_rewards.py','wild_battle.py','wild_encounters.py',
    'verify_wild_runtime.py','verify_wild_encounters.py','verify_wild_rewards.py','verify_wild_rewards_v2.py',
    'catalogs/wild-encounters.json','catalogs/wild-reward-pools.json',
    'design/wild-encounters-v1.json','design/wild-rewards-v2.json',
    'role_resource_plan.py','role_resource_storage.py','design/role-resources-v1.json','verify_role_resource_combat.py')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    review=ROOT/'evidence/reviews/role-resource-combat-20261023'
    for row in json.loads((review/'scope.json').read_text(encoding='utf-8'))['files']:
        if sha(OVERLAY_ROOT/row['path'])!=row['after_sha256']:raise ValueError('Resource review snapshot changed')
    original=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    for name,digest in original['sha256'].items():
        if sha(BASE/'source'/name)!=digest:raise ValueError('Current release base changed: '+name)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    release=ROOT/'runtime/deployments'/('wild-'+stamp)
    release.mkdir();source=release/'source';source.mkdir()
    # Preserve the exact immutable dependency set; output reports are not inputs.
    for name in set(original['sha256'])|set(BASE_INPUTS):
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(BASE/'source'/name,target)
    captured={name:sha(OVERLAY_ROOT/name) for name in OVERLAYS}
    for name in OVERLAYS:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(OVERLAY_ROOT/name,target)
    if any(sha(OVERLAY_ROOT/name)!=digest or sha(source/name)!=digest for name,digest in captured.items()):
        raise ValueError('Wild overlay changed while freezing')
    patch_file=ROOT/'evidence/wild-disconnect-fix.json'
    if patch_file.exists():
        patches=json.loads(patch_file.read_text(encoding='utf-8'))
        game=source/'game_runtime.py';text=game.read_text(encoding='utf-8')
        for patch in patches['patches']:
            if text.count(patch['before'])!=1:raise ValueError('Published wild function changed; rebase explicitly')
            text=text.replace(patch['before'],patch['after'],1)
        game.write_text(text,encoding='utf-8')
    runner=(BASE/'run_release.py').read_text(encoding='utf-8').replace('Verified immutable NPC release','Verified immutable wild release')
    (release/'run_release.py').write_text(runner,encoding='utf-8')
    keys=set(original['sha256'])|set(BASE_INPUTS)|set(OVERLAYS)
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        base_release=str(BASE),overlay_source=str(OVERLAY_ROOT),scope='exact published immutable base plus enumerated wild and reviewed combat resource correction',
        sha256={name:sha(source/name) for name in sorted(keys)},runner_sha256=sha(release/'run_release.py'),
        source_captured_coherently=True,training=False,automatic_resource_migration=False,overlays=list(OVERLAYS))
    (release/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    review_dir=ROOT/'evidence/reviews'/release.name;review_dir.mkdir()
    changes=[];files=[]
    for name in (*OVERLAYS,'game_runtime.py'):
        before=BASE/'source'/name;after=source/name
        old=before.read_text(encoding='utf-8-sig').splitlines(True) if before.exists() else []
        new=after.read_text(encoding='utf-8-sig').splitlines(True)
        delta=list(difflib.unified_diff(old,new,fromfile='published/'+name,tofile='candidate/'+name))
        if delta:
            files.append(dict(path=name,before_sha256=sha(before) if before.exists() else None,after_sha256=sha(after)))
            changes.extend(delta)
    (review_dir/'changes.diff').write_text(''.join(changes),encoding='utf-8')
    scope=dict(base=str(BASE/'source'),current=str(source),git_available=False,commits=[],files=files,
        preserved_context=['game_runtime.py wild_move/battle_step/finish_battle/load/close',
                           'runtime_storage.py startup resources','battle_owner.py engine factory'],
        spec=str(ROOT/'evidence/WILD_RUNTIME_INTEGRATION.md'))
    (review_dir/'scope.json').write_text(json.dumps(scope,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'evidence/wild-release-candidate.json').write_text(json.dumps(dict(release=str(release),review=str(review_dir)),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(release=str(release),review=str(review_dir),files=len(keys),changed=len(files)),ensure_ascii=False))


if __name__=='__main__':main()
