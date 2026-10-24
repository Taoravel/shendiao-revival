"""Actual encrypted owner route for depot cash. Red until shared integration.

No source patching or replacement dispatcher. Uses disposable database only.
"""
import asyncio
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from verify_runtime import Peer
import runtime_storage
import npc_gameplay


def balances(messages):
    slots={}
    for kind,body in messages:
        if kind==0xc03fa:
            slot,value=struct.unpack('>iq',body);slots[slot]=value
    return slots


async def check(store,prepared,role,npc):
    rt=GameRuntime(store,prepared)
    try:
        peer=Peer(rt);await peer.login(role);owner=rt.roles[role['id']]
        await owner.io(runtime_storage.initialize_role_wallet,store,1111,role['id'],owner.epoch,
            (10000000000,321,0,0),'explicit_migration')
        await owner.io(npc_gameplay.initialize_depot,owner.inventory,98765,'explicit_migration')
        key=(npc.map_id<<32)|npc.placement_id
        deposit=struct.pack('>qq',key,4294967303)
        assert await peer.request(0xc03fb,deposit)==[], 'Deposit without opened warehouse was accepted'
        await peer.request(0xc04f0,struct.pack('>q',key))
        result=balances(await peer.request(0xc03fb,deposit))
        assert result=={1:5705032697,2:4295066068}, f'Shared depot-money route not integrated: {result}'
        draw=struct.pack('>qq',key,4294967301)
        assert balances(await peer.request(0xc03fc,draw))=={1:9999999998,2:98767}
        await owner.mailbox.call('receive',0xc03fc,struct.pack('>qq',key,10),request_id='money-once')
        await owner.mailbox.call('receive',0xc03fc,struct.pack('>qq',key,10),request_id='money-once')
        assert balances(await owner.mailbox.call('receive',0xc03fc,struct.pack('>qq',key,10),request_id='money-once'))=={
            1:10000000008,2:98757}
        assert await peer.request(0xc03fb,struct.pack('>qq',key+1,1))==[]
        await peer.connection.close()
        peer=Peer(rt);await peer.login(role)
        assert await peer.request(0xc03fc,struct.pack('>qq',key,1))==[]
        await peer.request(0xc04f0,struct.pack('>q',key))
        assert balances(await peer.request(0xc03fb,struct.pack('>qq',key,8)))=={1:10000000000,2:98765}
        return {'passed':['native encrypted deposit/draw route through real RoleOwner',
            'unopened warehouse and mismatched NPC rejected','accepted retry transfers once',
            'reconnect invalidates access and preserves both64bit balances'],
            'native_gui_verified':False,'live_database_modified':False}
    finally:await rt.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'depot-money-runtime.sqlite3')
        role=store.create_role(1111,'银两接线',11,1010109);prepared=runtime_storage.prepare(store)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10003)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        try:report=asyncio.run(check(store,prepared,role,npc))
        except AssertionError as error:
            write_json(OUT/'evidence/npc-depot-money-runtime-baseline.json',{
                'status':'shared_route_missing','failure':str(error),'native_gui_verified':False,
                'live_database_modified':False})
            raise
    write_json(OUT/'evidence/npc-depot-money-runtime.json',report);print(report)


if __name__=='__main__':main()
