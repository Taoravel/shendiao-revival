"""Historical transfer results cannot project over later map membership.

Actual MapOwner/SerialOwner/maze commands. Initial memberships and successful
send receipts are explicit trusted map-Interface fixtures, not GUI or login.
"""
import asyncio
from dataclasses import replace
import time
from game_runtime import MapOwner,Position
from inspect_client import OUT,write_json
from runtime_movement import load_movement_policy
from world_catalog import maps,maze_grids
from world_protocol import ENTER_SCENE,scene_entry
from verify_world_resource_runtime import points


async def declaration(owner,location,*,confirm=True):
    receipt=await owner.mailbox.call('declare_movement',location.role_id,location.login_epoch,
        location,1,'controlled-transfer-replay',ENTER_SCENE,scene_entry(location.position,reason=0),'normal_scene')
    if confirm:
        await owner.mailbox.call('movement_sent',location.role_id,location.login_epoch,receipt,False)
    return receipt


async def movable(owner,current):
    import struct
    before=await owner.mailbox.call('location',current.role_id,current.login_epoch)
    assert before==current,'Historical receipt changed current public membership'
    body=b'\0'+struct.pack('>hhQ',current.x,current.y,current.address.map_id)
    moved,_=await owner.mailbox.call('move',current.role_id,current.login_epoch,current.version,0xc0faa,body)
    assert moved.value==current.position and moved.version==current.version+1


async def check(kind,*,same_epoch=False,idempotent=False):
    catalog,grids,policy=maps(),maze_grids(),load_movement_policy()
    source,target=(MapOwner(mid,catalog,maze=grids[mid],movement_policy=policy) for mid in (1006,1007))
    try:
        start=points(1006,catalog,grids[1006])[0]
        end=points(1007,catalog,grids[1007])[0]
        initial=Position(1,'old-transfer-epoch',(1006,*start),1,(start[0]//16,start[1]//16))
        await source.mailbox.call('join',initial)
        location=await source.mailbox.call('location',1,initial.epoch)
        offer=await source.mailbox.call('authorized_transfer',1,initial.epoch,location,
            (1007,*end),int(time.monotonic()*1000)+10000)
        reservation=await target.mailbox.call('reserve',offer)
        frozen=await source.mailbox.call('freeze',reservation)
        if kind=='resume':
            cancellation=await target.mailbox.call('cancel',reservation)
            result=await source.mailbox.call('resume',cancellation)
            owner,arg=source,cancellation
        elif kind=='freeze':
            owner,arg=source,reservation
            result=frozen.source
        else:
            receipt=await target.mailbox.call('activate',frozen)
            if kind=='activate':
                owner,arg,result=target,frozen,receipt.location
            else:
                await source.mailbox.call('finalize',receipt)
                assert await source.mailbox.call('finalize',receipt)==receipt
                owner,arg,result=source,receipt,frozen.source
        if idempotent:
            current=await owner.mailbox.call('location',1,initial.epoch)
            if kind=='activate':
                pending=await declaration(owner,current,confirm=False)
                await owner.mailbox.call(kind,arg)
                current=await owner.mailbox.call('ready',current)
                await owner.mailbox.call('movement_sent',1,initial.epoch,pending,True)
            else:
                await declaration(owner,current)
                await owner.mailbox.call(kind,arg)
        else:
            if kind=='freeze':
                # Frozen members cannot be left through the public Interface.
                # Resolve that old handoff first; its old freeze must reject.
                cancelled=await target.mailbox.call('cancel',reservation)
                await source.mailbox.call('resume',cancelled)
            elif kind=='activate':
                await target.mailbox.call('ready',receipt.location)
            old=owner.domain.location(1)
            if old is not None:await owner.mailbox.call('leave',1,initial.epoch)
            epoch=initial.epoch if same_epoch else 'replacement-transfer-epoch'
            point=start if owner is source else end
            await owner.mailbox.call('join',Position(1,epoch,(owner.domain.address.map_id,*point),10,
                (point[0]//16,point[1]//16)))
            current=await owner.mailbox.call('location',1,epoch)
            await declaration(owner,current)
            try:await owner.mailbox.call(kind,arg)
            except ValueError:
                assert kind=='freeze','Unexpected error hid a historical projection result'
            else:
                assert kind!='freeze','Resolved historical freeze was incorrectly accepted'
        await movable(owner,current)
        return dict(operation=kind,same_epoch=same_epoch,idempotent=idempotent,
            current_member_and_context_preserved=True)
    finally:
        await source.mailbox.close();await target.mailbox.close()


def main():
    async def all_cases():
        result=[]
        for kind in ('freeze','activate','resume','finalize'):
            for same_epoch in (False,True):result.append(await check(kind,same_epoch=same_epoch))
        for kind in ('activate','resume'):result.append(await check(kind,idempotent=True))
        return result
    result=dict(cases=asyncio.run(asyncio.wait_for(all_cases(),30)),
        trusted_membership_and_send_receipt_fixtures=True,actual_map_and_context_commands=True,
        live_service_changed=False,native_gui_verified=False,battle_executed=False)
    write_json(OUT/'evidence/runtime-transfer-replays-verification.json',result)
    print(dict(all_passed=True,cases=len(result['cases'])))


if __name__=='__main__':main()
