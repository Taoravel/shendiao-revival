"""Root offline acceptance: frozen production -> original HP consumer.

Never launches a client/service, opens a socket, or accesses a live database.
"""
import argparse
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys
import unittest


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', action='store_true')
    parser.add_argument('--production', type=Path)
    args = parser.parse_args()
    if args.base and args.production:
        parser.error('Select baseline or an explicit production release')
    root = Path(__file__).resolve().parents[1]
    record = json.loads((root/'staging/battle-damage-candidate.json').read_text(encoding='utf-8-sig'))
    release = Path(record['release'])
    production = args.production.resolve() if args.production else (Path(record['base_release']) if args.base else release)
    source, harness = production/'source', release/'harness'
    manifest = json.loads((production/'manifest.json').read_text(encoding='utf-8-sig'))
    output = root/'evidence/root-battle-damage-20261024'/(production.name if args.production else ('base' if args.base else 'candidate'))
    output.mkdir(parents=True, exist_ok=True)
    (output/'evidence').mkdir(exist_ok=True)

    def verify_inputs():
        for name, expected in manifest['sha256'].items():
            assert digest(source/name) == expected, name
        assert digest(production/'run_release.py') == manifest['runner_sha256']
        for name, expected in record['harness_sha256'].items():
            assert digest(harness/name) == expected, name

    verify_inputs()
    for name in record['changed_modules']:
        (output/name).write_bytes((source/name).read_bytes())
    sys.path[:0] = [str(harness), str(source)]
    import inspect_client
    inspect_client.ROOT = root.parent
    inspect_client.OUT = source
    probe = importlib.import_module('verify_battle_damage_presentation')
    probe.ROOT = output
    suite = (unittest.TestSuite([probe.DamageChecks('test_real_attack_output_reaches_native_hp_consumer')])
             if args.base else unittest.defaultTestLoader.loadTestsFromTestCase(probe.DamageChecks))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    log = stream.getvalue()
    (output/'unittest.txt').write_text(log, encoding='utf-8')
    if args.base:
        assert result.testsRun == 1 and len(result.failures) == 1 and not result.errors, log
        assert 'HP was put in the unrelated DemoAttr list' in log, log
        baseline_battle = probe.TrainingBattle(probe.ROLE)
        baseline_before = baseline_battle.battle.fighters[1].hp
        baseline_packets = baseline_battle.receive(probe.p.SEND_ACTION, probe.native_action(probe.p.ATTACK, 21))
        baseline_body = next(body for kind, body in baseline_packets if kind == probe.p.ROUND_SCRIPT)
        baseline_domain_hp = baseline_battle.battle.fighters[1].hp - baseline_before
        baseline_native_hp = probe.consumed_target_hp(baseline_body)
        assert baseline_domain_hp == -16 and baseline_native_hp == 0
    else:
        assert result.testsRun == 8 and result.wasSuccessful(), log
    modules = {}
    for name, module in list(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path == Path(__file__).resolve() and name == '__main__':
            continue
        if path.is_relative_to(root):
            assert path.is_relative_to(source) or path.is_relative_to(harness), str(path)
            modules[name] = str(path)
    import native_inspect
    report = dict(expected_baseline_failure=args.base, checks_run=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors),
                  original_image_sha256=hashlib.sha256(native_inspect.DATA).hexdigest(),
                  legacy_native_hp_change=probe.consumed_target_hp(probe.LEGACY_PACKET),
                  production=str(source), production_modules=modules,
                  source_files_verified=len(manifest['sha256']),
                  frozen_harnesses_verified=len(record['harness_sha256']),
                  changed_modules={name:digest(source/name) for name in record['changed_modules']},
                  live_service_changed=False, live_database_accessed=False,
                  live_client_opened=False, rendered_animation_verified=False)
    if args.base:
        report.update(baseline_domain_hp_change=baseline_domain_hp,
                      baseline_native_hp_change=baseline_native_hp)
    verify_inputs()
    (output/'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(log)
    print(json.dumps({k:v for k,v in report.items() if k != 'production_modules'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
