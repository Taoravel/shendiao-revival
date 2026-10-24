"""Run map/view lifecycles on shipped resources and ordinary portal witnesses.

Temporary map owners and original codec emulation only. Explicit state0 fixtures
do not establish live character state, scene loading, or a housing-entry rule.
"""
from collections import Counter,defaultdict
from dataclasses import replace
import struct
from unittest.mock import patch
from inspect_client import OUT,write_json
from world_catalog import maps,maze_grids,valid_position
from world_collision import maze_clear,maze_segment_clear
from world_owner import MapOwner,MapAddress,Location,MoveCommand
from world_roles import RoleScene
from world_role_protocol import RoleBasic,S_ROLE_MOVE
from world_protocol import scene_entry
from verify_world_entities_native import probe


def fixtures(mid,instance,catalog,grids):
    owner=MapOwner(MapAddress(mid,instance,0),catalog,
        capacity=2,transfer_capacity=2,mailbox_capacity=2,maze=grids[mid])
    view=RoleScene(owner.address,catalog,radius=64,role_capacity=2,pair_capacity=1,batch_size=2)
    return owner,view


def appearance(role_id,point):
    return RoleBasic(role_id,'地图验证',9,*point,0x71)


def movement(location,key,point):
    return MoveCommand(location,key,1000,0xc0faa,
        b'\0'+struct.pack('>hhQ',*point,0),movement_state=0)


