"""Fixed-input NPC column review runner; installed beside a sealed manifest."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys
from unittest.mock import patch


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('check')
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    review = Path(__file__).resolve().parent
    manifest = json.loads((review / 'manifest.json').read_text(encoding='utf8'))
    assert args.check in manifest['checks'] and args.label.replace('_', '').isalnum()
    root = Path(manifest['workspace_root'])
    release = Path(manifest['context_release'])
    source, harness = release / 'source', release / 'harness'

    def verify():
        for name, digest in manifest['local_inputs'].items():
            assert sha(review / name) == digest, name
        for name, digest in manifest['external_inputs'].items():
            assert sha(Path(name)) == digest, name

    verify()
    output = review / 'verification' / args.label / args.check
    assert not output.exists(), 'Use a new label; preserve earlier runs'
    output.mkdir(parents=True)
    passed = False
    origins = {}
    details = {}
    try:
        if args.check in ('baseline_red', 'native_compat'):
            probe = review / 'current/staging/verify_npc_repair_column_candidate.py'
            common = [sys.executable, '-X', 'utf8', '-B', str(probe), '--workspace-root', str(root),
                '--database', str(output / 'disposable.sqlite3')]
            for phase in ('legacy', 'candidate'):
                command = common + ['--phase', phase, '--report', str(output / (phase + '.json'))]
                if phase == 'candidate' and args.check == 'native_compat':
                    command += ['--npc-module', str(review / 'current/npc_repairs.py')]
                result = subprocess.run(command, capture_output=True, text=True, encoding='utf8', timeout=100)
                (output / (phase + '.stdout.txt')).write_text(result.stdout, encoding='utf8')
                (output / (phase + '.stderr.txt')).write_text(result.stderr, encoding='utf8')
                if phase == 'candidate' and args.check == 'baseline_red':
                    assert result.returncode != 0
                    assert 'Real legacy paid4 cannot replay original-column3' in result.stderr, result.stderr
                    details['actual_baseline_red_reproduced'] = True
                    details['feature_pass_claimed_for_red'] = False
                else:
                    assert result.returncode == 0, result.stdout + result.stderr
            if args.check == 'native_compat':
                old = json.loads((output / 'legacy.json').read_text(encoding='utf8'))
                new = json.loads((output / 'candidate.json').read_text(encoding='utf8'))
                assert old['process_id'] != new['process_id']
                assert old['legacy_accepted_login_epoch'] != new['current_login_epoch']
                assert old['probe_sha256'] == new['probe_sha256'] == sha(probe)
                assert new['override_sha256'] == manifest['scope']['npc_repairs.py']['current_sha256']
                assert new['actual_encrypted_native3_fresh_repair_passed']
                assert new['fresh4_rejected_before_payment'] and new['changed_paid_item_rejected']
                assert new['later_paid4_and3_keep_newer_condition_wallet_and_carried_location']
                details['cross_process_new_epoch_real_paid_receipt_passed'] = True
                origins = new['actual_project_module_origins']
        else:
            sys.path[:0] = [str(harness), str(source)]
            import inspect_client
            inspect_client.ROOT, inspect_client.OUT = root.parent, harness / 'workspace'
            override = review / 'current/npc_repairs.py'
            spec = importlib.util.spec_from_file_location('npc_repairs', override)
            module = importlib.util.module_from_spec(spec)
            sys.modules['npc_repairs'] = module
            spec.loader.exec_module(module)
            descriptor = manifest['checks'][args.check]
            script = review / descriptor['local_script'] if 'local_script' in descriptor else harness / descriptor['harness_script']
            original_write = Path.write_text

            def sink(path, data, *values, **keywords):
                if path.parent == inspect_client.OUT / 'evidence' and path.suffix == '.json':
                    return original_write(output / path.name, data, *values, **keywords)
                assert not path.is_relative_to(release), str(path)
                return original_write(path, data, *values, **keywords)

            sys.argv = [str(script)]
            with patch.object(Path, 'write_text', sink):
                runpy.run_path(str(script), run_name='__main__')
            for name, imported in tuple(sys.modules.items()):
                file = getattr(imported, '__file__', None)
                if not file or name == '__main__':
                    continue
                actual = Path(file).resolve()
                if actual.is_relative_to(root):
                    assert actual.parent in (source, harness) or (name == 'npc_repairs' and actual == override), str(actual)
                    origins[name] = str(actual)
            details['test_input_adaptation'] = descriptor.get('adaptation', 'none; exact frozen published helper')
        passed = True
    finally:
        verify()
        result = dict(check=args.check, passed=passed,
            fixed_local_inputs=len(manifest['local_inputs']), fixed_external_inputs=len(manifest['external_inputs']),
            actual_project_module_origins=origins, details=details,
            source_inventory_refresh_still_legacy4=True, whole_GUI_or_shop_query_fixed=False,
            production_or_policy_modified=False, live_database_accessed=False, service_or_GUI_changed=False)
        (output / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('PASS frozen NPC column check:', args.check)


if __name__ == '__main__':
    main()
