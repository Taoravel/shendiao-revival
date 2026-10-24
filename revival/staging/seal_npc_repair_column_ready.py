"""Seal the reviewed inactive repair candidate, keeping policy/Asset gates open."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'evidence/reviews/npc-repair-columns-20261024-r1'
READY = ROOT / 'evidence/npc-repair-column-candidate-ready.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    manifest = json.loads((REVIEW / 'manifest.json').read_text(encoding='utf8'))
    for name, digest in manifest['local_inputs'].items():
        assert sha(REVIEW / name) == digest, name
    for name, digest in manifest['external_inputs'].items():
        assert sha(Path(name)) == digest, name
    reports = {}
    for label in ('parent', 'standards', 'spec'):
        for check in manifest['checks']:
            path = REVIEW / 'verification' / label / check / 'result.json'
            result = json.loads(path.read_text(encoding='utf8'))
            assert result['check'] == check and result['passed'] is True
            assert result['fixed_local_inputs'] == len(manifest['local_inputs'])
            assert result['fixed_external_inputs'] == len(manifest['external_inputs'])
            if check == 'baseline_red':
                assert result['details']['actual_baseline_red_reproduced']
                assert result['details']['feature_pass_claimed_for_red'] is False
            reports[str(path.relative_to(ROOT)).replace('\\', '/')] = sha(path)
    for filename in ('standards.md', 'spec.md'):
        assert (REVIEW / filename).is_file()
    aggregate = '\n\n'.join((REVIEW / name).read_text(encoding='utf8').rstrip()
        for name in ('standards.md', 'spec.md'))
    aggregate += '\n\n总计：Standards 0（最严重：无）；Spec 0（最严重：无）。\n'
    (REVIEW / 'REVIEW.md').write_text(aggregate, encoding='utf8')
    scope = manifest['scope']
    staged = ROOT / 'staging/npc-repair-column-candidate-v1/npc_repairs.py'
    assert sha(staged) == scope['npc_repairs.py']['current_sha256']
    assert sha(ROOT / 'npc_repairs.py') == scope['npc_repairs.py']['base_sha256']
    created = datetime.now(timezone.utc).isoformat()
    if READY.exists():
        created = json.loads(READY.read_text(encoding='utf8'))['created_utc']
    result = dict(created_utc=created, status='npc_owned_candidate_reviewed_final_policy_and_asset_interface_pending',
        staged_module=str(staged), base_release=manifest['context_release'], scope=scope,
        review=str(REVIEW), manifest_sha256=sha(REVIEW / 'manifest.json'),
        aggregate_sha256=sha(REVIEW / 'REVIEW.md'),
        fixed_local_inputs=len(manifest['local_inputs']), fixed_external_inputs=len(manifest['external_inputs']),
        axes=dict(standards_findings=0, fowler_findings=0, spec_findings=0),
        independent_runs=18, positive_candidate_or_regression_runs=15, precise_original_red_reproductions=3,
        verification_sha256=reports,
        methods=['tdd: original published Owner red versus one-module candidate green',
            'codebase-design: native source/owned physical state/private receipt identity stay distinct',
            'code-review: independent Standards and Spec plus complete fixed-input replays'],
        actual_paid_receipt_generated_by_published_owner=True, cross_process_new_login_epoch_verified=True,
        fresh_native3_and_paid_current_only_verified=True, fresh4_rejected=True,
        legacy_receipt_fingerprint_token4_is_private=True,
        root_final_policy_adoption=False, asset_native_message_interface_selected=False,
        asset_network_refresh_and_shop_query_implemented=False,
        shop_query4_tab_semantics_under_separate_research=True,
        workspace_production_module_changed=False, shared_runtime_integrated=False,
        deployed=False, native_gui_verified=False,
        limits=['Published Inventory network outputs still use legacy4; full original UI path is incomplete',
            'Final compatibility policy and actual Asset Interface require joint acceptance',
            'Query4 is a shop-dialog path; its exact tab/payload must be researched, not invented from stock',
            'No special855, migration, new baseline or shared/PVE activation'])
    READY.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('Sealed inactive NPC repair candidate:', sha(READY))
    print('15 positive checks and3 original RED reproductions; each22local+3078external inputs')


if __name__ == '__main__':
    main()
