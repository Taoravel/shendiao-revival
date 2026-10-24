"""Independently check the rectangle audit by enumerating every integer pixel.

This validates the audit's disk geometry, not native automatic approach or
navigation from an arbitrary source. No policy is chosen by this verifier.
"""
import hashlib
import json
import time
from inspect_client import OUT, write_json, sha256
from world_catalog import maps, maze_grids
from world_collision import maze_clear


def main():
    path = OUT/'evidence/world-npc-approach-audit.json'
    payload = path.read_bytes()
    report = json.loads(payload)
    required = {'catalogs/scene-content.json', 'evidence/world-recovery.json',
                '../artres/map.pfs', '../artres/config.pfs'}
    assert required <= report['inputs_sha256'].keys(), 'Audit omitted bounds/availability/original archive input'
    before = {name: sha256(OUT/name) if (OUT/name).is_file() else None
              for name in report['inputs_sha256']}
    assert before == report['inputs_sha256'], 'Run the audit for this input snapshot first'
    grids, catalog = maze_grids(), maps()
    started, pixels, verified, alternate = time.monotonic(), 0, 0, 0
    for row in report['placements']:
        if row['status'] not in ('legal_point_and_current_domain_visit',
                                 'no_legal_integer_point_in_interaction_disk'):
            continue
        mid, x, y, radius = row['map_id'], row['x'], row['y'], row['radius']
        grid, best, best8 = grids[mid], None, None
        for py in range(max(0, y-radius), min(catalog[mid]['height'], 32768, y+radius+1)):
            for px in range(max(0, x-radius), min(catalog[mid]['width'], 32768, x+radius+1)):
                distance = (px-x)**2+(py-y)**2
                if distance > radius**2:
                    continue
                pixels += 1
                point = (distance, px, py)
                if maze_clear(grid, px, py, mask=1) and (best is None or point < best):
                    best = point
                if row['status'].startswith('no_legal') and maze_clear(grid, px, py, mask=8):
                    if best8 is None or point < best8:
                        best8 = point
        if best is None:
            assert row['status'] == 'no_legal_integer_point_in_interaction_disk', row
            predicted8 = row['diagnostic_mask8_point']
            assert (best8 is None) == (predicted8 is None), row
            if best8 is not None:
                assert best8 == (predicted8['distance_squared'], *predicted8['point']), row
                alternate += 1
        else:
            assert row['status'] == 'legal_point_and_current_domain_visit', row
            assert best == (row['distance_squared'], *row['point']), row
        verified += 1
    after = {name: sha256(OUT/name) if (OUT/name).is_file() else None for name in before}
    assert before == after and path.read_bytes() == payload, 'Audit snapshot changed during verification'
    result = dict(all_disks_match_literal_pixel_enumeration=True, placements_verified=verified,
                  integer_pixels_checked=pixels, mask1_empty_with_mask8_point=alternate,
                  source_report_sha256=hashlib.sha256(payload).hexdigest(), inputs_sha256=before,
                  verifier_sha256=hashlib.sha256((OUT/'verify_world_npc_approach_audit.py').read_bytes()).hexdigest(),
                  elapsed_seconds=round(time.monotonic()-started, 3),
                  native_gui_verified=False, alternate_character_state_authorized=False)
    write_json(OUT/'evidence/world-npc-approach-audit-independent.json', result)
    print({key: result[key] for key in ('all_disks_match_literal_pixel_enumeration', 'placements_verified',
                                      'integer_pixels_checked', 'mask1_empty_with_mask8_point', 'elapsed_seconds')})


if __name__ == '__main__':
    main()
