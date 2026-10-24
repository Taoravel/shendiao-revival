"""Original portal/maze cross-check; observations never rewrite portal policy."""
from collections import Counter
from inspect_client import OUT, write_json
from world_catalog import maps, maze_grids, valid_position
from world_collision import maze_clear


def main():
    catalog, grids = maps(), maze_grids()
    shortfalls = [mid for mid, row in catalog.items() if mid in grids and (
        grids[mid].width*16 < row['width'] or grids[mid].height*16 < row['height'])]
    assert not shortfalls, shortfalls
    counts, unexpected, unique = Counter(), [], {'source': set(), 'target': set()}
    for map_id, row in catalog.items():
        for cell, target in row['portals'].items():
            source = (map_id, cell[0]*16, cell[1]*16)
            if not valid_position(source, catalog) or not valid_position(target, catalog):
                continue
            for side, position in (('source', source), ('target', target)):
                mid, x, y = position
                if mid not in grids:
                    raise ValueError('Resource-backed portal lacks a maze')
                grid = grids[mid]
                state0 = maze_clear(grid, x, y, mask=1)
                state_nonzero = maze_clear(grid, x, y, mask=8)
                counts[side+'_total'] += 1
                counts[side+'_state0_clear'] += int(state0)
                counts[side+'_state_nonzero_clear'] += int(state_nonzero)
                if not state0:
                    unique[side].add(position)
                    unexpected.append(dict(portal_source_cell=(map_id, *cell), side=side,
                        checked_position=position, raw_maze=grid.cell(x//16, y//16),
                        state0_clear=state0, state_nonzero_clear=state_nonzero))
    result = dict(available_map_grids=len(grids), coverage_shortfalls=shortfalls,
        portal_observations=dict(counts), state0_blocked_unique_positions={
            side: len(points) for side, points in unique.items()}, state0_blocked_rows=unexpected,
        policy_applied=False, live_server_changed=False,
        limits=['Mask is selected from authoritative native character state, not map ID alone',
                'Portal landing adjustment and special movement transitions are not yet verified',
                'A blocked state0 observation does not establish a corrupt original portal'])
    write_json(OUT/'evidence/world-collision-catalog-audit.json', result)
    print({k: v for k, v in result.items() if k not in ('state0_blocked_rows', 'limits')})


if __name__ == '__main__':
    main()
