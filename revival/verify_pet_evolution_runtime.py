"""Actual encrypted ordinary evolution through existing Owner/common/source path."""
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
from inventory import AssetChange,REFRESH_PET,FREE_PET
from pet_protocol import PET_EVOLVE
from pet_skill_expiry import TimedSkillGrant
from role_equipment_storage import current_resource_profile
from role_resource_storage import read_role_resources
from verify_growth_runtime import GrowthPeer
from verify_resource_owner_runtime import fixture
from research_pet_evolution import native_stage
from research_pet_cake_protocol import native_notice
from inspect_client import OUT,write_json
import runtime_storage


def known_pet_level(store,inv,pet):
    with closing(inv.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,pet)
        inv.change_pet_growth(db,pet,'evolve:runtime20',p.progress.state.version,'experience',sum(inv.growth_rules.thresholds[i] for i in range(20)))
        p=inv.read_pet_state(db,pet);now=time.time_ns()//1000000
        inv.grant_pet_timed_skill(db,TimedSkillGrant('evolve:runtime-timed',pet,200011,now+600000,'known-evolution-fixture',p.skills.version),inv.epoch,now)
        runtime_storage._synchronize_source(db,store,inv,'evolve:fixture-source',replayed=False)


def current(store,owner):
    inv=owner.inventory
    with closing(inv.accounts.connect()) as db:
        db.execute('BEGIN');assets=inv.immutable_snapshot_transaction(db)
        current_resource_profile(db,inv.account_id,inv.role_id,inv.epoch,assets,
            equipment_rules=store.equipment_attribute_rules,resource_rules=store.resource_rules)
        resources=read_role_resources(db,inv.account_id,inv.role_id,inv.epoch,store.resource_rules)
        assert (resources.hp,resources.mp,resources.version)==(10,20,0)
        counts=tuple(db.execute('SELECT COUNT(*) FROM '+table+' WHERE role_id=?',(inv.role_id,)).fetchone()[0]
            for table in ('inventory_pet_evolution_receipts','role_inventory_commands','role_resource_receipts'))
        return assets,resources,counts


async def check(store,prepared,role):
    rt=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(rt);await peer.login(role);owner=rt.roles[role['id']]
        await owner.mailbox.call('settle',AssetChange('evolve:runtime-assets',grants=((31227,2),(31228,200),(31229,20)),pets=(500001,)))
        pet=current(store,owner)[0].pets[0].id
        await owner.io(known_pet_level,store,owner.inventory,pet)
        before=current(store,owner);body=struct.pack('>i',pet);now=time.time_ns()//1000000
        response=await peer.request(PET_EVOLVE,body)
        assert native_notice(next(b for t,b in response if t==0xc1775))==(143571,0,('小灰狗','二阶'))
        assert native_stage(next(b for t,b in response if t==REFRESH_PET))==1
        assert next(struct.unpack('>q',b)[0] for t,b in response if t==0xc0007)>=now
        after=current(store,owner);p=after[0].pets[0]
        assert (p.evolution.stage,p.progress.profile.growth_raw)==(1,1011)
        assert p.skill_expiry==before[0].pets[0].skill_expiry
        with closing(store.connect()) as db:
            accepted=db.execute('SELECT request_id FROM role_inventory_commands WHERE role_id=? ORDER BY rowid DESC LIMIT 1',(owner.id,)).fetchone()[0]
        # Identical new wire is a new accepted command, now the first final row.
        response=await peer.request(PET_EVOLVE,body);second=current(store,owner)
        assert native_notice(next(b for t,b in response if t==0xc1775))==(148963,0,())
        assert (second[0].pets[0].evolution.stage,second[0].pets[0].progress.profile.growth_raw)==(2,1012)
        base_connect=store.connect
        def readonly():
            db=base_connect();db.set_authorizer(lambda a,*args:sqlite3.SQLITE_DENY if a in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            return db
        with patch.object(store,'connect',side_effect=readonly):
            paid=await owner.mailbox.call('receive',PET_EVOLVE,body,request_id=accepted)
        assert current(store,owner)==second
        assert all(t!=0xc1775 for t,b in paid)
        assert native_stage(next(b for t,b in paid if t==REFRESH_PET))==2
        assert next(struct.unpack('>q',b)[0] for t,b in paid if t==0xc0007)>=now
        with closing(store.connect()) as db:
            db.execute("CREATE TRIGGER evolve_common_failure BEFORE INSERT ON role_inventory_commands BEGIN SELECT RAISE(ABORT,'actual common evolution receipt failed'); END")
        before=current(store,owner)
        try:await owner.mailbox.call('receive',PET_EVOLVE,body,request_id='evolve:common-fault')
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Actual common receipt failure committed evolution')
        assert current(store,owner)==before
        with closing(store.connect()) as db:db.execute('DROP TRIGGER evolve_common_failure')
        await owner.mailbox.call('receive',PET_EVOLVE,body,request_id='evolve:common-fault')
        assert current(store,owner)[0].pets[0].evolution.stage==3
        before=current(store,owner)
        with patch.object(owner.inventory,'clock_now_ms',return_value=-1):
            try:await owner.mailbox.call('receive',PET_EVOLVE,body,request_id='evolve:clock-fault')
            except ValueError:pass
            else:raise AssertionError('Late evolution representation failure committed')
        assert current(store,owner)==before
        await owner.mailbox.call('receive',PET_EVOLVE,body,request_id='evolve:clock-fault')
        persisted=current(store,owner);assert persisted[0].pets[0].evolution.stage==4
        old=owner;await peer.connection.close()
        peer=GrowthPeer(rt);await peer.login(role);owner=rt.roles[role['id']]
        assert current(store,owner)==persisted
        try:await old.mailbox.call('receive',PET_EVOLVE,body,request_id=accepted)
        except ValueError:pass
        else:raise AssertionError('Obsolete evolution owner remained valid')
        await owner.mailbox.call('receive',PET_EVOLVE,body,request_id=accepted)
        assert current(store,owner)==persisted
        await peer.request(FREE_PET,body);released=current(store,owner)
        paid=await owner.mailbox.call('receive',PET_EVOLVE,body,request_id=accepted)
        assert (0xc07dd,struct.pack('>ii',1,pet)) in paid and current(store,owner)==released
        await peer.connection.close()
    finally:await rt.close()


def main():
    with TemporaryDirectory(prefix='evolution-owner-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');role=store.create_role(1111,'原生进化',11,1010109)
        prepared=runtime_storage.prepare(store)
        npc=next(p for rows in store.npc_resources[0].values() for p in rows if p.npc_id==10004)
        fixture(store,role,npc);asyncio.run(check(store,prepared,role))
    write_json(OUT/'evidence/pet-evolution-runtime-verification.json',{'passed':[
        'actual encrypted CReqPetEvolve -> RoleOwner -> existing common/source transaction -> original stage refresh/Unix clock/143571 native name+stage notice; post-cap148963 empty-param success and no repeated paid notice',
        'new identical click advances separately; committed ID strictly SQL-readonly current replies with retained timed skill',
        'real common receipt and late clock encoding failures roll stages/growth/materials/source/all receipts back; same failed ID retries once',
        'actual reconnect preserves committed stage; stale owner rejects; historical released target stays removed',
        'roleHP10/MP20/version0 unchanged'],
        'database':'disposable','shared_files_changed':False,'live_server_changed':False,'native_gui_verified':False,'battle_executed':False})
    print('PASS actual encrypted evolution/source/common/rollback/timed current replay/reconnect/released target')


if __name__=='__main__':main()
