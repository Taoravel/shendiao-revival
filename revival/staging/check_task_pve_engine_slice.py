"""Freeze/replay only the dedicated engine slice against the published BASE."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'runtime/deployments/npc-repair-20261024T023920Z'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    snapshot = args.snapshot.resolve()
    if args.prepare:
        snapshot.mkdir(parents=True, exist_ok=False)
        files = ('task_pve.py', 'battle_owner.py', 'verify_task_pve_engine.py',
                 'design/task-pve-ai8001-v1.json')
        hashes = {}
        for name in files:
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
            hashes[name] = sha(target)
        record = dict(base=str(BASE), base_manifest_sha256=sha(BASE / 'manifest.json'),
            base_candidate_sha256=sha(BASE / 'candidate.json'),
            inputs=hashes, runner_sha256=sha(Path(__file__)),
            methods=['diagnosing-bugs: missing dedicated Module red, real Owner/native HP and terminal green',
                     'tdd: first two-round public Owner slice red before implementation; later guards are regression checks',
                     'codebase-design: dedicated Battle engine/producer, pure arithmetic and codec reuse only'],
            root_policy_receipt='evidence/reviews/task-pve-ai8001-policy-root-20261024-r1/acceptance-root.json',
            mailbox_capacity=64, receipt_capacity=1024,
            production_activation=False, database_access=False, client_operated=False)
        (snapshot / 'manifest.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    record = json.loads((snapshot / 'manifest.json').read_text(encoding='utf-8'))
    base = Path(record['base'])
    manifest = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
    candidate = json.loads((base / 'candidate.json').read_text(encoding='utf-8'))
    def verify():
        if (sha(base / 'manifest.json') != record['base_manifest_sha256']
                or sha(base / 'candidate.json') != record['base_candidate_sha256']
                or sha(Path(__file__)) != record['runner_sha256']):
            raise ValueError('Exact baseline or replay runner changed')
        for name, expected in manifest['sha256'].items():
            if sha(base / 'source' / name) != expected:
                raise ValueError('Frozen production input changed: ' + name)
        for name, expected in record['inputs'].items():
            if sha(snapshot / name) != expected:
                raise ValueError('Engine slice input changed: ' + name)
        for name, expected in candidate['harness_sha256'].items():
            if sha(base / 'harness' / name) != expected:
                raise ValueError('Original native/test helper changed: ' + name)
        for name, expected in candidate['workspace_sha256'].items():
            if sha(base / 'harness/workspace' / name) != expected:
                raise ValueError('Original verification resource changed: ' + name)
    verify()
    sys.path[:0] = [str(snapshot), str(base / 'source'), str(base / 'harness')]
    import inspect_client
    inspect_client.ROOT = ROOT.parent
    inspect_client.OUT = base / 'source'
    spec = importlib.util.spec_from_file_location('task_pve_slice_checks', snapshot / 'verify_task_pve_engine.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = snapshot
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    verify()
    imports = {}
    for name, loaded in tuple(sys.modules.items()):
        file = getattr(loaded, '__file__', None)
        if not file:
            continue
        path = Path(file).resolve()
        if ROOT in path.parents and path not in (Path(__file__).resolve(),):
            if path.parent not in (snapshot, base / 'source', base / 'harness'):
                raise ValueError('Unfrozen project gameplay import: ' + str(path))
            imports[name] = dict(path=str(path), sha256=sha(path))
    report = dict(passed=result.wasSuccessful(), checks=result.testsRun,
        base_inputs_verified=len(manifest['sha256']), selected_inputs_stable=True,
        imports=imports, production_changed=False, listener_started=False,
        real_database_accessed=False, native_gui_verified=False,
        task_admission_settlement_and_shared_path_verified=False)
    (snapshot / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('passed', 'checks', 'base_inputs_verified')}))
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
