"""Replay the exact formal task engine slice, outside its immutable snapshot."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(directory):
    return {str(p.relative_to(directory)):sha(p) for p in directory.rglob('*') if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--expected-checks', type=int, default=9)
    args = parser.parse_args()
    snapshot = args.snapshot.resolve(strict=True)
    report = args.report.resolve()
    record = json.loads((snapshot/'manifest.json').read_text(encoding='utf-8'))
    base = Path(record['base']).resolve(strict=True)
    root = Path(__file__).resolve().parents[2]
    if report.is_relative_to(snapshot) or report.is_relative_to(base):
        raise ValueError('Independent output outside frozen inputs required')
    manifest = json.loads((base/'manifest.json').read_text(encoding='utf-8'))
    candidate = json.loads((base/'candidate.json').read_text(encoding='utf-8'))
    sets = ((snapshot,record['inputs']), (base/'source',manifest['sha256']),
            (base/'harness',candidate['harness_sha256']),
            (base/'harness/workspace',candidate['workspace_sha256']))
    def verify():
        if sha(base/'manifest.json') != record['base_manifest_sha256'] or sha(base/'candidate.json') != record['base_candidate_sha256']:
            raise ValueError('Exact BASE record changed')
        for directory, expected in sets:
            for name, wanted in expected.items():
                if sha(directory/name) != wanted:
                    raise ValueError('Frozen input changed: '+str(directory/name))
    verify()
    before = files(snapshot)
    sys.path = [str(snapshot), str(base/'source'), str(base/'harness')] + [s for s in sys.path
        if s and not Path(s).resolve().is_relative_to(root)]
    import inspect_client
    inspect_client.ROOT, inspect_client.OUT = root, base/'source'
    spec = importlib.util.spec_from_file_location('root_task_pve_checks',snapshot/'verify_task_pve_engine.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.ROOT = snapshot
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    verify()
    after = files(snapshot)
    origins = {}
    for name, loaded in tuple(sys.modules.items()):
        filename = getattr(loaded,'__file__',None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(root):
            own = name == '__main__' and path == Path(__file__).resolve()
            if not own and not any(path.is_relative_to(d) for d in (snapshot,base/'source',base/'harness')):
                raise ValueError('Unfrozen application import: '+str(path))
            origins[name] = dict(path=str(path),sha256=sha(path))
    passed = result.wasSuccessful() and result.testsRun == args.expected_checks and before == after
    output = dict(passed=passed,checks=result.testsRun,expected_checks=args.expected_checks,
        tests_output=log.getvalue(),snapshot=str(snapshot),snapshot_sha256=before,
        all_snapshot_files_unchanged=before==after,
        base_input_counts=[len(expected) for _,expected in sets[1:]],
        base_manifest_sha256=sha(base/'manifest.json'),all_selected_inputs_verified=True,
        actual_import_origins=origins,root_harness_sha256=sha(Path(__file__)),
        live_socket=False,live_database=False,service_changed=False,native_gui_verified=False,
        task_admission_settlement_shared_or_publication_approved=False)
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('tests_output','snapshot_sha256','actual_import_origins')},ensure_ascii=False))
    if not passed:
        print(log.getvalue())
        raise SystemExit(1)


if __name__ == '__main__':
    main()
