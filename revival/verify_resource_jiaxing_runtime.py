"""Natural cart prefix then explicit known-wound migration and real title task.

No manual task offer/item grant/XP or spawn. Migration and70/40 wounds are a
controlled fixture between sessions; no automatic new-role resource activation.
"""
import asyncio
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import Inventory
from inspect_client import OUT,write_json
from role_attribute_storage import read_attribute_snapshot,update_role_vitals
from role_equipment import resource_caps_from_projection
from role_equipment_storage import current_equipment_totals
from role_resource_storage import migrate_role_resources,read_role_resources
from task_protocol import C_COMMIT_SCENARIO_QUEST,S_REFRESH_SCENARIO_QUEST_STATE
from verify_first_master_runtime import state
from verify_growth_runtime import GrowthPeer,role_values
from verify_newbie_cart_runtime import check as cart_prefix
from world_catalog import maps,maze_grids
from world_entity_protocol import VISIT_NPC
from world_movement import ROLE_MOVE,ROLE_STOP
from world_newbie import load_newbie_routes,check_birth_site
from world_npcs import load_placements
from wire import compact
import runtime_storage


async def check(store,prepared,role,route,witness):
    await cart_prefix(store,prepared,role,route,witness)
    title=next(q for q,s in state(store,role['id'])[0] if s=='active')
    definition=store.task_resources.definitions[title]
    epoch=store.acquire_lease(1111,role['id'])
    inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
    with closing(inv.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        old=read_attribute_snapshot(db,1111,role['id'],epoch)
        wound=replace(old.vitals,hp=70,mp=40,version=old.vitals.version+1)
        update_role_vitals(db,1111,role['id'],epoch,old.vitals,wound)
        totals=current_equipment_totals(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),store.equipment_attribute_rules)
        migrated=migrate_role_resources(db,1111,role['id'],epoch,wound,resource_caps_from_projection(totals),
            origin='explicit_migration',migration_id='known-jiaxing-wounds',rules=store.resource_rules,
            equipment_rules=store.equipment_attribute_rules)
    source=store.position(1111,role['id'])
    candidate=replace(route,home_map_id=source[0],first_npc_id=definition['target']['npc_id'],cinematic_endpoint=source)
    walk=check_birth_site(candidate,maps(),maze_grids()[source[0]],load_placements()[source[0]],
        state_byte=0,interaction_radius=32,max_visited=100000)
    assert walk.status=='reachable'
    rt=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(rt);await peer.login(role)
        assert tuple(role_values(peer.initial)[k] for k in (60,70,80,810,1230))==(70,40,45,35,8)
        path=walk.path
        await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*path[0],*path[-1],0))
        await peer.request(ROLE_STOP,compact(len(path))+b''.join(struct.pack('>hh',*p) for p in path)+struct.pack('>hhQ',*path[-1],0))
        key=(source[0]<<32)|walk.placement_id
        await peer.request(VISIT_NPC,struct.pack('>q',key))
        body=struct.pack('>iQi',title,key,0)
        completed=await peer.request(C_COMMIT_SCENARIO_QUEST,body)
        values=role_values(completed)
        assert tuple(values[k] for k in (490,500,60,140,70,150,80,810,1230))==(2,5,80,110,46,106,49,38,8)
        assert sum(k==0xc32c8 for k,_ in completed)==1
        marker=(S_REFRESH_SCENARIO_QUEST_STATE,struct.pack('>ii',title,1))
        assert completed.count(marker)==1
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            after=read_role_resources(db,1111,role['id'],rt.roles[role['id']].epoch,store.resource_rules)
        assert after.version==migrated.version+1
        paid=state(store,role['id'])
        assert paid[2]==(31,)
        assert marker not in await peer.request(C_COMMIT_SCENARIO_QUEST,body)
        assert state(store,role['id'])==paid
        await peer.connection.close();peer=GrowthPeer(rt);await peer.login(role)
        assert tuple(role_values(peer.initial)[k] for k in (60,70,80,810,1230))==(80,46,49,38,8)
        assert state(store,role['id'])==paid and marker not in peer.initial
        await peer.connection.close()
    finally:await rt.close()


def main():
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(r for r in audit['routes'] if (r['character_id'],r['school_id'])==(9,11))
    with tempfile.TemporaryDirectory(prefix='resource-jiaxing-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3');prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'资源嘉兴任务',11,1010109)
        asyncio.run(check(store,prepared,role,route,witness))
    result=dict(passed=['natural intro/card/equip/cart prefix without task offers, item grants, XP or spawn fixtures',
        'explicit known70/40 migration before actual original Jiaxing NPC commit',
        'original120XP earnsL2/31/free5 and one full20map80/110HP46/106MP49/38/8',
        'resource version advances once; duplicate/reconnect preserve current resources and title delegates once'],
        migration_fixture='explicit known wounds between sessions, not natural combat or automatic activation',
        database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/resource-jiaxing-runtime-verification.json',result);print(result)


if __name__=='__main__':main()
