"""Freeze only the automatic attack fix over a verified current release."""
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parent
BASE=Path(sys.argv[1]).resolve()
OVERLAYS=('training_battle.py','research_battle_auto.py','verify_wild_auto_runtime.py')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    original=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    for name,digest in original['sha256'].items():
        assert sha(BASE/'source'/name)==digest,name
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    release=ROOT/'runtime/deployments'/('wild-auto-'+stamp)
    source=release/'source';source.mkdir(parents=True)
    for name in original['sha256']:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/'source'/name,target)
    # training_battle is shared with damage presentation. Derive the exact
    # six-line auto hunk over BASE instead of copying concurrent workspace edits.
    training=(BASE/'source/training_battle.py').read_text(encoding='utf-8')
    anchor="                actor=1 if is_role else self.pet.position\n"
    patch="""                if is_auto and target==0 and command=='attack':
                    # Native automatic sender 0x1195aa0 clears the cached target.
                    # Resolve only this sentinel against authoritative live foes.
                    side=next(f.side for f in self.battle.fighters if f.id==actor)
                    target=next((f.id for f in self.battle.fighters
                        if f.side!=side and f.hp>0 and f.id not in self.battle.escaped),0)
"""
    assert training.count(anchor)==1 and patch not in training
    (source/'training_battle.py').write_text(training.replace(anchor,anchor+patch,1),encoding='utf-8')
    captured={name:sha(ROOT/name) for name in OVERLAYS if name!='training_battle.py'}
    for name in captured:shutil.copy2(ROOT/name,source/name)
    assert all(sha(ROOT/name)==digest==sha(source/name) for name,digest in captured.items())
    runner=(BASE/'run_release.py').read_text(encoding='utf-8')
    (release/'run_release.py').write_text(runner,encoding='utf-8')
    keys=set(original['sha256'])|set(OVERLAYS)
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),base_release=str(BASE),
        scope='ordinary native automatic target0 attack; all other published behavior preserved',
        sha256={name:sha(source/name) for name in sorted(keys)},runner_sha256=sha(release/'run_release.py'),
        source_captured_coherently=True,training=False,automatic_resource_migration=False,overlays=list(OVERLAYS))
    (release/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    review=ROOT/'evidence/reviews'/release.name;review.mkdir()
    files=[];changes=[]
    for name in OVERLAYS:
        before=BASE/'source'/name;after=source/name
        old=before.read_text(encoding='utf-8-sig').splitlines(True) if before.exists() else []
        delta=list(difflib.unified_diff(old,after.read_text(encoding='utf-8-sig').splitlines(True),fromfile='published/'+name,tofile='candidate/'+name))
        assert delta,name
        changes.extend(delta);files.append(dict(path=name,before_sha256=sha(before) if before.exists() else None,after_sha256=sha(after)))
    (review/'scope.json').write_text(json.dumps(dict(base=str(BASE/'source'),current=str(source),git_available=False,
        commits=[],files=files,spec=str(ROOT/'evidence/WILD_AUTO_FIX.md')),ensure_ascii=False,indent=2),encoding='utf-8')
    (review/'changes.diff').write_text(''.join(changes),encoding='utf-8')
    (ROOT/'evidence/wild-auto-release-candidate.json').write_text(json.dumps(dict(release=str(release),review=str(review)),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(release=str(release),review=str(review),files=len(keys)),ensure_ascii=False))

if __name__=='__main__':main()
