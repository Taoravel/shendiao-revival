"""Deterministic actual receive-batch cancellation; no DB/socket/client.

Default asserts safe terminal cleanup and fails on the current leaked suffix.
--expect-leak asserts the precise current defect, with a noncancelled control.
"""
import argparse
import asyncio
import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

# Resolve all game_runtime types consistently from an isolated candidate when
# requested; loading just ConnectionOwner under a foreign alias would break
# ScopedSceneMessage's exact isinstance identity.
if __name__=='__main__':
    bootstrap=argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument('--runtime-source',type=Path)
    selected,_=bootstrap.parse_known_args()
    if selected.runtime_source is not None:
        import inspect_client
        source=selected.runtime_source.resolve()
        if not (source/'game_runtime.py').is_file():raise ValueError('Runtime source directory required')
        inspect_client.OUT=source
        sys.path.insert(0,str(source))

from game_runtime import GameRuntime,ConnectionOwner,MapOwner,Position,SceneSendBarrier
from runtime_story_maps import RuntimeStoryMaps
from world_story_instances import StoryInstanceRules,StoryInstance,StoryInstanceIntent
from world_owner import MapAddress
from wire import frame


class Writer:
    """Transport Adapter only; no socket and no real recipient."""
    def write(self,data):pass
    async def drain(self):await asyncio.sleep(0)
    def close(self):pass


async def observe(*,cancel_receive,producer='receive'):
    if producer not in ('receive','tick','send_barrier'):raise ValueError('Unknown producer')
    # Explicit trusted identity/catalog fixtures, not directory authorization.
    rules=StoryInstanceRules('2026-10-23.story-instance.1','newbie_bloodmark_dream',
        1501,0,2**62,2**63,8,1,128,60000,64,64,None,{(9,11):100106})
    record=StoryInstance(rules.kind,1,1,StoryInstanceIntent('chapter','creation',
        'policy','route',100106),rules.revision,MapAddress(1501,2**62+1,0))
    rt=object.__new__(GameRuntime)
    rt.maps={};rt.roles={};rt.connections={};rt.clients=set();rt.logger=None
    clock=[1000]
    def create(rec):
        owner=MapOwner(rec.address,{1501:{'available':True,'width':4096,'height':4096}},story_rules=rules)
        rt.maps[rec.address]=owner
        return owner
    def forget(address,owner):
        assert rt.maps.pop(address) is owner
    manager=RuntimeStoryMaps(rules,create,forget,clock=lambda:clock[0])
    rt.story_maps=manager
    owner=await manager.get_map(record,request_id='load',deadline_ms=10000)
    await owner.mailbox.call('join',Position(1,1,(1501,1008,1264),1,(63,79)))
    role=SimpleNamespace(id=1,epoch=1,map_address=record.address,poisoned=False,
        scene_token='token',valid=lambda:None)
    rt.roles[1]=role
    messages=[]
    async def scene_messages(current,replies):
        result=await GameRuntime.scene_messages(rt,current,replies)
        messages.extend(result)
        return result
    rt.scene_messages=scene_messages
    async def dispatch(connection,kind,body):
        # Gameplay/auth dispatch is a seam. Scene construction is the actual
        # GameRuntime implementation, not fabricated delivery tickets.
        return await rt.scene_messages(role,[(11,b'a'),(12,b'b')])
    async def disconnect(connection):
        # No persistence/lease side effects. Actual map leave still runs on
        # its pinned mailbox, after the real finish command is released.
        await owner.mailbox.call('leave',1,1)
        rt.connections.pop(1,None);rt.roles.pop(1,None)
    rt.dispatch=dispatch;rt.disconnect=disconnect
    conn=ConnectionOwner(rt,Writer())
    await conn.queue.join()  # Actual opening pump has completed.
    conn.role_id=conn.epoch=1;rt.connections[1]=conn
    async def role_reply(operation,*args):
        assert operation in ('tick','scene_sent')
        if operation=='scene_sent':conn.byte_capacity=1
        return [(11,b'a'),(12,b'b')]
    role.mailbox=SimpleNamespace(call=role_reply)
    if producer!='send_barrier':conn.byte_capacity=1
    entered,release=asyncio.Event(),asyncio.Event()
    delegate=owner.control_mailbox.handler
    async def held_finish(command):
        if command.operation=='finish_scene_delivery':
            entered.set();await release.wait()
        return await delegate(command)
    owner.control_mailbox.handler=held_finish
    if producer=='receive':
        receiving=asyncio.create_task(conn.receive(frame(999,b'x')))
    elif producer=='tick':
        class Reader:
            async def read(self,count):raise TimeoutError('Controlled idle read tick')
        receiving=asyncio.create_task(conn.run(Reader()))
    else:
        barrier=SceneSendBarrier(1,1,conn.generation,'synthetic',1,b'barrier-trigger')
        assert conn.offer(0xc0fa9,b'barrier-trigger',1,barrier=barrier)
        receiving=conn.pump
    try:
        await asyncio.wait_for(entered.wait(),1)
        assert len(messages)==2 and conn.queue.empty()
        if cancel_receive:
            if producer!='send_barrier':receiving.cancel()
            # close itself cancels the barrier-producing send pump exactly
            # once. A second direct pump.cancel() would invent another race.
            closing=asyncio.create_task(conn.close())
            # A correct batch finally may WAIT for suffix cleanup behind this
            # held finish. Do not demand cancellation completion before its
            # dependency can terminate. Observe actual terminal or separately
            # tracked suffix cleanup after bounded event-loop scheduling.
            boundary=asyncio.Event()
            asyncio.get_running_loop().call_soon(boundary.set)
            await boundary.wait();await asyncio.sleep(0)
            release.set()
            outcome=(await asyncio.gather(receiving,return_exceptions=True))[0]
            assert isinstance(outcome,asyncio.CancelledError)
            await closing
        else:
            release.set()
            if producer=='send_barrier':await conn.queue.join()
            else:await receiving
            await conn.close()
        while manager.work:
            await asyncio.gather(*tuple(manager.work),return_exceptions=True)
        await owner.control_mailbox.queue.join()
        clock[0]=61000
        snapshot=await owner.control_mailbox.call('inspect_lifecycle',clock[0])
        unload_rejection=None
        if snapshot.pending_scene_deliveries:
            try:
                manager.pool.begin_unload(owner.story_handle,request_id='after-full-idle',now_ms=clock[0])
            except ValueError as error:unload_rejection=str(error)
            else:raise AssertionError('Pending scene unexpectedly allowed unload')
        # Public capacity probe supplies an independent occupied-pin witness;
        # the finding does not rely on reading pool._entries/private maps.
        acquired=[];capacity_rejection=None
        for index in range(rules.pins_per_projection):
            try:
                acquired.append(manager.pool.acquire(record,request_id='free-slot-'+str(index),
                    deadline_ms=62000,now_ms=clock[0],actor_state='static_original'))
            except ValueError as error:
                capacity_rejection=str(error);break
        for pin in acquired:assert manager.pool.release(pin,now_ms=clock[0])
        result={'producer':producer,'cancel_receive':cancel_receive,'prepared_replies':len(messages),
            'send_rejected':conn.metrics['send_rejected'],'queue_size_after_close':conn.queue.qsize(),
            'pending_bytes_after_close':conn.pending_bytes,'members_after_close':snapshot.members,
            'pending_deliveries_after_close':snapshot.pending_scene_deliveries,
            'finish_tasks_after_terminal':len(manager.work),
            'free_pin_slots_public':len(acquired),'pin_budget':rules.pins_per_projection,
            'capacity_rejection':capacity_rejection,'unload_rejection_at_61000':unload_rejection}
        assert result['queue_size_after_close']==result['pending_bytes_after_close']==result['members_after_close']==0
        assert result['finish_tasks_after_terminal']==0
        return result
    finally:
        release.set()
        if not receiving.done():
            receiving.cancel();await asyncio.gather(receiving,return_exceptions=True)
        if not conn.cleanup_started:await conn.close()
        # Test teardown possesses the otherwise abandoned suffix only because
        # the dispatch seam captured it; this is not production self-recovery.
        for message in messages:await manager.finish_delivery(message.delivery)
        await manager.close();await owner.mailbox.close()


