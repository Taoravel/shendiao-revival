"""Exact private-story acceptance; no workspace gameplay imports or live I/O."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('script')
    parser.add_argument('--candidate-record', type=Path, default=ROOT/'staging/private-story-candidate.json')
    args = parser.parse_args()
    record = json.loads(args.candidate_record.read_text(encoding='utf-8'))
    release = Path(record['release'])
    source, harness = release/'source', release/'harness'
    manifest = json.loads((release/'manifest.json').read_text(encoding='utf-8'))
    bundle=dict(production=manifest['sha256'],runner=manifest['runner_sha256'],
        harness=record['harness_sha256'],resources=record['harness_resource_sha256'],
        workspace=record['workspace_sha256'],checks=record['checks_required'],
        arguments=record.get('check_arguments',{}))
    actual_set=hashlib.sha256(json.dumps(bundle,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if actual_set!=record['acceptance_input_sha256']:
        raise ValueError('Frozen acceptance manifest seal changed')
    if args.script not in record['checks_required']:
        raise ValueError('Only the explicit acceptance list is admitted')
    def verify():
        for name, expected in manifest['sha256'].items():
            if hashlib.sha256((source/name).read_bytes()).hexdigest() != expected:
                raise ValueError('Frozen production input changed: '+name)
        for name, expected in record['harness_sha256'].items():
            if hashlib.sha256((harness/name).read_bytes()).hexdigest() != expected:
                raise ValueError('Frozen test input changed: '+name)
        for name, expected in record.get('harness_resource_sha256', {}).items():
            if hashlib.sha256((harness/name).read_bytes()).hexdigest() != expected:
                raise ValueError('Frozen native verification resource changed: '+name)
        for name, expected in record['workspace_sha256'].items():
            if hashlib.sha256((harness/'workspace'/name).read_bytes()).hexdigest() != expected:
                raise ValueError('Actual configuration/reference input changed: '+name)
    verify()
    sys.path[:0] = [str(harness), str(source)]
    import inspect_client
    inspect_client.ROOT = ROOT.parent
    inspect_client.OUT = harness/'workspace'
    sys.argv = [str(harness/args.script)]+record.get('check_arguments',{}).get(args.script,[])
    passed, failure = False, None
    try:
        try:
            runpy.run_path(str(harness/args.script), run_name='__main__')
        except SystemExit as error:
            if error.code not in (None, 0):
                raise
        passed = True
    except BaseException as error:
        failure = type(error).__name__+': '+str(error)
        raise
    finally:
        verify()
        modules = {}
        for name, module in tuple(sys.modules.items()):
            file = getattr(module, '__file__', None)
            if not file or name == '__main__':
                continue
            path = Path(file).resolve()
            if ROOT not in path.parents:
                continue
            if path.parent not in (harness, source):
                allowed=record.get('verification_module_sources',{}).get(str(path))
                if allowed is None or hashlib.sha256(path.read_bytes()).hexdigest()!=allowed:
                    raise ValueError('Acceptance imported a project module outside its frozen source/harness: '+str(path))
            modules[name] = str(path)
        checks = release/'checks'
        checks.mkdir(exist_ok=True)
        report = dict(script=args.script, passed=passed, failure=failure,
            production_and_harness_module_origins=modules,
            production_inputs_preserved=len(manifest['sha256']),
            harness_inputs_preserved=len(record['harness_sha256']),
            acceptance_input_sha256=record.get('acceptance_input_sha256'),
            real_database_opened=False, live_server_changed=False,
            native_gui_verified=False)
        (checks/(args.script+'.result.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(dict(script=args.script, passed=passed, failure=failure,
            project_modules=len(modules), production_inputs=len(manifest['sha256']))))


if __name__ == '__main__':
    main()
