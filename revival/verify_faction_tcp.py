"""Real ephemeral TCP acceptance of organization chat; never the live port."""
import asyncio
import json
import struct
import tempfile
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from verify_faction_runtime import fixture,seed,packet,command,now
from verify_social_tcp import TCPPeer
import runtime_storage
import social_protocol as p


async def check(store):
    loop=asyncio.get_running_loop();errors=[];previous=loop.get_exception_handler()
    loop.set_exception_handler(lambda loop,context:errors.append(context))
    rt=GameRuntime(store,runtime_storage.prepare(store))
    server=await asyncio.start_server(rt.handle_socket,'127.0.0.1',0)
    peers=[]
    async def barrier(peer):
        await peer.send(100,b'org!');assert await peer.read(100)==b'org!'
    try:
        port=server.sockets[0].getsockname()[1];roles=store.roles(1111)
        for role in roles:
            peer=TCPPeer(*await asyncio.open_connection('127.0.0.1',port));peers.append(peer)
            await peer.login(role)
        seed(rt);a,b,c,d=peers
        await a.send(p.CHAT_SEND,packet(10,'家族网络'))
        expected=p.chat_message(roles[0],10,'家族网络')
        assert await a.read(p.CHAT_RECEIVE)==expected and await b.read(p.CHAT_RECEIVE)==expected
        await c.send(p.CHAT_SEND,packet(4,'帮派网络'))
        expected=p.chat_message(roles[2],4,'帮派网络')
        for peer in (a,b,c):assert await peer.read(p.CHAT_RECEIVE)==expected
        await d.send(p.CHAT_SEND,packet(4,'外人伪造'));await barrier(d)
        assert not any(k==p.CHAT_RECEIVE for k,_ in d.pending)
        await b.send(p.ADD_SEND,struct.pack('>Q',1)+p.text(''))
        await b.read(p.ADD_RECEIVE)
        await b.send(p.MOVE_GROUP_SEND,p.text(p.GROUP_BLACK)+struct.pack('>Q',1)+p.text(''))
        await b.read(p.MOVE_GROUP_RECEIVE)
        await a.send(p.CHAT_SEND,packet(4,'帮派黑名单'))
        expected=p.chat_message(roles[0],4,'帮派黑名单')
        assert await a.read(p.CHAT_RECEIVE)==expected and await c.read(p.CHAT_RECEIVE)==expected
        await rt.social_runtime.idle();await barrier(b)
        assert not any(k==p.CHAT_RECEIVE for k,_ in b.pending)
        org=rt.social_runtime.organizations
        await org.command(command(rt,1,103,'mute',(3,)),now())
        await c.send(p.CHAT_SEND,packet(4,'禁言网络'));await barrier(c)
        assert not any(k==p.CHAT_RECEIVE for k,_ in c.pending)
        await org.command(command(rt,2,101,'leave'),now())
        await b.send(p.CHAT_SEND,packet(10,'退出后家族'));await barrier(b)
        await b.send(p.CHAT_SEND,packet(4,'退出后帮派'));await barrier(b)
        assert not any(k==p.CHAT_RECEIVE for k,_ in b.pending)
        await barrier(a);await barrier(c);await barrier(d)
    finally:
        for peer in peers:await peer.close()
        server.close();await server.wait_closed();await rt.close();await asyncio.sleep(0)
        loop.set_exception_handler(previous)
    assert not errors,[str(e.get('exception',e.get('message'))) for e in errors]


def main():
    with tempfile.TemporaryDirectory() as directory:asyncio.run(check(fixture(directory)))
    report=dict(passed=['four real authenticated TCP connections with continuous RC4/native MPPC',
        'family-only native chat and guild chat across two families','outsider send/receive exclusion',
        'recipient blacklist, persisted guild mute and leave revocation','heartbeat continuity and clean shutdown'],
        native_gui_verified=False,native_creation_verified=False,live_listener_28993_changed=False,persistent_user_store_changed=False)
    write_json(OUT/'evidence/faction-tcp-verification.json',report)
    print(json.dumps(report))


if __name__=='__main__':main()
