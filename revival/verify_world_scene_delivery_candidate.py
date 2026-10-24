"""Exact private-copy candidate for abandoned unqueued scene-reply suffixes.

Never writes shared runtime code, live state, deployments, or client memory.
"""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from inspect_client import OUT, write_json


def candidate(original):
    replacements = (
        ('''                        for message in await self.rt.scene_messages(owner,replies):
                            await self.offer_message(message,self.epoch)
''', '''                        await self._offer_batch(await self.rt.scene_messages(owner,replies))
'''),
        ('''            for reply in replies:
                if getattr(reply,'barrier',None) is not None:self.scene_generation+=1
                await self.offer_message(reply,self.epoch)
''', '''            await self._offer_batch(replies,advance_scene=True)
'''),
        ('''                            for message in await self.rt.scene_messages(role,replies):
                                await self.offer_message(message,self.epoch)
''', '''                            await self._offer_batch(await self.rt.scene_messages(role,replies))
'''),
        ('''    async def cleanup_delivery(self,delivery):
''', '''    async def _offer_batch(self,messages,*,advance_scene=False):
        # Each consumed item is owned by its queue or offer_message cleanup.
        # Only the unconsumed suffix remains the batch caller's responsibility.
        remaining=iter(messages)
        try:
            for message in remaining:
                if advance_scene and getattr(message,'barrier',None) is not None:
                    self.scene_generation+=1
                await self.offer_message(message,self.epoch)
        finally:
            cleanup=tuple(self.cleanup_delivery(getattr(message,'delivery',None))
                for message in remaining)
            if cleanup:
                await asyncio.shield(asyncio.gather(*cleanup,return_exceptions=True))

    async def cleanup_delivery(self,delivery):
'''),
    )
    text = original.decode('utf-8')
    for old, new in replacements:
        assert text.count(old) == 1, 'Candidate requires each exact audited batch caller'
        text = text.replace(old, new)
    return text.encode('utf-8')


