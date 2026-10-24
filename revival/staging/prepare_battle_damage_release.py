"""Freeze only the two damage-result inputs over the reviewed live baseline."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'runtime/deployments/npc-role-healing-20261023T125539Z'
PROTOCOL_HASH = '1a472edf4f1a9db20d8c08ba05eb5516b56b723b87b2b2c80ca0c0a60c75cd22'
CHECKS = ['verify_battle_damage_presentation.py', 'verify_battle.py',
          'verify_battle_owner.py', 'verify_battle_runtime.py', 'verify_wild_runtime.py']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in before['sha256'].items():
        if digest(BASE/'source'/name) != expected:
            raise ValueError('Baseline changed: '+name)
    if digest(BASE/'run_release.py') != before['runner_sha256']:
        raise ValueError('Baseline runner changed')
    if digest(ROOT/'battle_protocol.py') != PROTOCOL_HASH:
        raise ValueError('Battle protocol no longer matches completed native probe')
    training = (BASE/'source/training_battle.py').read_bytes()
    old = b'targets=[(hit.target,[(1,hit.hp_change,0)]) for hit in e.impacts]'
    new = b'targets=[p.TargetResult(hit.target,((p.HP_CHANGE,hit.hp_change),)) for hit in e.impacts]'
    if training.count(old) != 1:
        raise ValueError('Expected original damage projection seam changed')
    patch = {'battle_protocol.py': (ROOT/'battle_protocol.py').read_bytes(),
             'training_battle.py': training.replace(old, new, 1)}
    now = datetime.now(timezone.utc)
    release = ROOT/'runtime/deployments'/('battle-damage-'+now.strftime('%Y%m%dT%H%M%SZ'))
    source = release/'source'
    source.mkdir(parents=True, exist_ok=False)
    for name in before['sha256']:
        target = source/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BASE/'source'/name, target)
    changes = []
    for name, data in patch.items():
        target = source/name
        target.write_bytes(data)
        changes.extend(difflib.unified_diff(
            (BASE/'source'/name).read_text(encoding='utf-8').splitlines(True),
            target.read_text(encoding='utf-8').splitlines(True),
            fromfile='reviewed-base/'+name, tofile='damage-fix/'+name))
    hashes = {name: digest(source/name) for name in before['sha256']}
    changed = {name: value for name, value in hashes.items() if before['sha256'].get(name) != value}
    if set(changed) != set(patch):
        raise ValueError('Unexpected production scope')
    shutil.copy2(BASE/'run_release.py', release/'run_release.py')
    manifest = dict(created_utc=now.isoformat(), base_release=str(BASE), sha256=hashes,
        changed_modules=changed, runner_sha256=digest(release/'run_release.py'),
        scope='native target HP result map repair; unchanged battle numbers and ownership')
    (release/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (release/'changes.diff').write_text(''.join(changes), encoding='utf-8')
    harness = release/'harness'
    (harness/'evidence').mkdir(parents=True)
    (harness/'workspace/evidence').mkdir(parents=True)
    for name, data in patch.items():
        (harness/'workspace'/name).write_bytes(data)
    inputs = CHECKS+['research_battle_damage.py', 'research_battle_commands.py', 'research_battle.py']
    for name in inputs:
        # Existing runtime regressions use their matching frozen BASE harness.
        origin = BASE/'source'/name if name in ('verify_battle_owner.py', 'verify_battle_runtime.py', 'verify_wild_runtime.py') else ROOT/name
        data = origin.read_bytes()
        if name == 'verify_battle_damage_presentation.py':
            anchor = b'ROOT=Path(__file__).parent'
            if data.count(anchor) != 1:
                raise ValueError('Verification report path seam changed')
            data = data.replace(anchor, anchor+b"/'workspace'", 1)
        (harness/name).write_bytes(data)
    record = dict(release=str(release), base_release=str(BASE), base_pid_at_staging=45272,
        changed_modules=changed, file_count=len(hashes), started=False,
        checks_required=CHECKS, new_empty_tables=[], verification_name='battle-damage',
        harness_sha256={name: digest(harness/name) for name in inputs},
        harness_sources={name: str(harness/name) for name in inputs},
        scope=manifest['scope'], training_derived_from_frozen_base=True,
        harness_adaptation='damage verifier report ROOT redirected to workspace copy only; all gameplay imports frozen source',
        excluded='auto-target patch, private/story/pool/social/NPC-distance and every other workspace gameplay change',
        native_gui_verified=False)
    text = json.dumps(record, indent=2)
    (release/'candidate.json').write_text(text, encoding='utf-8')
    (ROOT/'staging/battle-damage-candidate.json').write_text(text, encoding='utf-8')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
