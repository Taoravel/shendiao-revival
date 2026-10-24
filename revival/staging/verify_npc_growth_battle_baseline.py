"""Independently replay the integrator's natural first-battle red witness.

Keep its exact probe and all approved release inputs; no shared source edits.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'runtime/deployments/npc-repair-20261024T023920Z'
FROZEN = ROOT / 'npc_growth_first_battle_frozen_probe_20261024.py'
REPORT = ROOT / 'evidence/npc-growth-first-battle-owner-baseline.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    manifest = json.loads((RELEASE / 'manifest.json').read_text(encoding='utf8'))
    candidate = json.loads((RELEASE / 'candidate.json').read_text(encoding='utf8'))
    groups = ((RELEASE / 'source', manifest['sha256']),
        (RELEASE / 'harness', candidate['harness_sha256']),
        (RELEASE / 'harness', candidate['harness_resource_sha256']),
        (RELEASE / 'harness/workspace', candidate['workspace_sha256']))

    def verify():
        for directory, entries in groups:
            for name, digest in entries.items():
                assert sha(directory / name) == digest, name

    verify()
    original = ROOT / 'diagnose_growth_first_battle_runtime.py'
    data = original.read_bytes()
    if FROZEN.exists():
        assert FROZEN.read_bytes() == data, 'Preserve original frozen growth witness'
    else:
        FROZEN.write_bytes(data)
    probe_sha = sha(FROZEN)
    environment = dict(os.environ)
    environment['PYTHONPATH'] = str(RELEASE / 'harness')
    completed = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-P', str(FROZEN),
        '--source', str(RELEASE / 'source'), '--report', str(REPORT), '--expect-missing'],
        capture_output=True, text=True, encoding='utf8', timeout=120, env=environment)
    verify()
    assert sha(FROZEN) == probe_sha
    if completed.returncode:
        print(completed.stdout)
        print(completed.stderr)
        raise AssertionError('Original growth witness did not reproduce: ' + str(completed.returncode))
    result = json.loads(REPORT.read_text(encoding='utf8'))
    assert Path(result['harness_prefix_helper']['path']) == RELEASE / 'harness/verify_master_commit_card_runtime.py'
    assert result['harness_prefix_helper']['sha256'] == candidate['harness_sha256']['verify_master_commit_card_runtime.py']
    assert result['level'] == 2 and result['task_id'] == 100107
    assert result['npc_id'] == 10908 and result['npc_placement_id'] == 10
    assert result['task_still_active'] and not result['task_completed']
    assert not result['original_task_offered'] and not result['battle_started']
    assert not result['battle_admissions_table_prepared'] and not result['durable_admissions']
    acceptance = dict(release=str(RELEASE), original_probe_sha256=probe_sha,
        frozen_probe=str(FROZEN), original_probe=str(original),
        exact_missing_capability_reproduced=True, result_sha256=sha(REPORT),
        source_inputs_unchanged=len(manifest['sha256']),
        helper_inputs_unchanged=len(candidate['harness_sha256']),
        config_inputs_unchanged=len(candidate['workspace_sha256']),
        actual_helper_path_verified=True,
        fixture_setup_corrections=['Explicit frozen helper path; initial relocated copy could not import helper',
            'Probe remains at its original directory depth for original artres resolution',
            'Python safe-path prevents workspace helpers shadowing the frozen harness'],
        observed='Natural level2 private1501/10908: task100107 absent from menu; native c4a4c does not start battle',
        actual_battle_executed=False, live_database_accessed=False, listener_started=False,
        production_or_service_changed=False, gui_verified=False,
        limits=['Red diagnostic only; no claim that independent TaskPve implementation is complete'])
    output = ROOT / 'evidence/npc-growth-first-battle-owner-acceptance.json'
    output.write_text(json.dumps(acceptance, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(completed.stdout.strip())
    print('REPRODUCED NPC growth first-battle baseline; immutable release inputs unchanged')


if __name__ == '__main__':
    main()
