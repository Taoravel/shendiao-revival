"""Re-read original configuration, preserving evidence for wild encounter pools."""
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from inspect_client import ROOT, OUT, catalog_rows, write_json
from pfs import PfsArchive
from bxml import decode
from world_catalog import maps


def main():
    archive = PfsArchive(ROOT/'artres/config.pfs')
    tables, audit = {}, []
    for name in ('map.cmapconfig', 'npc.cmonsterconfig', 'pet.cpetattr', 'battle.cbattlebackground',
                 'role.cresmoneyconfig', 'item.citemattr', 'npc.cnpcconfig', 'servant.bookanswerconfig'):
        path = 'autoconfig/knight.gsp.'+name+'.xml'
        data = archive.read(path)
        rows = catalog_rows(decode(data))
        cached = json.loads((OUT/'catalogs'/('knight.gsp.'+name+'.json')).read_text(encoding='utf-8'))
        # Catalog was pretty-printed before parsing: ignore formatting-only
        # text/tail whitespace while comparing attributes, lists and child data.
        def normalized(value):
            if isinstance(value, dict):
                return {k: normalized(v) for k, v in value.items()}
            if isinstance(value, list): return [normalized(v) for v in value]
            if isinstance(value, str) and not value.strip(): return None
            return value
        if normalized(rows) != normalized(cached):
            raise ValueError('Original configuration differs: '+name)
        tables[name] = rows
        audit.append(dict(path=path, sha256=hashlib.sha256(data).hexdigest(), rows=len(rows), crc_verified=True))
    definitions = defaultdict(list)
    for row in tables['npc.cmonsterconfig']:
        a = row['attributes']
        if a.get('title') == '练功区' and a.get('becatch') == '1':
            definitions[a['name'], int(a['modelID'])].append(a)
    pools, issues = defaultdict(dict), []
    for row in tables['pet.cpetattr']:
        pet = row['attributes']
        candidates = definitions.get((pet['name'], int(pet['modelid'])), ())
        if len(candidates) != 1:
            issues.append(dict(pet_id=int(pet['id']), reason='no_unique_training_monster', candidates=len(candidates)))
            continue
        # Description links prove display distribution, not server spawn weights.
        description = ET.fromstring('<root>'+pet.get('desciption', '')+'</root>')
        for link in description.iter('G'):
            if link.get('m', '').isdigit():
                pools[int(link.get('m'))][int(candidates[0]['id'])] = dict(
                    template_id=int(candidates[0]['id']), pet_id=int(pet['id']),
                    name=pet['name'], shape_id=int(pet['modelid']),
                    catchable=candidates[0].get('becatch') == '1',
                    source_status='client_verified')
    # Scene-specific ordinary templates are stronger than generic display
    # joins and include uncapturable enemies absent from the pet encyclopedia.
    scene_pools = defaultdict(dict)
    for row in tables['npc.cmonsterconfig']:
        a = row['attributes']; title = a.get('title', '')
        if title.endswith(':普通'):
            scene_pools[title[:-3]][int(a['id'])] = dict(template_id=int(a['id']),
                name=a['name'], shape_id=int(a['modelID']), catchable=a.get('becatch') == '1',
                source_status='client_verified', source_field='cmonsterconfig.title')
    result = []
    catalog = maps()
    for row in tables['map.cmapconfig']:
        a = row['attributes']; mid = int(a['id'])
        monsters = scene_pools.get(a['mapName']) or pools.get(mid)
        if a.get('safemap') != '0' or not monsters or not catalog[mid]['available']:
            continue
        level = int(a.get('LevelLimitMin', 0))
        if level < 1:
            issues.append(dict(map_id=mid, reason='no_positive_scene_level')); continue
        background = int(a['battleground'])
        if background not in {int(r['attributes']['id']) for r in tables['battle.cbattlebackground']}:
            raise ValueError('Unknown original battle background')
        result.append(dict(map_id=mid, name=a['mapName'], level=level, background=background,
            encounter_mode='visible' if 1200<=mid<=1206 else 'hidden',
            encounter_mode_source='bookanswerconfig9603 + floor-specific cnpcconfig npctype6' if 1200<=mid<=1206 else 'local_recovery_policy',
            monsters=sorted(monsters.values(), key=lambda m:m['template_id']),
            distribution_source_status='client_verified',
            activation_source_status='designed', area_scope='whole_map_local_recovery'))
    write_json(OUT/'catalogs/wild-encounters.json', dict(revision='wild-encounters-v1', maps=result))
    write_json(OUT/'evidence/wild-encounters-source-audit.json', dict(original_tables=audit,
        maps=len(result), placements=sum(len(m['monsters']) for m in result), issues=issues,
        original_server_spawn_weights_verified=False, monster_dat_semantics_used=False))
    print(dict(maps=len(result), placements=sum(len(m['monsters']) for m in result), issues=len(issues)))


if __name__ == '__main__': main()
