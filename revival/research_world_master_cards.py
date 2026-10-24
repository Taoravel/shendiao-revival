"""Export original master-weapon choices and item identity facts; no gameplay."""
import hashlib
import json
from pathlib import Path
from bxml import decode
from inspect_client import ROOT, OUT, catalog_rows
from pfs import PfsArchive


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def export():
    archive_path=ROOT/'artres/config.pfs'
    archive=PfsArchive(archive_path)
    source_meta={}
    tables={}
    for name in ('task.ccardeffect','task.cmainmissioninfo','item.citemattr',
                 'item.cequipeffect','item.citemtype'):
        entry='autoconfig/knight.gsp.'+name+'.xml'
        raw=archive.read(entry)  # Includes original PFS CRC validation.
        rows=catalog_rows(decode(raw))
        table={int(r['attributes']['id']):r for r in rows}
        if len(table)!=len(rows):raise ValueError('Duplicate original table ID: '+entry)
        tables[name]=table
        source_meta[name]={'archive_path':'artres/config.pfs','entry_path':entry,
            'extracted_path':'revival/extracted/config/'+entry,
            'decoded_path':'revival/decoded/config/'+entry,
            'catalog_path':'revival/catalogs/knight.gsp.'+name+'.json',
            'original_entry_size':len(raw),'original_entry_sha256':sha(raw),
            'PFS_crc32':f'{archive.entries[entry].crc:08x}','crc_checked':True}
    route_path=OUT/'catalogs/newbie-routes.json'
    route_raw=route_path.read_bytes()
    doc=json.loads(route_raw)
    if doc['schema']!=1 or doc['source_status']!='client_verified':
        raise ValueError('Unverified route input')
    routes,items,issues=[],{},[]
    for route in doc['routes']:
        quest=tables['task.cmainmissioninfo'][route['successor_task_id']]
        attrs=quest['attributes']
        card_id=int(attrs['ScenarioInfoAnimationID'])
        if (card_id!=route['successor_card_effect_id'] or int(attrs['MissionType'])!=10
                or str(route['role_id']) not in quest['lists']['RequestRoleIDList']):
            raise ValueError('Route/task/card mismatch')
        card=tables['task.ccardeffect'][card_id]['attributes']
        choices=[]
        for slot in range(1,5):
            item_id=int(card.get('item'+str(slot),'0'))
            count=int(card.get('num'+str(slot),'0'))
            if not item_id:
                if count:issues.append({'card_id':card_id,'slot':slot,'issue':'count without item'})
                continue
            item=tables['item.citemattr'].get(item_id)
            equip=tables['item.cequipeffect'].get(item_id)
            if item is None:
                issues.append({'card_id':card_id,'item_id':item_id,'issue':'missing CItemAttr'})
                continue
            itype=int(item['attributes']['itemtypeid'])
            typ=tables['item.citemtype'].get(itype)
            items[str(item_id)]={'item_id':item_id,'CItemAttr':item['attributes'],
                'CEquipEffect':None if equip is None else equip['attributes'],
                'CItemType':None if typ is None else {'attributes':typ['attributes'],'lists':typ['lists']},
                'has_original_equipment_row':equip is not None,
                'source_tables':['item.citemattr','item.cequipeffect','item.citemtype']}
            if equip is None:issues.append({'item_id':item_id,'issue':'missing CEquipEffect'})
            if count<=0:issues.append({'card_id':card_id,'item_id':item_id,'issue':'nonpositive quantity'})
            choices.append({'slot':slot,'item_id_raw':card['item'+str(slot)],
                'quantity_raw':card['num'+str(slot)],'item_id':item_id,'quantity':count,
                'button_raw':card.get('button'+str(slot)),
                'weapon_visual_raw':card.get('weapon'+str(slot))})
        if len(choices)!=2:issues.append({'card_id':card_id,'issue':'not exactly two choices'})
        routes.append({'character_id':route['role_id'],'school_id':route['school_id'],
            'home_map_id':route['home_map_id'],'intro_task_id':route['intro_task_id'],
            'master_task_id':route['successor_task_id'],'mission_type_raw':attrs['MissionType'],
            'npc_id':int(attrs['ActiveInfoNpcID']),'card_effect_id':card_id,
            'next_task_ids_raw':quest['lists'].get('PostMissionList',[]),
            'card_attributes_raw':card,'choices':choices})
    assert len(routes)==43 and len({r['card_effect_id'] for r in routes})==43
    assert not issues,issues
    return {'schema':1,'source_status':'client_verified','kind':'read_only_original_catalog',
        'authorization_or_reward_policy':False,
        'sources':source_meta,
        'route_input':{'path':'revival/catalogs/newbie-routes.json','sha256':sha(route_raw)},
        'summary':{'route_count':len(routes),'unique_card_count':len({r['card_effect_id'] for r in routes}),
                   'unique_item_count':len(items),'choice_count':sum(len(r['choices']) for r in routes),
                   'issues':issues},
        'routes':routes,'items':items,
        'limits':['Original item/config identity only; no rewards issued.',
                  'No original server card timing, instance stats, binding, or equip state inferred.']}


if __name__=='__main__':
    result=export()
    path=OUT/'catalogs/newbie-master-cards.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    raw=path.read_bytes()
    report={'output_path':str(path),'output_sha256':sha(raw),**result['summary']}
    (OUT/'evidence/newbie-master-cards-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
