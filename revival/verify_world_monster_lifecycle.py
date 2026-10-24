"""Instance-owned monster lifecycle checks through MonsterScene Interface."""
from world_catalog import maps
from world_owner import MapAddress, Location
from world_npcs import load_npc_definitions
from world_monsters import MonsterScene, load_monster_templates, load_shape_ids


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Expected stale/foreign monster action to be refused')


def main():
    address = MapAddress(1014, 901, 0)
    scene = MonsterScene(address, maps(), load_monster_templates(),
                         load_npc_definitions(), load_shape_ids(), capacity=2)
    old, _ = scene.spawn(1, 20001, 896, 3776, carrier_npc_id=10000)
    scene.remove(old)
    current, _ = scene.spawn(1, 20001, 896, 3776, carrier_npc_id=10000)
    assert current.revision > old.revision, 'Reused entity key reset its generation'
    refused(lambda: scene.remove(old))
    role = Location(1, 'monster-lifecycle', address, 1, 896, 3776)
    refused(lambda: scene.encounter(old, role, interaction_radius=1, battle_id='old'))
    assert scene.snapshot(1) == current
    reserved = scene.encounter(current, role, interaction_radius=1, battle_id='battle-a')
    assert reserved.state == 'reserved', 'Battle reservation was reported as started'
    restored = scene.cancel_encounter(reserved)
    assert restored.state == 'visible' and restored.revision > reserved.revision
    assert not restored.battle_id and not restored.claimant_role_id and restored.claimant_epoch == ''
    refused(lambda: scene.cancel_encounter(reserved))
    refused(lambda: scene.encounter(current, role, interaction_radius=1, battle_id='stale'))
    assert scene.snapshot(1) == restored
    reserved = scene.encounter(restored, role, interaction_radius=1, battle_id='battle-b')
    active = scene.confirm_encounter(reserved)
    assert active.state == 'in_battle' and active.battle_id == 'battle-b'
    assert active.revision > reserved.revision
    refused(lambda: scene.remove(active))
    refused(lambda: scene.cancel_encounter(active))
    refused(lambda: scene.cancel_encounter(reserved))
    resumed, messages = scene.end_encounter(active, despawn=False)
    assert resumed.state == 'visible' and resumed.revision > active.revision and messages == ()
    refused(lambda: scene.end_encounter(active, despawn=True))
    reserved = scene.encounter(resumed, role, interaction_radius=1, battle_id='battle-c')
    refused(lambda: scene.end_encounter(reserved, despawn=True))
    active = scene.confirm_encounter(reserved)
    ended, messages = scene.end_encounter(active, despawn=True)
    assert ended is None and scene.snapshot(1) is None
    assert messages == ((0xc0fa6, b'\0\1'+b'\0'*7+b'\1'),)
    replacement, _ = scene.spawn(1, 20001, 896, 3776, carrier_npc_id=10000)
    refused(lambda: scene.end_encounter(active, despawn=True))
    assert scene.snapshot(1) == replacement
    reloaded = MonsterScene(address, maps(), load_monster_templates(),
                            load_npc_definitions(), load_shape_ids(), capacity=2)
    reloaded_entity, _ = reloaded.spawn(1, 20001, 896, 3776, carrier_npc_id=10000)
    refused(lambda: reloaded.remove(old))
    assert reloaded.snapshot(1) == reloaded_entity
    print('PASS key reuse, owner replacement, reservation and terminal battle disposition')


if __name__ == '__main__':
    main()
