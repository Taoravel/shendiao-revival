"""Read-only PFS source audit for 43 creation routes through AI8027/CG10001.

No generated catalog is an authority, no DB/service or gameplay is touched,
and stdout is the only output. Does not assign an enemy roster or stats.
"""
from pathlib import Path
import hashlib
import json
import sys
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inspect_client import ROOT, catalog_rows
from pfs import PfsArchive
from bxml import decode


def audit():
    archive = PfsArchive(ROOT / 'artres/config.pfs')
    tables, sources = {}, {}
    for suffix in ('role.createroleconfig', 'role.schoolinfo', 'task.cmainmissioninfo',
                   'npc.cnpcconfig', 'npc.cmonsterconfig', 'battle.cbattleaiconfig', 'gm.cbattlelist'):
        name = 'autoconfig/knight.gsp.' + suffix + '.xml'
        raw = archive.read(name)
        rows = catalog_rows(decode(raw))
        tables[suffix] = {int(r['attributes']['id']): r for r in rows}
        assert len(rows) == len(tables[suffix])
        sources[name] = dict(sha256=hashlib.sha256(raw).hexdigest(),
                             crc32=f'{zlib.crc32(raw):08x}', size=len(raw), rows=len(rows))
    tasks = tables['task.cmainmissioninfo']
    def nexts(ident):
        return tuple(map(int, tasks[ident]['lists'].get('PostMissionList', ())))
    incoming = {ident: [] for ident in tasks}
    for ident in tasks:
        for target in nexts(ident):
            incoming.setdefault(target, []).append(ident)
    allowed = {(rid, int(school)) for rid, r in tables['role.createroleconfig'].items()
               for school in r['lists']['schools']}
    assert len(allowed) == 43
    by_home = {int(r['attributes']['schoolmapid']): sid for sid, r in tables['role.schoolinfo'].items()}
    assert len(by_home) == 10
    # Select the real creation roots by their raw role-specific first edges
    # and original school home maps, not by task/movie ID arithmetic.
    roots = [q for q, r in tasks.items() if r['attributes']['MissionType'] == '50'
             and nexts(q) and all(child in tasks
                 and len(tasks[child]['lists'].get('RequestRoleIDList', ())) == 1
                 and int(tasks[child]['attributes']['ActiveInfoMapID']) in by_home
                 for child in nexts(q))]
    assert len(roots) == 10
    routes, families = [], {}
    for root in sorted(roots):
        for first in nexts(root):
            role_ids = tuple(map(int, tasks[first]['lists']['RequestRoleIDList']))
            assert len(role_ids) == 1
            rid = role_ids[0]
            school = by_home[int(tasks[first]['attributes']['ActiveInfoMapID'])]
            assert (rid, school) in allowed
            path = [root, first]
            while tasks[path[-1]]['attributes']['AIInfoAIID'] != '8027':
                successors = nexts(path[-1])
                assert len(successors) == 1 and len(path) < 100
                assert successors[0] not in path
                path.append(successors[0])
            second, teaching, first_battle = path[-1], path[-2], path[-3]
            assert tasks[first_battle]['attributes']['AIInfoAIID'] == '8001'
            assert tasks[teaching]['attributes']['MissionType'] == '10'
            assert tasks[teaching]['attributes']['ProcessBarText'] == '掌握技能'
            assert incoming[second] == [teaching]
            cg, = nexts(second)
            assert incoming[cg] == [second]
            assert tasks[cg]['attributes']['MissionType'] == '10'
            assert tasks[cg]['attributes']['ScenarioInfoAnimationID'] == '10001'
            post_cg, = nexts(cg)
            key = (school, root, first_battle, teaching, second, cg, post_cg)
            families.setdefault(key, []).append(rid)
            routes.append(dict(character_id=rid, school_id=school, path=path + [cg, post_cg]))
    assert {(r['character_id'], r['school_id']) for r in routes} == allowed
    assert len(routes) == 43 and len(families) == 10
    expected = {100190, 100290, 100390, 100490, 100590, 100690, 100790, 100890, 100990, 103290}
    assert {key[4] for key in families} == expected
    def normalized(ident):
        r = tasks[ident]
        return dict(attributes={k: v for k, v in r['attributes'].items() if k != 'id'},
                    lists={k: v for k, v in r['lists'].items() if k != 'PostMissionList'})
    common = normalized(100190)
    assert all(normalized(q) == common for q in expected)
    assert common['lists']['DisPlayNPCID'] == ['10910', '10911', '10912']
    ai8027 = {q for q, r in tasks.items() if r['attributes'].get('AIInfoAIID') == '8027'}
    assert ai8027 - expected == {101004}
    monsters = [r for r in tables['npc.cmonsterconfig'].values() if r['attributes'].get('name') == '梦魇邪兽']
    assert {int(r['attributes']['id']) for r in monsters} == {29061, 29062, 29105, 29113, 29130}
    assert all(not r['lists'] for r in monsters)
    assert not any('8027' in json.dumps(r, ensure_ascii=False) for r in tables['battle.cbattleaiconfig'].values())
    assert tables['gm.cbattlelist'][8027]['attributes'] == {'id': '8027'}
    assert not tables['gm.cbattlelist'][8027]['lists']
    movie = archive.read('movie/10001.txt')
    sources['movie/10001.txt'] = dict(sha256=hashlib.sha256(movie).hexdigest(),
                                     crc32=f'{zlib.crc32(movie):08x}', size=len(movie))
    return dict(sources=sources, route_count=len(routes), routes=routes,
                families=[dict(school=k[0], root=k[1], characters=sorted(ids), first_battle=k[2],
                               teaching=k[3], second_battle=k[4], cg=k[5], cg_successor=k[6])
                          for k, ids in sorted(families.items())],
                common_second_battle=common,
                excluded_legacy=dict(task=101004, incoming=incoming[101004], successors=nexts(101004)),
                npcs=[tables['npc.cnpcconfig'][q] for q in (10908, 10910, 10911, 10912, 10084)],
                same_name_monsters=monsters,
                model6070_monster_count=sum(r['attributes'].get('modelID') == '6070'
                                            for r in tables['npc.cmonsterconfig'].values()),
                gm_battle_8027=tables['gm.cbattlelist'][8027],
                enemy_roster_verified=False, enemy_stats_verified=False,
                runtime_changed=False, live_db_accessed=False)


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
