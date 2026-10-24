"""Independent offline checks against the sealed private-story candidate."""
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
    parser.add_argument('script')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    record_path = root/'staging/private-story-candidate.json'
    record_bytes = record_path.read_bytes()
    record = json.loads(record_bytes)
    release = Path(record['release'])
    source, harness = release/'source', release/'harness'
    manifest_path = release/'manifest.json'
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    admitted = {
        'verify_scene_cleanup_recovery.py', 'verify_story_maintenance_recovery.py',
        'verify_story_cleanup_retry.py', 'verify_story_gc_isolation.py',
        'verify_scene_delivery_terminals.py', 'verify_prologue_touch_two_roles.py',
        'verify_private_transfer_disconnect.py', 'research_world_scene_delivery_abandonment.py',
    }
    if args.script not in admitted or args.script not in record['checks_required']:
        parser.error('Select an explicitly admitted offline check')
    bundle = dict(production=manifest['sha256'], runner=manifest['runner_sha256'],
        harness=record['harness_sha256'], resources=record['harness_resource_sha256'],
        workspace=record['workspace_sha256'], checks=record['checks_required'],
        arguments=record.get('check_arguments', {}))
    seal = hashlib.sha256(json.dumps(bundle, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert seal == record['acceptance_input_sha256'], 'Acceptance input seal changed'
    output = root/'evidence/root-private-story-release-20261024'/release.name/args.script
    output.mkdir(parents=True, exist_ok=True)

    def verify():
        assert record_path.read_bytes() == record_bytes, 'Candidate record changed during root check'
        assert manifest_path.read_bytes() == manifest_bytes, 'Manifest changed during root check'
        for name, expected in manifest['sha256'].items():
            assert digest(source/name) == expected, 'Production drift: '+name
        assert digest(release/'run_release.py') == manifest['runner_sha256']
        for name, expected in record['harness_sha256'].items():
            assert digest(harness/name) == expected, 'Harness drift: '+name
        for name, expected in record['harness_resource_sha256'].items():
            assert digest(harness/name) == expected, 'Native resource drift: '+name
        for name, expected in record['workspace_sha256'].items():
            assert digest(harness/'workspace'/name) == expected, 'Actual input drift: '+name

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
    if args.script == 'research_world_scene_delivery_abandonment.py':
        sys.argv += ['--report', str(output/'abandonment.json')]
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
                assert path.parent in (source, harness), 'Project import outside frozen inputs: '+str(path)
                modules[name] = str(path)
        report = dict(script=args.script, passed=passed, failure=failure,
            release=str(release), acceptance_input_sha256=seal,
            source_files_verified=len(manifest['sha256']),
            harness_files_verified=len(record['harness_sha256']),
            actual_workspace_inputs_verified=len(record['workspace_sha256']),
            module_origins=modules, production_unchanged=True,
            live_service_changed=False, live_database_accessed=False,
            native_gui_verified=False, commercial_capacity_verified=False)
        (output/'root-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({key:value for key,value in report.items() if key != 'module_origins'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
