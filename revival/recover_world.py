"""Join shipped map metadata, NPC placements and portal cells without guessing units."""
from pathlib import Path
import json
from collections import Counter
from pfs import PfsArchive
from bxml import decode
from inspect_client import ROOT, OUT, write_json


def catalog(name):
    return json.loads((OUT / 'catalogs' / f'knight.gsp.{name}.json').read_text(encoding='utf-8'))


def main():
    archive = PfsArchive(ROOT / 'artres/map.pfs')
    paths = {name.casefold(): name for name in archive.entries}
    if len(paths) != len(archive.entries):
        raise ValueError('Ambiguous case-insensitive map archive paths')
    maps = catalog('map.cmapconfig')
    npc_defs = {r['attributes']['id']: r for r in catalog('npc.cnpcconfig')}
    known_maps = {r['attributes']['id'] for r in maps}
    result = []
    summary = Counter()
    issues = []
    for row in maps:
        attrs = row['attributes']
        directory = attrs['resdir']
        item = {'attributes': attrs, 'npc_placements': [], 'portal_cells': [], 'minimap': None}
        summary['maps'] += 1
        if (directory + '/map.rmp').casefold() not in paths:
            issues.append({'map': attrs['id'], 'issue': 'missing map.rmp', 'resdir': directory})
        else:
            summary['maps_with_rmp'] += 1
        for file, key in [('npc.xml', 'npc_placements'), ('goto.xml', 'portal_cells')]:
            name = paths.get((directory + '/' + file).casefold())
            if name is None:
                continue
            item[key] = [dict(child.attrib) for child in decode(archive.read(name))]
            summary[key] += len(item[key])
        for npc in item['npc_placements']:
            definition = npc_defs.get(npc.get('id'))
            if definition:
                npc['definition_name'] = definition['attributes'].get('name', '')
                summary['npc_placements_with_definition'] += 1
            else:
                issues.append({'map': attrs['id'], 'issue': 'NPC definition not found', 'id': npc.get('id')})
        for portal in item['portal_cells']:
            if portal.get('destmap') not in known_maps:
                issues.append({'map': attrs['id'], 'issue': 'destination map not found', 'destination': portal.get('destmap')})
        for suffix in ('jpg', 'png', 'tga'):
            name = paths.get((directory + '/mini_map.' + suffix).casefold())
            if name is not None:
                target = OUT / 'extracted/maps' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
                item['minimap'] = str(target.relative_to(OUT)).replace('\\', '/')
                summary['maps_with_minimap'] += 1
                break
        result.append(item)
    write_json(OUT / 'catalogs/world.json', result)
    write_json(OUT / 'evidence/world-recovery.json', {'summary': dict(summary), 'issues': issues,
        'coordinate_units': 'Original literals preserved. NPC posx/posy and portal posx/posy are not assumed to use the same units.',
        'runtime_verified': False})
    print(json.dumps({'summary': dict(summary), 'issues': len(issues)}))


if __name__ == '__main__':
    main()