def nearby(mid,point,catalog,grid):
    """A distinct state0-clear point in the same cell, with an exact DDA leg."""
    x,y=point
    for candidate in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
        if ((candidate[0]//16,candidate[1]//16)==(x//16,y//16)
                and valid_position((mid,*candidate),catalog)
                and maze_clear(grid,*candidate,mask=1)
                and maze_segment_clear(grid,point,candidate,mask=1)):
            return candidate
    return None


def map_point(mid,catalog,grid):
    for cy in range(min(grid.height,(min(catalog[mid]['height'],32768)+15)//16)):
        for cx in range(min(grid.width,(min(catalog[mid]['width'],32768)+15)//16)):
            point=(cx*16+8,cy*16+8)
            if (valid_position((mid,*point),catalog)
                    and maze_clear(grid,*point,mask=1)
                    and nearby(mid,point,catalog,grid) is not None):
                return point
    return None


def native_scene(mid,point):
    body=scene_entry((mid,*point),reason=0)
    _,raw=probe(0xdac580,0xe50b00,0xf74260,payload=body)
    assert struct.unpack_from('<hh',raw,0x28)==point
    assert struct.unpack_from('<Q',raw,0x38)[0]==mid
    assert raw[0x2c]==0 and raw[0x40]==0
    return len(body)


def map_case(mid,catalog,grids):
    point=map_point(mid,catalog,grids[mid])
    if point is None:
        return dict(map_id=mid,status='no_state0_fixture')
    step=nearby(mid,point,catalog,grids[mid])
    owner,view=fixtures(mid,1,catalog,grids)
    isolated,iv=fixtures(mid,2,catalog,grids)
    a=Location(1,'resource-a',owner.address,1,*point)
    owner.join_with_view(a,appearance(1,point),view)
    peer=Location(2,'resource-b',owner.address,1,*step)
    owner.join_with_view(peer,appearance(2,step),view)
    other=replace(a,address=isolated.address,login_epoch='isolated-a')
    isolated.join_with_view(other,appearance(1,point),iv)
    untouched=isolated.location(1),iv.snapshot(1)
    with patch('builtins.open',side_effect=AssertionError('Map movement file I/O')), \
         patch('io.open',side_effect=AssertionError('Map movement file I/O')):
        result,change=owner.move_with_view(movement(a,'resource-step',step),1,view)
    assert not result.rejection and result.location.position==(mid,*step)
    assert owner.location(1)==view.snapshot(1).location==result.checkpoint
    assert len(change.deliveries)==1 and change.deliveries[0].recipient_role_id==2
    kind,body=change.deliveries[0].packets[0]
    assert kind==S_ROLE_MOVE
    _,raw=probe(0xdacd10,0xe50d90,0xdacdc0,payload=body)
    assert struct.unpack_from('<q',raw,8)[0]==1
    assert struct.unpack_from('<hh',raw,0x14)==step
    _,removed=owner.leave_with_view(result.location,view)
    assert len(removed.deliveries)==1 and removed.deliveries[0].recipient_role_id==2
    assert owner.location(1) is None and view.snapshot(1) is None
    assert untouched==(isolated.location(1),iv.snapshot(1))
    return dict(map_id=mid,status='passed',fixture=point,step=step,
        native_scene_bytes=native_scene(mid,step),native_move_decoded=True,
        separate_instance_unchanged=True)


def approach(mid,cell,catalog,grid):
    point=(cell[0]*16+8,cell[1]*16+8)
    for dx,dy in ((-1,0),(0,-1),(1,0),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)):
        start=(point[0]+16*dx,point[1]+16*dy)
        if (valid_position((mid,*start),catalog) and maze_clear(grid,*start,mask=1)
                and maze_segment_clear(grid,start,point,mask=1)):
            return start,point
    return None


def portal_case(mid,cell,target,catalog,grids):
    start,point=approach(mid,cell,catalog,grids[mid])
    peer_point=nearby(target[0],target[1:],catalog,grids[target[0]])
    source,sv=fixtures(mid,1,catalog,grids)
    destination,tv=fixtures(target[0],1,catalog,grids)
    a=Location(1,'portal-a',source.address,1,*start)
    source.join_with_view(a,appearance(1,start),sv)
    source.join_with_view(Location(2,'portal-source-peer',source.address,1,*point),
        appearance(2,point),sv)
    destination.join_with_view(Location(3,'portal-target-peer',destination.address,1,*peer_point),
        appearance(3,peer_point),tv)
    result,_=source.move_with_view(movement(a,'resource-portal',point),1,sv)
    assert not result.rejection and result.offer is not None
    assert result.offer.target_position==target and result.location.position==(mid,*point)
    reservation=destination.reserve(result.offer,1)
    frozen=source.freeze(reservation,1)
    receipt=destination.activate(frozen,1)
    assert sv.snapshot(1) is not None and tv.snapshot(1) is None
    # A trusted durable commit is an explicit fixture precondition here; SQL
    # atomicity/fault/reconnect tests are owned by their separate verifiers.
    _,removed=source.finalize_with_view(receipt,sv)
    assert source.location(1) is None and sv.snapshot(1) is None
    assert len(removed.deliveries)==1
    active,added=destination.ready_with_view(receipt.location,appearance(1,target[1:]),tv)
    assert active.position==target and active==tv.snapshot(1).location
    assert {d.recipient_role_id for d in added.deliveries}=={1,3}
    assert native_scene(target[0],target[1:])>0
    moved,_=destination.move_with_view(movement(active,'target-step',peer_point),2,tv)
    assert not moved.rejection and moved.location.position==(target[0],*peer_point)
    return dict(source_map=mid,source_cell=cell,approach=start,
        target=target,target_step=peer_point,status='passed')


def main():
    catalog,grids=maps(),maze_grids()
    map_cases=[map_case(mid,catalog,grids) for mid in sorted(grids)]
    assert len(map_cases)==302 and all(c['status']=='passed' for c in map_cases),map_cases
    grouped=defaultdict(list);counts=Counter();special=[]
    for mid,row in catalog.items():
        for cell,target in row['portals'].items():
            source=(mid,cell[0]*16,cell[1]*16)
            status='eligible'
            if not valid_position(source,catalog) or not valid_position(target,catalog):
                status='unavailable_or_bounds'
            elif mid==target[0]:
                status='same_map_special'
                special.append(dict(map_id=mid,source_cell=cell,target=target))
            elif not maze_clear(grids[mid],*source[1:],mask=1):
                status='source_blocked_state0'
            elif not maze_clear(grids[target[0]],*target[1:],mask=1):
                status='target_blocked_state0'
            elif approach(mid,cell,catalog,grids[mid]) is None:
                status='no_local_approach_witness'
            elif nearby(target[0],target[1:],catalog,grids[target[0]]) is None:
                status='no_target_step_witness'
            grouped[(mid,target[0])].append((status,cell,target))
            counts[status]+=1
    portal_cases=[];uncovered=[]
    for (mid,target_mid),rows in sorted(grouped.items()):
        candidate=next((r for r in rows if r[0]=='eligible'),None)
        if candidate is None:
            uncovered.append(dict(source_map=mid,target_map=target_mid,
                reasons=dict(Counter(r[0] for r in rows))))
        else:
            _,cell,target=candidate
            portal_cases.append(portal_case(mid,cell,target,catalog,grids))
    assert sum(counts.values())==6275
    report=dict(available_maps=len(grids),configured_unavailable=sorted(set(catalog)-set(grids)),
        map_cases=map_cases,portal_cell_classification=dict(counts),
        configured_directed_pairs=len(grouped),tested_directed_pairs=len(portal_cases),
        portal_cases=portal_cases,uncovered_directed_pairs=uncovered,
        same_map_special_cells=special,
        fixture='explicit state0, source local native-DDA witness, target one-cell native-DDA step',
        durable_commit_tested=False,shared_runtime_integrated=False,gui_verified=False,
        full_world_complete=False,
        original_client_pathfinder_used=False,client_launched=False,live_server_changed=False,
        limits=['Map fixture points are controlled, not real spawn points or map accessibility proof',
            'One eligible representative per directed pair, not every portal cell walked',
            'Native scene decoder is not a successful resource loader or visible acknowledgement',
            'Same-map original portals need specific semantics; no housing owner or instance is guessed',
            'Blocked state0 is not proof of corrupt original portal or authorization to move its target'])
    write_json(OUT/'evidence/world-resource-handoffs-verification.json',report)
    print({k:report[k] for k in ('available_maps','configured_unavailable',
        'portal_cell_classification','configured_directed_pairs','tested_directed_pairs',
        'shared_runtime_integrated','gui_verified')})


if __name__=='__main__':main()
