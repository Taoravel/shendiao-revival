"""Actual inventory native mutations synchronize the sole resource source."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import sqlite3

from accounts import AccountStore
from inventory import (Inventory,AssetChange,MOVE_ITEM,ARRANGE_BAG,RENAME_PET,REST_PET,
    FREE_PET,USE_ITEM,ADD_PET_POINT,REFRESH_PET,FIGHT_PET)
from role_growth import initialize_growth
from role_attribute_storage import initialize_attribute_baseline
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_totals,
    current_resource_profile,synchronize_inventory_resource_source)
from role_resource_plan import load_resource_rules
from role_resource_storage import migrate_role_resources,read_role_resources
from currency import initialize_wallet
from wire import octets
from native_gameplay_probe import probe
from native_inspect import u32
from pet_battle_care import BattleCareEvent
from pet_protocol import SUPER_RETURN_SUBMIT,SUPER_RETURN_CLEAR,SUPER_RETURN_QUERY
from inspect_client import OUT,write_json
from research_pet_skills import native_record_skills
import runtime_storage


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Pending, stale or conflicting precommit was accepted')


def main():
    with TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'背包资源同步',11,1010109)
        runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id']);rules=load_resource_rules();gear=store.equipment_attribute_rules
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
            p=store.attribute_rules.initial_profile
            before=initialize_attribute_baseline(db,1111,role['id'],epoch,p.baseline(role['id']),growth,
                store.attribute_rules,replace(p.vitals(role['id']),hp=70,mp=40)).vitals
            initialize_wallet(db,1111,role['id'],epoch,(100,0,0,0),'explicit_migration',store.currency_rules)
            initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
                EquipmentAttributeBasis(role['id'],9,0,gear.revision,0,'known-inventory-hook-fixture'),gear)
            inv.apply_settlement(db,AssetChange('hook-items',grants=((49009,1,1),(32000,3),(31003,2),(36117,2),(32036,2),(32007,1,0,95),(32004,2,0,100),(31576,3),(31002,3),(31268,3)),pets=(500001,500051)))
            snapshot=inv.immutable_snapshot_transaction(db)
            weapon=next(i.id for i in snapshot.items if i.template_id==49009)
            medicine=next(i.id for i in snapshot.items if i.template_id==32000)
            inv.equip_transaction(db,weapon,0,epoch,'hook-equipped')
            totals=current_equipment_totals(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),gear)
            initial=migrate_role_resources(db,1111,role['id'],epoch,before,resource_caps_from_projection(totals),
                origin='explicit_migration',migration_id='known-inventory-hook',rules=rules,equipment_rules=gear)
        calls=[]
        def hook(request,expected_inventory=None):
            def precommit(db,inventory,snapshot,*,replayed):
                assert db.in_transaction and inventory is (expected_inventory or inv)
                state=synchronize_inventory_resource_source(db,1111,role['id'],epoch,snapshot,request,
                    resource_rules=rules,equipment_rules=gear,replayed=replayed)
                profile=current_resource_profile(db,1111,role['id'],epoch,snapshot,equipment_rules=gear,resource_rules=rules)
                assert (profile.vitals.hp,profile.vitals.mp,profile.vitals.version)==(70,40,0)
                calls.append((request,replayed,snapshot.inventory_revision))
                return state
            return precommit
        item=next(i for i in inv.immutable_snapshot().items if i.id==medicine)
        body=struct.pack('>6iq',1,medicine,item.slot,1,7,0,-1)
        replies=inv.receive(MOVE_ITEM,body,hook('hook:move'))
        assert replies[0][0]==0xc03f3 and next(i.slot for i in inv.immutable_snapshot().items if i.id==medicine)==7
        with closing(inv.accounts.connect()) as db:
            db.execute('BEGIN')
            state=read_role_resources(db,1111,role['id'],epoch,rules)
            assert state.version==0 and state.hp==70 and state.mp==40
            assert state.caps.source.inventory_revision>initial.caps.source.inventory_revision
        assert calls[-1][0:2]==('hook:move',False)
        def current():
            with closing(inv.accounts.connect()) as db:
                db.execute('BEGIN')
                return read_role_resources(db,1111,role['id'],epoch,rules)
        probe(0xef6220,u32(0x2284234),u32(0x2284238),payload=replies[0][1])
        inv.receive(ARRANGE_BAG,struct.pack('>iQ',1,role['id']),hook('hook:arrange'))
        pet=inv.immutable_snapshot().pets[0].id
        inv.receive(RENAME_PET,struct.pack('>i',pet)+octets('重登宠物'.encode('utf-16le')),hook('hook:rename'))
        assert inv.immutable_snapshot().pets[0].name=='重登宠物'
        book=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31003)
        request=struct.pack('>6i',pet,book,-1,-1,-1,-1)
        learned=inv.receive_pet_skill_book(request,epoch,'hook:book',(0,0),None,hook('hook:book'))
        assert calls[-1][0:2]==('hook:book',False)
        assert native_record_skills(next(b for k,b in learned if k==REFRESH_PET))[0]==(200091,200061,200011)
        before=inv.immutable_snapshot();prior=current()
        inv.receive_pet_skill_book(request,epoch,'hook:book',(0,0),None,hook('hook:book'))
        assert calls[-1][0:2]==('hook:book',True)
        assert inv.immutable_snapshot()==before and current()==prior
        count=len(calls)
        refused(lambda:inv.receive_pet_skill_book(request,epoch,'hook:book',(1,0),None,hook('hook:book')))
        assert len(calls)==count and inv.immutable_snapshot()==before and current()==prior
        # A historical receipt cannot repair unrelated later pending assets.
        inv.grant_item(32001,quality=10)
        pending=inv.immutable_snapshot();prior=current()
        refused(lambda:inv.receive_pet_skill_book(request,epoch,'hook:book',(0,0),None,hook('hook:book')))
        assert inv.immutable_snapshot()==pending and current()==prior
        inv.receive(ARRANGE_BAG,struct.pack('>iQ',1,0),hook('hook:fresh-arrange'))
        # Use a real caller transaction to stage pet damage/XP; synchronize this
        # legitimate asset mutation before the next separately admitted request.
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=inv.pet_progress(db,pet)
            growth=inv.change_pet_growth(db,pet,'hook:pet-xp',growth.state.version,'experience',50)
            inv.change_pet_growth(db,pet,'hook:pet-wound',growth.state.version,'resources',(1,1))
            hook('hook:controlled-pet-state')(db,inv,inv.immutable_snapshot_transaction(db),replayed=False)
        inv.receive(ADD_PET_POINT,struct.pack('>6i',pet,1,0,0,0,0),hook('hook:pet-point'))
        essence=next(i.id for i in inv.immutable_snapshot().items if i.template_id==36117)
        essence_body=struct.pack('>iiQ',essence,1,pet)
        inv.receive_pet_consumable(essence_body,epoch,'hook:essence',None,hook('hook:essence'))
        before=inv.immutable_snapshot();prior=current()
        inv.receive_pet_consumable(essence_body,epoch,'hook:essence',None,hook('hook:essence'))
        assert calls[-1][0:2]==('hook:essence',True) and inv.immutable_snapshot()==before and current()==prior
        pill=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31576)
        return_body=struct.pack('>iiQ',pill,1,pet)
        preview_replies=inv.receive_super_return(USE_ITEM,return_body,epoch,'hook:return',draws=(5000,)*7,precommit=hook('hook:return'))
        preview_aptitudes=struct.unpack('>9i',next(b for t,b in preview_replies if t==0xc0810))[1:6]
        before=inv.immutable_snapshot();prior=current()
        inv.receive_super_return(USE_ITEM,return_body,epoch,'hook:return',precommit=hook('hook:return'))
        assert calls[-1][0:2]==('hook:return',True) and inv.immutable_snapshot()==before and current()==prior
        def fail_return_source(db,inventory,snapshot,*,replayed):
            hook('hook:return-save')(db,inventory,snapshot,replayed=replayed)
            raise ValueError('Controlled failure after real super-return resource source CAS')
        save_body=struct.pack('>i',pet)
        refused(lambda:inv.receive_super_return(SUPER_RETURN_SUBMIT,save_body,epoch,'hook:return-save',
            expected_candidate='hook:return',precommit=fail_return_source))
        assert inv.immutable_snapshot()==before and current()==prior
        assert inv.receive_super_return(SUPER_RETURN_QUERY,save_body,epoch)
        inv.receive_super_return(SUPER_RETURN_SUBMIT,save_body,epoch,'hook:return-save',
            expected_candidate='hook:return',precommit=hook('hook:return-save'))
        saved_return=next(p for p in inv.immutable_snapshot().pets if p.id==pet)
        assert saved_return.progress.effective_profile.aptitudes==preview_aptitudes,'候选展示与保留血脉后的实际保存资质不一致'
        before=inv.immutable_snapshot();prior=current()
        inv.receive_super_return(SUPER_RETURN_SUBMIT,save_body,epoch,'hook:return-save',
            expected_candidate='hook:return',precommit=hook('hook:return-save'))
        assert calls[-1][0:2]==('hook:return-save',True) and inv.immutable_snapshot()==before and current()==prior
        assert not inv.receive_super_return(SUPER_RETURN_QUERY,save_body,epoch)
        inv.receive_super_return(USE_ITEM,return_body,epoch,'hook:return-clear-preview',draws=(0,)*7,precommit=hook('hook:return-clear-preview'))
        inv.receive_super_return(SUPER_RETURN_CLEAR,save_body,epoch,'hook:return-clear',
            expected_candidate='hook:return-clear-preview',precommit=hook('hook:return-clear'))
        before=inv.immutable_snapshot();prior=current()
        inv.receive_super_return(SUPER_RETURN_CLEAR,save_body,epoch,'hook:return-clear',
            expected_candidate='hook:return-clear-preview',precommit=hook('hook:return-clear'))
        assert calls[-1][0:2]==('hook:return-clear',True) and inv.immutable_snapshot()==before and current()==prior
        lifetime=next(i.id for i in inv.immutable_snapshot().items if i.template_id==32036)
        lifetime_body=struct.pack('>iiQ',lifetime,1,pet)
        inv.receive_pet_consumable(lifetime_body,epoch,'hook:lifetime',None,hook('hook:lifetime'))
        before=inv.immutable_snapshot();prior=current()
        inv.receive_pet_consumable(lifetime_body,epoch,'hook:lifetime',None,hook('hook:lifetime'))
        assert calls[-1][0:2]==('hook:lifetime',True) and inv.immutable_snapshot()==before and current()==prior
        quality_food=next(i.id for i in inv.immutable_snapshot().items if i.template_id==32007)
        quality_body=struct.pack('>iiQ',quality_food,1,pet)
        inv.receive_pet_consumable(quality_body,epoch,'hook:quality-lifetime',None,hook('hook:quality-lifetime'))
        before=inv.immutable_snapshot();prior=current()
        inv.receive_pet_consumable(quality_body,epoch,'hook:quality-lifetime',None,hook('hook:quality-lifetime'))
        assert calls[-1][0:2]==('hook:quality-lifetime',True) and inv.immutable_snapshot()==before and current()==prior
        toxic_food=next(i.id for i in inv.immutable_snapshot().items if i.template_id==32004)
        toxic_body=struct.pack('>iiQ',toxic_food,1,pet)
        before=inv.immutable_snapshot();prior=current()
        def fail_toxic_source(db,inventory,snapshot,*,replayed):
            hook('hook:toxic-lifetime')(db,inventory,snapshot,replayed=replayed)
            raise ValueError('Controlled after actual toxic-food source CAS')
        refused(lambda:inv.receive_pet_consumable(toxic_body,epoch,'hook:toxic-lifetime',None,fail_toxic_source,0))
        assert inv.immutable_snapshot()==before and current()==prior
        inv.receive_pet_consumable(toxic_body,epoch,'hook:toxic-lifetime',None,hook('hook:toxic-lifetime'),0)
        before=inv.immutable_snapshot();prior=current()
        inv.receive_pet_consumable(toxic_body,epoch,'hook:toxic-lifetime',None,hook('hook:toxic-lifetime'))
        assert calls[-1][0:2]==('hook:toxic-lifetime',True) and inv.immutable_snapshot()==before and current()==prior
        low_food=next(i.id for i in inv.immutable_snapshot().items if i.template_id==32004)
        low_body=struct.pack('>iiQ',low_food,1,pet)
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            receipt=inv.use_pet_toxic_food(db,low_food,pet,epoch,'hook:toxic-low',0,None)
            assert not receipt.replayed
            hook('hook:toxic-low')(db,inv,inv.immutable_snapshot_transaction(db),replayed=False)
        before=inv.immutable_snapshot();prior=current()
        class ReadOnlyStorage:
            def __getattr__(self,name):return getattr(store,name)
            def connect(self):
                db=store.connect()
                db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                    (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
                return db
        read_only=Inventory(ReadOnlyStorage(),1111,role['id'],store.inventory_config,
            epoch=epoch,currency_rules=store.currency_rules)
        read_only.receive_pet_consumable(low_body,epoch,'hook:toxic-low',None,hook('hook:toxic-low',read_only))
        assert calls[-1][0:2]==('hook:toxic-low',True) and inv.immutable_snapshot()==before and current()==prior
        read_only.receive_super_return(USE_ITEM,return_body,epoch,'hook:return',precommit=hook('hook:return',read_only))
        read_only.receive_super_return(SUPER_RETURN_SUBMIT,save_body,epoch,'hook:return-save',
            expected_candidate='hook:return',precommit=hook('hook:return-save',read_only))
        read_only.receive_super_return(SUPER_RETURN_CLEAR,save_body,epoch,'hook:return-clear',
            expected_candidate='hook:return-clear-preview',precommit=hook('hook:return-clear',read_only))
        assert inv.immutable_snapshot()==before and current()==prior
        with closing(inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');p=inv.pet_progress(db,pet)
            assert p.state.level==1
            inv.change_pet_growth(db,pet,'hook:battle-care-xp',p.state.version,'experience',
                sum(inv.growth_rules.thresholds[i] for i in range(1,31)))
            hook('hook:battle-care-stage')(db,inv,inv.immutable_snapshot_transaction(db),replayed=False)
            p=inv.read_pet_state(db,pet);meter=inv.pet_battle_care_counter(db,pet)
            assert p.progress.state.level==31
            battle_event=BattleCareEvent('hook:battle-care',pet,p.template_id,p.care.version,
                                       p.progress.state.version,meter.version)
        def battle_care(inventory=inv,fail_after_source=False):
            with closing(inventory.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                receipt=inventory.settle_pet_battle_care(db,battle_event,epoch)
                hook('hook:battle-care',inventory)(db,inventory,
                    inventory.immutable_snapshot_transaction(db),replayed=receipt.replayed)
                if fail_after_source:raise ValueError('Controlled after actual battle-care source CAS')
                return receipt
        before=inv.immutable_snapshot();prior=current()
        refused(lambda:battle_care(fail_after_source=True))
        assert inv.immutable_snapshot()==before and current()==prior
        fresh=battle_care();assert not fresh.replayed and fresh.counter_after.mod3==1
        before=inv.immutable_snapshot();prior=current()
        assert battle_care(read_only).replayed
        assert calls[-1][0:2]==('hook:battle-care',True) and inv.immutable_snapshot()==before and current()==prior
        medicine=next(i.id for i in inv.immutable_snapshot().items if i.template_id==32000)
        inv.receive(USE_ITEM,struct.pack('>iiQ',medicine,1,pet),hook('hook:pet-medicine'))
        ordinary_pill=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31002)
        ordinary_body=struct.pack('>iiQ',ordinary_pill,1,pet)
        before=inv.immutable_snapshot();prior=current()
        def ordinary_late_source(db,inventory,snapshot,*,replayed):
            hook('hook:ordinary-return')(db,inventory,snapshot,replayed=replayed)
            raise ValueError('Controlled ordinary return failure after actual source CAS')
        refused(lambda:inv.receive_ordinary_return(ordinary_body,epoch,'hook:ordinary-return',(5000,)*15,
            precommit=ordinary_late_source))
        assert inv.immutable_snapshot()==before and current()==prior
        inv.receive_ordinary_return(ordinary_body,epoch,'hook:ordinary-return',(5000,)*15,precommit=hook('hook:ordinary-return'))
        assert next(p for p in inv.immutable_snapshot().pets if p.id==pet).progress.state.level==0
        before=inv.immutable_snapshot();prior=current()
        read_only.receive_ordinary_return(ordinary_body,epoch,'hook:ordinary-return',precommit=hook('hook:ordinary-return',read_only))
        assert calls[-1][0:2]==('hook:ordinary-return',True) and inv.immutable_snapshot()==before and current()==prior
        cake_key=next(i.id for i in inv.immutable_snapshot().items if i.template_id==31268)
        cake_body=struct.pack('>iiQ',cake_key,1,pet)
        before=inv.immutable_snapshot();prior=current()
        def cake_late_source(db,inventory,snapshot,*,replayed):
            hook('hook:cake')(db,inventory,snapshot,replayed=replayed)
            raise ValueError('Controlled cake failure after actual root source CAS')
        refused(lambda:inv.receive_pet_consumable(cake_body,epoch,'hook:cake',precommit=cake_late_source))
        assert inv.immutable_snapshot()==before and current()==prior
        cake_replies=inv.receive_pet_consumable(cake_body,epoch,'hook:cake',precommit=hook('hook:cake'))
        from research_pet_cake_protocol import native_notice
        assert native_notice(next(b for t,b in cake_replies if t==0xc1775))==(145135,0,('外功','7','19'))
        before=inv.immutable_snapshot();prior=current()
        read_only.receive_pet_consumable(cake_body,epoch,'hook:cake',precommit=hook('hook:cake',read_only))
        assert calls[-1][0:2]==('hook:cake',True) and inv.immutable_snapshot()==before and current()==prior
        second=next(p.id for p in inv.immutable_snapshot().pets if p.id!=pet)
        inv.receive(FIGHT_PET,struct.pack('>i',second),hook('hook:select-pet'))
        assert next(p.fighting for p in inv.immutable_snapshot().pets if p.id==second)==1
        inv.receive(REST_PET,b'',hook('hook:rest'))
        inv.receive(FREE_PET,struct.pack('>i',pet),hook('hook:release'))
        inv.receive(FREE_PET,struct.pack('>i',second),hook('hook:release-second'))
        assert not inv.immutable_snapshot().pets
        assert all(not replayed for request,replayed,revision in calls if request not in ('hook:book','hook:essence','hook:lifetime','hook:quality-lifetime','hook:toxic-lifetime','hook:toxic-low','hook:battle-care','hook:return','hook:return-save','hook:return-clear','hook:ordinary-return','hook:cake'))
        # Callback failure occurs AFTER real source CAS and before commit.
        def move_body(destination):
            item=next(i for i in inv.immutable_snapshot().items if i.id==medicine)
            return struct.pack('>6iq',1,medicine,item.slot,1,destination,0,-1)
        before=inv.immutable_snapshot();prior=current();body=move_body(8)
        def late(db,inventory,snapshot,*,replayed):
            hook('hook:late')(db,inventory,snapshot,replayed=replayed)
            raise RuntimeError('late full-profile/native failure')
        try:inv.receive(MOVE_ITEM,body,late)
        except RuntimeError:pass
        else:raise AssertionError('Actual post-source callback failure was not executed')
        assert inv.immutable_snapshot()==before and current()==prior
        inv.receive(MOVE_ITEM,body,hook('hook:late'))
        # Real resource-source receipt failure rolls the inventory mutation back.
        before=inv.immutable_snapshot();prior=current();body=move_body(9)
        with closing(store.connect()) as db:
            db.execute("CREATE TRIGGER fail_inventory_source BEFORE INSERT ON role_resource_receipts BEGIN SELECT RAISE(ABORT,'inventory source failed'); END")
        try:inv.receive(MOVE_ITEM,body,hook('hook:receipt-fail'))
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Real source receipt fault did not execute')
        assert inv.immutable_snapshot()==before and current()==prior
        with closing(store.connect()) as db:db.execute('DROP TRIGGER fail_inventory_source')
        # Corrupt one independent carried quantity to fail the actual bag codec
        # after BOTH the item move and source update; no mocked encoder.
        other=next(i.id for i in inv.immutable_snapshot().items if i.template_id==32001)
        with closing(store.connect()) as db,db:
            db.execute('UPDATE inventory_items SET quantity=? WHERE id=?',(2**31,other))
        before=inv.immutable_snapshot();prior=current()
        try:inv.receive(MOVE_ITEM,body,hook('hook:encoding-fail'))
        except struct.error:pass
        else:raise AssertionError('Late actual bag overflow did not execute')
        assert inv.immutable_snapshot()==before and current()==prior
        with closing(store.connect()) as db,db:db.execute('UPDATE inventory_items SET quantity=1 WHERE id=?',(other,))
        inv.receive(MOVE_ITEM,body,hook('hook:encoding-fail'))
        before=inv.immutable_snapshot();prior=current()
        async def async_hook(*args,**kwargs):pass
        refused(lambda:inv.receive(MOVE_ITEM,move_body(10),async_hook))
        assert inv.immutable_snapshot()==before and current()==prior
        old=inv
        epoch='背包提交:00007'
        with closing(store.connect()) as db,db:db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(epoch,role['id']))
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        refused(lambda:old.receive(MOVE_ITEM,move_body(10),hook('hook:obsolete')))
        inv.receive(MOVE_ITEM,move_body(10),hook('hook:opaque-current'))
        assert (current().hp,current().mp,current().version)==(70,40,0)
    report={'passed':['native move/arrange/rename/point/pet medicine/selection/rest/release synchronize actual source in caller transaction',
        'skill book fresh False and validated durable replay True; current native learned IDs retained',
        'actual blood essence Adapter source-only False/True joins the migrated profile without changing role resources',
        'super-return preview/save/clear source False/True shares the actual profile; post-source save failure rolls back candidate/pet/source and preserves role70/40',
        'ordinary return complete reset and real source CAS share one transaction; late source failure rolls back, paid replay SQL-readonly and role70/40 unchanged',
        'actual named cake BASE/count/item/notice/root source commit together; after-source failure rolls all back and paid True is SQL-readonly',
        'actual fixed lifetime food Adapter source-only False/True joins the same profile and preserves role70/40',
        'actual quality95 lifetime food plus deleted-key paid replay synchronize source atomically without role healing',
        'actual poisoned lifetime food commits changed base aptitudes with source; paid True does not reroll or repair source',
        'low-level-only paid poison plus actual strict source True succeeds while all SQL writes are forbidden',
        'real level31 battle care/meter/root-source CAS share one transaction; after-source failure rolls back, readonly paid True preserves current',
        'invalid historical intent refuses before hook; paid replay refuses unrelated pending source without repairing it',
        'actual callback after source CAS, source receipt abort and late native bag overflow all roll back assets/source/receipts',
        'same aborted key later commits; synchronous hook enforced; actual opaque lease works and obsolete lease refuses',
        'all source-only operations preserve role70/40 and resource version0'],
        'live_server_changed':False,'native_gui_tested':False,'shared_route_changed_by_this_window':False}
    write_json(OUT/'evidence/inventory-resource-hook-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