def import_closure(base, seeds):
    pending, found = list(seeds), {}
    while pending:
        name = pending.pop()
        path = base/(name+'.py')
        if name+'.py' in found or not path.is_file():
            continue
        raw = path.read_bytes()
        found[name+'.py'] = hashlib.sha256(raw).hexdigest()
        for node in ast.walk(ast.parse(raw, filename=str(path))):
            if isinstance(node, ast.Import):
                pending.extend(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                pending.append(node.module.split('.')[0])
    return found


BOOTSTRAP = '''
import runpy,sys
from pathlib import Path
sys.path.insert(0,sys.argv[2])
import inspect_client
sys.path.insert(0,sys.argv[1])
script=Path(sys.argv[1])/"research_world_scene_delivery_abandonment.py"
sys.argv=[str(script),"--runtime-source",sys.argv[1],"--report",sys.argv[3]]
runpy.run_path(str(script),run_name="__main__")
'''

REGRESSION = '''
import asyncio,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,sys.argv[2])
import inspect_client
sys.path.insert(0,sys.argv[1])
from accounts import AccountStore
import runtime_storage
from verify_world_scene_delivery_terminal import check
rows=[]
with tempfile.TemporaryDirectory(prefix="candidate-scene-terminal-") as directory:
    store=AccountStore(Path(directory)/"state.sqlite3")
    asyncio.run(asyncio.wait_for(check(store,runtime_storage.prepare(store),rows),60))
print(json.dumps({"all_passed":True,"passed":rows}))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-source', type=Path, default=OUT)
    parser.add_argument('--label', default='current')
    parser.add_argument('--skip-regression', action='store_true')
    args = parser.parse_args()
    assert args.label and args.label.replace('-', '').isalnum()
    base = args.base_source.resolve(strict=True)
    original = (base/'game_runtime.py').read_bytes()
    changed = candidate(original)
    prefix = f'world-scene-delivery-{args.label}'
    closure = import_closure(base, ('game_runtime', 'runtime_story_maps',
        'research_world_scene_delivery_abandonment', 'verify_world_scene_delivery_terminal'))
    files = sorted(base.glob('*.py'))
    for folder in ('design', 'catalogs', 'evidence'):
        files.extend(sorted((base/folder).glob('*.json')))
    if not args.skip_regression:
        # The original MPPC decoder resolves this relative to its own module,
        # independently of inspect_client's deliberately cached resource root.
        files.append(base/'evidence/native-image.bin')
    snapshot = {}
    with tempfile.TemporaryDirectory(prefix='world-scene-suffix-candidate-') as directory:
        source = Path(directory)/'source'
        source.mkdir()
        for file in files:
            relative = str(file.relative_to(base))
            raw = file.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if relative in closure:
                assert digest == closure[relative], f'Source changed while copying {relative}'
            destination = source/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            snapshot[relative] = digest
        for name, digest in closure.items():
            assert hashlib.sha256((base/name).read_bytes()).hexdigest() == digest
        assert (source/'game_runtime.py').read_bytes() == original
        baseline_path = OUT/f'evidence/{prefix}-baseline.json'
        baseline = subprocess.run([sys.executable, '-B', '-c', BOOTSTRAP, str(source),
            str(OUT), str(baseline_path)], capture_output=True, text=True,
            encoding='utf-8', timeout=30)
        baseline_result = json.loads(baseline_path.read_text(encoding='utf-8'))
        assert baseline.returncode == 1 and not baseline_result['safe_terminal'], \
            baseline.stderr or baseline.stdout
        assert baseline_result['sources']['game_runtime']['sha256'] == hashlib.sha256(original).hexdigest()
        assert baseline_result['sources_stable']
        (source/'game_runtime.py').write_bytes(changed)
        green_path = OUT/f'evidence/{prefix}-candidate.json'
        green = subprocess.run([sys.executable, '-B', '-c', BOOTSTRAP, str(source),
            str(OUT), str(green_path)], capture_output=True, text=True,
            encoding='utf-8', timeout=30)
        assert green.returncode == 0, green.stderr or green.stdout
        green_result = json.loads(green_path.read_text(encoding='utf-8'))
        assert green_result['safe_terminal'] and green_result['sources_stable']
        assert green_result['sources']['game_runtime']['sha256'] == hashlib.sha256(changed).hexdigest()
        regression = None
        if not args.skip_regression:
            run = subprocess.run([sys.executable, '-B', '-c', REGRESSION, str(source), str(OUT)],
                capture_output=True, text=True, encoding='utf-8', timeout=90)
            assert run.returncode == 0, run.stderr or run.stdout
            regression = json.loads(run.stdout)
    patch = ''.join(difflib.unified_diff(original.decode('utf-8').splitlines(True),
        changed.decode('utf-8').splitlines(True), fromfile='a/revival/game_runtime.py',
        tofile='b/revival/game_runtime.py'))
    patch_path = OUT/f'evidence/{prefix}-candidate.patch'
    patch_path.write_text(patch, encoding='utf-8', newline='')
    captured = OUT/f'evidence/candidates/{prefix}'
    for name, raw in (('base/game_runtime.py', original), ('final/game_runtime.py', changed)):
        path = captured/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    report = dict(base_source=str(base), base_sha256=hashlib.sha256(original).hexdigest(),
        candidate_sha256=hashlib.sha256(changed).hexdigest(),
        baseline=baseline_result, candidate=green_result, regression=regression,
        patch=str(patch_path), source_snapshot_sha256=snapshot,
        captured_sources=str(captured),
        wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        static_import_closure=closure,
        resource_adapter='inspect_client ROOT/OUT cached from actual workspace before importing private code',
        shared_source_matches_base=(base/'game_runtime.py').read_bytes() == original,
        candidate_only=True, shared_runtime_modified=False, live_server_changed=False,
        native_gui_verified=False, battle_executed=False)
    write_json(OUT/f'evidence/{prefix}-candidate-verification.json', report)
    print(dict(candidate_only=True, baseline_safe=False, candidate_safe=True,
        regression_groups=len(regression['passed']) if regression else None,
        base_sha256=report['base_sha256'], candidate_sha256=report['candidate_sha256']))


if __name__ == '__main__':
    main()