def source_hashes():
    names=('game_runtime','runtime_story_maps','runtime_core','world_owner',
        'world_story_projection_pool','world_story_instances','connection_codec','wire')
    return {name:{'path':str(Path(importlib.import_module(name).__file__).resolve()),
        'sha256':hashlib.sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest()}
        for name in names}


async def check():
    """Return bounded structured observations; caller can assert_expected()."""
    sources=source_hashes()
    results=[await observe(cancel_receive=cancel,producer=producer)
        for producer in ('receive','tick','send_barrier') for cancel in (False,True)]
    return {'sources':sources,'sources_stable':sources==source_hashes(),
        'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'results':results,'safe_terminal':all(r['pending_deliveries_after_close']==0 and
            r['free_pin_slots_public']==64 for r in results),
        'scope':'actual receive/scene_messages/map delivery and pin termination; synthetic role/dispatch/catalog/transport; no DB/socket/GUI/service'}


def assert_expected(report,*,expect_leak=False):
    assert report['sources_stable'],'Source changed during probe'
    expected_pending,expected_free=(1,63) if expect_leak else (0,64)
    for case in report['results']:
        expected=(expected_pending,expected_free) if case['cancel_receive'] else (0,64)
        assert (case['pending_deliveries_after_close'],case['free_pin_slots_public'])==expected,(
            'Unqueued private reply suffix has no terminal owner after producer cancellation',case)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--expect-leak',action='store_true')
    parser.add_argument('--runtime-source',type=Path)
    parser.add_argument('--report',type=Path,default=Path(__file__).parent/'evidence/world-scene-delivery-abandonment.json')
    args=parser.parse_args()
    report=asyncio.run(asyncio.wait_for(check(),10))
    report['mode']='expect_exact_leak' if args.expect_leak else 'assert_safe_terminal'
    # Persist the same observed result before safety assertion, including red.
    args.report.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))
    assert_expected(report,expect_leak=args.expect_leak)


if __name__=='__main__':main()
