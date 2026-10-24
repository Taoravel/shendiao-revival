"""Four real authenticated TCP clients exercise native family management."""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile
import uuid
from accounts import AccountStore
from game_runtime import GameRuntime
from faction_domain import OrganizationCommand
from verify_social_tcp import TCPPeer
from verify_family_management import members
from verify_faction_runtime import now
from inspect_client import OUT,write_json
import runtime_storage
import faction_protocol as p


async def refresh(peer,*,clear=False,applications=False,removed=None):
    if removed is not None:assert await peer.read(p.REMOVE_FAMILY_MEMBER)==struct.pack('>Q',removed)
    if clear:await peer.read(p.REMOVE_FAMILY_APPLICATIONS)
    await peer.read(p.UPDATE_FAMILY)
    rows=members(await peer.read(p.ADD_FAMILY_MEMBERS))
    if applications:await peer.read(p.ADD_FAMILY_APPLICATIONS)
    return rows


async def check(store):
    loop=asyncio.get_running_loop();errors=[];previous=loop.get_exception_handler()
    loop.set_exception_handler(lambda loop,context:errors.append(context))
    rt=GameRuntime(store,runtime_storage.prepare(store))
    server=await asyncio.start_server(rt.handle_socket,'127.0.0.1',0);peers=[]
    try:
        port=server.sockets[0].getsockname()[1]
        for role in store.roles(1111):
            peer=TCPPeer(*await asyncio.open_connection('127.0.0.1',port));peers.append(peer);await peer.login(role)
        a,b,c,d=peers;online=rt.online_snapshot();org=rt.social_runtime.organizations
        cmd=OrganizationCommand(1,online[1].login_epoch,uuid.uuid4().hex,now()+5000,0,'create_family',
            ('网络家族','同心协力',tuple((rid,online[rid].login_epoch) for rid in (1,2,3))))
        with closing(org.store.connect()) as db,db:org.store.record_funding(db,cmd,org.policy['family_create_fee'])
        family=(await org.command(cmd,now())).organization
        for peer in (a,b,c):assert set(await refresh(peer))=={1,2,3}
        await d.send(p.JOIN_FAMILY,p.family_join_request((family,)))
        await refresh(a,clear=True,applications=True);await refresh(b);await refresh(c)
        await a.send(p.FAMILY_POSITION,struct.pack('>Qi',2,1))
        assert (await refresh(a,clear=True,applications=True))[2]['position']==1
        await refresh(b,clear=True,applications=True);await refresh(c)
        await b.send(p.FAMILY_REVIEW,struct.pack('>Qi',4,1))
        for peer in (a,b):assert set(await refresh(peer,clear=True))=={1,2,3,4}
        for peer in (c,d):assert set(await refresh(peer))=={1,2,3,4}
        await d.send(p.LEAVE_FAMILY,b'');assert await d.read(p.LEFT_FAMILY)==b''
        for peer in (a,b,c):assert set(await refresh(peer,removed=4))=={1,2,3}
        await a.send(p.FAMILY_POSITION,struct.pack('>Qi',1,0))
        for peer in (a,b,c):
            rows=await refresh(peer);assert rows[1]['position']==0 and rows[2]['position']==2
        # A departed player cannot use a retained native management packet.
        await d.send(p.FAMILY_REVIEW,struct.pack('>Qi',1,1))
        for peer in peers:
            await peer.send(100,b'fam!');assert await peer.read(100)==b'fam!'
        assert not any(k in (p.UPDATE_FAMILY,p.ADD_FAMILY_MEMBERS,p.ADD_FAMILY_APPLICATIONS) for k,_ in d.pending)
    finally:
        for peer in peers:await peer.close()
        server.close();await server.wait_closed();await rt.close();await asyncio.sleep(0)
        loop.set_exception_handler(previous)
    assert not errors,[str(e.get('exception',e.get('message'))) for e in errors]


def main():
    with tempfile.TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'state.db')
        with closing(store.connect()) as db,db:
            for rid in range(1,5):db.execute('INSERT INTO roles(id,account_id,name,school,shape,level) VALUES(?,1111,?,12,1010101,40)',(rid,'网络族员'+str(rid)))
        asyncio.run(check(store))
    result=dict(passed=['four actual TCP authentication/cipher/native MPPC streams',
        'family panel and roster','manager-only application, deputy appointment and native approval',
        'leave removes departed and updates remaining clients','native self-abdication transfers to deputy',
        'departed management refuses, heartbeat continuity and clean shutdown'],
        creation_funding='explicit disposable test grant; native paid creation not exercised',native_gui_verified=False,
        live_listener_28993_changed=False,persistent_user_store_changed=False)
    write_json(OUT/'evidence/family-tcp-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
