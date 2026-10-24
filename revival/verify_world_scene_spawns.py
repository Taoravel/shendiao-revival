"""Batch every valid original placement through the native NPC model codec."""
from collections import Counter
from inspect_client import OUT, write_json
from world_catalog import maps, valid_position
from world_npcs import load_placements, load_npc_definitions, NpcScene
from world_owner import MapAddress


def main():
    catalog, placements, definitions = maps(), load_placements(), load_npc_definitions()
    rejected, duplicates, spawned, packets = [], 0, 0, 0
    for mid, rows in placements.items():
        valid = []
        for p in rows:
            if not valid_position((mid, p.x, p.y), catalog):
                rejected.append(dict(map=mid, npc=p.npc_id, placement=p.placement_id, x=p.x, y=p.y))
            else:
                valid.append(p)
        if not valid:
            continue
        scene = NpcScene(MapAddress(mid, mid, 0), rows, catalog,
                         interaction_radius=1, binding_capacity=len(valid))
        # Radius is unused in this encoding audit and not a gameplay default.
        output = scene.spawn(tuple((i+1, p.placement_id) for i, p in enumerate(valid)),
                             definitions, batch_size=64)
        spawned += len(valid); packets += len(output)
        duplicates += sum(n-1 for n in Counter(p.npc_id for p in valid).values())
    result = dict(encoded_placements=spawned, duplicate_id_placements_preserved=duplicates,
                  packet_batches=packets, rejected=rejected,
                  original_total=sum(map(len, placements.values())),
                  real_client_display_verified=False)
    write_json(OUT/'evidence/world-scene-spawn-verification.json', result)
    print({k: (len(v) if k == 'rejected' else v) for k, v in result.items()})


if __name__ == '__main__': main()
