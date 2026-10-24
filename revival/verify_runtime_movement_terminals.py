"""Real connection terminal and CG lifecycle checks using disposable roles.

Observe only the logical send Interface; every offered message still runs the
actual ConnectionOwner. Public map callbacks are adversarial stale server
receipts, never wire authentication or a fabricated client load ACK.
"""
import asyncio
from pathlib import Path
import struct
import tempfile

from accounts import AccountStore
from game_runtime import GameRuntime,SceneMessage
from inspect_client import OUT,write_json
from runtime_movement import MovementDeclaration,SET_ROLE_LOCATION
import runtime_storage
from verify_runtime_movement_lifecycle import GatedWriter
from verify_world_resource_runtime import MapPeer,checkpoint_fixture,Events
from world_newbie import load_newbie_routes,END_PLAY_CG
from wire import frame


def observe(peer):
    declarations=[]
    original=peer.connection.offer_message
    async def offer(message,epoch):
        declaration=getattr(message,'barrier',None)
        if type(declaration) is MovementDeclaration:declarations.append(declaration)
        return await original(message,epoch)
    peer.connection.offer_message=offer
    return declarations


async def refuses(awaitable):
    try:await awaitable
    except (ValueError,ConnectionError):return
    raise AssertionError('Stale or unsupported movement authority was accepted')


async def check(store,prepared,legacy,fresh):
    checkpoint_fixture(store,legacy,(1006,360,2264))
    events=Events();runtime=GameRuntime(store,prepared,logger=events)
    try:
        peer=MapPeer(runtime);declarations=observe(peer);await peer.login(legacy)
        owner=runtime.roles[legacy['id']];old=declarations[-1]
        target=runtime.map(owner.map_address)
        await target.mailbox.call('invalidate_movement',owner.id,owner.epoch)
        await refuses(owner.mailbox.call('movement_sent',old))
        before=owner.position
        await peer.request(0xc0faa,b'\0'+struct.pack('>hhQ',361,2264,1006))
        assert owner.position==before
        await peer.connection.close()
        again=MapPeer(runtime);await again.login(legacy)
        current=runtime.roles[legacy['id']]
        await refuses(current.mailbox.call('movement_sent',old))
        await again.request(0xc0faa,b'\0'+struct.pack('>hhQ',361,2264,1006))
        assert current.position.value==(1006,361,2264)
        # The real ingress rejects unsupported state-changing input; closing
        # is what the socket runner does when receive raises ConnectionError.
        await refuses(again.connection.receive(again.output.transform(frame(0xc0fcf,b'\0'*5))))
        before=current.position
        await target.mailbox.call('location',current.id,current.epoch)
        await again.request(0xc0faa,b'\0'+struct.pack('>hhQ',362,2264,1006))
        assert current.position==before
        await again.connection.close()

        # Natural fresh intro, matching CEnd transaction, and native location0.
        peer=MapPeer(runtime);writer=GatedWriter();peer.writer=peer.connection.writer=writer
        declarations=observe(peer);await peer.login(fresh)
        owner=runtime.roles[fresh['id']]
        route=load_newbie_routes()[(9,fresh['school'])]
        initial=declarations[-1]
        await refuses(owner.mailbox.call('movement_sent',initial))
        writer.remaining=1
        pending=asyncio.create_task(peer.request(END_PLAY_CG,struct.pack('>i',route.intro_movie_id)))
        try:
            await asyncio.wait_for(writer.entered.wait(),2)
            location=await runtime.map(owner.map_address).mailbox.call('location',owner.id,owner.epoch)
            before=owner.position
            stop=b'\0'+struct.pack('>hhQ',location.x,location.y,location.address.map_id)
            await peer.connection.receive(peer.output.transform(frame(0xc0faa,stop)))
            assert owner.position==before
            writer.release.set();replies=await pending
        finally:
            writer.release.set();await asyncio.gather(pending,return_exceptions=True)
        assert replies[-1]==(SET_ROLE_LOCATION,struct.pack('>QhhB',owner.id,location.x,location.y,0))
        after=declarations[-1]
        assert after.source=='authorized_intro_completed'
        events.rows.clear();await peer.request(0xc0faa,stop)
        assert not events.rows
        # Paid/duplicate completion has no new declaration and cannot revive
        # revoked permission: durable success is not a reusable state grant.
        await runtime.map(owner.map_address).mailbox.call('invalidate_movement',owner.id,owner.epoch)
        duplicate=await peer.request(END_PLAY_CG,struct.pack('>i',route.intro_movie_id))
        assert not any(kind==SET_ROLE_LOCATION for kind,_ in duplicate)
        await refuses(owner.mailbox.call('movement_sent',after))
        before=owner.position;await peer.request(0xc0faa,stop);assert owner.position==before
        await peer.connection.close()

        # A rejected queue owns no successful delivery, including a declaration
        # constructed by the real load path before output admission failed.
        class FullPeer(MapPeer):
            async def request(self,kind,body):
                if kind==0xc0005:self.connection.byte_capacity=1
                return await super().request(kind,body)
        peer=FullPeer(runtime);decls=observe(peer)
        try:await peer.login(legacy)
        except AssertionError:pass
        else:raise AssertionError('Queue exhaustion did not reject login output')
        assert peer.connection.closed and decls
        owner=runtime.roles[legacy['id']];before=owner.position
        await refuses(owner.mailbox.call('movement_sent',decls[-1]))
        location=await runtime.map(owner.map_address).mailbox.call('location',owner.id,owner.epoch)
        await refuses(runtime.map(owner.map_address).mailbox.call('move',owner.id,owner.epoch,
            location.version,0xc0faa,b'\0'+struct.pack('>hhQ',362,2264,1006)))
        assert owner.position==before
        await peer.connection.close()

        # The valid pending declaration cannot be attached to a different
        # queued body and acknowledged by that unrelated successful write.
        peer=MapPeer(runtime)
        original=peer.connection.offer_message
        altered=[]
        async def wrong_body(message,epoch):
            declaration=getattr(message,'barrier',None)
            if type(declaration) is MovementDeclaration:
                altered.append(declaration)
                message=SceneMessage(message.kind,message.body+b'\0',declaration)
            return await original(message,epoch)
        peer.connection.offer_message=wrong_body
        try:await peer.login(legacy)
        except AssertionError:pass
        else:raise AssertionError('Mismatched declaration body was sent as successful entry')
        assert altered and peer.connection.closed
        owner=runtime.roles[legacy['id']]
        await refuses(owner.mailbox.call('movement_sent',altered[-1]))
        await peer.connection.close()
        return dict(groups=['generation and old-lease replay refuse; fresh scene restores clear movement',
            'unsupported JumpStop invalidates; its wire byte never selects state',
            'natural intro CEnd commits, exact location0 output restores; duplicate cannot regrant',
            'actual queue exhaustion and closed connection cannot install pending declaration',
            'exact valid declaration with mismatched queued body fails before encoding/write'],
            battle_executed=False,live_service_changed=False,native_gui_verified=False)
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='runtime-movement-terminals-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        legacy=store.create_role(1111,'行走旧档',11,1010109)
        prepared=runtime_storage.prepare(store)
        fresh=store.create_role(1111,'行走剧情新角',11,1010109)
        result=asyncio.run(asyncio.wait_for(check(store,prepared,legacy,fresh),45))
    write_json(OUT/'evidence/runtime-movement-terminals-verification.json',result);print(result)


if __name__=='__main__':main()
