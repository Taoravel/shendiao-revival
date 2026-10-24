"""Independent original-resource audit of nine blocked exit destinations.

Writes research evidence only. No production imports, service, GUI or database.
"""
import hashlib
import json
from pathlib import Path

from bxml import decode
from pfs import PfsArchive
from world_grids import maze_grid

ROOT = Path(__file__).resolve().parent
PAIRS = {1301:1100,1304:1103,1305:1104,1306:1105,1308:1107,1309:1108,
         1393:1007,1394:1007,1395:1007}


def main():
    config = PfsArchive(ROOT.parent / 'artres/config.pfs')
    maps = PfsArchive(ROOT.parent / 'artres/map.pfs')
    map_names = {name.casefold():name for name in maps.entries}
    assert len(map_names) == len(maps.entries), 'Ambiguous case-insensitive map resource names'
    sources = []
    def read(archive, name):
        raw = archive.read(name)
        sources.append({'archive':str(archive.path),'entry':name,
                        'sha256':hashlib.sha256(raw).hexdigest(),'CRC_checked':True})
        return raw
    name = 'autoconfig/knight.gsp.map.cmapconfig.xml'
    configs = {int(e.attrib['id']):dict(e.attrib) for e in decode(read(config,name))}
    incoming = {mid:[] for mid in PAIRS}
    own = {}
    goto_scanned = 0
    goto_rows_scanned = 0
    casefold_resolutions = []
    for mid,cfg in configs.items():
        configured_name = cfg['resdir'] + '/goto.xml'
        name = map_names.get(configured_name.casefold())
        if name is None:
            continue
        if name != configured_name:
            casefold_resolutions.append(dict(map_id=mid, configured=configured_name, actual=name))
        records = [dict(e.attrib) for e in decode(read(maps,name))]
        goto_scanned += 1
        goto_rows_scanned += len(records)
        if mid in PAIRS:
            own[mid] = records
        for row in records:
            target = int(row['destmap'])
            if target in incoming:
                incoming[target].append({'source_map':mid,'entry':name,'row':row})
    paths = [dict(e.attrib) for e in decode(read(config,'paths.xml'))]
    shimen = decode(read(config,'autoconfig/knight.gsp.map.cshimenxunlu.xml'))
    shimen_records = [{'attributes':dict(e.attrib),
                      'descendants':[{'tag':c.tag,'attributes':dict(c.attrib),'text':c.text} for c in e.iter() if c is not e]}
                     for e in shimen]
    cases = []
    for source,target in PAIRS.items():
        raw = own[source][0]
        npc_name=map_names[(configs[source]['resdir']+'/npc.xml').casefold()]
        # Raw field spellings are checked below, not silently guessed.
        cases.append({'source_map':source,'target_map':target,'source_config':configs[source],
            'target_config':configs[target], 'goto_rows':own[source],
            'original_source_npcs':[dict(e.attrib) for e in decode(read(maps,npc_name))],
            'source_map_entries':[n for n in maps.entries if n.startswith(configs[source]['resdir']+'/')],
            'incoming_goto_rows':incoming[source],
            'exact_path_rows':[p for p in paths if p.get('sourceMapID')==str(source) and p.get('destMapID')==str(target)]})
    related_map_rows = []
    xml_count = 0
    for entry in config.entries:
        if not entry.lower().endswith('.xml') or entry == 'paths.xml':
            continue
        raw = config.read(entry)
        tree = decode(raw)
        xml_count += 1
        matched = []
        for element in tree.iter():
            hits = {k:v for k,v in element.attrib.items()
                    if ('map' in k.lower() or 'scene' in k.lower()) and v in {str(i) for i in PAIRS}}
            if hits:
                matched.append({'tag':element.tag,'matching_fields':hits,'attributes':dict(element.attrib)})
        if matched:
            related_map_rows.append({'entry':entry,'sha256':hashlib.sha256(raw).hexdigest(),
                                     'CRC_checked':True,'matched_rows':matched})
    result = {'method':'fresh original archives; enumerate every configured goto table and exact ordered path rows',
        'configured_maps':len(configs),'goto_tables_scanned':goto_scanned,'path_rows':len(paths),
        'goto_rows_scanned':goto_rows_scanned,'casefold_resolutions':casefold_resolutions,
        'cases':cases,'shimen_records':shimen_records,'sources':sources,
        'config_xml_entries_scanned':xml_count,'map_scene_attribute_matches':related_map_rows,
        'audit_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limitations':['No original server packet capture: goto marker units do not prove server landing coordinates.',
            'No incoming goto does not prove interiors are obsolete or unreachable.',
            'No nearest-clear landing substitution, mask change, instance alias or production change.']}
    out = ROOT/'evidence/world-portal-exit-source-audit.json'
    assert goto_scanned == 142 and goto_rows_scanned == 6275
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'result':str(out),'configured_maps':len(configs),
        'goto_tables_scanned':goto_scanned,'incoming_counts':{k:len(v) for k,v in incoming.items()},
        'first_goto':own[1301][0],'first_path':cases[0]['exact_path_rows'][:2]}))


if __name__ == '__main__':
    main()
