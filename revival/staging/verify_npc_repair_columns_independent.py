"""Replay original column research without overwriting its four evidence files."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    'research_npc_repair_columns.py': 'c73f3f20ad1be46130790e3ca8917f1ebfeba64111813eb15d0e839657b7aed3',
    'evidence/NPC_REPAIR_COLUMN_RESEARCH.md': 'd6d40c1bbcc1d4434ceee02e561b9bee5fef49fef53704261a3da7dd64546133',
    'evidence/npc-repair-column-native.json': 'fa3b4aa032f9f9dd671189eb5d2c153ff480e4fc4f1d93ea6496ea6df0572b27',
    'evidence/npc-repair-column-disassembly.txt': '085dcc7c6a2333bef076509d7b4e0c3d09b0e15ffea77af8e8122353c2559c67'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    original = json.loads((ROOT / 'evidence/npc-repair-column-native.json').read_text(encoding='utf8'))
    watched = dict(original['watched_sha256'])
    watched.update(FILES)
    for name in ('inspect_client.py', 'evidence/native-image.bin',
            'catalogs/knight.gsp.item.citemattr.json', 'catalogs/knight.gsp.npc.cnpcserverconfig.json'):
        watched[name] = sha(ROOT / name)
    archives = {name: sha(ROOT.parent / 'artres' / name) for name in ('config.pfs', 'ui.pfs')}

    def verify():
        for name, digest in watched.items():
            assert sha(ROOT / name) == digest, name
        for name, digest in archives.items():
            assert sha(ROOT.parent / 'artres' / name) == digest, name

    verify()
    output = ROOT / 'evidence/npc-repair-column-parent-replay'
    output.mkdir(exist_ok=True)
    original_write = Path.write_text
    names = ('npc-repair-column-native.json', 'npc-repair-column-disassembly.txt')

    def sink(path, data, *args, **kwargs):
        assert path.parent == ROOT / 'evidence' and path.name in names, str(path)
        return original_write(output / path.name, data, *args, **kwargs)

    sys.path.insert(0, str(ROOT))
    with patch.object(Path, 'write_text', sink):
        runpy.run_path(str(ROOT / 'research_npc_repair_columns.py'), run_name='__main__')
    verify()
    for name in names:
        assert sha(output / name) == FILES['evidence/' + name], name
    assert original['new_native_case_count'] == 27
    assert original['original_bag_decoder_cases'] == 12
    assert original['native_repair_chain_cases'] == 24
    assert original['native_selected_click_and_send_cases'] == 8
    assert original['native_shop_open_and_query']['actual_query_fields'][0] == 4
    assert {row['column'] for row in original['native_equipment_slot_drag_cases']} == {3}
    result = dict(independent_parent_replay=True, native_combination_cases=27,
        original_bag_decoders_within_combinations=12, selected_native_clicks_within_combinations=8,
        four_evidence_sha256=FILES, all_original_inputs_unchanged=True,
        only_output_sinks_redirected=True, watched_sha256=watched,
        original_archive_sha256=archives, verifier_sha256=sha(Path(__file__)),
        historical_cases_replayed=0, production_or_policy_changed=False,
        live_database_accessed=False, service_or_gui_operated=False,
        compatibility_alias_or_migration_implemented=False,
        limits=['Controlled single-item map copy and missing click-config dependency',
            'Complete CEGUI, saved-asset qualification and full shop lifecycle not executed'])
    (ROOT / 'evidence/npc-repair-column-independent.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('PASS parent27 native combinations; four exact artifacts and historical inputs preserved')


if __name__ == '__main__':
    main()
