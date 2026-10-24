"""Committed task growth must reach live role and social-directory snapshots.

Disposable original NPC/dialogue flow; no battle, listener or live client.
"""
import argparse
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from item_effects import VitalState
from role_growth import initialize_growth
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline
from task_protocol import C_COMMIT_SCENARIO_QUEST
from verify_runtime import Peer
from world_entity_protocol import VISIT_NPC
from wire import read_octets,read_compact
import runtime_storage


class GrowthPeer(Peer):
    async def request(self,kind,body):
        replies=await super().request(kind,body)
        for response,payload in replies:
            if response==0xc0006:self.world_body=payload
        return replies


def world_vitals(peer):
    _,pos=read_octets(peer.world_body,8)
    level=struct.unpack_from('>i',peer.world_body,pos)[0]
    return level,struct.unpack_from('>5i',peer.world_body,pos+24)


def role_values(frames):
    result={}
    for kind,body in frames:
        if kind==0xc32c8:
            count,pos=read_compact(body)
            assert len(body)==pos+count*8
            result.update(struct.unpack_from('>if',body,pos+i*8) for i in range(count))
    return result


async def check(store,prepared,role,npc):
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime);await peer.login(role)
        assert world_vitals(peer)==(1,(70,100,100,40,100)), 'Explicit initial role profile lost wounds'
        first_values=role_values(peer.initial)
        assert {k:first_values[k] for k in (490,500,60,70,140,150)}=={490:1,500:0,60:70,70:40,140:100,150:100}
        owner=runtime.roles[role['id']]
        key=(npc.map_id<<32)|npc.placement_id
        command=struct.pack('>iQi',100192,key,0)
        await owner.mailbox.call('offer_task',100192)
        await peer.request(VISIT_NPC,struct.pack('>q',key))
        await peer.request(C_COMMIT_SCENARIO_QUEST,command)
        completion=await peer.request(C_COMMIT_SCENARIO_QUEST,command)
        current_values=role_values(completion)
        assert {k:current_values[k] for k in (490,500,60,70,140,150,80,110)}=={
            490:2,500:5,60:80,70:46,140:110,150:106,80:24,110:44}
        with closing(store.connect()) as db:
            row=db.execute('SELECT r.level,p.experience FROM roles r JOIN role_progress p ON p.role_id=r.id WHERE r.id=?',
                           (role['id'],)).fetchone()
        assert row==(2,61),('Fresh NPC completion did not exercise growth',row)
        social=runtime.social_runtime.endpoints[role['id']]
        observed={'database_level':row[0],'database_experience':row[1],
            'role_level':owner.role['level'],'snapshot_level':owner.snapshot().level,
            'online_directory_level':runtime.online[role['id']].level,
            'social_endpoint_level':social.snapshot.level,
            'social_sender_level':social.domain.snapshot.level}
        observed['levels_consistent']=all(value==row[0] for name,value in observed.items()
                                          if name.endswith('_level'))
        await peer.connection.close()
        peer=GrowthPeer(runtime);await peer.login(role)
        assert world_vitals(peer)==(2,(80,110,110,46,106)), 'Reconnect reset committed wounds/maxima'
        resumed=role_values(peer.initial)
        assert {k:resumed[k] for k in current_values}==current_values
        observed['world_entry_growth_and_reconnect_verified']=True
        return observed
    finally:
        await runtime.close()


def main():
    args=argparse.ArgumentParser();args.add_argument('--expect-stale',action='store_true')
    options=args.parse_args()
    with tempfile.TemporaryDirectory(prefix='growth-runtime-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        role=store.create_role(1111,'成长联调',11,1010109)
        # This slice tests an explicitly migrated legacy profile. Fresh roles
        # now have creation provenance and are covered without manual baselines
        # by verify_new_character_growth.py instead.
        prepared=runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
            baseline=AttributeBaseline(role['id'],1,0,(10,10,10,10,10),(100,100,20,5,40,20,10,20,5))
            initialize_attribute_baseline(db,1111,role['id'],epoch,baseline,growth,store.attribute_rules,
                VitalState(role['id'],0,70,100,40,100))
        npc=next(p for p in store.npc_resources[0][1006] if p.npc_id==10899)
        store.save_position(1111,role['id'],(npc.map_id,npc.x,npc.y))
        result=asyncio.run(check(store,prepared,role,npc))
    result.update(database='disposable',live_server_changed=False,native_gui_verified=False,battle_executed=False)
    suffix='baseline' if options.expect_stale else 'verification'
    write_json(OUT/f'evidence/growth-runtime-{suffix}.json',result)
    print(result)
    if options.expect_stale:
        assert not result['levels_consistent'],'Stale-level baseline no longer reproduces'
    else:
        assert result['levels_consistent'],'Committed growth left live role/social snapshots stale'


if __name__=='__main__': main()
