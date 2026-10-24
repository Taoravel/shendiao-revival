"""Offline real MapOwner collision probe against one immutable release."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('release', type=Path)
    parser.add_argument('--expect-gap', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    release = args.release.resolve()
    source = release/'source'
    manifest = json.loads((release/'manifest.json').read_text(encoding='utf-8'))
    output = root/'evidence/root-world-collision-20261024'/release.name
    output.mkdir(parents=True, exist_ok=True)
    helper = output/'verify_world_runtime_collision_probe.py'
    original = root/'verify_world_runtime_collision_probe.py'
    if helper.exists():
        assert helper.read_bytes() == original.read_bytes(), 'Use a new root observation directory for a changed probe'
    else:
        helper.write_bytes(original.read_bytes())
    helper_sha = hashlib.sha256(helper.read_bytes()).hexdigest()

    def verify():
        for name, expected in manifest['sha256'].items():
            assert hashlib.sha256((source/name).read_bytes()).hexdigest() == expected, name
        assert hashlib.sha256((release/'run_release.py').read_bytes()).hexdigest() == manifest['runner_sha256']
        assert hashlib.sha256(helper.read_bytes()).hexdigest() == helper_sha

    verify()
    sys.path.insert(0, str(source))
    import inspect_client
    inspect_client.ROOT = root.parent
    inspect_client.OUT = source
    suffix = 'gap' if args.expect_gap else 'safety'
    report = output/(suffix+'.json')
    sys.argv = [str(helper), '--report', str(report)]
    if args.expect_gap:
        sys.argv.append('--expect-gap')
    passed, failure, modules = False, None, {}
    try:
        runpy.run_path(str(helper), run_name='__main__')
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
                assert path.parent == source, 'Project import escaped release: '+str(path)
                modules[name] = str(path)
        evidence = dict(release=str(release), expect_gap=args.expect_gap,
            invocation_passed=passed, failure=failure,
            manifest_files_verified=len(manifest['sha256']), runner_verified=True,
            helper_sha256=helper_sha, module_origins=modules,
            live_database_accessed=False, live_service_changed=False,
            actual_login_executed=False, battle_executed=False,
            native_gui_verified=False)
        (output/(suffix+'-root-verification.json')).write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({key:value for key,value in evidence.items() if key != 'module_origins'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
