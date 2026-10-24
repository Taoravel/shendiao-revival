"""Seal a reviewed readonly candidate; preserve its independent policy gates."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'evidence/reviews/npc-buyback-query-20261024-r1'
OUTPUT=ROOT/'evidence/npc-buyback-query-candidate-reviewed.json'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):return json.loads(path.read_text(encoding='utf8'))


def main():
    assert not OUTPUT.exists(),'Preserve reviewed artifacts'
    manifest=load(REVIEW/'manifest.json')
    assert sha(REVIEW/'manifest.json')=='075e967157188aaf5dcf0fa491cfcfde768a13630ac4ccbcb700692a4aae0bd5'
    for name,digest in manifest['local_inputs'].items():assert sha(REVIEW/name)==digest,name
    for name,digest in manifest['external_inputs'].items():assert sha(Path(name))==digest,name
    current=ROOT/'staging/npc-buyback-query-candidate-v2/npc_shop_sales.py'
    assert sha(current)==manifest['scope']['npc_shop_sales.py']['current_sha256']=='5b25096ce774e0d27469a6259e6efbbedc4d11b62a3ecc76553841019d6b9a24'
    results={};positive=[];red=[]
    for label in ('parent','standards','spec'):
        for check in manifest['checks']:
            path=REVIEW/'verification'/label/check/'result.json';record=load(path)
            assert record['passed'] and record['fixed_local_inputs']==12 and record['fixed_external_inputs']==3083
            results[str(path.relative_to(REVIEW)).replace('\\','/')]=sha(path)
            if check in ('missing_query_red','bad_record_red'):
                assert record['details']['actual_probe_exit']==1 and not record['details']['feature_pass_claimed']
                red.append(label+':'+check)
            else:
                assert record['details']['feature_pass_claimed'];positive.append(label+':'+check)
            if check=='readonly_query':
                probe=load(Path(record['details']['probe_result']))
                assert probe['passed'] and len(probe['checked'])==13 and probe['candidate_sha256']==sha(current)
    reports={name:sha(REVIEW/name) for name in ('standards.md','spec.md','REVIEW.md')}
    result=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        status='npc_owned_readonly_query_candidate_reviewed_pending_root_adoption_price_consistency_and_shared',
        full_NPC_goal='active',source_candidate=str(current),source_candidate_sha256=sha(current),
        real_published_base_sha256=manifest['scope']['npc_shop_sales.py']['base_sha256'],
        prototype_bad_record_red_sha256=sha(REVIEW/'prototypes/npc_shop_sales_bad_record.py'),
        fixed_review_directory=str(REVIEW),manifest_sha256=sha(REVIEW/'manifest.json'),
        fixed_local_inputs=12,fixed_external_inputs=3083,
        standards_hard_findings=0,standards_judgement_findings=0,spec_findings=0,
        positive_check_runs=6,actual_missing_query_red_reproductions=3,actual_bad_record_red_reproductions=3,
        red_counted_as_feature_pass=False,positive_checks=positive,actual_red_checks=red,
        readonly_public_behavior_groups_per_run=13,original_Peer_sale_groups_per_run=12,
        result_sha256=results,independent_report_sha256=reports,
        method=dict(diagnosing_bugs='published actual encrypted query empty loop retained; permission/route/cache differentiated',
            tdd='actual missing-interface RED; real source-scope reads green; actual malformed-record RED to controlled refusal',
            codebase_design='query read snapshot separate from mutator cleanup; one real pure c0434 projection for read/transaction',
            code_review='actual non-Git BASE, independent Standards/Spec each2positive+2actualRED',
            writing_for_agents='map-member receipt/deadline/send fence and independent policy gates co-located with integration steps'),
        original_service2_read_permission_is_server_proposal=True,response_choice_is_server_proposal=True,
        existing_display_debit_discrepancy_resolved=False,fees_or_receipt_identity_changed=False,
        shared_query_routed=False,query_native_GUI_verified=False,deployed=False,
        live_database_or_service_or_GUI_changed=False,
        unverified=['root adoption of service2/c0434 read-only proposal',
            'root display/debit policy and oldpaid compatibility for actual buyback',
            'main actual encrypted query4 with current permission/delivery revalidation',
            'complete original GUI and atomic immutable deployment','full NPC restoration and capacity'])
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Sealed reviewed NPC query candidate:',sha(OUTPUT))


if __name__=='__main__':main()
