"""Offline original intro gate against the actual frozen service baseline."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    release = root/'runtime/deployments/wild-auto-20261023T181143Z'
    source = release/'source'
    manifest = json.loads((release/'manifest.json').read_text(encoding='utf-8-sig'))
    output = root/'evidence/root-legacy-intro-gate-20261024'/('candidate' if args.candidate else 'base')
    overlay = output/'source'
    harness = output/'harness'
    overlay.mkdir(parents=True, exist_ok=True)
    harness.mkdir(exist_ok=True)
    old = b'intro=0 if self.newbie_chapter is None else self.newbie_chapter.intro_discriminator'
    new = b'intro=1 if self.newbie_chapter is None else self.newbie_chapter.intro_discriminator'

    def verify():
        for name, expected in manifest['sha256'].items():
            assert hashlib.sha256((source/name).read_bytes()).hexdigest() == expected, name
        assert hashlib.sha256((release/'run_release.py').read_bytes()).hexdigest() == manifest['runner_sha256']

    verify()
    original = (source/'game_runtime.py').read_bytes()
    assert original.count(old) == 1
    actual = original.replace(old, new) if args.candidate else original
    (overlay/'game_runtime.py').write_bytes(actual)
    helper = (root/'verify_world_legacy_intro_entry.py').read_bytes()
    (harness/'verify_world_legacy_intro_entry.py').write_bytes(helper)
    sys.path[:0] = [str(harness), str(overlay), str(source)]
    import inspect_client
    inspect_client.ROOT = root.parent
    inspect_client.OUT = source

    def write(path, value):
        (output/Path(path).name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

    inspect_client.write_json = write
    probe = importlib.import_module('verify_world_legacy_intro_entry')
    sys.argv = ['verify_world_legacy_intro_entry.py'] + ([] if args.candidate else ['--expect-blocked'])
    probe.main()
    verify()
    assert (overlay/'game_runtime.py').read_bytes() == actual
    assert hashlib.sha256((root/'verify_world_legacy_intro_entry.py').read_bytes()).digest() == hashlib.sha256(helper).digest()
    origins = {}
    for name, module in list(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if not filename or name == '__main__':
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(root):
            assert any(path.is_relative_to(folder) for folder in (source, overlay, harness)), str(path)
            origins[name] = str(path)
    write('root-inputs.json', dict(candidate=args.candidate, base=str(source),
        base_files_verified=len(manifest['sha256']), production_modules=origins,
        game_runtime_sha256=hashlib.sha256(actual).hexdigest(),
        helper_sha256=hashlib.sha256(helper).hexdigest(),
        live_service_changed=False, live_database_accessed=False, gui_verified=False))
    print('root independent exact frozen baseline/one-line candidate native intro gate verified')


if __name__ == '__main__':
    main()
