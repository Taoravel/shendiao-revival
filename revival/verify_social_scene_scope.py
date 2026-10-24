"""Scene-key public contract; disposable fixtures, no live map admission."""
from dataclasses import FrozenInstanceError, replace
import asyncio,json,struct,tempfile
from pathlib import Path
from accounts import AccountStore
from game_runtime import GameRuntime
import runtime_storage
from runtime_core import StaleEpoch
from inspect_client import OUT,write_json
from social_owner import RoleSnapshot,RoleSocialOwner,SocialCommand,Publish
import social_protocol as p


def check_snapshot():
    legacy=RoleSnapshot(1,100,'频道角色',40,12,1010101,1394)
    public=replace(legacy,scene_scope=(1394,1394,0))
    first=replace(legacy,scene_scope=(1394,70001,0))
    second=replace(legacy,scene_scope=(1394,70002,0))
    partition=replace(legacy,scene_scope=(1394,70001,1))
    assert legacy.scene_key==public.scene_key==1394
    assert first.scene_key==(1394,70001,0)
    assert len({legacy.scene_key,first.scene_key,second.scene_key,partition.scene_key})==4
    assert legacy.profile()==first.profile()
    try:first.scene_scope=(1394,70002,0)
    except FrozenInstanceError:pass
    else:raise AssertionError('Scene identity is mutable')


def check_invalid_scope():
    legacy=RoleSnapshot(1,100,'频道角色',40,12,1010101,1394)
    invalid=([1394,70001,0],(1394,70001), (1394,70001,0,0),
        (True,70001,0),(1394,True,0),(1394,70001,False),
        (1394,70001,0.0),(1394,'70001',0),(1394,0,0),
        (1394,-1,0),(1394,70001,-1),(1395,70001,0),
        (1394,2**63,0),(1394,70001,2**63),())
    for scope in invalid:
        try:replace(legacy,scene_scope=scope)
        except ValueError:pass
        else:raise AssertionError(f'Invalid scene scope accepted: {scope!r}')
    assert replace(legacy,scene_scope=(1394,2**63-1,2**63-1)).scene_key==(1394,2**63-1,2**63-1)
    # The public no-scope path keeps the original constructor contract.
    assert legacy.scene_scope is None


def command(snapshot,channel=p.CURRENT_CHANNEL):
    body=struct.pack('>i',channel)+p.text('当前实例')+p.text('')+b'\0'
    return SocialCommand(snapshot.role_id,snapshot.login_epoch,'scene-chat',100,p.CHAT_SEND,body)


def check_owner():
    first=RoleSnapshot(1,100,'频道角色',40,12,1010101,1394,(1394,70001,0))
    scopes=((1394,70001,0),(1394,70002,0),(1394,70001,1),None,(1394,1394,0))
    expected=((1394,70001,0),(1394,70002,0),(1394,70001,1),1394,1394)
    for scope,key in zip(scopes,expected):
        snapshot=replace(first,scene_scope=scope)
        owner=RoleSocialOwner(snapshot,None,200,256)
        result=owner.execute(command(snapshot),{},0)
        assert not result.rejection
        assert result.effects==(Publish('scene',key,1,p.CHAT_RECEIVE,
            p.chat_message(first.profile(),p.CURRENT_CHANNEL,'当前实例')),)
        for channel,route in ((p.SCHOOL_CHANNEL,('school',12)),(p.WORLD_CHANNEL,('world',0))):
            other=owner.execute(command(snapshot,channel),{},0)
            assert not other.rejection and (other.effects[0].scope,other.effects[0].partition_key)==route


async def check_runtime(store):
    rt=GameRuntime(store,runtime_storage.prepare(store))
    role=store.roles(1111)[0]
    epoch=store.acquire_lease(1111,role['id'])
    first=RoleSnapshot(role['id'],epoch,role['name'],role['level'],role['school'],role['shape'],
        1394,(1394,70001,0))
    rt.social_runtime.open(first)
    try:
        result=await rt.social_runtime.request(first,command(first),0)
        assert not result.rejection and result.effects[0].partition_key==(1394,70001,0)
        second=replace(first,scene_scope=(1394,70001,1))
        assert await rt.social_runtime.publish(second,1)==second
        result=await rt.social_runtime.request(second,command(second),0,1)
        assert not result.rejection and result.effects[0].partition_key==(1394,70001,1)
        try:await rt.social_runtime.request(first,command(first),0,0)
        except StaleEpoch:pass
        else:raise AssertionError('Stale scope request overwrote committed snapshot')
        result=await rt.social_runtime.request(second,command(second),0,1)
        assert not result.rejection and result.effects[0].partition_key==(1394,70001,1)
    finally:await rt.close()


if __name__=='__main__':
    check_snapshot()
    check_invalid_scope()
    check_owner()
    with tempfile.TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'scene.db')
        store.create_role(1111,'频道角色',12,1010101)
        asyncio.run(check_runtime(store))
    result=dict(passed=['old seven arguments and explicit public scope share integer key',
        'private instance and partition keys remain distinct and immutable',
        'mutable/bool/malformed/mismatched/out-of-range scope rejected',
        'actual RoleSocialOwner emits complete scope and unchanged native chat body',
        'school and world routes retain existing scope',
        'actual SocialRuntime publishes and consumes scope with revision fencing'],
        live_server_changed=False,native_gui_verified=False,
        real_private_admission_verified=False,private_recipient_fanout_verified=False)
    write_json(OUT/'evidence/social-scene-scope-verification.json',result)
    print(json.dumps(result))
