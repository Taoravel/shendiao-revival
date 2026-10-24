"""Actual encrypted clearing through existing Owner/common/source; add seed is trusted."""
import asyncio
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sqlite3
import struct
import time
from accounts import AccountStore
from game_runtime import GameRuntime
from inventory import AssetChange,USE_ITEM,FREE_PET
from verify_growth_runtime import GrowthPeer
from verify_resource_owner_runtime import fixture
from verify_pet_evolution_runtime import current as resource_current
from research_pet_stones_native import native_stone_attributes,native_pet_stones
from research_pet_cake_protocol import native_notice
from pet_skill_expiry import TimedSkillGrant
from inspect_client import OUT,write_json
import runtime_storage


def current(store,owner):
    assets,resources,counts=resource_current(store,owner)
    with closing(store.connect()) as db:
        stones=db.execute('SELECT COUNT(*) FROM inventory_pet_stone_receipts WHERE role_id=?',(owner.id,)).fetchone()[0]
    return assets,resources,(*counts,stones)


def known_stones(store,inv,pet,request='stones:runtime-seed'):
    with closing(store.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');assets=inv.immutable_snapshot_transaction(db)
        key=next(i.id for i in assets.items if i.template_id==70052)
        inv.use_pet_stone(db,key,pet,inv.epoch,request,(0,)*50)
        p=inv.read_pet_state(db,pet);now=time.time_ns()//1000000
        if 200011 not in p.skills.learned:
            inv.grant_pet_timed_skill(db,TimedSkillGrant('stones:runtime-timed',pet,200011,now+600000,'known-stone-fixture',p.skills.version),inv.epoch,now)
        runtime_storage._synchronize_source(db,store,inv,request+':source',replayed=False)


async def check(store,prepared,role):
    rt=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(rt);await peer.login(role);owner=rt.roles[role['id']]
        await owner.mailbox.call('settle',AssetChange('stones:runtime-assets',grants=((70052,3),(70053,3)),pets=(500001,)))
        pet=current(store,owner)[0].pets[0].id
        await owner.io(known_stones,store,owner.inventory,pet)
        before=current(store,owner);p=before[0].pets[0]
        key=next(i.id for i in before[0].items if i.template_id==70053);body=struct.pack('>iiQ',key,1,pet)
        now=time.time_ns()//1000000
        response=await peer.request(USE_ITEM,body)
        assert native_notice(next(b for t,b in response if t==0xc1775))==(150456,0,())
        zeros=tuple((k,0) for k in (1930,1940,1950,1960,1970,1980))
        assert native_stone_attributes(next(b for t,b in response if t==0xc32c9))==zeros
        assert next(struct.unpack('>q',b)[0] for t,b in response if t==0xc0007)>=now
        after=current(store,owner);q=after[0].pets[0]
        assert q.progress.stones.count==0 and q.progress.profile.growth_raw==1006
        assert q.skill_expiry==p.skill_expiry and q.progress.state.hp==p.progress.state.hp
        assert native_pet_stones(next(b for t,b in response if t==0xc07d5))==zeros
        with closing(store.connect()) as db:
            accepted=db.execute('SELECT request_id FROM role_inventory_commands WHERE role_id=? ORDER BY rowid DESC LIMIT 1',(owner.id,)).fetchone()[0]
        base_connect=store.connect
        def readonly():
            db=base_connect();db.set_authorizer(lambda a,*args:sqlite3.SQLITE_DENY if a in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            return db
        with patch.object(store,'connect',side_effect=readonly):
            paid=await owner.mailbox.call('receive',USE_ITEM,body,request_id=accepted)
        assert current(store,owner)==after and all(t!=0xc1775 for t,b in paid)
        assert native_stone_attributes(next(b for t,b in paid if t==0xc32c9))==zeros
        # A new empty clearing request refuses without spending and never calls asset precommit.
        response=await peer.request(USE_ITEM,body)
        assert native_notice(next(b for t,b in response if t==0xc1775))==(150483,0,())
        assert current(store,owner)==after
        # Real shared common receipt failure and late encoding undo the clear,
        # its paid/source facts and item together, then a retry clears once.
        await owner.io(known_stones,store,owner.inventory,pet,'stones:runtime-refill')
        with closing(store.connect()) as db,db:
            db.execute("CREATE TRIGGER stone_common_fault BEFORE INSERT ON role_inventory_commands BEGIN SELECT RAISE(ABORT,'actual common stone failure'); END")
        before=current(store,owner)
        try:await owner.mailbox.call('receive',USE_ITEM,body,request_id='stones:common-fault')
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Actual shared receipt failure committed clearing')
        assert current(store,owner)==before
        with closing(store.connect()) as db,db:db.execute('DROP TRIGGER stone_common_fault')
        for target in ('inventory.stone_attributes_message','inventory.stone_notice'):
            with patch(target,side_effect=RuntimeError('late actual stone encoding')):
                try:await owner.mailbox.call('receive',USE_ITEM,body,request_id='stones:common-fault')
                except RuntimeError:pass
                else:raise AssertionError('Late shared stone encoding failure committed')
            assert current(store,owner)==before
        await owner.mailbox.call('receive',USE_ITEM,body,request_id='stones:common-fault')
        after=current(store,owner)
        assert after[0].pets[0].progress.stones.count==0
        old=owner;await peer.connection.close()
        peer=GrowthPeer(rt);await peer.login(role);owner=rt.roles[role['id']]
        assert current(store,owner)==after
        try:await old.mailbox.call('receive',USE_ITEM,body,request_id=accepted)
        except ValueError:pass
        else:raise AssertionError('Obsolete stone owner remained valid')
        await peer.request(FREE_PET,struct.pack('>i',pet));released=current(store,owner)
        paid=await owner.mailbox.call('receive',USE_ITEM,body,request_id=accepted)
        assert (0xc07dd,struct.pack('>ii',1,pet)) in paid and current(store,owner)==released
        await peer.connection.close()
    finally:await rt.close()


def main():
    with TemporaryDirectory(prefix='stones-owner-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'原生驱灵',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for rows in store.npc_resources[0].values() for p in rows if p.npc_id==10004)
        fixture(store,role,npc);asyncio.run(check(store,prepared,role))
    write_json(OUT/'evidence/pet-stones-runtime-verification.json',{'passed':[
        'actual encrypted clearing -> RoleOwner -> existing common/source transaction -> native six zero attrs/basic growth/150456/Unix clock',
        'committed command SQL-readonly current state; empty new clear no-debit150483; reconnect/stale owner/released paid',
        'actual common receipt failure and late attribute/notice encoding failures roll assets/source/all receipts back; same failed ID retries once; roleHP10/MP20/version0 unchanged'],
        'random_add_admission':'trusted seed through caller transaction only; generic shared captured RNG admission pending',
        'database':'disposable','shared_files_changed':False,'live_server_changed':False,'native_gui_verified':False})
    print('PASS actual encrypted clearing/source/common/timed read-only replay/reconnect/released target')


if __name__=='__main__':main()
