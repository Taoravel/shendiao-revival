"""Pin exact repair bytes, adapted test inputs and published dependency paths."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'runtime/deployments/npc-repair-20261024T023920Z'
REVIEW = ROOT / 'evidence/reviews/npc-repair-columns-20261024-r1'
STAGE = ROOT / 'staging/npc-repair-column-candidate-v1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    assert not REVIEW.exists()
    candidate = json.loads((RELEASE / 'candidate.json').read_text(encoding='utf8'))
    published = json.loads((RELEASE / 'manifest.json').read_text(encoding='utf8'))
    metadata = json.loads((STAGE / 'candidate.json').read_text(encoding='utf8'))
    assert sha(ROOT / 'npc_repairs.py') == metadata['production_base_sha256']
    assert sha(STAGE / 'npc_repairs.py') == metadata['candidate_sha256']
    REVIEW.mkdir(parents=True)

    def copy(source, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    copy(RELEASE / 'source/npc_repairs.py', REVIEW / 'base/npc_repairs.py')
    copy(STAGE / 'npc_repairs.py', REVIEW / 'current/npc_repairs.py')
    probe = 'staging/verify_npc_repair_column_candidate.py'
    copy(ROOT / probe, REVIEW / 'current' / probe)
    (REVIEW / 'base/staging').mkdir(parents=True)
    (REVIEW / 'base' / probe).write_bytes(b'')
    adaptations = {}
    for name, old, new in (
            ('verify_npc_repair_resource_runtime.py', ',4,weapon)', ',3,weapon)'),
            ('verify_npc_equipped_repair_runtime.py', ",4,gear['id']))", ",3,gear['id']))")):
        source = RELEASE / 'harness' / name
        copy(source, REVIEW / 'base/fixtures' / name)
        text = source.read_text(encoding='utf8')
        assert text.count(old) == 1
        changed = text.replace(old, new)
        if name == 'verify_npc_equipped_repair_runtime.py':
            assert changed.count('ordinary NPC method2/column4 repair') == 1
            changed = changed.replace('ordinary NPC method2/column4 repair', 'ordinary NPC method2/column3 repair')
        target = REVIEW / 'current/fixtures' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(changed, encoding='utf8')
        adaptations[name] = dict(original_harness_sha256=sha(source), native3_fixture_sha256=sha(target),
            input_change=dict(old=old, new=new), production_dispatcher_or_projection_changed=False)
    scope_names = ('npc_repairs.py', probe, *('fixtures/' + name for name in adaptations))
    scope = {}
    diff = []
    for name in scope_names:
        before, after = REVIEW / 'base' / name, REVIEW / 'current' / name
        scope[name] = dict(base_sha256=sha(before), current_sha256=sha(after))
        diff.extend(difflib.unified_diff(before.read_text(encoding='utf8').splitlines(True),
            after.read_text(encoding='utf8').splitlines(True), fromfile='base/' + name, tofile='current/' + name))
    assert diff
    (REVIEW / 'changes.diff').write_text(''.join(diff), encoding='utf8')
    refs = ('AGENTS.md', 'revival/ARCHITECTURE.md', 'revival/DESIGN_AUTHORITY.md',
        'GLOSSARY.md', 'docs/adr/0001-domain-owned-member-permission.md')
    for name in refs:
        copy(ROOT.parent / name, REVIEW / 'references' / name)
    for name in ('NPC_REPAIR_COLUMN_CANDIDATE.md', 'NPC_REPAIR_COLUMN_DIAGNOSIS.md',
            'NPC_REPAIR_COLUMN_RESEARCH.md', 'npc-repair-column-native.json',
            'npc-repair-column-independent.json', 'npc-repair-column-runtime-baseline.json'):
        copy(ROOT / 'evidence' / name, REVIEW / 'references/evidence' / name)
    (REVIEW / 'references/root-compatibility-principle.txt').write_text(
        'Source: authorized planner thread01a16695-63b4-7be3-a17d-171c74f7a6ec, direct message2026-10-24.\n'
        '收到封签27组合，已按实际来源转Asset对接自身bag3/refresh/tips/gem；不全局3↔4、不迁移内部持久col4，现PVE仍用已知内部快照。'
        '后续旧paid4兼容原则先固定：只已有真实stable receipt/current-only恢复，不将其重解释为新NPC货架权限或重扣款，'
        '新fresh修理4不凭历史可付而继续接受；最终独立policy需与你Asset实际Interface候选一起定。'
        '继续所属原source+最小修复准备，不插队PVE、不动shared/现役/9b05/761c。\n', encoding='utf8')
    copy(ROOT / 'staging/npc_repair_column_review_runner.py', REVIEW / 'verify_frozen.py')
    external = {}
    for directory, entries in ((RELEASE / 'source', published['sha256']),
            (RELEASE / 'harness', candidate['harness_sha256']),
            (RELEASE / 'harness', candidate['harness_resource_sha256']),
            (RELEASE / 'harness/workspace', candidate['workspace_sha256'])):
        for name, digest in entries.items():
            path = directory / name
            assert sha(path) == digest, str(path)
            external[str(path)] = digest
    for path in (ROOT.parent / 'artres/map.pfs', ROOT.parent / 'artres/config.pfs',
            ROOT / 'npc_repairs.py', ROOT / 'evidence/npc-equipment-identification-ready.json',
            ROOT / 'evidence/npc-placement-direction-ready.json'):
        external[str(path)] = sha(path)
    local = {str(path.relative_to(REVIEW)).replace('\\', '/'): sha(path)
        for path in REVIEW.rglob('*') if path.is_file()}
    result = dict(workspace_root=str(ROOT), context_release=str(RELEASE), scope=scope,
        comparison='non-Git exact published3cc; new probe empty base; two exact original harness input diffs',
        source_inputs=len(published['sha256']), helper_inputs=len(candidate['harness_sha256']),
        configuration_inputs=len(candidate['workspace_sha256']), local_inputs=local, external_inputs=external,
        test_input_adaptations=adaptations,
        checks=dict(baseline_red=dict(), native_compat=dict(),
            carried_transactions=dict(harness_script='verify_npc_repair_transactions.py'),
            carried_runtime=dict(harness_script='verify_npc_repair_runtime.py'),
            known_native3=dict(local_script='current/fixtures/verify_npc_repair_resource_runtime.py',
                adaptation='Only test wire column4 changes to native3; all known-resource expectations retained'),
            equipped_native3=dict(local_script='current/fixtures/verify_npc_equipped_repair_runtime.py',
                adaptation='Only test wire column4 and descriptive label change to native3; all transaction/reconnect expectations retained')),
        actual_module_override_only='npc_repairs', final_policy_adoption=False,
        asset_network_refresh_and_shop_query_fixed=False, shared_deployment=False)
    (REVIEW / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('Frozen repair column candidate:', len(scope), 'scope files;', len(local), 'local;', len(external), 'external inputs')
    print('Manifest SHA256:', sha(REVIEW / 'manifest.json'))


if __name__ == '__main__':
    main()
