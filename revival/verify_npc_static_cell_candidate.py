"""Captured original visits cross the static NPC Interface used by this release.

Dynamic NpcLifecycle is deliberately not activated or imported by this candidate.
Its independently reviewed domain checks remain a separate delivery.
"""
from dataclasses import replace
import json
import struct
from inspect_client import OUT, write_json
from npc_interaction import load_npc_interaction_rules
from world_catalog import maps, maze_grids
from world_collision import maze_clear
from world_npcs import NpcScene, load_placements, load_npc_definitions
from world_owner import MapAddress, Location


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Static NPC accepted foreign or expired interaction authority')


def main():
    placements, definitions, catalog = load_placements(), load_npc_definitions(), maps()
    rules = load_npc_interaction_rules(placements, definitions)
    original = json.loads((OUT/'evidence/npc-client-visit-root-red.json').read_text(encoding='utf-8'))
    audit = json.loads((OUT/'evidence/npc-interaction-compatibility-audit.json').read_text(encoding='utf-8'))
    npc = next(p for p in placements[1006] if (p.placement_id, p.npc_id) == (13, 10498))
    body = bytes.fromhex(original['captured_body_hex'])
    key, = struct.unpack('>q', body)
    assert original['original_visit_sent'] and original['role_logical'] == [1668, 1032]
    assert maze_clear(maze_grids()[1006], 1668, 1032, mask=1)
    address = MapAddress(1006, 1006, 0)
    scene = NpcScene(address, placements[1006], catalog, interaction_radius=32,
                     binding_capacity=64, interaction_rules=rules)
    scene.spawn(((key, npc.placement_id),), definitions, batch_size=64)
    point = Location(1, 'static-proof', address, 1, 1668, 1032)
    assert scene.interact(body, point, point, request_id='native62', deadline_ms=10, now_ms=1)
    for case in audit['ordinary_cases']:
        target_npc = next(p for p in placements[case['map_id']]
                          if (p.placement_id, p.npc_id) == (case['placement_id'], case['npc_id']))
        assert [target_npc.x, target_npc.y] == case['npc_logical']
        assert maze_clear(maze_grids()[target_npc.map_id], *case['actor_logical'], mask=1)
        scope = MapAddress(target_npc.map_id, target_npc.map_id, 0)
        ordinary = NpcScene(scope, (target_npc,), catalog, binding_capacity=64, interaction_rules=rules)
        ordinary.spawn(((case['key'], target_npc.placement_id),), definitions, batch_size=64)
        location = Location(1, 'static-proof', scope, 1, *case['actor_logical'])
        assert ordinary.interact(struct.pack('>q', case['key']), location, location,
            request_id='native64', deadline_ms=10, now_ms=1).npc_id == target_npc.npc_id
    controlled = replace(npc, x=1615, y=1600)
    assert rules.allows(controlled, (1006, 1807, 1600))
    assert not rules.allows(controlled, (1006, 1808, 1600))
    controlled = replace(npc, x=1600, y=1600)
    assert rules.allows(controlled, (1006, 1807, 1679))
    assert rules.allows(controlled, (1006, 1760, 1728))
    assert not rules.allows(controlled, (1006, 1792, 1680))
    for changed in (replace(point, version=2), replace(point, login_epoch='old'),
            replace(point, address=MapAddress(1006, 999, 0)), replace(point, state='loading'),
            replace(point, address=MapAddress(1006, 1006, 1))):
        refused(lambda: scene.interact(body, point, changed, request_id='stale', deadline_ms=10, now_ms=1))
    far = replace(point, x=npc.x+13*16, y=npc.y)
    refused(lambda: scene.interact(body, far, far, request_id='far', deadline_ms=10, now_ms=1))
    refused(lambda: scene.interact(body, point, point, request_id='expired', deadline_ms=1, now_ms=1))
    refused(lambda: rules.radius_for(1006, 13, 10498))
    report = dict(passed=['captured native62 visit passes actual static NpcScene at original-clear point',
        'ordinary captured64 visits retain original placements, entity keys and real static admission',
        'literal cell boundaries and non-circle examples agree with approved original predicate',
        'full address, lease, version, active state and deadline reject stale/foreign requests'],
        policy=rules.revision, dynamic_npc_lifecycle_activated=False,
        actual_peer_natural_approach_verified_separately=True,
        live_server_changed=False, native_gui_verified=False)
    write_json(OUT/'evidence/npc-static-cell-candidate-verification.json', report)
    print(report)


if __name__ == '__main__':
    main()
