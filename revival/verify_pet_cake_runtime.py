"""Real encrypted Owner cake path with actual common receipts and root source.

Disposable known legacy-resource fixture, no shim/dispatcher replacement,
live listener, GUI, movement or battle.
"""
import asyncio
from functools import partial
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import struct
import sqlite3
import time
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import AssetChange,USE_ITEM,REFRESH_PET
from pet_skill_expiry import TimedSkillGrant
from role_resource_storage import read_role_resources
from role_equipment_storage import current_resource_profile
from verify_growth_runtime import GrowthPeer
from verify_resource_owner_runtime import fixture
from research_pet_cake_protocol import native_notice
from inspect_client import OUT,write_json
import runtime_storage


def current(store,owner,*,strict=True):
    with closing(owner.inventory.accounts.connect()) as db:
        db.execute('BEGIN')
        assets=owner.inventory.immutable_snapshot_transaction(db)
        resources=read_role_resources(db,1111,owner.id,owner.epoch,store.resource_rules)
        if strict:current_resource_profile(db,1111,owner.id,owner.epoch,assets,
            equipment_rules=store.equipment_attribute_rules,resource_rules=store.resource_rules)
        counts=tuple(db.execute('SELECT COUNT(*) FROM '+table+' WHERE role_id=?',(owner.id,)).fetchone()[0] for table in
            ('role_inventory_commands','role_resource_receipts','inventory_pet_cake_receipts'))
        assert (resources.hp,resources.mp,resources.version)==(10,20,0)
        return assets,resources,counts


def mutate_fixture(store,inv,pet,identity,*,timed=False):
    with closing(inv.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,pet)
        if timed:
            now=time.time_ns()//1000000
            inv.grant_pet_timed_skill(db,TimedSkillGrant(identity,pet,200011,now+600000,'known-cake-runtime-fixture',p.skills.version),inv.epoch,now)
        else:inv.change_pet_growth(db,pet,identity,p.progress.state.version,'resources',(0,3))
        runtime_storage._synchronize_source(db,store,inv,identity+':source',replayed=False)


