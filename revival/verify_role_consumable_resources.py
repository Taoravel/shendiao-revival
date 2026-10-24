"""Real medicine joins explicitly migrated resources and current equipment."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import sqlite3

from accounts import AccountStore
from inventory import Inventory,AssetChange
from role_growth import initialize_growth
from role_attribute_storage import initialize_attribute_baseline,read_attribute_snapshot
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import (initialize_equipment_attribute_basis,current_equipment_totals,
    current_resource_profile)
from role_resource_plan import load_resource_rules,plan_resource_values
from role_resource_storage import migrate_role_resources,read_role_resources,apply_resource_transition
from currency import initialize_wallet
import runtime_storage
from native_gameplay_probe import probe
from native_inspect import u32
from inspect_client import OUT,write_json


def refused(action):
    try:action()
    except ValueError:return
    raise AssertionError('Invalid migrated medicine context was accepted')


def main():
    with TemporaryDirectory() as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'资源人物药品',11,1010109)
        runtime_storage.prepare(store)
        epoch=store.acquire_lease(1111,role['id'])
        rules=load_resource_rules();gear=store.equipment_attribute_rules
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,role['id'],epoch,store.growth_rules,expected_level=1,free_points=0)
            p=store.attribute_rules.initial_profile
            before=initialize_attribute_baseline(db,1111,role['id'],epoch,p.baseline(role['id']),growth,
                store.attribute_rules,replace(p.vitals(role['id']),hp=70,mp=40)).vitals
            initialize_wallet(db,1111,role['id'],epoch,(100,0,0,0),'explicit_migration',store.currency_rules)
            initialize_equipment_attribute_basis(db,1111,role['id'],epoch,
                EquipmentAttributeBasis(role['id'],9,0,gear.revision,0,'known-medicine-fixture'),gear)
            inv.apply_settlement(db,AssetChange('resource-medicine-items',grants=((49009,1,1),(32000,3))))
            snapshot=inv.immutable_snapshot_transaction(db)
            weapon=next(i.id for i in snapshot.items if i.template_id==49009)
            medicine=next(i.id for i in snapshot.items if i.template_id==32000)
            inv.equip_transaction(db,weapon,0,epoch,'resource-medicine-equip')
            totals=current_equipment_totals(db,1111,role['id'],epoch,inv.immutable_snapshot_transaction(db),gear)
            initial=migrate_role_resources(db,1111,role['id'],epoch,before,resource_caps_from_projection(totals),
                origin='explicit_migration',migration_id='known-medicine-resource',rules=rules,equipment_rules=gear)
        active=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'],
            resource_rules=rules,equipment_attribute_rules=gear)
        with closing(active.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            receipt=active.use_role_consumable(db,medicine,epoch,'resource-medicine-once')
            current=read_role_resources(db,1111,role['id'],epoch,rules)
            assert (initial.hp,initial.mp,current.hp,current.mp,current.version)==(70,40,100,40,1)
            assert (receipt.vitals.hp,receipt.vitals.max_hp)==(100,100)
            snapshot=active.immutable_snapshot_transaction(db)
            assert next(i.quantity for i in snapshot.items if i.id==medicine)==2
            assert current.caps.source.inventory_revision==snapshot.inventory_revision
            assert current.caps.source.inventory_revision>initial.caps.source.inventory_revision
            final=current_resource_profile(db,1111,role['id'],epoch,snapshot,equipment_rules=gear,resource_rules=rules)
            assert (final.vitals.hp,final.attributes.physical_attack)==(100,45)
        def resources():
            with closing(active.accounts.connect()) as db:
                db.execute('BEGIN')
                return read_role_resources(db,1111,role['id'],epoch,rules)
        def use(request='resource-medicine-once',key=medicine,owner_epoch=None):
            with closing(active.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return active.use_role_consumable(db,key,epoch if owner_epoch is None else owner_epoch,request)
        # A real MP item, instance quality, original world and bag codecs.
        active.grant_item(32001,2,quality=10)
        mana=next(i.id for i in active.immutable_snapshot().items if i.template_id==32001)
        mana_body=struct.pack('>iiQ',mana,0,role['id'])
        replies=active.receive_role_consumable(mana_body,epoch,'resource-medicine-mana')
        assert [kind for kind,_ in replies]==[0xc32c8,0xc03f3]
        assert (resources().hp,resources().mp,resources().version)==(100,100,2)
        probe(0xec3590,0xec36b0,0xec3730,payload=replies[0][1])
        probe(0xef6220,u32(0x2284234),u32(0x2284238),payload=replies[1][1])
        # A later controlled resource write, without running a battle. Replays
        # acknowledge the domain payment, returning current wounds, not a new plan.
        def controlled_values(hp,mp,request):
            with closing(active.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                before=read_role_resources(db,1111,role['id'],epoch,rules)
                transition=plan_resource_values(before,hp,mp,'medicine',rules)
                return apply_resource_transition(db,1111,role['id'],epoch,transition,request,
                    rules=rules,equipment_rules=gear).resources
        wounded=controlled_values(10,20,'controlled-later-resource-state')
        before=active.immutable_snapshot()
        assert use().vitals.hp==10 and resources()==wounded
        again=active.receive_role_consumable(mana_body,epoch,'resource-medicine-mana')
        assert struct.unpack_from('>f',again[0][1],5)[0]==10
        assert struct.unpack_from('>f',again[0][1],13)[0]==20
        assert active.immutable_snapshot()==before and resources()==wounded
        with closing(active.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:active.use_role_consumable(db,mana,epoch,'resource-medicine-once'))
            refused(lambda:active.use_role_consumable(db,medicine,epoch,'partial-rules',resource_rules=rules))
        # Native pre-commit late failures undo the actual debit, source, resource
        # receipt and domain receipt, including subsequent same-key successful retry.
        body=struct.pack('>iiQ',medicine,0,role['id'])
        for table,action in (('role_attribute_snapshots','UPDATE'),('role_resource_receipts','INSERT'),
                             ('inventory_role_consumables','INSERT')):
            with closing(store.connect()) as db:
                db.execute(f"CREATE TRIGGER fail_medicine_resources BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'resource medicine failure'); END")
            try:active.receive_role_consumable(body,epoch,'resource-medicine-failure')
            except sqlite3.IntegrityError:pass
            else:raise AssertionError('Actual resource/domain save fault did not execute')
            assert active.immutable_snapshot()==before and resources()==wounded
            with closing(store.connect()) as db:db.execute('DROP TRIGGER fail_medicine_resources')
        try:
            with closing(active.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                active.use_role_consumable(db,medicine,epoch,'resource-medicine-outer')
                raise RuntimeError('late common settlement failed')
        except RuntimeError:pass
        assert active.immutable_snapshot()==before and resources()==wounded
        no_cash=Inventory(AccountStore(store.path),1111,role['id'],store.inventory_config,epoch=epoch,
            resource_rules=rules,equipment_attribute_rules=gear)
        refused(lambda:no_cash.receive_role_consumable(body,epoch,'resource-medicine-failure'))
        assert active.immutable_snapshot()==before and resources()==wounded
        # Corrupt only a carried quantity in this disposable fixture. Equipment
        # caps remain valid; the real original bag encoding fails after the heal.
        carried_mana=next(i.id for i in active.immutable_snapshot().items if i.template_id==32001)
        with closing(store.connect()) as db,db:
            assert db.execute('UPDATE inventory_items SET quantity=? WHERE id=?',(2**31,carried_mana)).rowcount==1
        bad_assets=active.immutable_snapshot()
        assert next(i.quantity for i in bad_assets.items if i.id==carried_mana)==2**31
        try:active.receive_role_consumable(body,epoch,'resource-medicine-failure')
        except struct.error:pass
        else:raise AssertionError('Late native bag overflow did not execute')
        assert active.immutable_snapshot()==bad_assets and resources()==wounded
        with closing(store.connect()) as db,db:
            db.execute('UPDATE inventory_items SET quantity=1 WHERE id=?',(carried_mana,))
        paid=active.receive_role_consumable(body,epoch,'resource-medicine-failure')
        assert (resources().hp,resources().mp)==(100,20)
        assert struct.unpack_from('>f',paid[0][1],5)[0]==100
        current=resources();before=active.immutable_snapshot()
        active.receive_role_consumable(body,epoch,'resource-medicine-failure')
        assert resources()==current and active.immutable_snapshot()==before
        refused(lambda:use('resource-medicine-full'))
        assert resources()==current and active.immutable_snapshot()==before
        dead=controlled_values(0,20,'controlled-dead-resource-state')
        refused(lambda:use('resource-medicine-dead'))
        assert resources()==dead and active.immutable_snapshot()==before
        # Explicit argument injection also works; a legacy Inventory has no new
        # authority merely because metadata exists, and new rules do not migrate.
        legacy=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refused(lambda:legacy.use_role_consumable(db,medicine,epoch,'no-resource-contract'))
            receipt=legacy.use_role_consumable(db,medicine,epoch,'resource-medicine-once',
                resource_rules=rules,equipment_rules=gear)
            assert receipt.vitals.hp==0
        # Swap to a real opaque lease; an old callback cannot even replay. The
        # paid domain identity survives the new lease without resource mutation.
        old_epoch=epoch;epoch='药品资源:00007'
        with closing(store.connect()) as db,db:
            db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?',(epoch,role['id']))
        active=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'],
            resource_rules=rules,equipment_attribute_rules=gear)
        refused(lambda:legacy.receive_role_consumable(body,old_epoch,'resource-medicine-once',rules,gear))
        assert active.receive_role_consumable(body,epoch,'resource-medicine-once')[0][0]==0xc32c8
        assert resources()==dead and active.immutable_snapshot()==before
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            final=current_resource_profile(db,1111,role['id'],epoch,active.immutable_snapshot_transaction(db),
                equipment_rules=gear,resource_rules=rules)
            assert final.vitals.hp==0 and final.attributes.physical_attack==45
        assert Inventory(AccountStore(store.path),1111,role['id'],store.inventory_config).immutable_snapshot()==before
        # Injected rules keep an explicitly UNMIGRATED role on the legacy
        # contract. Its already-paid legacy receipt also survives later transfer.
        other=store.create_role(1111,'未转交药品',11,1010109)
        other_epoch=store.acquire_lease(1111,other['id'])
        other_inv=Inventory(store.leased(1111,other['id'],other_epoch),1111,other['id'],
            resource_rules=rules,equipment_attribute_rules=gear)
        with closing(other_inv.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            growth=initialize_growth(db,1111,other['id'],other_epoch,store.growth_rules,expected_level=1,free_points=0)
            initialize_attribute_baseline(db,1111,other['id'],other_epoch,p.baseline(other['id']),growth,
                store.attribute_rules,replace(p.vitals(other['id']),hp=70,mp=40))
            initialize_wallet(db,1111,other['id'],other_epoch,(100,0,0,0),'explicit_migration',store.currency_rules)
            initialize_equipment_attribute_basis(db,1111,other['id'],other_epoch,
                EquipmentAttributeBasis(other['id'],9,0,gear.revision,0,'known-old-medicine-fixture'),gear)
            other_inv.apply_settlement(db,AssetChange('old-profile-medicine',grants=((32000,2),)))
            other_key=other_inv.immutable_snapshot_transaction(db).items[0].id
            old_paid=other_inv.use_role_consumable(db,other_key,other_epoch,'paid-before-transfer')
            assert (old_paid.vitals.hp,old_paid.vitals.mp)==(100,40)
            refused(lambda:read_role_resources(db,1111,other['id'],other_epoch,rules))
            known=read_attribute_snapshot(db,1111,other['id'],other_epoch).vitals
            totals=current_equipment_totals(db,1111,other['id'],other_epoch,other_inv.immutable_snapshot_transaction(db),gear)
            migrated=migrate_role_resources(db,1111,other['id'],other_epoch,known,resource_caps_from_projection(totals),
                origin='explicit_migration',migration_id='old-profile-transfer',rules=rules,equipment_rules=gear)
            transition=plan_resource_values(migrated,10,40,'medicine',rules)
            late=apply_resource_transition(db,1111,other['id'],other_epoch,transition,'controlled-old-profile-wound',
                rules=rules,equipment_rules=gear).resources
        before_other=other_inv.immutable_snapshot()
        raw=Inventory(store.leased(1111,other['id'],other_epoch),1111,other['id'])
        other_reply=raw.receive_role_consumable(struct.pack('>iiQ',other_key,0,other['id']),other_epoch,
            'paid-before-transfer',rules,gear)
        assert struct.unpack_from('>f',other_reply[0][1],5)[0]==10
        assert other_inv.immutable_snapshot()==before_other
        with closing(other_inv.accounts.connect()) as db:
            db.execute('BEGIN')
            assert read_role_resources(db,1111,other['id'],other_epoch,rules)==late
    report={'passed':['explicit migrated70/40 and actual equipped starter medicine debit use one carrier',
        'instance quality MP effect and original world resource/bag decoders',
        'actual debit advances inventory source; final equipment/resource profile agrees',
        'paid domain replay returns current10/20 and later0 without replanning or consuming',
        'actual carrier/resource/domain receipt aborts, outer failure and unknown cash roll back together',
        'actual late native bag overflow rolls back resource/source/item/receipts; same ID later commits once',
        'full/dead refuse without spending; missing/partial explicit contract refuses',
        'method/constructor/positional native rule injection; untransferred legacy path and paid pre-transfer receipt retained',
        'actual opaque LeasedAccounts replacement lease and reopen'],
        'live_server_changed':False,'native_gui_tested':False,'automatic_migration':False,'six_slot_expansion':False}
    write_json(OUT/'evidence/role-consumable-resources-verification.json',report)
    print('PASS',', '.join(report['passed']))


if __name__=='__main__':main()
