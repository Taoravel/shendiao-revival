"""Audit resource-backed travel graph; this is not live-map acceptance."""
from collections import deque
import json
from inspect_client import OUT, write_json
from world_catalog import maps, valid_position


def main():
    catalog = maps()
    bad, edges, total, valid = [], set(), 0, 0
    for map_id, row in catalog.items():
        for cell, dest in row['portals'].items():
            total += 1
            if valid_position((map_id, cell[0]*16, cell[1]*16)) and valid_position(dest):
                valid += 1
                edges.add((map_id, dest[0]))
            else:
                bad.append({'map': map_id, 'cell': cell, 'destination': dest})
    seen, queue = {1007}, deque([1007])
    while queue:
        current = queue.popleft()
        for source, target in edges:
            if source == current and target not in seen:
                seen.add(target); queue.append(target)
    result = {'configured_maps': len(catalog),
              'resource_available_maps': sum(row['available'] for row in catalog.values()),
              'unique_portal_cells': total, 'valid_portal_cells': valid,
              'directed_map_links': len(edges), 'reachable_from_linan': len(seen),
              'reachable_map_ids': sorted(seen), 'unavailable_or_out_of_bounds': bad,
              'live_travel_verified': False}
    write_json(OUT/'evidence/world-travel-audit.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('reachable_map_ids', 'unavailable_or_out_of_bounds')}))


if __name__ == '__main__': main()
