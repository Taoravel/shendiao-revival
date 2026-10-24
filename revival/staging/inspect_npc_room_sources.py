"""Read original PFS records for102002/10157 and the real inn portal pair."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'revival'))
from bxml import decode
from inspect_client import catalog_rows,write_json
from pfs import PfsArchive


def main():
    sources=[]
    config=PfsArchive(ROOT/'artres/config.pfs');maps=PfsArchive(ROOT/'artres/map.pfs')
    def read(archive,name):
        raw=archive.read(name);entry=archive.entries[name]
        sources.append(dict(archive=archive.path.name,entry=name,crc32=entry.crc,
            length=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        return decode(raw)
    tasks=catalog_rows(read(config,'autoconfig/knight.gsp.task.cmainmissioninfo.xml'))
    npcs=catalog_rows(read(config,'autoconfig/knight.gsp.npc.cnpcconfig.xml'))
    maprows=catalog_rows(read(config,'autoconfig/knight.gsp.map.cmapconfig.xml'))
    task=next(r for r in tasks if r['attributes']['id']=='102002')
    npc=next(r for r in npcs if r['attributes']['id']=='10157')
    inn=next(r for r in maprows if r['attributes']['id']=='1376')
    assert task['attributes']['ActiveInfoNpcID']=='10157'
    assert task['attributes']['ActiveInfoMapID']=='1007'
    assert npc['attributes']['mapid']=='1376' and inn['attributes']['mapName']=='临安客栈'
    world=json.loads((ROOT/'revival/catalogs/world.json').read_text(encoding='utf8'))
    mapfacts=[]
    for mapid,resdir in ((1007,'map_1007_linan'),(1376,'linankezhan')):
        original_npcs=[dict(row.attrib) for row in read(maps,resdir+'/npc.xml')]
        original_portals=[dict(row.attrib) for row in read(maps,resdir+'/goto.xml')]
        saved=next(r for r in world if int(r['attributes']['id'])==mapid)
        assert [{k:v for k,v in row.items() if k!='definition_name'} for row in saved['npc_placements']]==original_npcs
        assert saved['portal_cells']==original_portals
        to_other=[row for row in original_portals if int(row['destmap'])==(1376 if mapid==1007 else 1007)]
        mapfacts.append(dict(map_id=mapid,npc10157=[r for r in original_npcs if r['id']=='10157'],
            portals_to_other_map=to_other))
    assert mapfacts[0]['npc10157']==[]
    assert len(mapfacts[1]['npc10157'])==1
    assert tuple(mapfacts[1]['npc10157'][0][k] for k in ('id','posx','posy'))==('10157','532','920')
    assert all(row['portals_to_other_map'] for row in mapfacts)
    report=dict(sources=sources,task_attributes=task['attributes'],npc_attributes=npc['attributes'],
        inn_attributes=inn['attributes'],original_maps=mapfacts,original_pfs_crc_and_length_verified=True,
        saved_world_portal_and_npc_projection_matches=True,
        findings=['Original task102002 names NPC10157 but ActiveInfoMapID1007.',
            'Original NPC10157 and original npc.xml place it only in inn1376, not1007.',
            'Original goto.xml has an explicit bidirectional1007/1376 portal pair.'],
        interpretation='Supports an outer-map versus room-map mismatch; does not prove the original server acceptance rule.',
        mapping_policy_authorized=False,dynamic_spawn_proven=False,live_database_accessed=False)
    path=ROOT/'revival/evidence/npc-task-room-original-sources.json'
    write_json(path,report)
    print(json.dumps(dict(sources=len(sources),portals=[len(r['portals_to_other_map']) for r in mapfacts],
        npc10157=mapfacts[1]['npc10157'],sha256=hashlib.sha256(path.read_bytes()).hexdigest()),ensure_ascii=False))


if __name__=='__main__':main()
