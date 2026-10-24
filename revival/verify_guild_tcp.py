"""Four disposable real TCP clients exercise native guild membership/offices."""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile
import uuid
from game_runtime import GameRuntime
from faction_domain import OrganizationCommand
from verify_social_tcp import TCPPeer
from verify_guild_offices import setup
from verify_guild_management import roster
from verify_faction_runtime import now
from inspect_client import OUT,write_json
import runtime_storage
import faction_protocol as p
import guild_protocol as g


async def refresh(peer,predicate):
    for _ in range(32):
        rows=roster([(g.ADD_GUILD_MEMBERS,await peer.read(g.ADD_GUILD_MEMBERS))])
        await peer.read(g.UPDATE_GUILD)
        mask=struct.unpack('>i',await peer.read(p.DEPUTY_AUTHORITY))[0]
        if predicate(rows):return rows,mask
    raise AssertionError('Expected guild state did not arrive')


async def check(f,guild):
    loop=asyncio.get_running_loop();errors=[];previous=loop.get_exception_handler()
    loop.set_exception_handler(lambda loop,context:errors.append(context))
    rt=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    server=await asyncio.start_server(rt.handle_socket,'127.0.0.1',0);peers=[]
    try:
        port=server.sockets[0].getsockname()[1];roles={r['id']:r for r in f.accounts.roles(1111)}
        for rid in (1,2,17,19):
            peer=TCPPeer(*await asyncio.open_connection('127.0.0.1',port));peers.append(peer);await peer.login(roles[rid])
        a,b,m,o=peers
        for peer in (a,b,m):
            rows,mask=await refresh(peer,lambda r:all(r[i]['offline']=='' for i in (1,2,17)))
            assert len(rows)==18 and mask==0
        await a.send(p.REQUEST_FACTION,b'');assert len((await refresh(a,lambda r:len(r)==18))[0])==18
        await a.send(p.FAMILY_POSITION,struct.pack('>Qi',2,1))
        await a.send(p.FACTION_POSITION,struct.pack('>Qi',2,5))
        for peer in (a,b,m):
            rows,_=await refresh(peer,lambda r:r[2]['guild_rank']==5 and r[2]['family_rank']==1)
        online=rt.online_snapshot();org=rt.social_runtime.organizations
        cmd=OrganizationCommand(1,online[1].login_epoch,uuid.uuid4().hex,now()+5000,guild,'set_authority',(2,6,True))
        await org.command(cmd,now())
        # Find the authority update after any older same-position snapshot.
        mask=0
        while mask!=64:_,mask=await refresh(b,lambda r:r[2]['guild_rank']==5)
        assert (await refresh(m,lambda r:r[2]['guild_rank']==5))[1]==0
        await b.send(p.FACTION_POSITION,struct.pack('>Qi',3,3))
        for peer in (a,b,m):await refresh(peer,lambda r:r[3]['guild_rank']==3)
        await b.send(p.RESIGN_FACTION_OFFICE,b'')
        rows,mask=await refresh(b,lambda r:r[2]['guild_rank']==0)
        assert rows[2]['family_rank']==1 and mask==0
        await o.send(p.JOIN_FAMILY,p.family_join_request((1,)))
        # Family application delivery is the acknowledgement that the request
        # reached its owner before the head sends the approval over TCP.
        await a.read(p.ADD_FAMILY_APPLICATIONS)
        await a.send(p.FAMILY_REVIEW,struct.pack('>Qi',19,1))
        assert 19 in (await refresh(o,lambda r:19 in r))[0]
        for peer in (a,b,m):await refresh(peer,lambda r:19 in r)
        await o.send(p.LEAVE_FAMILY,b'');assert await o.read(p.LEFT_FAMILY)==b''
        assert await o.read(p.LEFT_FACTION)==b''
        for peer in (a,b,m):
            await refresh(peer,lambda r:19 not in r)
            assert await peer.read(g.REMOVE_GUILD_MEMBER)==struct.pack('>Q',19)
        await o.send(p.FACTION_POSITION,struct.pack('>Qi',3,5))
        for peer in peers:
            await peer.send(100,b'gld!');assert await peer.read(100)==b'gld!'
        assert not any(k in (g.UPDATE_GUILD,g.ADD_GUILD_MEMBERS) for k,_ in o.pending)
    finally:
        for peer in peers:await peer.close()
        server.close();await server.wait_closed();await rt.close();await asyncio.sleep(0)
        loop.set_exception_handler(previous)
    assert not errors,[str(e.get('exception',e.get('message'))) for e in errors]


def main():
    with tempfile.TemporaryDirectory() as directory:
        f,_,_,guild=setup(Path(directory)/'state.db')
        with closing(f.accounts.connect()) as db,db:
            db.execute("INSERT INTO roles(id,account_id,name,school,shape,level) VALUES(19,1111,'帮外侠客',12,1010101,40)")
        asyncio.run(check(f,guild))
    report=dict(passed=['four real TCP authentication/RC4/native MPPC streams',
        'guild bootstrap/query and cross-family roster','native nomination, delegated appointment and resignation',
        'private authority mask and independent family office','family approval joins guild through durable handoff',
        'family departure clears guild and native roster cache','outsider rejection, heartbeat continuity and clean shutdown'],
        guild_creation='actual disposable wallet funding plus explicit level fixtures; native NPC creation not exercised',
        native_gui_verified=False,live_listener_28993_changed=False,persistent_user_store_changed=False)
    write_json(OUT/'evidence/guild-tcp-verification.json',report);print(json.dumps(report))


if __name__=='__main__':main()
