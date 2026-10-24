"""Independent temporary-domain/Peer checks of the exact loyalty release."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('script', choices=('verify_npc_loyalty_quote.py', 'verify_npc_loyalty_quote_runtime.py'))
    parser.add_argument('--candidate-record', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    record_path = args.candidate_record or root/'staging/npc-loyalty-candidate.json'
    record_bytes = record_path.read_bytes()
    record = json.loads(record_bytes)
    release = Path(record['release'])
    source, harness = release/'source', release/'harness'
    manifest_path = release/'manifest.json'
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    assert args.script in record['checks_required']
    output = root/'evidence/root-npc-loyalty-release-20261024'/release.name/args.script
    output.mkdir(parents=True, exist_ok=True)
    bundle = dict(production=manifest['sha256'], runner=manifest['runner_sha256'],
        harness=record['harness_sha256'], resources=record['harness_resource_sha256'],
        workspace=record['workspace_sha256'], checks=record['checks_required'],
        arguments=record.get('check_arguments', {}))
    seal = hashlib.sha256(json.dumps(bundle, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert seal == record['acceptance_input_sha256']
    historical = {Path(name).resolve():sha for name,sha in record.get('verification_module_sources', {}).items()}

    def verify():
        assert record_path.read_bytes() == record_bytes, 'Candidate metadata changed during root check'
        assert manifest_path.read_bytes() == manifest_bytes, 'Manifest changed during root check'
        for name, expected in manifest['sha256'].items():
            assert digest(source/name) == expected, 'Production drift: '+name
        assert digest(release/'run_release.py') == manifest['runner_sha256']
        for name, expected in record['harness_sha256'].items():
            assert digest(harness/name) == expected, 'Harness drift: '+name
        for name, expected in record['harness_resource_sha256'].items():
            assert digest(harness/name) == expected, 'Native input drift: '+name
        for name, expected in record['workspace_sha256'].items():
            assert digest(harness/'workspace'/name) == expected, 'Actual input drift: '+name
        for path, expected in historical.items():
            assert path.is_relative_to(harness/'workspace'), 'Historical reference outside frozen harness'
            assert digest(path) == expected, 'Historical baseline source drift'

    verify()
    sys.path[:0] = [str(harness), str(source)]
    import inspect_client
    inspect_client.ROOT = root.parent
    inspect_client.OUT = harness/'workspace'

    def write_report(path, value):
        relative = Path(path).resolve().relative_to((harness/'workspace/evidence').resolve())
        target = output/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

    inspect_client.write_json = write_report
    sys.argv = [str(harness/args.script)]
    passed, failure, modules = False, None, {}
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
        for name, module in tuple(sys.modules.items()):
            filename = getattr(module, '__file__', None)
            if not filename or name == '__main__':
                continue
            path = Path(filename).resolve()
            if path.is_relative_to(root):
                assert path.parent in (source, harness) or path in historical, 'Project import escaped frozen inputs: '+str(path)
                modules[name] = str(path)
        report = dict(script=args.script, passed=passed, failure=failure,
            release=str(release), acceptance_input_sha256=seal,
            source_files_verified=len(manifest['sha256']),
            harness_files_verified=len(record['harness_sha256']),
            actual_workspace_inputs_verified=len(record['workspace_sha256']),
            historical_sources_verified=len(historical), module_origins=modules,
            production_unchanged=True, live_service_changed=False,
            live_database_accessed=False, native_gui_verified=False)
        (output/'root-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({key:value for key,value in report.items() if key != 'module_origins'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
