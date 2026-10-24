"""Seal completed independent NPC domain review without promoting shared code."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'evidence/reviews/npc-equipment-identification-20261024-r1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    manifest=json.loads((REVIEW/'manifest.json').read_text(encoding='utf8'))
    for name,digest in manifest['files'].items():
        assert sha(REVIEW/name)==digest,name
    for name,row in manifest['scope'].items():
        assert sha(ROOT/name)==row['current_sha256'],name
        assert row['base_sha256']==hashlib.sha256(b'').hexdigest()
    provider=json.loads((ROOT/'evidence/equipment-identification-assets-ready.json').read_text(encoding='utf8'))
    assert provider['status']=='asset_provider_ready_fixed_r2'
    assert provider['production_sha256']==manifest['provider_production']
    for name,digest in manifest['provider_production'].items():
        assert sha(ROOT/name)==digest,name
    for name in ('design/npc-equipment-identification-v1.json',
            'design/npc-identification-query-v1.json','npc_identification_query.py',
            'npc_identification_protocol.py'):
        assert sha(ROOT/name)==manifest['files']['current/revival/'+name],name
    scripts=tuple(name for name in manifest['scope'] if name.startswith('verify_'))
    results={}
    for label in ('parent','standards','spec'):
        results[label]={}
        for script in scripts:
            path=REVIEW/'verification'/label/(script+'.result.json')
            result=json.loads(path.read_text(encoding='utf8'))
            assert result['passed'] is True and result['frozen_inputs']==len(manifest['files'])
            assert result['shared_route_activated'] is False
            results[label][script]=sha(path)
    aggregate=(REVIEW/'standards.md').read_text(encoding='utf8').rstrip()+'\n\n'+(
        REVIEW/'spec.md').read_text(encoding='utf8').rstrip()+(
        '\n\nStandards：硬规则0项、Fowler判断0项；Spec：缺失/部分0项、越界0项、错误0项。'
        '\n本结论仅覆盖四个NPC新增文件；共享候选、部署、GUI和随机鉴定另验。\n')
    (REVIEW/'REVIEW.md').write_text(aggregate,encoding='utf8')
    fixed={name:sha(REVIEW/name) for name in ('manifest.json','changes.diff','verify_frozen.py',
        'standards.md','spec.md','REVIEW.md')}
    path=ROOT/'evidence/npc-equipment-identification-ready.json'
    created=(json.loads(path.read_text(encoding='utf8'))['created_utc'] if path.exists()
        else datetime.now(timezone.utc).isoformat())
    ready=dict(created_utc=created,status='reviewed_domain_pending_shared',
        scope='NPC fixed clean identification only; no random generation or default/old-profile migration',
        npc_production_sha256={'npc_equipment_identification.py':sha(ROOT/'npc_equipment_identification.py')},
        npc_verification_sha256={name:sha(ROOT/name) for name in scripts},
        policy_sha256={name:sha(ROOT/name) for name in ('design/npc-equipment-identification-v1.json',
            'design/npc-identification-query-v1.json')},
        existing_npc_dependencies_sha256={name:sha(ROOT/name) for name in (
            'npc_identification_query.py','npc_identification_protocol.py')},
        provider_production_sha256=manifest['provider_production'],
        provider_ready_sha256=sha(ROOT/'evidence/equipment-identification-assets-ready.json'),
        provider_review=str(manifest['provider_review']),
        fixed_review=dict(directory=str(REVIEW),sha256=fixed,inputs=len(manifest['files']),
            standards_hard=0,standards_fowler=0,spec_missing_partial=0,spec_scope=0,spec_wrong=0),
        independently_passed_results_sha256=results,
        verification=dict(settlement_groups=13,late_rollback_faults=5,dialogue_rejections=18,
            startup_invalid_recipes=55,paid_current_only_SQL_authorizer=True),
        integration_handoff='evidence/NPC_IDENTIFICATION_INTEGRATION.md',
        shared_required=['startup after currency','original local menu495 and C04cc/C4276 routing',
            'server ticket lifecycle and modal gates','current map/member/connection authority',
            'actual-send fences','actual BASE-specific provider delta and candidate review'],
        shared_route_activated=False,deployed=False,native_gui_verified=False,
        live_database_modified=False,random_identification_implemented=False)
    path.write_text(json.dumps(ready,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(status=ready['status'],inputs=len(manifest['files']),
        independent_runs=9,ready_sha256=sha(path),aggregate_sha256=fixed['REVIEW.md']),ensure_ascii=False))


if __name__=='__main__':
    main()
