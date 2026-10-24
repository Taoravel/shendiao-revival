"""Batch native model encoding for all resolvable original monster templates."""
from dataclasses import replace
from inspect_client import OUT, write_json
from world_catalog import maps
from world_owner import MapAddress, Location
from world_npcs import load_npc_definitions
from world_monsters import MonsterScene, load_monster_templates, load_shape_ids


def main():
    templates, shapes, npcs, catalog = load_monster_templates(), load_shape_ids(), load_npc_definitions(), maps()
    address = MapAddress(1014, 1, 0)
    scene = MonsterScene(address, catalog, templates, npcs, shapes, capacity=1)
    missing, encoded = [], 0
    for tid, template in templates.items():
        if template.shape_id not in shapes:
            missing.append(dict(template=tid, shape=template.shape_id)); continue
        # Carrier 10000 is a codec test fixture, not a production monster policy.
        entity, packets = scene.spawn(tid, tid, 896, 3776, carrier_npc_id=10000)
        assert packets and entity.template_id == tid
        scene.remove(entity); encoded += 1
    entity, _ = scene.spawn(1, 20001, 896, 3776, carrier_npc_id=10000)
    role = Location(1, 'monster-check', address, 1, 896, 3776)
    reserved = scene.encounter(entity, role, interaction_radius=1, battle_id='battle-check')
    assert reserved.state == 'reserved'
    try: scene.encounter(entity, role, interaction_radius=1, battle_id='double')
    except ValueError: pass
    else: raise AssertionError('Monster claimed twice')
    write_json(OUT/'evidence/world-monster-verification.json', dict(
        template_count=len(templates), encoded_templates=encoded, missing_original_shapes=missing,
        native_shape_override_strategy=True, unique_encounter_reservation=True,
        live_client_verified=False, original_spawn_stats_drop_rules_verified=False))
    print(dict(templates=len(templates), encoded=encoded, missing_shapes=missing))


if __name__ == '__main__': main()
