"""Real soul action keeps a worn green-gem human cap in the sole resource row."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from fractions import Fraction
import struct
import sqlite3
from accounts import AccountStore
from inventory import Inventory,AssetChange
from item_effects import VitalState
from role_attributes import AttributeBaseline
from role_attribute_storage import initialize_attribute_baseline
from role_growth import initialize_growth
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis
from role_resource_storage import migrate_role_resources,read_role_resources
from role_equipment_gems import GemEquipmentRules,GemExtraBasis
import role_equipment_gem_storage as gem_roles
from equipment_gems import GemState,embed
from equipment_gem_score import GemScoreBasis,project
import equipment_gem_storage as sockets
import equipment_gem_score_storage as scores
import equipment_gem_presentation as presentation
from currency import initialize_wallet
from pet_souls import SoulProfile
from pet_soul_item_storage import OrbSource
from pet_soul_item_data import OrbTips
from pet_soul_actions import SoulActionRules,SoulActionAuthority
import pet_soul_storage as souls
import pet_soul_item_storage as orbs
import pet_soul_action_storage as actions
import runtime_storage


def main():
    with TemporaryDirectory(prefix='soul-gem-resource-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        rules=SoulActionRules.load();gems=GemEquipmentRules.load()
        context=actions.SoulResourceRules(store.resource_rules,gems.carrier_rules)
        with closing(store.connect()) as db:
            souls.prepare(db);orbs.prepare(db);actions.prepare(db);sockets.prepare(db);scores.prepare(db);gem_roles.prepare(db)
            db.execute('CREATE TABLE test_gem_soul_authority(role_id INTEGER PRIMARY KEY,version INTEGER,allowed INTEGER,flag22 INTEGER)')
        shape=next(k for k,c in gems.carrier_rules.shape_characters.items() if c==2)
        role=store.create_role(1111,'宝石元魂同源',min(store.choices[shape]),shape);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid)
        def source(db,inventory,pet,keys):
            row=db.execute('SELECT version,allowed,flag22 FROM test_gem_soul_authority WHERE role_id=?',(inventory.role_id,)).fetchone()
            if row is None or keys or row[1] not in (0,1):raise ValueError('Missing explicit fixture authority')
            return SoulActionAuthority(rid,pet,inventory.epoch,'explicit-gem-soul-fixture',row[0],row[1]==1,row[2],())
        def sync(db,inventory,snapshot,*,replayed,request_id):
            return gem_roles.synchronize_inventory_source(db,inventory,gems,store.resource_rules,request_id,replayed=replayed)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('UPDATE roles SET level=10 WHERE id=?',(rid,));db.execute('INSERT INTO role_progress VALUES(?,0)',(rid,))
            growth=initialize_growth(db,1111,rid,epoch,store.growth_rules,expected_level=10,free_points=0)
            old=initialize_attribute_baseline(db,1111,rid,epoch,
                AttributeBaseline(rid,10,0,(10,)*5,(100,100,20,10,50,10,10,20,10)),growth,
                store.attribute_rules,VitalState(rid,0,70,100,40,100)).vitals
            basis=EquipmentAttributeBasis(rid,2,0,gems.revision,0,'explicit-gem-role',seal_resistance=0)
            initialize_equipment_attribute_basis(db,1111,rid,epoch,basis,gems.carrier_rules)
            gem_roles.initialize_extra(db,inv,gems,GemExtraBasis(rid,0,gems.revision,basis.source_id,
                ((350,0),(360,0),(370,0),(380,0),(1130,0),(1530,0))),'explicit_known_ungemmed_extras')
            migrate_role_resources(db,1111,rid,epoch,old,resource_caps_from_projection(gem_roles.read_totals(db,inv,gems).core),
                origin='explicit_migration',migration_id='explicit-gem-soul-role',rules=store.resource_rules,equipment_rules=gems.carrier_rules)
            initialize_wallet(db,1111,rid,epoch,(20000,0,0,0),'explicit_migration',store.currency_rules)
            db.execute('INSERT INTO test_gem_soul_authority VALUES(?,0,1,0)',(rid,))
        # Explicit known human-gear setup using public domain writers. This is
        # fixture preparation, not a paid gem insertion/admission certification.
        inv.grant_item(45001);inv.grant_item(35005)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');snapshot=inv.immutable_snapshot_transaction(db)
            belt=next(i for i in snapshot.items if i.template_id==45001);stone=next(i for i in snapshot.items if i.template_id==35005)
            sockets.initialize(db,inv,gems.gem_rules,belt.id,GemState(0,(),gems.gem_rules.revision),0,'explicit_known_socket_profile')
            score=GemScoreBasis(rid,belt.id,gems.score_rules.revision,0,'known-gem-belt')
            scores.initialize(db,inv,gems.score_rules,gems.gem_rules,score,'explicit_known_pre_gem_score')
            sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='known-gem-import')
            before=read_role_resources(db,1111,rid,epoch,store.resource_rules)
            inv.equip_transaction(db,belt.id,4,epoch,'known-gem-wear')
            gem_roles.settle_equipment(db,inv,gems,store.resource_rules,before,'known-gem-wear')
            before=read_role_resources(db,1111,rid,epoch,store.resource_rules)
            socket=sockets.read(db,inv,gems.gem_rules,belt.id)
            plan=embed(gems.gem_rules,socket.item,socket.state,stone,0,flags=(0,0))
            change=project(gems.score_rules,gems.gem_rules,socket.item,socket.state,plan.after,score)
            saved=sockets.replace_state(db,inv,gems.gem_rules,socket,plan.after)
            presentation.apply(db,inv,gems.gem_rules,gems.score_rules,socket,saved,change)
            inv.apply_settlement(db,AssetChange('known-green-material',debits=((stone.id,1),)))
            gem_roles.settle_equipment(db,inv,gems,store.resource_rules,before,'known-green-fixture')
        pet=inv.grant_pet(500001);inv.fight_pet(pet);inv.grant_item(31276)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');orb=next(i for i in inv.immutable_snapshot_transaction(db).items if i.template_id==31276)
            souls.initialize(db,inv,rules.orbs.souls,SoulProfile(rid,pet,0,rules.orbs.souls.revision,'known-empty-gem-pet',()),'explicit_known_pet_souls')
            orbs.initialize(db,inv,rules.orbs,OrbSource(rid,orb.id,31276,0,rules.orbs.revision,'known-gem-role-orb',
                OrbTips(61,10001,-205,204),0,-2),'explicit_known_orb_instance')
            sync(db,inv,inv.immutable_snapshot_transaction(db),replayed=False,request_id='known-soul-fixture')
            human_before=gem_roles.read_profile(db,inv,gems,store.resource_rules)
            assert (human_before.core.vitals.hp,human_before.core.vitals.max_hp,human_before.core.vitals.mp)==(70,203,40)
            command=actions.admit(db,inv,rules,'gem-role-soul-wear',0xc03ff,struct.pack('>iiq',orb.id,1,pet),authority_reader=source,deadline_ms=1000,clock_ms=lambda:100)
            result=actions.apply(db,inv,rules,store.currency_rules,command,resource_context=context,clock_ms=lambda:100,authority_reader=source,precommit=sync)
            assert result.effects==((1,31276,2,2,81,1,Fraction(32)),)
            human_after=gem_roles.read_profile(db,inv,gems,store.resource_rules)
            assert human_after.core.attributes==human_before.core.attributes
            assert human_after.raw_modifiers==((141,55),)
            assert (result.resources.hp,result.resources.caps.hp_max,result.resources.mp)==(70,203,40)
            assert result.resources.version==human_before.core.vitals.version
            assert result.resources.caps.source.inventory_revision==result.snapshot.inventory_revision
            assert sockets.read(db,inv,gems.gem_rules,belt.id).state.templates==(35005,)
        with closing(store.connect()) as db:
            db.execute('BEGIN');db.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in
                (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            paid=actions.apply(db,inv,rules,store.currency_rules,command,resource_context=context,clock_ms=lambda:100,authority_reader=source,precommit=sync)
            assert paid.replayed and paid.resources==result.resources
        print('PASS actual soul wear joins complete-gem source policy/sole carrier with real worn green belt203 cap; '
            '70HP/40MP/version/human attributes/gem remain unchanged, paid strict readonly; explicit clearance fixture')


if __name__=='__main__':main()
