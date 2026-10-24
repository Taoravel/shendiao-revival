"""Run frozen battle acceptance against one immutable release, without sockets."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('script')
    parser.add_argument('--candidate-record', type=Path, required=True)
    parser.add_argument('--base-only', action='store_true')
    args = parser.parse_args()
    record = json.loads(args.candidate_record.read_text(encoding='utf-8'))
    release = Path(record['release'])
    production = Path(record['base_release']) if args.base_only else release
    source = production/'source'
    harness = release/'harness'
    if args.script not in record['harness_sha256']:
        raise ValueError('Harness must be explicitly frozen in candidate record')
    manifest = json.loads((production/'manifest.json').read_text(encoding='utf-8'))

    def verify():
        for name, expected in manifest['sha256'].items():
            if digest(source/name) != expected:
                raise ValueError('Immutable production input changed: '+name)
        for name, expected in record['harness_sha256'].items():
            if digest(harness/name) != expected:
                raise ValueError('Frozen acceptance input changed: '+name)

    verify()
    sys.path[:0] = [str(harness), str(source)]
    import inspect_client
    inspect_client.ROOT = ROOT.parent
    inspect_client.OUT = source
    sys.argv = [str(harness/args.script)]
    passed = False
    failure = None
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
        modules = {name: str(sys.modules[name].__file__) for name in (
            'battle', 'battle_protocol', 'training_battle', 'wild_battle',
            'battle_owner', 'game_runtime', 'runtime_storage', 'accounts')
            if name in sys.modules}
        for path in modules.values():
            if Path(path).parent != source:
                raise ValueError('Acceptance imported unfrozen gameplay: '+path)
        checks = release/'checks'
        checks.mkdir(exist_ok=True)
        suffix = '.base.result.json' if args.base_only else '.result.json'
        report = dict(script=args.script, passed=passed, failure=failure,
            production_modules=modules, source=str(source),
            candidate_hashes_preserved=len(manifest['sha256']),
            frozen_harnesses_preserved=len(record['harness_sha256']),
            live_server_changed=False, native_gui_verified=False)
        (checks/(args.script+suffix)).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
