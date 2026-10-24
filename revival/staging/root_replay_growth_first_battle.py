"""Independent exact-release natural story gap replay, with frozen harness."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--release', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    release = args.release.resolve(strict=True)
    output = args.output.resolve()
    if output.is_relative_to(release):
        raise ValueError('Independent output outside immutable release required')
    manifest = json.loads((release/'manifest.json').read_text(encoding='utf-8'))
    record = json.loads((release/'candidate.json').read_text(encoding='utf-8'))
    sets = ((release/'source', manifest['sha256']),
            (release/'harness', record['harness_sha256']),
            (release/'harness/workspace', record['workspace_sha256']))
    def verify():
        for directory, files in sets:
            for name, expected in files.items():
                if sha(directory/name) != expected:
                    raise ValueError('Frozen input mismatch: '+str(directory/name))
    verify()
    resources = (root/'artres/config.pfs', root/'revival/evidence/native-image.bin')
    before_resources = {str(x): sha(x) for x in resources}
    original = root/'revival/diagnose_growth_first_battle_runtime.py'
    raw = original.read_bytes()
    output.mkdir(parents=True, exist_ok=True)
    frozen = output/'diagnose_growth_first_battle_runtime.py'
    if frozen.exists() and frozen.read_bytes() != raw:
        raise ValueError('Preserve existing independent probe')
    frozen.write_bytes(raw)
    source, harness = release/'source', release/'harness'
    sys.path = [str(harness), str(source)] + [s for s in sys.path if s
        and not Path(s).resolve().is_relative_to(root)]
    child = output/'natural-gap.json'
    sys.argv = [str(original), '--source', str(source), '--report', str(child)]
    failure = None
    try:
        # Execute the frozen bytes. Its original filename only preserves its
        # documented workspace ROOT calculation; no hot source is executed.
        exec(compile(raw, str(original), 'exec'),
             {'__name__': '__main__', '__file__': str(original)})
    except AssertionError as exc:
        failure = str(exc)
    finally:
        verify()
    after_resources = {str(x): sha(x) for x in resources}
    result = json.loads(child.read_text(encoding='utf-8'))
    exact_red = failure == 'Level2 dream storyteller does not start original task battle'
    exact_red = exact_red and (result['level'], result['task_id'], result['task_still_active'],
        result['task_completed'], result['original_task_offered'], result['battle_started'],
        result['battle_admissions_table_prepared']) == (2, 100107, True, False, False, False, False)
    origins = {}
    for name, module in tuple(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if not path:
            continue
        path = Path(path).resolve()
        if path.is_relative_to(root):
            own = name == '__main__' and path == Path(__file__).resolve()
            if not own and not any(path.is_relative_to(d) for d in (source, harness)):
                raise ValueError('Unapproved application import: '+str(path))
            origins[name] = dict(path=str(path), sha256=sha(path))
    summary = dict(expected_natural_gap_reproduced=bool(exact_red), failure=failure,
        input_counts=[len(files) for _, files in sets], all_frozen_inputs_verified=True,
        resource_sha256=before_resources, resources_stable=before_resources == after_resources,
        frozen_probe=str(frozen), frozen_probe_sha256=sha(frozen),
        virtual_probe_filename=str(original), no_hot_probe_source_executed=True,
        actual_import_origins=origins, child_report=str(child), child_report_sha256=sha(child),
        root_harness_sha256=sha(Path(__file__)), live_database=False, live_socket=False,
        listener_started=False, service_changed=False, task_skipped=False, battle_executed=False)
    (output/'verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n',
        encoding='utf-8', newline='\n')
    print(json.dumps({k:v for k,v in summary.items()
        if k not in ('resource_sha256','actual_import_origins')}, ensure_ascii=False))
    if not exact_red or before_resources != after_resources:
        raise AssertionError('Exact frozen natural gap not independently reproduced')


if __name__ == '__main__':
    main()
