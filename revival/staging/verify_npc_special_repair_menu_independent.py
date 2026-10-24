"""Replay stopped native research with separate output sinks and fixed evidence."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    'research_npc_special_repair_menu.py': 'b82d31d73ac85383e8a1f730048ec597012fa4053222754acdb5e622b6fc78a9',
    'evidence/NPC_SPECIAL_REPAIR_MENU_RESEARCH.md': '3a49bb3b26c7c3c0a366617367e80c869e7dc70c38502596abc5ea7d03e35b6f',
    'evidence/npc-special-repair-menu-native.json': 'c252c9b5b9c15efaf685705500b38d2b228f58da80ec98d30f23ebcffb13b9df',
    'evidence/npc-special-repair-menu-disassembly.txt': 'fcccf19772a38bca3a130cdd74e8e0542baff2ebc7fe60d7ee6d1ffaf78fb25b'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    original = json.loads((ROOT / 'evidence/npc-special-repair-menu-native.json').read_text(encoding='utf8'))
    for name, digest in FILES.items():
        assert sha(ROOT / name) == digest, name
    watched = dict(original['watched_sha256'])
    # A separate diagnostic was created after the researcher took its glob.
    # Let the unmodified script discover it normally; only report sinks differ.
    added = sorted(set(p.name for p in ROOT.glob('npc_*.py')) - set(watched))
    assert added == ['npc_growth_first_battle_frozen_probe_20261024.py'], added
    watched.update({name: sha(ROOT / name) for name in added})
    for name in ('research_npc_submenu.py', 'verify_social_native.py', 'native_inspect.py',
            'inspect_client.py', 'pfs.py', 'bxml.py', 'evidence/native-image.bin'):
        watched[name] = sha(ROOT / name)
    for name, source in original['sources'].items():
        watched['catalogs/' + Path(name).stem + '.json'] = source['cache_sha256']
    archive = ROOT.parent / 'artres/config.pfs'
    archive_sha = sha(archive)

    def verify():
        for name, digest in watched.items():
            assert sha(ROOT / name) == digest, name
        assert sha(archive) == archive_sha
        for name, digest in FILES.items():
            assert sha(ROOT / name) == digest, name

    verify()
    output = ROOT / 'evidence/npc-special-repair-menu-parent-replay'
    output.mkdir(exist_ok=True)
    original_write = Path.write_text
    names = ('npc-special-repair-menu-native.json', 'npc-special-repair-menu-disassembly.txt')

    def sink(path, data, *args, **kwargs):
        assert path.parent == ROOT / 'evidence' and path.name in names, str(path)
        return original_write(output / path.name, data, *args, **kwargs)

    sys.path.insert(0, str(ROOT))
    with patch.object(Path, 'write_text', sink):
        runpy.run_path(str(ROOT / 'research_npc_special_repair_menu.py'), run_name='__main__')
    verify()
    replay = json.loads((output / names[0]).read_text(encoding='utf8'))
    expected_watched = dict(original['watched_sha256'])
    expected_watched.update({name: watched[name] for name in added})
    assert replay.pop('watched_sha256') == expected_watched
    unchanged = dict(original)
    unchanged.pop('watched_sha256')
    assert replay == unchanged, 'Native/source result changed beyond the declared additional watch'
    assert sha(output / names[1]) == FILES['evidence/' + names[1]]
    assert replay['new_native_case_count'] == 112 and len(replay['sources']) == 51
    result = dict(independent_parent_replay=True, new_native_cases=112, original_tables=51,
        original_evidence_sha256=FILES, all_native_and_source_results_equal=True,
        additional_discovered_watch={name: watched[name] for name in added},
        only_report_sinks_redirected=True, additional_inputs_sha256=watched,
        original_config_pfs_sha256=archive_sha, historical_cases_replayed=0,
        production_or_policy_changed=False, special_service_activated=False,
        live_database_accessed=False, service_or_gui_operated=False,
        limit='Controlled lookup sentinel and bounded item predicates; no real special-asset eligibility claim')
    (ROOT / 'evidence/npc-special-repair-menu-independent.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('PASS independent112 replay; four original artifacts unchanged; explicit extra diagnostic watch')


if __name__ == '__main__':
    main()
