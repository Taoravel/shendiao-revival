"""Two natural bloodmark entries, then shared private movement/chat/recovery.

Only disposable roles are used. Paths are original-clear movement reports,
not native navigation or GUI evidence. No private checkpoint fixture or battle.
"""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from verify_prologue_touch_runtime import check as natural_entry
from verify_runtime import Peer
from world_collision import maze_clear,maze_segment_clear
from world_catalog import maze_grids
from world_movement import ROLE_STOP
from world_newbie import load_newbie_routes
from world_transfer_storage import load_map_instance_transaction
import runtime_storage
import social_protocol as sp


async def check(store,prepared):
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(row for row in audit['routes'] if (row['character_id'],row['school_id'])==(9,11))
    roles=[store.create_role(1111,name,11,1010109) for name in ('血印自然双甲','血印自然双乙')]
    approaches=[]
    for role in roles:
        result=await natural_entry(store,prepared,role,route,witness)
        assert result['natural_bloodmark_approach_verified'] and not result['initial_npc_approach_fixture']
        approaches.append(dict(position=result['bloodmark_approach_position'],
            distance_squared=result['bloodmark_approach_distance_squared'],policy=result['interaction_policy']))
    runtime=GameRuntime(store,prepared);peers=[]
    try:
        for role in roles:
            peer=Peer(runtime);await peer.login(role);peers.append(peer)
        owners=[runtime.roles[role['id']] for role in roles]
        addresses=[owner.map_address for owner in owners]
        assert len(set(addresses))==2 and all(a.map_id==1501 and 2**62<=a.instance_id<2**63 for a in addresses)
        maps=[runtime.registered_map(address) for address in addresses]
        assert all(m is not None for m in maps) and maps[0] is not maps[1]
        assert runtime.registered_map(1501) is None
        other=await maps[1].mailbox.call('location',roles[1]['id'],owners[1].epoch)
        current=await maps[0].mailbox.call('location',roles[0]['id'],owners[0].epoch)
        start=current.x,current.y;end=current.x+1,current.y;grid=maze_grids()[1501]
        assert maze_clear(grid,*start,mask=1) and maze_clear(grid,*end,mask=1)
        assert maze_segment_clear(grid,start,end,mask=1)
        await peers[0].request(ROLE_STOP,b'\0'+struct.pack('>hhQ',*end,1501))
        assert owners[0].position.value==(1501,*end)
        assert await maps[1].mailbox.call('location',roles[1]['id'],owners[1].epoch)==other
        own=await peers[0].request(sp.CHAT_SEND,struct.pack('>i',sp.CURRENT_CHANNEL)
            +sp.text('自然私境隔离')+sp.text('')+b'\0')
        assert any(kind==sp.CHAT_RECEIVE for kind,_ in own)
        assert not any(kind==sp.CHAT_RECEIVE for kind,_ in await peers[1].take())
        for channel in (sp.WORLD_CHANNEL,sp.SCHOOL_CHANNEL):
            await peers[0].request(sp.CHAT_SEND,struct.pack('>i',channel)+sp.text('原公共范围')+sp.text('')+b'\0')
            assert any(kind==sp.CHAT_RECEIVE for kind,_ in await peers[1].take())
        with closing(store.leased(1111,roles[0]['id'],owners[0].epoch).connect()) as db,db:
            db.execute('BEGIN')
            checkpoint=load_map_instance_transaction(db,1111,roles[0]['id'],owners[0].epoch)
        assert checkpoint.address==addresses[0] and checkpoint.position==(1501,*end)
        assert all(owner.battle is None for owner in owners)
    finally:await runtime.close()
    cold=GameRuntime(store,prepared)
    try:
        for index,role in enumerate(roles):
            peer=Peer(cold);await peer.login(role)
            owner=cold.roles[role['id']]
            assert owner.map_address==addresses[index] and owner.battle is None
        assert cold.roles[roles[0]['id']].position.value==checkpoint.position
        assert cold.roles[roles[1]['id']].position.value==other.position
    finally:await cold.close()
    return dict(passed=['two real natural opening-to-bloodmark handoffs allocate distinct private addresses',
        'shared encrypted login and one clear-pixel STOP preserve both exact owners and durable positions',
        'actual current chat remains private while school/world retain their original scope',
        'cold runtime restores both natural private addresses without a checkpoint fixture or battle'],
        natural_origins=2,private_checkpoint_fixture=False,approach_fixture=False,
        natural_approaches=approaches,
        private_capacity_or_unload_verified=False,native_gui_verified=False,
        live_server_changed=False,battle_executed=False)


def main():
    with tempfile.TemporaryDirectory(prefix='natural-bloodmark-two-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        report=asyncio.run(asyncio.wait_for(check(store,runtime_storage.prepare(store)),90))
    write_json(OUT/'evidence/prologue-touch-two-roles-verification.json',report);print(report)


if __name__=='__main__':main()
