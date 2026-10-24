"""Read original NPC configuration and map placements into a recovery inventory.

Does not modify original archives, policy, live roles or runtime entry points.
All configuration evidence is reread with PFS CRC/length validation.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from bxml import decode
from pfs import PfsArchive
from inspect_client import ROOT, OUT, catalog_rows, write_json
from world_catalog import maps, valid_position


def main():
    archive = PfsArchive(ROOT/'artres/config.pfs')
    tables, sources, differences = {}, [], []
    for name in sorted(archive.entries):
        stem = Path(name).stem
        if not name.startswith('autoconfig/knight.gsp.npc.') or not name.endswith('.xml'):
            continue
        raw = archive.read(name)
        rows = catalog_rows(decode(raw))
        tables[stem] = rows
        saved_path = OUT/'catalogs'/f'{stem}.json'
        saved = json.loads(saved_path.read_text(encoding='utf-8')) if saved_path.exists() else []
        projection = lambda rs: [(r['attributes'], r['lists']) for r in rs]
        matches = projection(saved) == projection(rows)
        if not matches:
            differences.append(stem)
        sources.append({'archive_path':name,'rows':len(rows),'crc32':archive.entries[name].crc,
                        'sha256':hashlib.sha256(raw).hexdigest(),'existing_catalog_matches':matches})

    def table(suffix):
        return tables['knight.gsp.npc.'+suffix]

    definitions = {int(r['attributes']['id']):r for r in table('cnpcconfig')}
    services = {int(r['attributes']['id']):r for r in table('cnpcserverconfig')}
    chats = {int(r['attributes']['id']):r['attributes']['chat'] for r in table('cnpcchat')}
    world = json.loads((OUT/'catalogs/world.json').read_text(encoding='utf-8'))
    map_archive = PfsArchive(ROOT/'artres/map.pfs')
    paths = {name.casefold():name for name in map_archive.entries}
    catalog = maps()
    placements, by_npc, issues, map_sources = [], defaultdict(list), [], []
    for row in world:
        mid = int(row['attributes']['id'])
        name = paths.get((row['attributes']['resdir']+'/npc.xml').casefold())
        original = [] if name is None else [dict(c.attrib) for c in decode(map_archive.read(name))]
        projected = [{k:v for k,v in p.items() if k != 'definition_name'} for p in row['npc_placements']]
        if original != projected:
            issues.append({'map_id':mid,'issue':'world_catalog_differs_from_original'})
        map_sources.append({'map_id':mid,'archive_path':name,'placements':len(original)})
        for i, p in enumerate(original,1):
            npc_id = int(p['id'])
            reasons = []
            if npc_id not in definitions:
                reasons.append('definition_missing')
            if not valid_position((mid,int(p['posx']),int(p['posy'])),catalog):
                reasons.append('unavailable_map_or_outside_bounds')
            record = {'map_id':mid,'placement_id':i,'npc_id':npc_id,'raw':p,
                      'entity_key':(mid<<32)|i,'spawn_candidate':not reasons,'blocked_reasons':reasons,
                      'source_status':'client_verified','runtime_status':'candidate_not_gui_verified'}
            placements.append(record)
            by_npc[npc_id].append((mid,i))
    npc_records = []
    for npc_id, row in definitions.items():
        chat_ids = tuple(int(i) for i in row['lists'].get('chitchatidlist',()))
        npc_records.append({'npc_id':npc_id,'attributes':row['attributes'],'lists':row['lists'],
            'placements':by_npc[npc_id],
            'chitchats':[{'id':i,'text':chats.get(i)} for i in chat_ids],
            'missing_chat_ids':sorted({i for i in chat_ids if i not in chats}),
            'service_binding_status':'not_assessed_by_archive_audit',
            'source_status':'client_verified'})
    service_records = []
    for sid, row in services.items():
        children = tuple(int(i) for i in row['lists'].get('childservice',()))
        service_records.append({'service_id':sid,'attributes':row['attributes'],'childservice':children,
            'missing_children':[i for i in children if i not in services],
            'binding_status':'not_assessed_by_archive_audit','source_status':'client_verified'})
    # Scene movie NPCs are a different identity space; never spawn them as static NPCs.
    scene_bases = {int(r['attributes']['id']) for r in table('cscenenpcbase')}
    scene_placements = [{'attributes':r['attributes'],
        'base_found':int(r['attributes']['baseid']) in scene_bases,
        'runtime_status':'scene_lifecycle_not_connected'} for r in table('cscenenpcconfig')]
    result = {'schema':1,'source_status':'client_verified','sources':sources,'map_sources':map_sources,
        'definitions':npc_records,'placements':placements,'services':service_records,
        'scene_npc_placements':scene_placements,'catalog_differences':differences,'issues':issues,
        'summary':{'tables':len(sources),'table_rows':sum(s['rows'] for s in sources),
            'npc_definitions':len(definitions),'static_placements':len(placements),
            'spawn_candidates':sum(p['spawn_candidate'] for p in placements),
            'unplaced_definitions':sum(not r['placements'] for r in npc_records),
            'service_definitions':len(services),'scene_npc_placements':len(scene_placements),
            'blocked_reasons':dict(Counter(reason for p in placements for reason in p['blocked_reasons']))},
        'verification':{'original_pfs_crc_and_length':True,'live_database_modified':False,
            'runtime_service_dispatch_connected':None,'runtime_status':'not_assessed_by_archive_audit',
            'native_gui_verified':False}}
    write_json(OUT/'catalogs/npc-recovery.json',result)
    print(json.dumps(result['summary'],ensure_ascii=False))
    if differences or issues:
        raise SystemExit('NPC audit differences: inspect npc-recovery.json')


if __name__ == '__main__':
    main()
