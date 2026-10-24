"""Replay stopped16-chain merchant research into separate fixed report sinks."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    'research_npc_shop_catalog.py': 'fd3f5dc3feac5c532a35251c59cb38daa98e7b68ab757c734d1ebbe3390033ea',
    'evidence/NPC_SHOP_CATALOG_NATIVE_RESEARCH.md': '0b7622cba029fcad6e0bd34bfde696ca6dc115b99dd30d131ceb5d4da0677c0c',
    'evidence/npc-shop-catalog-native.json': 'ddeddb4a860377559cb3a5f60ddc2c2ae73922757d9b878ad93d793257a07c5b',
    'evidence/npc-shop-catalog-disassembly.txt': '65f618d1113e4f75bc6ec0c3b4778d8f05a26da7c8044960632e6cc08329b5e2'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    report = json.loads((ROOT / 'evidence/npc-shop-catalog-native.json').read_text(encoding='utf8'))
    assert report['input_sha256_before'] == report['input_sha256_after']
    watched = dict(report['input_sha256_before'])
    watched.update(FILES)
    for name in ('evidence/npc-repair-column-candidate-ready.json',
            'staging/npc-repair-column-candidate-v1/npc_repairs.py'):
        watched[name] = sha(ROOT / name)

    def verify():
        for name, digest in watched.items():
            assert sha(ROOT / name) == digest, name

    verify()
    output = ROOT / 'evidence/npc-shop-catalog-parent-replay'
    output.mkdir(exist_ok=True)
    original_write = Path.write_text
    names = ('npc-shop-catalog-native.json', 'npc-shop-catalog-disassembly.txt')

    def sink(path, data, *args, **kwargs):
        assert path.parent == ROOT / 'evidence' and path.name in names, str(path)
        return original_write(output / path.name, data, *args, **kwargs)

    sys.path.insert(0, str(ROOT))
    with patch.object(Path, 'write_text', sink):
        runpy.run_path(str(ROOT / 'research_npc_shop_catalog.py'), run_name='__main__')
    verify()
    for name in names:
        assert sha(output / name) == FILES['evidence/' + name], name
    assert report['actual_case_count'] == 16
    assert report['tabs']['NpcSellItem/tab11'] == '回购'
    assert {row['repurchase_request']['protocol'] for row in report['repurchase_chains']} == {'0xc232e'}
    result = dict(independent_parent_replay=True, native_cases=16, four_original_artifacts_sha256=FILES,
        all_source_and_case_evidence_identical=True, watched_inputs_sha256=watched,
        historical_cases_replayed=0, only_output_sinks_redirected=True,
        verifier_sha256=sha(Path(__file__)),
        conclusions=['Purchase templates are local configuration; query4 belongs to buyback tab',
            'Native dedicated buyback response carries real instances and a price map',
            'Default display price and post-default override need separate final pricing research'],
        original_server_reply_selection_verified=False, final_buyback_pricing_verified=False,
        production_or_policy_changed=False, live_database_accessed=False, service_or_GUI_changed=False)
    (ROOT / 'evidence/npc-shop-catalog-independent.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('PASS parent16 merchant chains; four original artifacts and all protected inputs unchanged')


if __name__ == '__main__':
    main()
