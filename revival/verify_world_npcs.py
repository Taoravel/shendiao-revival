"""Validate a real Linan NPC against instance/epoch/version/distance scope."""
from dataclasses import replace
import struct
from unittest.mock import patch
from world_catalog import maps
from world_owner import MapAddress, Location
from world_npcs import load_placements, load_npc_definitions, NpcScene
from world_entity_protocol import ADD_USER_SCREEN


def main():
    address = MapAddress(1007, 1, 0)
    placements = load_placements()[1007]
    npc = next(p for p in placements if p.npc_id == 10000)
    definitions = load_npc_definitions()
    assert (npc.x, npc.y) == (1680, 5311)
    scene = NpcScene(address, placements, maps(), interaction_radius=32, binding_capacity=1)
    packets = scene.spawn(((0x12345678, npc.placement_id),), definitions, batch_size=64)
    assert len(packets) == 1 and packets[0][0] == ADD_USER_SCREEN
    location = Location(1, 'login-epoch-a', address, 7, npc.x, npc.y)
    body = struct.pack('>q', 0x12345678)
    with patch('builtins.open', side_effect=AssertionError('NPC hot-path file read')), \
         patch('io.open', side_effect=AssertionError('NPC hot-path file read')):
        event = scene.interact(body, location, location, request_id='visit-1', deadline_ms=10, now_ms=1)
        assert event.npc_id == 10000 and event.kind == 'npc_interacted'
        assert scene.activation(batch_size=64)
        for wrong in (replace(location, x=1), replace(location, login_epoch='old'),
                      replace(location, version=6), replace(location, state='loading'),
                      replace(location, address=MapAddress(1007, 2, 0))):
            try:
                scene.interact(body, location, wrong, request_id='bad', deadline_ms=10, now_ms=1)
            except ValueError:
                pass
            else:
                raise AssertionError('Unscoped NPC event accepted')
        far = replace(location, x=npc.x+33)
        try:
            scene.interact(body, far, far, request_id='far', deadline_ms=10, now_ms=1)
        except ValueError:
            pass
        else:
            raise AssertionError('Distant NPC event accepted')
    print('PASS Linan NPC 10000: binding, scope, distance, activation; no dialogue completion inferred')


if __name__ == '__main__': main()
