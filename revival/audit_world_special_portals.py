"""Fresh original goto/config audit and unsupported same-map owner feedback.

This records gaps, never changes portal coordinates or housing instance rules.
"""
from collections import Counter
import hashlib
import json
import struct
from inspect_client import ROOT,OUT,write_json
from pfs import PfsArchive
from bxml import decode
from world_catalog import maps,maze_grids
from world_collision import maze_clear
from world_owner import MapOwner,MapAddress,Location,MoveCommand


def same_map_feedback(mid,catalog):
    cell,target=next((p,t) for p,t in catalog[mid]['portals'].items() if t[0]==mid)
    point=(cell[0]*16+8,cell[1]*16+8)
    owner=MapOwner(MapAddress(mid,mid,0),catalog,capacity=1,
        transfer_capacity=1,mailbox_capacity=1)
    source=owner.join(Location(1,'special-portal-fixture',owner.address,1,point[0]-16,point[1]))
    result=owner.move(MoveCommand(source,'same-map-original',100,0xc0faa,
        b'\0'+struct.pack('>hhQ',*point,0)),1)
    assert result.offer is not None and result.offer.target_position==target
    before=owner.inspect_transfer(1,result.offer.transfer_id)
    try:
        owner.reserve(result.offer,1)
    except ValueError as error:
        refusal=str(error)
    else:
        raise AssertionError('Same-map behavior changed: reassess special portal contract')
    assert owner.inspect_transfer(1,result.offer.transfer_id)==before
    assert owner.location(1).position==(mid,*point) and owner.location(1).state=='active'
    return dict(map_id=mid,source_cell=cell,catalog_target=target,
        current_reserve_rejection=refusal,same_map_supported=False,
        source_after_refusal=owner.location(1).position,failed_reservation_changed_state=False,
        fixture='public map owner, synthetic role/report, current runtime no-maze constructor')


def main():
    catalog,grids=maps(),maze_grids()
    maps_archive=PfsArchive(ROOT/'artres/map.pfs')
    names={n.casefold():n for n in maps_archive.entries}
    original_catalog=json.loads((OUT/'catalogs/world.json').read_text(encoding='utf-8'))
    config_archive=PfsArchive(ROOT/'artres/config.pfs')
    config_raw=config_archive.read('autoconfig/knight.gsp.map.cmapconfig.xml')
    config={int(r.attrib['id']):dict(r.attrib) for r in decode(config_raw)}
    total,entries,special,blocked_targets=0,[],[],{}
    for row in original_catalog:
        attrs=row['attributes'];mid=int(attrs['id'])
        assert attrs==config[mid],mid
        entry=names.get((attrs['resdir']+'/goto.xml').casefold())
        if entry is None:
            assert not row['portal_cells']
            continue
        raw=maps_archive.read(entry)
        rows=[dict(r.attrib) for r in decode(raw)]
        assert rows==row['portal_cells'],entry
        total+=len(rows)
        entries.append(dict(map_id=mid,entry=entry,rows=len(rows),sha256=hashlib.sha256(raw).hexdigest()))
        same=[r for r in rows if int(r['destmap'])==mid]
        if same:
            targets=Counter((int(r['destx']),int(r['desty'])) for r in same)
            special.append(dict(map_id=mid,name=attrs['mapName'],dynamic=attrs['dynamic'],
                findpathin=attrs['findpathin'],raw_rows=len(same),
                raw_target_counts=[dict(raw_xy=xy,cells=count) for xy,count in sorted(targets.items())],
                raw_rows_sha256=hashlib.sha256(json.dumps(same,sort_keys=True).encode()).hexdigest(),
                entry_semantics='unconfirmed; raw integers are not assumed to be housing owner IDs'))
        for r in rows:
            tmid,x,y=int(r['destmap']),int(r['destx'])*16,int(r['desty'])*16
            if tmid in grids and 0<=x<grids[tmid].width*16 and 0<=y<grids[tmid].height*16:
                if not maze_clear(grids[tmid],x,y,mask=1):
                    blocked_targets.setdefault((tmid,x,y),set()).add(mid)
    assert total==6275 and sum(r['raw_rows'] for r in special)==650
    feedback=[same_map_feedback(mid,catalog) for mid in (1594,1627)]
    report=dict(original_config_sha256=hashlib.sha256(config_raw).hexdigest(),
        original_goto_entries=entries,original_goto_rows=total,
        fresh_config_and_goto_equal_catalog=True,same_map_original=special,
        same_map_owner_feedback=feedback,unsupported_same_map_cases=len(feedback),
        blocked_state0_target_positions=[dict(target=p,source_maps=sorted(source_maps))
            for p,source_maps in sorted(blocked_targets.items())],
        diagnostic_reproduced=True,world_complete=False,policy_applied=False,
        live_server_changed=False,gui_verified=False,client_launched=False,
        limits=['Refusal is a reproduced missing capability, not a fixed or passed same-map transfer',
            'Synthetic report demonstrates owner behavior; no legitimate arrival or natural navigation claimed',
            'Housing destination interpretation/ownership and same-map relocation barrier require separate source/design',
            'Target mask1 observation does not prove the original destination should be moved'])
    write_json(OUT/'evidence/world-special-portals-audit.json',report)
    print({k:report[k] for k in ('original_goto_rows','fresh_config_and_goto_equal_catalog',
        'unsupported_same_map_cases','diagnostic_reproduced','world_complete','policy_applied')})


if __name__=='__main__':main()
