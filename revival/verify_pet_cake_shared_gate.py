"""Acceptance gate for the ACTUAL shared inventory dispatcher, without a shim.

The existing common command receipt and source precommit route named cakes
through owned Inventory code. No dispatcher shim or live service/client is used.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import time
from contextlib import closing
from accounts import AccountStore
from inventory import Inventory,USE_ITEM,InventoryNotReady
from inventory_test_support import known_cash_context
from inspect_client import OUT,write_json
from pet_skill_expiry import TimedSkillGrant
import runtime_storage


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'shared-cake-gate.sqlite3')
        role=store.create_role(1111,'共享年糕门禁',12,1010101)
        runtime_storage.prepare(store)
        inv=Inventory(store,1111,role['id'],store.inventory_config,**known_cash_context(store,1111,role['id']))
        pet=inv.grant_pet(500001);inv.grant_item(31268,5)
        before=inv.immutable_snapshot();key=next(i.id for i in before.items if i.template_id==31268)
        body=struct.pack('>iiQ',key,1,pet)
        try:runtime_storage.receive_inventory(store,inv,USE_ITEM,body,'shared:cake',1000)
        except InventoryNotReady as error:
            assert inv.immutable_snapshot()==before
            write_json(OUT/'evidence/pet-cake-shared-gate.json',{
                'status':'not_integrated','actual_entry':'runtime_storage.receive_inventory -> Inventory.receive',
                'reason':str(error),'assets_unchanged':True,'shim_used':False,'live_server_changed':False})
            raise AssertionError('Actual shared CUseItem has not connected confirmed cake Adapter: '+str(error)) from error
        after=inv.immutable_snapshot()
        assert after.pets[0].cake.count==1 and after.pets[0].progress.profile.aptitudes[0]==1137
        assert next(i.quantity for i in after.items if i.id==key)==4
        runtime_storage.receive_inventory(store,inv,USE_ITEM,body,'shared:cake',1001)
        assert inv.immutable_snapshot()==after
        wall_before=time.time_ns()//1000000
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.read_pet_state(db,pet)
            inv.grant_pet_timed_skill(db,TimedSkillGrant('shared:cake-timed-skill',pet,200011,wall_before+600000,
                'known-shared-fixture',p.skills.version),inv.epoch,wall_before)
        fresh=runtime_storage.receive_inventory(store,inv,USE_ITEM,body,'shared:cake:timed',1002)
        native_clock=next((struct.unpack('>q',b)[0] for t,b in fresh if t==0xc0007),None)
        assert native_clock is not None and native_clock>=wall_before,'Actual shared cake refresh lacks a current Unix-ms clock'
        after=inv.immutable_snapshot()
        paid=runtime_storage.receive_inventory(store,inv,USE_ITEM,body,'shared:cake:timed',1003)
        paid_clock=next((struct.unpack('>q',b)[0] for t,b in paid if t==0xc0007),None)
        assert paid_clock is not None and paid_clock>=wall_before,'Paid cake reply used owner monotonic time as the native Unix clock'
        assert inv.immutable_snapshot()==after
    write_json(OUT/'evidence/pet-cake-shared-gate.json',{
        'status':'passed','actual_entry':'runtime_storage.receive_inventory','shim_used':False,
        'paid_current_only':True,'live_server_changed':False,'native_gui_verified':False})
    print('PASS actual shared cake entry, real mutation and stable shared paid retry')


if __name__=='__main__':main()
