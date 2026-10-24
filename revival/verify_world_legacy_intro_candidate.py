"""Verify a one-line integration candidate only in a private disposable copy.

The shared source and immutable deployed release are read, never rewritten.
The integration owner still owns policy publication, shared editing/deployment.
"""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from inspect_client import OUT,write_json


def source_dependencies(base):
    """Freeze the tested runtime/helper import closure, not unrelated editors."""
    pending=['game_runtime','runtime_storage','accounts','verify_growth_runtime',
        'verify_runtime','verify_newbie_runtime','native_gameplay_probe','native_inspect','verify_mppc_native']
    result={}
    while pending:
        name=pending.pop();path=base/(name+'.py')
        if name+'.py' in result or not path.is_file():continue
        raw=path.read_bytes();result[name+'.py']=hashlib.sha256(raw).hexdigest()
        for node in ast.walk(ast.parse(raw,filename=str(path))):
            if isinstance(node,ast.Import):pending.extend(a.name.split('.')[0] for a in node.names)
            elif isinstance(node,ast.ImportFrom) and not node.level and node.module:
                pending.append(node.module.split('.')[0])
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base-source',type=Path,
        default=OUT/'runtime/deployments/20261023T063445Z/source')
    parser.add_argument('--label',default='',help='Separate current-source and immutable-release evidence')
    motion=parser.add_mutually_exclusive_group()
    motion.add_argument('--with-native-arrival',action='store_true',help='Also verify captured native END/MOVE/STOP and reconnect')
    motion.add_argument('--with-native-check-arrival',action='store_true',help='Also verify same-object native timed CHECK/STOP through encrypted owners')
    args=parser.parse_args()
    assert not args.label or args.label.replace('-','').isalnum()
    base=args.base_source.resolve(strict=True)
    label=(args.label+'-') if args.label else ''
    legacy_suffix=label+'candidate'
    critical=source_dependencies(base)
    files=sorted(base.glob('*.py'))
    for name in ('design','catalogs','evidence'):
        files.extend(sorted((base/name).glob('*.json')))
    if (base/'evidence/native-image.bin').is_file():files.append(base/'evidence/native-image.bin')
    snapshot=dict(critical)
    snapshot.update((str(file.relative_to(base)),hashlib.sha256(file.read_bytes()).hexdigest())
        for file in files if file.parent.name in ('design','catalogs'))
    old='intro=0 if self.newbie_chapter is None else self.newbie_chapter.intro_discriminator'
    new='intro=1 if self.newbie_chapter is None else self.newbie_chapter.intro_discriminator'
    original=(base/'game_runtime.py').read_bytes()
    assert original.count(old.encode())==1, 'Candidate requires the exact audited source branch'
    changed=original.replace(old.encode(),new.encode())
    with tempfile.TemporaryDirectory(prefix='world-legacy-entry-candidate-') as folder:
        source=Path(folder)/'source';source.mkdir()
        # Only code/static policy, no live database/deployment files are copied.
        for file in files:
            relative=file.relative_to(base);target=source/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            if str(relative) not in snapshot:
                data=file.read_bytes();target.write_bytes(data)
                snapshot[str(relative)]=hashlib.sha256(data).hexdigest()
            else:
                shutil.copyfile(file,target)
                assert hashlib.sha256(target.read_bytes()).hexdigest()==snapshot[str(relative)], f'Source changed during private snapshot: {relative}'
        # Check executable source/policies/catalogs again before testing the
        # private copy. Unrelated evidence writers need not freeze the project.
        for file in files:
            if str(file.relative_to(base)) in critical or file.parent.name in ('design','catalogs'):
                assert hashlib.sha256(file.read_bytes()).hexdigest()==snapshot[str(file.relative_to(base))], f'Source changed during snapshot: {file.relative_to(base)}'
        baseline=subprocess.run([sys.executable,'-B',str(OUT/'verify_world_legacy_intro_entry.py'),
            '--release-source',str(source),'--expect-blocked','--report-suffix',label+'baseline'],
            capture_output=True,text=True,timeout=60)
        assert baseline.returncode==0,baseline.stderr or baseline.stdout
        baseline_result=json.loads((OUT/f'evidence/world-legacy-intro-entry-{label}baseline.json').read_text(encoding='utf-8'))
        assert baseline_result['unsafe_entry_reproduced'] and not baseline_result['safe_entry']
        assert baseline_result['runtime_source_sha256']==hashlib.sha256(original).hexdigest()
        (source/'game_runtime.py').write_bytes(changed)
        command=[sys.executable,'-B',str(OUT/'verify_world_legacy_intro_entry.py'),
            '--release-source',str(source),'--report-suffix',legacy_suffix]
        legacy=subprocess.run(command,capture_output=True,text=True,timeout=60)
        assert legacy.returncode==0, legacy.stderr or legacy.stdout
        # The two fresh chapters are exercised through the existing public
        # owner check; don't overwrite its shared-runtime evidence report.
        wrapper='''
import asyncio,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,sys.argv[2])
import inspect_client
sys.path.insert(0,sys.argv[1])
from accounts import AccountStore
import runtime_storage
from verify_newbie_runtime import check
from world_newbie import load_newbie_routes
with tempfile.TemporaryDirectory(prefix='candidate-fresh-chapters-') as folder:
    store=AccountStore(Path(folder)/'state.sqlite3')
    legacy=store.create_role(1111,'旧章检查',11,1010109)
    prepared=runtime_storage.prepare(store)
    fresh=(store.create_role(1111,'古墓新角',11,1010109),store.create_role(1111,'少林新角',111,1010109))
    result=asyncio.run(asyncio.wait_for(check(store,prepared,legacy,fresh,load_newbie_routes()),timeout=60))
print(json.dumps(result))
'''
        fresh=subprocess.run([sys.executable,'-B','-c',wrapper,str(source),str(OUT)],
            capture_output=True,text=True,encoding='utf-8',timeout=90)
        assert fresh.returncode==0,fresh.stderr or fresh.stdout
        result=json.loads(fresh.stdout)
        legacy_result=json.loads((OUT/f'evidence/world-legacy-intro-entry-{legacy_suffix}.json').read_text(encoding='utf-8'))
        assert legacy_result['safe_entry'] and not legacy_result['start_movie_frames']
        assert legacy_result['runtime_source_sha256']==hashlib.sha256(changed).hexdigest()
        arrival_result=None
        if args.with_native_arrival or args.with_native_check_arrival:
            report_label=args.label+'-candidate' if args.label else 'release-candidate'
            motion_name='check-arrival' if args.with_native_check_arrival else 'arrival'
            arrival=subprocess.run([sys.executable,'-B',str(OUT/'verify_world_click_move_owner.py'),
                '--'+motion_name,'--native-opening-report',str(OUT/'evidence/world-intro-dispatch-native.json'),
                '--runtime-source',str(source),'--report-label',report_label],
                capture_output=True,text=True,timeout=70)
            assert arrival.returncode==0,arrival.stderr or arrival.stdout
            arrival_result=json.loads((OUT/f'evidence/world-click-{motion_name}-{report_label}-owner-verification.json').read_text(encoding='utf-8'))
            assert arrival_result['reconnect_preserved_arrival'] and arrival_result['source_sha256']==hashlib.sha256(changed).hexdigest()
            if args.with_native_check_arrival:assert arrival_result['natural_timed_checks_accepted']
    report=dict(base_source=str(base/'game_runtime.py'),
        base_sha256=hashlib.sha256(original).hexdigest(),candidate_sha256=hashlib.sha256(changed).hexdigest(),
        exact_old=old,exact_new=new,legacy_baseline=baseline_result,legacy_candidate=legacy_result,fresh_chapter_regression=result,
        source_scope='private disposable Python/static-JSON/native-image snapshot of the explicitly selected base; shared code not changed',
        source_snapshot_sha256=snapshot,
        critical_source_modules=sorted(critical),
        snapshot_fence='Tested runtime static-import closure/design/catalogs stable across copying; unrelated scripts/evidence captured per file',
        candidate_only=True,policy_published=False,shared_runtime_modified=False,
        deployed_release_modified=False,live_server_changed=False,gui_verified=False)
    if arrival_result is not None:
        report['native_check_arrival_owner' if args.with_native_check_arrival else 'native_arrival_owner']=arrival_result
    patch=''.join(difflib.unified_diff(original.decode('utf-8').splitlines(keepends=True),
        changed.decode('utf-8').splitlines(keepends=True),
        fromfile='a/revival/game_runtime.py',tofile='b/revival/game_runtime.py'))
    (OUT/f'evidence/world-legacy-intro-{label}candidate.patch').write_text(patch,encoding='utf-8',newline='')
    write_json(OUT/f'evidence/world-legacy-intro-{label}candidate-verification.json',report)
    print({key:report[key] for key in ('candidate_only','shared_runtime_modified','live_server_changed','gui_verified')})
    print({'legacy_safe':legacy_result['safe_entry'],'fresh_regression_groups':len(result['passed'])})


if __name__=='__main__':main()
