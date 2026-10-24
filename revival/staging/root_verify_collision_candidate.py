"""Independent sealed runtime acceptance; disposable peers and databases only.

The historical filename remains stable for prior collision evidence commands.
"""
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
    parser.add_argument('--release', default='world-collision-20261023T200906Z')
    parser.add_argument('--maps', help='Explicit diagnostic map subset, never a full-map acceptance claim')
    parser.add_argument('--supplemental', type=Path,
        help='Freeze a newly supplied admitted probe without changing the historical candidate')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    release = root/'runtime/deployments'/args.release
    record_path, manifest_path = release/'candidate.json', release/'manifest.json'
    record_bytes, manifest_bytes = record_path.read_bytes(), manifest_path.read_bytes()
    record, manifest = json.loads(record_bytes), json.loads(manifest_bytes)
    admitted = {'verify_runtime_movement_lifecycle.py', 'verify_world_encrypted_collision.py',
        'verify_runtime_movement_terminals.py', 'verify_world_movement_delivery_boundaries.py',
        'verify_runtime_movement_intro_race.py',
        'verify_world_late_finalize_membership.py',
        'verify_runtime_transfer_replays.py',
        'verify_npc_repair_resource_runtime.py', 'verify_resource_npc_care_runtime.py',
        'verify_npc_repair_resources.py', 'verify_npc_repair_transactions.py',
        'verify_npc_equipped_repair_runtime.py', 'verify_npc_loyalty_quote_runtime.py',
        'verify_npc_pet_recovery_runtime.py',
        'verify_world_resource_runtime.py',
        'verify_scene_delivery_terminals.py', 'verify_prologue_touch_two_roles.py',
        'verify_private_transfer_disconnect.py', 'verify_story_gc_isolation.py',
        'verify_story_maintenance_recovery.py', 'verify_social_scene_scope.py'}
    if args.script not in admitted or (args.script not in record['checks_required'] and not args.supplemental):
        parser.error('Select an admitted disposable integration check')
    if args.supplemental and (args.script not in ('verify_runtime_movement_intro_race.py',
            'verify_world_late_finalize_membership.py', 'verify_npc_repair_resource_runtime.py')
            or args.supplemental.resolve() != root/args.script):
        parser.error('Only the explicit new lifecycle/repair probes may supplement a historical candidate')
    if args.maps and args.script != 'verify_world_resource_runtime.py':
        parser.error('Map subsets are only meaningful for the resource runtime check')
    source, harness = release/'source', release/'harness'
    workspace = harness/'workspace'
    group = ('root-npc-repair-release-20261024' if release.name.startswith('npc-repair-')
        or args.script == 'verify_npc_repair_resource_runtime.py' else 'root-world-collision-20261024')
    output = root/'evidence'/group/release.name/args.script
    output.mkdir(parents=True, exist_ok=True)
    probe = harness/args.script
    probe_sha256 = None
    if args.supplemental:
        probe = output/args.script
        raw = args.supplemental.read_bytes()
        if probe.exists():
            assert probe.read_bytes() == raw, 'Supplemental probe is already frozen at different bytes'
        else:
            probe.write_bytes(raw)
        probe_sha256 = digest(probe)
    bundle = dict(production=manifest['sha256'], runner=manifest['runner_sha256'],
        harness=record['harness_sha256'], resources=record['harness_resource_sha256'],
        workspace=record['workspace_sha256'], checks=record['checks_required'],
        arguments=record.get('check_arguments', {}))
    seal = hashlib.sha256(json.dumps(bundle, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert seal == record['acceptance_input_sha256']

    def verify():
        assert record_path.read_bytes() == record_bytes
        assert manifest_path.read_bytes() == manifest_bytes
        if probe_sha256 is not None:
            assert digest(probe) == probe_sha256
        for directory, hashes in ((source, manifest['sha256']),
                (harness, record['harness_sha256']),
                (harness, record['harness_resource_sha256']),
                (workspace, record['workspace_sha256'])):
            for name, expected in hashes.items():
                assert digest(directory/name) == expected, 'Input drift: '+str(directory/name)
        assert digest(release/'run_release.py') == manifest['runner_sha256']

    verify()
    sys.path[:0] = [str(harness), str(source)]
    import inspect_client
    inspect_client.ROOT, inspect_client.OUT = root.parent, workspace

    def write_report(path, value):
        path = Path(path).resolve()
        for directory in (workspace/'evidence', harness/'evidence'):
            if path.is_relative_to(directory):
                target = output/path.relative_to(directory)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
                return
        raise ValueError('Unexpected report target: '+str(path))

    inspect_client.write_json = write_report
    sys.argv = [str(probe)]
    if args.script == 'verify_world_late_finalize_membership.py':
        sys.argv += ['--report', str(output/'late-finalize.json')]
    if args.script == 'verify_world_resource_runtime.py':
        sys.argv += record.get('check_arguments', {}).get(args.script, [])
        if args.maps:
            sys.argv += ['--maps', args.maps]
    passed, failure, origins = False, None, {}
    try:
        try:
            runpy.run_path(str(probe), run_name='__main__')
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
                assert path.parent in (source, harness), 'Unsealed project import: '+str(path)
                if path.parent == harness:
                    assert (path.stem.startswith(('verify_', 'research_'))
                        or path.name == 'diagnose_npc_loyalty_quote.py'), \
                        'Production module shadowed by verification harness: '+str(path)
                    assert digest(path) == record['harness_sha256'][path.name]
                else:
                    assert digest(path) == manifest['sha256'][path.name]
                origins[name] = str(path)
        report = dict(passed=passed, failure=failure, script=args.script, release=str(release),
            acceptance_input_sha256=seal, module_origins=origins,
            diagnostic_map_subset=args.maps,
            supplemental_probe=bool(args.supplemental), supplemental_probe_sha256=probe_sha256,
            source_files_verified=len(manifest['sha256']),
            harness_files_verified=len(record['harness_sha256']),
            workspace_inputs_verified=len(record['workspace_sha256']),
            inputs_unchanged=True, live_service_changed=False, live_database_accessed=False,
            native_gui_verified=False, commercial_capacity_verified=False)
        (output/'root-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k:v for k,v in report.items() if k != 'module_origins'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
