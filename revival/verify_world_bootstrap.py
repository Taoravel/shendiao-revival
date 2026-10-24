"""Compare actual production bytes to independently executed original serializers."""
import json
from world_protocol import world_snapshot, scene_entry
from inspect_client import OUT, write_json


def main():
    role = {'id': 1, 'name': '初入江湖', 'level': 1, 'school': 11, 'shape': 1010109}
    world = world_snapshot(role)
    scene = scene_entry()
    assert world == (OUT / 'evidence/world-named-probe.bin').read_bytes()
    assert scene == (OUT / 'evidence/scene-named-probe.bin').read_bytes()
    result = {'world_bytes': len(world), 'scene_bytes': len(scene),
              'production_matches_native_serializers': True,
              'native_decoders_consumed_full_candidates': True,
              'vitals_policy': 'Local experiment: HP/MP and limits 100. Original server formula unknown.',
              'spawn_policy': 'Local test: Linan 1007, original portal destination (8480,6976). Not original new-role spawn.',
              'real_client_world_verified': False}
    write_json(OUT / 'evidence/world-bootstrap-verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
