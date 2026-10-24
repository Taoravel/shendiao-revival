"""Supplementary actual-owner294 retries, reconnect and entrance guards.

Canonical damage and occupancy are explicitly controlled fixtures, not a battle
or scene handoff. The network, dispatcher and settlement remain unmodified.
"""
import asyncio
from contextlib import closing
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from currency import read_wallet
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from role_resource_plan import plan_combat_resources
from role_resource_storage import read_role_resources,apply_resource_transition,ResourceNotInitialized
from verify_growth_runtime import role_values
from verify_npc_role_healing_runtime import known_profile
from verify_runtime import Peer
from world_entity_protocol import NPC_SERVICE
import runtime_storage


def state(store,inventory):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN')
        try:resources=read_role_resources(db,1111,inventory.role_id,inventory.epoch,store.resource_rules)
        except ResourceNotInitialized:resources=None
        wallet=tuple((r.currency,r.balance) for r in read_wallet(db,1111,inventory.role_id,
            inventory.epoch,store.currency_rules))
        receipts=tuple((table,tuple(db.execute('SELECT * FROM '+table+' WHERE role_id=? ORDER BY rowid',
            (inventory.role_id,)))) for table in ('npc_role_healing_receipts','npc_command_receipts',
                'role_resource_receipts','role_wallet_receipts'))
        return resources,wallet,receipts


def damage_fixture(store,inventory):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        before=read_role_resources(db,1111,inventory.role_id,inventory.epoch,store.resource_rules)
        plan=plan_combat_resources(before,80,60,store.resource_rules)
        apply_resource_transition(db,1111,inventory.role_id,inventory.epoch,plan,'controlled-later-damage',
            rules=store.resource_rules,equipment_rules=store.equipment_attribute_rules)


async def check(store,prepared,role,unknown,npc):
    runtime=GameRuntime(store,prepared)
    try:
        peer=Peer(runtime);await peer.login(role);owner=runtime.roles[role['id']]
        body=struct.pack('>qi',(npc.map_id<<32)|npc.placement_id,294)
        messages=await peer.request(NPC_SERVICE,body)
        assert (role_values(messages)[60],role_values(messages)[70])==(100,100)
        full=await owner.io(state,store,owner.inventory)
        # Observe the server-generated admitted identity, never synthesize a paid receipt.
        identity=next(rows[0][1] for table,rows in full[2] if table=='npc_role_healing_receipts')
        assert await peer.request(NPC_SERVICE,body)==[]
        assert await owner.io(state,store,owner.inventory)==full
        await owner.io(damage_fixture,store,owner.inventory)
        wounded=await owner.io(state,store,owner.inventory)
        values=role_values(await owner.mailbox.call('receive',NPC_SERVICE,body,request_id=identity))
        assert (values[60],values[70])==(80,60)
        assert await owner.io(state,store,owner.inventory)==wounded
        for attribute in ('transfer','battle'):
            previous=getattr(owner,attribute);setattr(owner,attribute,object())
            try:assert await peer.request(NPC_SERVICE,body)==[]
            finally:setattr(owner,attribute,previous)
            assert await owner.io(state,store,owner.inventory)==wounded
        for invalid in (struct.pack('>qi',(npc.map_id<<32)|npc.placement_id,92),body+b'\0',
                struct.pack('>qi',(npc.map_id<<32)|9999,294)):
            assert await peer.request(NPC_SERVICE,invalid)==[]
            assert await owner.io(state,store,owner.inventory)==wounded
        old_epoch=owner.epoch
        await peer.connection.close();peer=Peer(runtime);await peer.login(role)
        owner=runtime.roles[role['id']];assert owner.epoch!=old_epoch
        assert await owner.io(state,store,owner.inventory)==wounded
        values=role_values(await owner.mailbox.call('receive',NPC_SERVICE,body,request_id=identity))
        assert (values[60],values[70])==(80,60)
        assert await owner.io(state,store,owner.inventory)==wounded
        assert (role_values(await peer.request(NPC_SERVICE,body))[60])==100
        healed=await owner.io(state,store,owner.inventory)
        assert (healed[0].hp,healed[0].mp,healed[0].version)==(100,100,3)
        assert dict(healed[1])['cash']==940 and dict(healed[1])['bound_silver']==500
        await peer.connection.close()
        peer=Peer(runtime);await peer.login(unknown);owner=runtime.roles[unknown['id']]
        before=await owner.io(state,store,owner.inventory)
        assert before[0] is None
        assert await peer.request(NPC_SERVICE,body)==[]
        assert await owner.io(state,store,owner.inventory)==before
        return {'passed':['fresh full treatment rejects without fees, resources or receipt changes',
            'actual admitted server identity replay preserves later controlled80/60 and original cash970',
            'controlled loading/battle occupancy gates reject treatment before settlement',
            'unbound family92, malformed body and unknown NPC key reject without mutation',
            'new authenticated lease restores current wounds; paid retry does not heal or charge',
            'fresh native request after wounds heals once and charges a new30; cash940/bound500',
            'actual unknown-resource role refuses without migration, fee or receipt creation'],
            'state_gate_fixtures_only':True,'damage_fixture_only':True,'battle_executed':False,
            'scene_handoff_executed':False,'native_gui_verified':False,'live_database_modified':False}
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'healer-guards.sqlite3')
        role=store.create_role(1111,'治疗接线围栏',11,1010109)
        unknown=store.create_role(1111,'治疗来源未知',11,1010109)
        prepared=runtime_storage.prepare(store)
        known_profile(store,role);known_profile(store,unknown,migrated=False)
        npc=next(p for ps in store.npc_resources[0].values() for p in ps if p.npc_id==10380)
        for current in (role,unknown):
            epoch=store.acquire_lease(1111,current['id'])
            assert store.save_checkpoint(1111,current['id'],epoch,(npc.map_id,npc.x,npc.y),1)
        report=asyncio.run(check(store,prepared,role,unknown,npc))
    write_json(OUT/'evidence/npc-role-healing-guards.json',report);print(report)


if __name__=='__main__':main()
