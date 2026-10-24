"""Actual original chapter domains with an explicitly migrated resource profile.

No task offer or XP grant is injected into the Jiaxing objective. NPC positions
are trusted domain fixtures; this is not the root's natural navigation verifier.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory
from task_newbie_chapter import record_newbie_creation,initialize_newbie_chapter,authorize_newbie_playback,finish_newbie_chapter
from task_master_card import open_master_dialogue,authorize_master_card,choose_master_card,equip_master_transaction,reconcile_master_equipment
from task_cart_dialogue import open_cart_dialogue_transaction,authorize_cart_transfer_transaction
from task_cart_transfer import resolve_cart_transfer,complete_cart_transfer_transaction
from task_conversation import TaskConversation
from task_session import TaskIntent
from task_protocol import C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,S_REFRESH_SCENARIO_QUEST_STATE
from task_persistence import load_task_state
from task_workflow import complete_task_transaction,completion_messages
from world_newbie import NewbieFlow
from world_owner import Location,MapAddress,MapOwner
from world_catalog import maps,maze_grids
from world_npcs import load_placements,NpcScene
import world_transfer_storage
from role_growth import initialize_growth,read_growth
from role_attribute_storage import initialize_attribute_baseline
from role_equipment import EquipmentAttributeBasis,resource_caps_from_projection
from role_equipment_storage import initialize_equipment_attribute_basis,current_equipment_totals
from role_resource_plan import load_resource_rules,plan_resource_caps
from role_resource_storage import migrate_role_resources,read_role_resources,apply_resource_transition
from currency import initialize_wallet
from role_attribute_protocol import role_detail_profile
from inspect_client import OUT
import runtime_storage


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Unstaged migrated equipment accepted')


class BrokenBag(Inventory):
    def equipment_bag_messages(self,db,epoch):
        raise ValueError('controlled migrated master precommit encoding failure')


def main():
    with tempfile.TemporaryDirectory(prefix='task-resource-jiaxing-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3');runtime_storage.prepare(store)
        resources=store.task_resources;chapters=store.newbie_rules;masters=store.master_card_rules
        carts=store.cart_resources;cart_rules=store.cart_transfer_rules;gear=store.equipment_attribute_rules
        route=chapters.routes[(9,11)];master=masters.routes[(9,11)];cart=carts.routes[master.cart_task_id]
        catalog=maps();grids=maze_grids();placements=load_placements();rules=load_resource_rules()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            role_id=db.execute("INSERT INTO roles(account_id,name,school,shape) VALUES(1111,'原领域嘉兴资源',11,1010109)").lastrowid
            origin=record_newbie_creation(db,1111,role_id,'resource-chain-creation',resources,chapters)
            db.execute('INSERT INTO role_positions VALUES(?,?,?,?)',(role_id,*origin.spawn))
        epoch=store.acquire_lease(1111,role_id);inv=Inventory(store.leased(1111,role_id,epoch),1111,role_id)
        location=Location(role_id,epoch,MapAddress(route.home_map_id,1,0),1,*origin.spawn[1:])
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            initialize_wallet(db,1111,role_id,epoch,(31,0,0,0),'explicit_migration',store.currency_rules)
            growth=initialize_growth(db,1111,role_id,epoch,store.growth_rules,expected_level=1,free_points=0)
            p=store.attribute_rules.initial_profile
            legacy=initialize_attribute_baseline(db,1111,role_id,epoch,p.baseline(role_id),growth,
                store.attribute_rules,replace(p.vitals(role_id),hp=70,mp=40))
            initialize_equipment_attribute_basis(db,1111,role_id,epoch,
                EquipmentAttributeBasis(role_id,9,0,gear.revision,0,'known-chapter-resource-fixture'),gear)
            caps=resource_caps_from_projection(current_equipment_totals(db,1111,role_id,epoch,inv.immutable_snapshot_transaction(db),gear))
            migrate_role_resources(db,1111,role_id,epoch,legacy.vitals,caps,origin='explicit_migration',
                migration_id='known-profile-before-intro',rules=rules,equipment_rules=gear)
            flow=NewbieFlow(resources,chapters.routes)
            initialize_newbie_chapter(db,1111,role_id,epoch,flow,chapters)
            intro=authorize_newbie_playback(db,1111,role_id,epoch,flow,chapters,location,generation=1,request_id='resource-intro',now_ms=1)
            finish_newbie_chapter(db,1111,role_id,epoch,NewbieFlow.from_ticket(resources,chapters.routes,intro.ticket),chapters,
                struct.pack('>i',route.intro_movie_id),location,inv,generation=1,now_ms=2,currency_rules=store.currency_rules,
                growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,pet_experience_rules=store.task_pet_experience_rules,
                resource_rules=rules,equipment_rules=gear)
        teacher=next(p for p in placements[master.home_map_id] if p.npc_id==master.npc_id)
        location=replace(location,version=2,x=teacher.x,y=teacher.y)
        scene=NpcScene(location.address,placements[location.address.map_id],catalog,interaction_radius=32,binding_capacity=2)
        scene.bind(701,teacher.placement_id)
        proof=scene.interact(struct.pack('>Q',701),location,location,request_id='resource-teacher',deadline_ms=1000,now_ms=3)
        assert (49009,1) in master.choices
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            opening=open_master_dialogue(db,1111,role_id,epoch,resources,masters,proof,location,generation=1,now_ms=4)
            authorize_master_card(db,1111,role_id,epoch,resources,masters,opening.ticket,
                TaskIntent(C_COMMIT_SCENARIO_QUEST,master.master_task_id,opening.ticket.entity_key,0),location,generation=1,now_ms=5)
        with closing(store.connect()) as db:
            before_card=tuple(db.iterdump())
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                choose_master_card(db,1111,role_id,epoch,resources,masters,struct.pack('>ii',master.card_effect_id,49009),
                    location,BrokenBag(store.leased(1111,role_id,epoch),1111,role_id),generation=1,now_ms=6,
                    currency_rules=store.currency_rules,growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,
                    pet_experience_rules=store.task_pet_experience_rules,resource_rules=rules,equipment_rules=gear)
            raise AssertionError('Controlled card failure did not fire')
        except ValueError as error:
            assert 'controlled migrated master' in str(error)
        with closing(store.connect()) as db:
            assert tuple(db.iterdump())==before_card
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            chosen=choose_master_card(db,1111,role_id,epoch,resources,masters,struct.pack('>ii',master.card_effect_id,49009),
                location,inv,generation=1,now_ms=6,currency_rules=store.currency_rules,
                growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,pet_experience_rules=store.task_pet_experience_rules,
                resource_rules=rules,equipment_rules=gear)
            source=read_role_resources(db,1111,role_id,epoch,rules)
            assert source.caps.source.inventory_revision==inv.immutable_snapshot_transaction(db).inventory_revision
            assert (source.hp,source.mp,source.version)==(70,40,0)
            changes=db.total_changes
            refuse(lambda:equip_master_transaction(db,1111,role_id,epoch,resources,masters,inv,chosen.choice.item_key,0,
                'resource-equip',resource_rules=rules,equipment_rules=gear))
            assert db.total_changes==changes
        def equip_and_reconcile(db):
            source=read_role_resources(db,1111,role_id,epoch,rules)
            event=inv.equip_transaction(db,chosen.choice.item_key,0,epoch,'resource-equip')
            changes=db.total_changes
            refuse(lambda:reconcile_master_equipment(db,1111,role_id,epoch,resources,masters,inv,event=event,
                resource_rules=rules,equipment_rules=gear))
            assert db.total_changes==changes
            caps=resource_caps_from_projection(current_equipment_totals(db,1111,role_id,epoch,inv.immutable_snapshot_transaction(db),gear))
            transition=plan_resource_caps(source,caps,'equip',rules)
            apply_resource_transition(db,1111,role_id,epoch,transition,'resource-equip-caps',rules=rules,equipment_rules=gear)
            equipped=reconcile_master_equipment(db,1111,role_id,epoch,resources,masters,inv,event=event,
                currency_rules=store.currency_rules,growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,
                pet_experience_rules=store.task_pet_experience_rules,resource_rules=rules,equipment_rules=gear)
            assert equipped.completion.started_tasks==(cart.task_id,)
            assert read_role_resources(db,1111,role_id,epoch,rules)==transition.after
            assert completion_messages(equipped.completion)
            return equipped
        with closing(store.connect()) as db:
            before_equip=tuple(db.iterdump())
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');equip_and_reconcile(db)
                raise RuntimeError('controlled after equipment/resource/type59 encoding')
        except RuntimeError as error:
            assert 'controlled after equipment' in str(error)
        with closing(store.connect()) as db:
            assert tuple(db.iterdump())==before_equip
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');equipped=equip_and_reconcile(db)
        driver=next(p for p in placements[cart.map_id] if p.npc_id==cart.npc_id)
        source=replace(location,version=10,x=driver.x,y=driver.y);scene.bind(702,driver.placement_id)
        proof=scene.interact(struct.pack('>Q',702),source,source,request_id='resource-driver',deadline_ms=1000,now_ms=10)
        store.save_checkpoint(1111,role_id,epoch,source.position,source.version)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            opening=open_cart_dialogue_transaction(db,1111,role_id,epoch,resources,carts,proof,source,generation=1,now_ms=11,deadline_ms=1000)
            intent=authorize_cart_transfer_transaction(db,1111,role_id,epoch,resources,carts,opening.ticket,
                TaskIntent(C_COMMIT_SCENARIO_QUEST,cart.task_id,702,0),source,generation=1,now_ms=12)
        resolved=resolve_cart_transfer(intent,carts,cart_rules,movement_state=0)
        src=MapOwner(source.address,catalog,capacity=1,transfer_capacity=1,mailbox_capacity=2,maze=grids[source.address.map_id]);src.join(source)
        dst=MapOwner(MapAddress(1006,1,0),catalog,capacity=1,transfer_capacity=1,mailbox_capacity=2,maze=grids[1006])
        offer=src.prepare_transfer(source,resolved.target_position,request_id=intent.request_id,deadline_ms=intent.deadline_ms,now_ms=13)
        receipt=dst.activate(src.freeze(dst.reserve(offer,14),15),16)
        world_transfer_storage.begin(store,1111,role_id,epoch,offer)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            cart_result=complete_cart_transfer_transaction(db,1111,role_id,epoch,resources,carts,cart_rules,intent,receipt,inv,
                generation=1,now_ms=17,movement_state=0,currency_rules=store.currency_rules,
                growth_rules=store.growth_rules,attribute_rules=store.attribute_rules,pet_experience_rules=store.task_pet_experience_rules,
                resource_rules=rules,equipment_rules=gear)
            assert cart_result.completion.started_tasks==(cart.successor_id,)
        src.finalize(receipt);current=dst.ready(receipt.location)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            assert read_growth(db,1111,role_id).experience==0
            actor,state=load_task_state(db,1111,role_id,epoch)
        target=resources.definitions[cart.successor_id]['target'];npc=next(p for p in placements[1006] if p.npc_id==target['npc_id'])
        location=replace(current,version=current.version+1,x=npc.x,y=npc.y)
        scene=NpcScene(location.address,placements[1006],catalog,interaction_radius=32,binding_capacity=1);scene.bind(703,npc.placement_id)
        proof=scene.interact(struct.pack('>Q',703),location,location,request_id='resource-jiaxing',deadline_ms=1000,now_ms=20)
        conversation=TaskConversation(resources,role_id,epoch)
        conversation.open(actor,state,cart.successor_id,proof,location,now_ms=21,deadline_ms=1000)
        plan=conversation.plan_finish(actor,state,TaskIntent(C_COMMIT_SCENARIO_QUEST,cart.successor_id,703,0),location,now_ms=22)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            result=complete_task_transaction(db,actor,plan,'resource-jiaxing-complete',resources,inv,store.growth_rules,store.attribute_rules,
                store.currency_rules,store.task_pet_experience_rules,resource_rules=rules,equipment_rules=gear)
            grown=read_growth(db,1111,role_id)
            assert (grown.level,grown.experience,grown.free_points)==(2,31,5)
            profile=result.attributes
            assert (profile.vitals.hp,profile.vitals.max_hp,profile.vitals.mp,profile.vitals.max_mp,profile.vitals.version)==(80,110,46,106,1)
            assert (profile.attributes.physical_attack,profile.attributes.magic_attack,profile.seal_strength)==(49,38,8)
            assert role_detail_profile(grown,profile).values[:5]==(80,110,110,46,106)
            assert sum(kind==0xc32c8 for kind,_ in completion_messages(result))==1
        conversation.acknowledge(plan)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');before=read_role_resources(db,1111,role_id,epoch,rules)
            replay=complete_task_transaction(db,actor,plan,'resource-jiaxing-complete',resources,inv,store.growth_rules,store.attribute_rules,
                store.currency_rules,store.task_pet_experience_rules,resource_rules=rules,equipment_rules=gear)
            assert read_role_resources(db,1111,role_id,epoch,rules)==before
            assert not any(kind==S_REFRESH_SCENARIO_QUEST_STATE for kind,_ in completion_messages(replay))
            # Paid card is a current read even after equipment/growth changed.
            changes=db.total_changes
            card_replay=choose_master_card(db,1111,role_id,epoch,resources,masters,struct.pack('>ii',master.card_effect_id,49009),
                None,inv,generation=1,now_ms=10000,resource_rules=rules,equipment_rules=gear)
            assert card_replay.replayed and db.total_changes==changes
            assert read_role_resources(db,1111,role_id,epoch,rules)==before
        report=dict(passed=['known70/40 explicitly transferred before intro; actual creation/intro/master-card/exact49009 equipment/cart/world transaction activates original Jiaxing without test offer',
            'card grant synchronizes inventory-only source without healing; paid card after equipment/growth is read-only; legacy equip wrapper and unstaged reconcile reject before writes',
            'public equip plus explicit equip resource transition then independent type59 reconcile share one transaction; task reconcile adds no second equipment transition',
            'late master bag encoding and post-equipment/resource/type59 encoding failures roll back full database; same durable identities retry once',
            'original120XP grows toL2/31/free5,80/110HP46/106MP/version1 and49/38/8 using migrated profile throughout chapter domains',
            'inner final profile produces one growth map and matching RoleDetail; original60001 delegates once, paid retry preserves current resource and suppressesstate1'],
            scope='original chapter domain chain, actual public modules and disposable DB/map owners; trusted NPC-position fixtures, not natural movement/connection barrier/GUI',
            shared_runtime_tested=False,native_gui_verified=False,live_server_changed=False,battle_executed=False)
    (OUT/'evidence/task-resource-jiaxing-chain-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