async def check(store,prepared,role):
    rt=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(rt);await peer.login(role);owner=rt.roles[role['id']]
        await owner.mailbox.call('settle',AssetChange('cake-runtime-assets',grants=((31268,8),(31269,1,1)),pets=(500001,)))
        before=current(store,owner);pet=before[0].pets[0].id
        key=next(i.id for i in before[0].items if i.template_id==31268)
        one=next(i.id for i in before[0].items if i.template_id==31269)
        body=struct.pack('>iiQ',key,1,pet);one_body=struct.pack('>iiQ',one,1,pet)
        response=await peer.request(USE_ITEM,body)
        assert native_notice(next(b for t,b in response if t==0xc1775))==(145135,0,('外功','7','19'))
        after=current(store,owner);assert after[0].pets[0].cake.count==1
        with closing(store.connect()) as db:
            accepted=db.execute('SELECT request_id FROM role_inventory_commands WHERE role_id=? ORDER BY rowid DESC LIMIT 1',(owner.id,)).fetchone()[0]
        # An identical NEW encrypted click is a fresh accepted command.
        await peer.request(USE_ITEM,body);second=current(store,owner)
        assert second[0].pets[0].cake.count==2
        paid=await owner.mailbox.call('receive',USE_ITEM,body,request_id=accepted)
        assert current(store,owner)==second and all(t!=0xc1775 for t,b in paid)
        # Real common receipt abort is after cake and source CAS. No fake hook.
        with closing(store.connect()) as db:
            db.execute("CREATE TRIGGER cake_common_fail BEFORE INSERT ON role_inventory_commands BEGIN SELECT RAISE(ABORT,'actual cake common receipt failed'); END")
        before=current(store,owner)
        try:await owner.mailbox.call('receive',USE_ITEM,body,request_id='cake-runtime-common-fault')
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Actual common receipt failure was bypassed')
        assert current(store,owner)==before
        with closing(store.connect()) as db:db.execute('DROP TRIGGER cake_common_fail')
        await owner.mailbox.call('receive',USE_ITEM,body,request_id='cake-runtime-common-fault')
        assert current(store,owner)[0].pets[0].cake.count==3
        # The clock is an external boundary, deliberately invalid after source
        # and common receipt writes to prove late representation rollback.
        before=current(store,owner)
        with patch.object(owner.inventory,'clock_now_ms',return_value=-1):
            try:await owner.mailbox.call('receive',USE_ITEM,body,request_id='cake-runtime-clock-fault')
            except ValueError:pass
            else:raise AssertionError('Invalid native clock committed a cake')
        assert current(store,owner)==before
        await owner.mailbox.call('receive',USE_ITEM,body,request_id='cake-runtime-clock-fault')
        await owner.io(partial(mutate_fixture,timed=True),store,owner.inventory,pet,'cake-runtime-timed')
        now=time.time_ns()//1000000
        response=await peer.request(USE_ITEM,one_body)
        assert all(i.id!=one for i in current(store,owner)[0].items)
        assert next(struct.unpack('>q',b)[0] for t,b in response if t==0xc0007)>=now
        with closing(store.connect()) as db:
            one_request=db.execute('SELECT request_id FROM role_inventory_commands WHERE role_id=? ORDER BY rowid DESC LIMIT 1',(owner.id,)).fetchone()[0]
        before=current(store,owner)
        base_connect=store.connect
        def readonly_connect():
            db=base_connect();db.set_authorizer(lambda a,*args:sqlite3.SQLITE_DENY if a in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            return db
        with patch.object(store,'connect',side_effect=readonly_connect):
            paid=await owner.mailbox.call('receive',USE_ITEM,one_body,request_id=one_request)
        assert current(store,owner)==before
        assert next(struct.unpack('>q',b)[0] for t,b in paid if t==0xc0007)>=now
        await owner.io(mutate_fixture,store,owner.inventory,pet,'cake-runtime-later-wound')
        wounded=current(store,owner)
        assert wounded[0].pets[0].progress.state.hp==0
        await owner.mailbox.call('receive',USE_ITEM,body,request_id=accepted)
        assert current(store,owner)==wounded
        # Real reconnect changes owner/lease, preserving all committed states.
        old=owner;await peer.connection.close()
        peer=GrowthPeer(rt);await peer.login(role);owner=rt.roles[role['id']]
        assert current(store,owner)==wounded
        try:await old.mailbox.call('receive',USE_ITEM,body,request_id=accepted)
        except ValueError:pass
        else:raise AssertionError('Old cake owner remained active')
        await owner.mailbox.call('receive',USE_ITEM,body,request_id=accepted)
        assert current(store,owner)==wounded
        # Paid source must not repair an unrelated later unsynchronized grant.
        await owner.io(owner.inventory.grant_item,32001,1,0,10)
        pending=current(store,owner,strict=False)
        try:await owner.mailbox.call('receive',USE_ITEM,body,request_id=accepted)
        except ValueError:pass
        else:raise AssertionError('Paid cake repaired unrelated pending source')
        assert current(store,owner,strict=False)==pending
        await peer.connection.close()
    finally:await rt.close()


def main():
    with TemporaryDirectory(prefix='cake-actual-owner-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'原生年糕链路',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for rows in store.npc_resources[0].values() for p in rows if p.npc_id==10004)
        fixture(store,role,npc)
        asyncio.run(check(store,prepared,role))
    write_json(OUT/'evidence/pet-cake-runtime-verification.json',{
        'passed':['actual encrypted RC4/MPPC CUseItem ->RoleOwner/shared dispatcher/cake/source/common receipt -> original native notice',
            'identical new wire uses fresh accepted ID; old committed ID readonly current reply without repeat effect',
            'real common receipt abort and invalid external native clock roll BASE/cake/item/source/all receipts back; same failed ID succeeds once',
            'last bound item deletion and timed-skill fresh/paid Unix clock work; actual shared paid path SQL-readonly',
            'later pet death preserved on retry; reconnect retains state and stale owner refuses',
            'unrelated pending source rejected without repair; roleHP10/MP20/version0 unchanged'],
        'database':'disposable','shared_dispatcher_replaced':False,'live_server_changed':False,'native_gui_verified':False,
        'battle_executed':False})
    print('PASS actual encrypted cake Owner/source/common receipts, rollback, timed deleted-key replay and reconnect')


if __name__=='__main__':main()
