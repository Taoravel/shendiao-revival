"""Independent replay of final client quotes against the actual sale frame."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    'research_npc_buyback_quote.py': 'ac3264d0fc8501e65f71e20de525822f8a2a560fefc4ac169d7cad5eb3e9d365',
    'evidence/NPC_BUYBACK_QUOTE_NATIVE_RESEARCH.md': '9d491cac456a2d60644ef964256b0da50f6a3bac450cc1ce79fc0ecdf1e6fcb7',
    'evidence/npc-buyback-quote-native.json': 'f48e9ace60d2c3aa5816f7c947cb83ff18411d17698c9b5556fed310a14e4502',
    'evidence/npc-buyback-quote-disassembly.txt': '2a6653f87817cb0be1625033cb5def97affa3e64ed993e35638589618a3a9043'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    original = json.loads((ROOT / 'evidence/npc-buyback-quote-native.json').read_text(encoding='utf8'))
    assert original['input_sha256_before'] == original['input_sha256_after']
    watched = dict(original['input_sha256_before'])
    watched.update(FILES)

    def verify():
        for name, digest in watched.items():
            assert sha(ROOT / name) == digest, name

    verify()
    output = ROOT / 'evidence/npc-buyback-quote-parent-replay'
    output.mkdir(exist_ok=True)
    original_write = Path.write_text
    names = ('npc-buyback-quote-native.json', 'npc-buyback-quote-disassembly.txt')

    def sink(path, data, *args, **kwargs):
        assert path.parent == ROOT / 'evidence' and path.name in names, str(path)
        return original_write(output / path.name, data, *args, **kwargs)

    sys.path.insert(0, str(ROOT))
    with patch.object(Path, 'write_text', sink):
        runpy.run_path(str(ROOT / 'research_npc_buyback_quote.py'), run_name='__main__')
    verify()
    for name in names:
        assert sha(output / name) == FILES['evidence/' + name], name
    assert original['actual_case_count'] == 20
    assert [row['final_native_quote'] for row in original['quote_chains']] == [275, 7700, 300]
    assert [row['actual_published_cash_debit'] for row in original['quote_chains']] == [250, 7000, 150]
    assert sum(len(row['cash_guards']) for row in original['quote_chains']) == 12
    result = dict(independent_parent_replay=True, native_cases=20, included_cash_subchecks=12,
        four_original_artifact_sha256=FILES, watched_inputs_sha256=watched,
        all_original_source_and_native_results_identical=True, only_output_sinks_redirected=True,
        actual_captured_frame_producer_owner='NPC parent chat; upstream supplied frame was not a claimed run by the main integrator',
        current_published_debits=[250, 7000, 150], corresponding_original_final_native_quotes=[275, 7700, 300],
        quote_override_source='Original Citemsell.buyprice; 32000 uses150 per unit, equipment rows absent',
        historical_probes_replayed=0, original_server_pricing_verified=False,
        production_or_policy_changed=False, live_database_accessed=False, service_or_GUI_changed=False,
        verifier_sha256=sha(Path(__file__)),
        limitations=['Three real-frame item chains and bounded scalar precision cases',
            'Extreme signed32 values, other templates and full GUI require separate validation'])
    (ROOT / 'evidence/npc-buyback-quote-independent.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('PASS parent20 quote cases;12 cash checks included; four artifacts and real source frame preserved')


if __name__ == '__main__':
    main()
