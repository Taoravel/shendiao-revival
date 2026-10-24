"""Seal only a fully reviewed inactive NPC repair/native-message composition."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'evidence/reviews/npc-repair-native-messages-20261024-r1'
READY=ROOT/'evidence/npc-repair-native-messages-ready.json'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):return json.loads(path.read_text(encoding='utf8'))


def main():
    assert not READY.exists(),'Keep ready artifacts immutable'
    manifest=load(REVIEW/'manifest.json')
    assert sha(REVIEW/'manifest.json')=='bc82e4eacae0b80b39f17a0c17682812fd282ad140cedc72a75c78a07710530a'
    for name,digest in manifest['local_inputs'].items():assert sha(REVIEW/name)==digest,name
    for name,digest in manifest['external_inputs'].items():assert sha(Path(name))==digest,name
    candidate=ROOT/'staging/npc-repair-column-candidate-v2/npc_repairs.py'
    assert sha(candidate)==sha(REVIEW/'current/npc_repairs.py')=='60820efa2e5db0e6a6a10ccfc1ea035e717d80ddf37ee0a3ccfd1c3fc59ced86'
    assert sha(ROOT/'npc_repairs.py')=='3cc4ff7dc2a956946fd31debb18b1a3773d6ca472b93b218fcc257e5aaf86884'
    prior={
        'npc-equipment-identification-ready.json':'9b05ab14fd786558a2e320a70ae5a9579b578b3c4170ecb241fac8e2bab98794',
        'npc-placement-direction-ready.json':'761c97193b18d92e860aa8cbfeac045a34d9c10057c792d586b0484c7df62d82',
        'npc-repair-column-candidate-ready.json':'9e297b2f66678c2a198492a3240ec72cf3d7bf4659531427e5d759582b5e1543'}
    for name,digest in prior.items():assert sha(ROOT/'evidence'/name)==digest,name
    checks=('native_messages','native_compat','carried_transactions','carried_runtime','known_native3','equipped_native3')
    results={};native={}
    for label in ('parent','standards','spec'):
        for check in checks+('native_red',):
            path=REVIEW/'verification'/label/check/'result.json';result=load(path)
            assert result['passed'] is True,str(path)
            assert result['fixed_local_inputs']==18 and result['fixed_external_inputs']==6112
            results[str(path.relative_to(REVIEW)).replace('\\','/')]=sha(path)
            if check in ('native_messages','native_red'):
                probe_result=Path(result['original_probe_result']);probe=load(probe_result)
                assert probe['passed'] and probe['expected_red']==(check=='native_red')
                assert probe['feature_pass_claimed']==(check=='native_messages')
                if check=='native_messages':
                    actual=load(probe_result.parent/'candidate.json')
                    assert len(actual['passed'])==11 and actual['actual_migrated_HPMP_source_combination']
                    assert actual['npc_module_sha256']==sha(candidate)
                    assert not actual['actual_shared_provider_injection'] and not actual['encrypted_delivery_for_this_provider']
                    native[label]=dict(report=str(probe_result.parent/'candidate.json'),
                        report_sha256=sha(probe_result.parent/'candidate.json'),public_behavior_groups=11)
    # Report contents are independently reviewed before calling this sealer.
    reports={name:sha(REVIEW/name) for name in ('standards.md','spec.md','REVIEW.md')}
    result=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        status='npc_owned_repair_and_reviewed_asset_adapter_composition_ready_pending_policy_and_shared',
        goal_status='active; all NPC restoration is not complete',
        source_candidate=str(candidate),source_candidate_sha256=sha(candidate),
        exact_base_sha256=manifest['scope']['npc_repairs.py']['base_sha256'],
        current_workspace_npc_repairs_sha256=sha(ROOT/'npc_repairs.py'),
        review_directory=str(REVIEW),review_manifest_sha256=sha(REVIEW/'manifest.json'),
        fixed_local_inputs=18,fixed_external_inputs=6112,
        independent_reports_sha256=reports,standards_hard_findings=0,standards_judgement_findings=0,spec_findings=0,
        positive_check_runs=18,actual_base_red_reproductions=3,
        red_counted_as_feature_pass=False,verification_result_sha256=results,
        public_provider_native_proofs=native,
        asset_review='equipment-native-columns-20261024-r1',
        selected_asset_module_sha256='e9130e06c16be3c84bb7da407f78133d9c57fa0714d433a8c170efa491c5c5a9',
        dependency_context=str(ROOT/'staging/npc-repair-native-context-v1'),
        dependency_context_manifest_sha256=sha(ROOT/'staging/npc-repair-native-context-v1/manifest.json'),
        dependency_scope='exact023920 Inventory/shared +5 reviewed Asset readonly modules and5 configs; no whole workspace Inventory',
        preserved_ready_sha256=prior,
        methods=dict(tdd='actual E648 missing-provider RED then real source/mutation/encoding rollback and same-ID retry green',
            codebase_design='inject the real selected Asset producer at the existing caller transaction; no Gem import or bag alias in NPC',
            code_review='fixed exact BASE, independent Standards and Spec, each6 positive+1actualRED',
            writing_for_agents='startup dependency and same-Tx encoding/release conditions co-located with handoff'),
        root_final_policy_adopted=False,shared_provider_injected=False,deployed=False,GUI_verified=False,
        nonempty_gem_full_role_resource_source_verified=False,
        real_database_or_service_or_GUI_changed=False,
        unverified=['final compatibility policy adoption','main startup/repair wrapper provider selection',
            'actual encrypted current-provider dispatch and login/reconnect/query3/other action composition',
            'full nonemptyGem role attribute/source contract','buyback query4 and display/debit policy consistency',
            'immutable deployment and actual original GUI','capacity and complete NPC lifecycle/services'])
    READY.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Sealed inactive NPC repair/native composition:',sha(READY))


if __name__=='__main__':main()
