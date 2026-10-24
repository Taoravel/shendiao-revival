"""Social recipient scene fencing; shared connection/ticket hook is an Adapter."""
from dataclasses import replace,FrozenInstanceError
import argparse,asyncio,json,tempfile
from pathlib import Path
from types import SimpleNamespace
from accounts import AccountStore
from social_owner import Delivery,RoleSnapshot,SQLiteSocialStore
from social_runtime import SocialEndpoint,SnapshotUpdate
from runtime_core import BlockingIO
from guild_runtime import GuildWake
from family_runtime import FamilyWake
from group_runtime import GroupDelivery,GroupHistoryDelivery
from faction_runtime import OrganizationDelivery
from faction_domain import OrganizationBroadcast
from inspect_client import OUT,write_json
import social_protocol as p


def check_delivery_contract():
    legacy=Delivery(1,100,123,b'body')
    assert legacy.scene_key is None
    scoped=Delivery(1,100,123,b'body',scene_key=(1394,70001,0))
    assert scoped.scene_key==(1394,70001,0)
    assert replace(scoped,scene_key=(1394,1394,0)).scene_key==1394
    assert replace(scoped,scene_key=1394).scene_key==1394
    try:scoped.scene_key=1394
    except FrozenInstanceError:pass
    else:raise AssertionError('Mutable scene delivery')
    for key in (True,False,0,-1,2**63,[],[1394,70001,0],(1394,70001),
            (1394,70001,0,0),(True,70001,0),(1394,True,0),(1394,70001,False),
            (0,70001,0),(1394,0,0),(1394,70001,-1),(1394,70001,2**63),(1394,'70001',0)):
        try:replace(scoped,scene_key=key)
        except ValueError:pass
        else:raise AssertionError(f'Invalid scene key accepted: {key!r}')
    try:Delivery(1,100,123,b'body',1394)
    except TypeError:pass
    else:raise AssertionError('Scene key must be keyword-only')
    inherited=(GuildWake(1,100,0,b'',8,'family-token','member-token'),
        FamilyWake(1,100,0,b'',9,'member-token'),GroupDelivery(1,100,0,b'',10,'generation',3),
        GroupHistoryDelivery(1,100,0,b'',10,'generation',3),
        OrganizationDelivery(1,100,0,b'',OrganizationBroadcast(9,1,2,(1,2),'text',())))
    assert all(value.scene_key is None for value in inherited)
    assert all(replace(value,scene_key=(1394,1394,0)).scene_key==1394 for value in inherited)


async def check_late_delivery(directory):
    store=AccountStore(Path(directory)/'social.db')
    role=store.create_role(1111,'场景收件',12,1010101)
    sender=store.create_role(1111,'场景发件',12,1010101)
    epoch=store.acquire_lease(1111,role['id'])
    repository=SQLiteSocialStore(store.path);repository.initialize()
    first=RoleSnapshot(role['id'],epoch,role['name'],40,12,1010101,1394,(1394,70001,0))
    calls=[];direct=[]
    async def hook(snapshot,delivery):calls.append((snapshot,delivery));return True
    target=SimpleNamespace(offer=lambda *args:direct.append(args))
    io=BlockingIO(partitions=1,workers_per_partition=1,capacity=8)
    rt=SimpleNamespace(social_store=repository,social_limits=dict(max_contacts=100,max_text=256),
        io=io,connections={first.role_id:target},offer_scene_channel=hook,log=lambda **_:None)
    router=SimpleNamespace(rt=rt,endpoints={})
    endpoint=SocialEndpoint(router,first,8);router.endpoints[first.role_id]=endpoint
    body=p.chat_message(sender,p.CURRENT_CHANNEL,'迟到的当前消息')
    old=Delivery(first.role_id,epoch,p.CHAT_RECEIVE,body,scene_key=first.scene_key)
    gate=asyncio.Event()
    async def late():await gate.wait();await endpoint.call('delivery',old)
    pending=asyncio.create_task(late())
    second=replace(first,scene_scope=(1394,70002,0))
    try:
        await endpoint.call('snapshot',SnapshotUpdate(second,1))
        gate.set();await pending
        assert calls==direct==[],'Old instance delivery bypassed the shared scene hook'
        assert endpoint.metrics['scene_delivery_stale']==1
        current=replace(old,scene_key=second.scene_key)
        await endpoint.call('delivery',current)
        assert calls==[(second,current)] and direct==[]
        del rt.offer_scene_channel
        await endpoint.call('delivery',current)
        assert len(calls)==1 and direct==[] and endpoint.metrics['scene_delivery_unavailable']==1
        async def refused(snapshot,delivery):calls.append((snapshot,delivery));return False
        rt.offer_scene_channel=refused
        await endpoint.call('delivery',current)
        assert direct==[] and endpoint.metrics['scene_delivery_rejected']==1
        # World/school and other legacy deliveries retain the direct path.
        for channel in (p.WORLD_CHANNEL,p.SCHOOL_CHANNEL):
            message=p.chat_message(sender,channel,'旧频道仍正常')
            await endpoint.call('delivery',Delivery(first.role_id,epoch,p.CHAT_RECEIVE,message))
            assert direct[-1]==(p.CHAT_RECEIVE,message,epoch)
        assert len(direct)==2
        rt.offer_scene_channel=hook
        repository.contact(first.role_id,sender['id'],True,100)
        repository.move_group(first.role_id,sender['id'],p.GROUP_BLACK)
        count=len(calls)
        await endpoint.call('delivery',current)
        assert len(calls)==count and len(direct)==2 and endpoint.metrics['filtered']==1
        repository.move_group(first.role_id,sender['id'],p.GROUP_FRIEND)
        await endpoint.call('delivery',replace(current,login_epoch='old-epoch'))
        assert len(calls)==count and endpoint.metrics['stale_delivery']==1
        public=replace(second,scene_scope=(1394,1394,0))
        await endpoint.call('snapshot',SnapshotUpdate(public,2))
        public_delivery=replace(current,scene_key=1394)
        await endpoint.call('delivery',public_delivery)
        assert calls[-1]==(public,public_delivery) and len(direct)==2
    finally:
        gate.set();await pending
        await endpoint.close();await io.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,default=OUT/'evidence/social-scene-delivery-verification.json')
    args=parser.parse_args()
    check_delivery_contract()
    with tempfile.TemporaryDirectory() as directory:asyncio.run(check_late_delivery(directory))
    report=dict(passed=['keyword-only frozen Delivery key preserves legacy four arguments and public normalization',
        'bool/mutable/malformed/negative/out-of-signed63 keys refuse',
        'GuildWake/FamilyWake/GroupDelivery/history/OrganizationDelivery retain inherited constructors',
        'real SocialEndpoint rejects delayed old-instance delivery before hook or generic target offer',
        'matching complete key invokes only the asynchronous shared hook',
        'missing/refused hook never falls back to unscoped target offer and counts refusal',
        'None world/school deliveries retain their original recipient path',
        'real persisted blacklist and stale epoch filter before scene hook; explicit public key interoperates'],
        scope='actual recipient endpoint/mailbox and SQLite relation filter; recording shared hook/connection Adapters',
        shared_scene_ticket_pin_connection_drain_verified=False,native_gui_verified=False,
        shared_entry_files_edited=False,live_server_changed=False)
    write_json(args.report,report);print(json.dumps(report))
