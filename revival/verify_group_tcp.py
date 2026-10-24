"""Native-encoded common groups across two real authenticated TCP clients."""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from verify_social_tcp import TCPPeer
from inspect_client import OUT,write_json
import runtime_storage
import group_protocol as p
from verify_group_management import message_fields,history_fields


async def check(store):
    loop=asyncio.get_running_loop();errors=[]
    previous=loop.get_exception_handler()
    loop.set_exception_handler(lambda loop,context:errors.append(context))
    runtime=GameRuntime(store,runtime_storage.prepare(store))
    server=await asyncio.start_server(runtime.handle_socket,'127.0.0.1',0)
    peers=[]
    try:
        port=server.sockets[0].getsockname()[1]
        a,b=store.roles(1111)
        for role in (a,b):
            peer=TCPPeer(*await asyncio.open_connection('127.0.0.1',port));peers.append(peer)
            await peer.login(role)
        pa,pb=peers
        await pa.send(p.CREATE,b'');assert await pa.read(p.CREATE_READY)==b''
        await pa.send(p.NAME,p.text('论剑群'))
        gid=struct.unpack_from('>Q',await pa.read(p.CREATED))[0]
        await pa.read(p.UPDATED)
        await pb.send(p.SEARCH,p.text('论剑群')+bytes(12));assert struct.unpack_from('>Q',await pb.read(p.SEARCHED))[0]==gid
        await pb.send(p.JOIN,struct.pack('>Q',gid))
        assert await pa.read(p.JOIN_NOTICE)==p.join_notice(b['id'],gid,b['name'])
        await pa.send(p.RESPOND,struct.pack('>iQQ',0,b['id'],gid))
        await pa.read(p.UPDATED);await pb.read(p.UPDATED)
        await pb.send(p.SEND,p.text('真实群聊')+p.text('')+struct.pack('>Q',gid)+b'\0')
        received=await pa.read(p.MESSAGE)
        assert received==await pb.read(p.MESSAGE)
        content,sender,stamp,actual_gid=message_fields(received)
        assert (content,sender,actual_gid)==('真实群聊',b['name'],gid) and len(stamp)==19
        await pb.send(p.LEAVE,struct.pack('>Q',gid))
        assert await pb.read(p.LEFT)==struct.pack('>Q',gid)
        await pa.read(p.UPDATED)
        # Rejoin through the native invitation path (its Agree enum is 1).
        await pa.send(p.INVITE,struct.pack('>QQ',b['id'],gid));await pa.read(p.INVITE_ACK)
        assert await pb.read(p.INVITED)==p.invited(gid,a['name'],'论剑群')
        await pb.send(p.INVITE_REPLY,struct.pack('>iQ',1,gid))
        await pa.read(p.UPDATED);await pb.read(p.UPDATED)
        await pa.send(p.MANAGER,struct.pack('>QQQ',1,gid,b['id']))
        await pa.read(p.UPDATED);await pb.read(p.UPDATED)
        config=struct.pack('>Qii',gid,1,0)+p.text('网络群公告')+p.text('')+struct.pack('>i',0)
        await pb.send(p.CONFIG,config)
        owner_config=await pa.read(p.CONFIGURED)
        member_config=await pb.read(p.CONFIGURED)
        assert struct.unpack_from('>i',owner_config,8)[0]==1
        assert struct.unpack_from('>i',member_config,8)[0]==0
        await pa.read(p.UPDATED);await pb.read(p.UPDATED)
        await pb.send(p.HISTORY,struct.pack('>Qi',gid,-1))
        page,last,rows=history_fields(await pb.read(p.HISTORY_PAGE))
        assert page==1 and last and [(r[0],r[1]) for r in rows]==[('真实群聊',b['name'])]
        await pa.send(p.MANAGER,struct.pack('>QQQ',0,gid,b['id']))
        await pa.read(p.UPDATED);await pb.read(p.UPDATED)
        await pa.send(p.EXPEL,struct.pack('>QQ',b['id'],gid))
        assert await pb.read(p.LEFT)==struct.pack('>Q',gid)
        await pa.read(p.UPDATED)
        await pb.send(p.HISTORY,struct.pack('>Qi',gid,-1))
        await pb.send(100,b'ping');assert await pb.read(100)==b'ping'
        assert not any(k==p.HISTORY_PAGE for k,_ in pb.pending)
    finally:
        for peer in peers:await peer.close()
        server.close();await server.wait_closed();await runtime.close();await asyncio.sleep(0)
        loop.set_exception_handler(previous)
    assert not errors,[str(e.get('exception',e.get('message'))) for e in errors]


def main():
    with tempfile.TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'tcp.db')
        for name in ('网络群甲','网络群乙'):store.create_role(1111,name,12,1010101)
        with closing(store.connect()) as db,db:db.execute('UPDATE roles SET level=20')
        asyncio.run(check(store))
    result=dict(transport='real temporary loopback TCP, two authenticated encrypted clients',
        passed=['two-step creation','exact search','join notice','approval roster updates','bidirectional group chat delivery',
                'leave and roster update','invitation accept and member generation renewal','manager appointment and demotion',
                'shared notice plus distinct per-recipient flash settings','native history page with server timestamp',
                'expulsion and nonmember history refusal','continuous native MPPC/cipher and heartbeat','no unhandled shutdown errors'],
        native_gui_verified=False,live_listener_28993_changed=False,persistent_user_store_changed=False)
    write_json(OUT/'evidence/group-tcp-verification.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
