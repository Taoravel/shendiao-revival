"""Actual intro/card/equipment/cart Modules in disposable DB/map owners.

NPC positions are trusted fixtures, not natural navigation or the live client.
The root's natural GameRuntime verifier remains independent and unchanged.
"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from unittest.mock import patch
import task_cart_transfer
from accounts import AccountStore
from inventory import Inventory
from tasks import prepare_task_store
from task_rewards import prepare_reward_storage
from task_persistence import load_task_state
from task_session import TaskIntent
from task_protocol import C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,S_REFRESH_SCENARIO_QUEST_STATE,decode_accept_scenario_quest
from task_newbie_chapter import (load_newbie_chapter_rules,prepare_newbie_chapter_storage,record_newbie_creation,
    initialize_newbie_chapter,authorize_newbie_playback,finish_newbie_chapter)
from task_master_card import (load_master_card_rules,prepare_master_card_storage,open_master_dialogue,
    authorize_master_card,choose_master_card,equip_master_transaction)
from task_cart_dialogue import load_cart_resources,open_cart_dialogue_transaction,authorize_cart_transfer_transaction
from task_cart_transfer import (load_cart_transfer_rules,prepare_cart_transfer_storage,resolve_cart_transfer,
    complete_cart_transfer_transaction)
from world_newbie import load_newbie_routes,NewbieFlow
from world_catalog import maps,maze_grids
from world_owner import MapOwner,MapAddress,Location
from world_npcs import NpcScene,load_placements
import world_transfer_storage as handoffs
from currency import prepare_wallet_storage,initialize_wallet,load_currency_rules
from progression import read_experience,credit_experience
from inspect_client import OUT


class BrokenRefresh(Inventory):
    def equipment_bag_messages(self,db,epoch):
        raise ValueError('controlled cart reply failure')


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid cart completion accepted')


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'cart.sqlite3');resources=prepare_task_store(accounts)
        config=Inventory.prepare(accounts);accounts.inventory_config=config
        catalog=maps();grids=maze_grids();cash=load_currency_rules()
        routes=load_newbie_routes();chapters=load_newbie_chapter_rules(resources,routes,catalog,grids)
        masters=load_master_card_rules(resources,chapters,config);carts=load_cart_resources(resources,masters)
        rules=load_cart_transfer_rules(carts,catalog,grids);placements=load_placements()
        # Exercise the real startup Interface with documentation-only edits;
        # a business-contract edit must still change the durable fingerprint.
        policy=json.loads((OUT/'design/newbie-cart-transfer-v1.json').read_text(encoding='utf-8'))
        alternate=Path(directory)/'alternate-policy';(alternate/'design').mkdir(parents=True)
        alternate_file=alternate/'design/newbie-cart-transfer-v1.json'
        policy['implementation_status']='a later documentation-only progress report'
        policy['native_gui_verified']=True;policy['live_server_changed']=True
        alternate_file.write_text(json.dumps(policy),encoding='utf-8')
        with patch.object(task_cart_transfer,'OUT',alternate):
            documented=load_cart_transfer_rules(carts,catalog,grids)
        assert documented.fingerprint==rules.fingerprint and documented.targets==rules.targets
        policy['authorization']['ticket']+='; a different business contract'
        alternate_file.write_text(json.dumps(policy),encoding='utf-8')
        with patch.object(task_cart_transfer,'OUT',alternate):
            changed=load_cart_transfer_rules(carts,catalog,grids)
        assert changed.fingerprint!=rules.fingerprint
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db);prepare_wallet_storage(db);prepare_newbie_chapter_storage(db)
            prepare_master_card_storage(db);prepare_cart_transfer_storage(db);handoffs.prepare(db)
        tested=set();exp_deltas=[]
        for origin_route in routes.values():
            master=masters.routes[(origin_route.character_id,origin_route.school_id)]
            if master.cart_task_id in tested:continue
            route=carts.routes[master.cart_task_id];index=len(tested)
            shape=next(s for s,c in resources.shape_to_role_config.items() if c==origin_route.character_id)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                role_id=db.execute('INSERT INTO roles(account_id,name,school,shape) VALUES(1111,?,?,?)',
                    (f'车夫完整前置{index}',origin_route.school_id,shape)).lastrowid
                creation=record_newbie_creation(db,1111,role_id,f'cart-test-create:{index}',resources,chapters)
                db.execute('INSERT INTO role_positions VALUES(?,?,?,?)',(role_id,*creation.spawn))
            epoch=accounts.acquire_lease(1111,role_id)
            inv=Inventory(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
            location=Location(role_id,epoch,MapAddress(origin_route.home_map_id,1,0),1,*creation.spawn[1:])
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                initialize_wallet(db,1111,role_id,epoch,(31,0,0,0),'explicit_migration',cash)
                flow=NewbieFlow(resources,routes)
                initialize_newbie_chapter(db,1111,role_id,epoch,flow,chapters)
                intro=authorize_newbie_playback(db,1111,role_id,epoch,flow,chapters,location,
                    generation=1,request_id='cart-intro',now_ms=1)
                finish_newbie_chapter(db,1111,role_id,epoch,NewbieFlow.from_ticket(resources,routes,intro.ticket),
                    chapters,struct.pack('>i',origin_route.intro_movie_id),location,inv,
                    generation=1,now_ms=2,currency_rules=cash)
            master_npc=next(x for x in placements[master.home_map_id] if x.npc_id==master.npc_id)
            location=replace(location,version=2,x=master_npc.x,y=master_npc.y)
            scene=NpcScene(location.address,placements[master.home_map_id],catalog,interaction_radius=32,binding_capacity=2)
            scene.bind(100,master_npc.placement_id)
            proof=scene.interact(struct.pack('>Q',100),location,location,
                request_id='actual-master',deadline_ms=1000,now_ms=3)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                opening=open_master_dialogue(db,1111,role_id,epoch,resources,masters,proof,location,generation=1,now_ms=4)
                authorize_master_card(db,1111,role_id,epoch,resources,masters,opening.ticket,
                    TaskIntent(C_COMMIT_SCENARIO_QUEST,master.master_task_id,opening.ticket.entity_key,0),location,generation=1,now_ms=5)
                chosen=choose_master_card(db,1111,role_id,epoch,resources,masters,
                    struct.pack('>ii',master.card_effect_id,master.choices[0][0]),location,inv,
                    generation=1,now_ms=6,currency_rules=cash)
                equipped=equip_master_transaction(db,1111,role_id,epoch,resources,masters,inv,
                    chosen.choice.item_key,0,'cart-equip',currency_rules=cash)
                assert equipped.completion.started_tasks==(route.task_id,)
            npc=next(x for x in placements[route.map_id] if x.npc_id==route.npc_id)
            source=replace(location,version=10,x=npc.x,y=npc.y)
            scene.bind(101,npc.placement_id)
            proof=scene.interact(struct.pack('>Q',101),source,source,
                request_id='actual-cart',deadline_ms=1000,now_ms=10)
            accounts.save_checkpoint(1111,role_id,epoch,source.position,source.version)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                opening=open_cart_dialogue_transaction(db,1111,role_id,epoch,resources,carts,proof,source,
                    generation=1,now_ms=11,deadline_ms=1000)
                intent=authorize_cart_transfer_transaction(db,1111,role_id,epoch,resources,carts,opening.ticket,
                    TaskIntent(C_COMMIT_SCENARIO_QUEST,route.task_id,101,0),source,generation=1,now_ms=12)
                before_exp=read_experience(db,1111,role_id).experience
                before_items=inv.immutable_snapshot_transaction(db,epoch=epoch).items
            resolved=resolve_cart_transfer(intent,carts,rules,movement_state=0)
            assert resolved.target_position==(1006,route.destination.x*16,route.destination.y*16)
            source_owner=MapOwner(source.address,catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2,
                maze=grids[source.address.map_id]);source_owner.join(source)
            target_owner=MapOwner(MapAddress(1006,1,0),catalog,capacity=2,transfer_capacity=2,mailbox_capacity=2,maze=grids[1006])
            offer=source_owner.prepare_transfer(source,resolved.target_position,request_id=intent.request_id,
                deadline_ms=intent.deadline_ms,now_ms=13)
            reservation=target_owner.reserve(offer,14);frozen=source_owner.freeze(reservation,15)
            receipt=target_owner.activate(frozen,16)
            def complete(db,request=intent,result=receipt,inventory=inv,**changes):
                options=dict(generation=1,now_ms=17,movement_state=0,currency_rules=cash);options.update(changes)
                return complete_cart_transfer_transaction(db,1111,role_id,epoch,resources,carts,rules,
                    request,result,inventory,**options)
            # No matching world journal is not a durable transfer proof.
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');refuse(lambda:complete(db))
            handoffs.begin(accounts,1111,role_id,epoch,offer)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                refuse(lambda:complete(db,generation=2));refuse(lambda:complete(db,now_ms=1000))
                refuse(lambda:complete(db,movement_state=1))
                refuse(lambda:complete(db,replace(intent,option_index=1)))
                refuse(lambda:complete(db,replace(intent,chapter_id='another-chapter')))
                refuse(lambda:complete(db,replace(intent,source=replace(source,version=source.version-1))))
                refuse(lambda:complete(db,replace(intent,task_revision=intent.task_revision+1)))
                refuse(lambda:complete(db,result=replace(receipt,location=replace(receipt.location,x=0))))
            if index==0:
                broken=BrokenRefresh(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
                try:
                    with closing(accounts.connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE');complete(db,inventory=broken)
                    raise AssertionError('Late cart reply failure committed')
                except ValueError as error:assert str(error)=='controlled cart reply failure'
            if index==1:
                try:
                    with closing(accounts.connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE');complete(db)
                        raise RuntimeError('caller target-scene encoding failed')
                except RuntimeError:pass
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                assert db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(role_id,)).fetchone()==source.position
                assert db.execute('SELECT stage FROM world_handoffs WHERE transfer_id=?',(intent.request_id,)).fetchone()==('prepared',)
                assert route.task_id in load_task_state(db,1111,role_id,epoch)[1].active
                assert read_experience(db,1111,role_id).experience==before_exp
                assert not db.execute('SELECT 1 FROM task_cart_transfers WHERE role_id=?',(role_id,)).fetchone()
                result=complete(db)
                assert not result.replayed and result.target==receipt.location
                assert result.completion.started_tasks==(route.successor_id,)
                assert decode_accept_scenario_quest(result.messages[-1][1]).state==0
                state=load_task_state(db,1111,role_id,epoch)[1]
                assert route.task_id in state.completed and route.successor_id in state.active
                assert inv.immutable_snapshot_transaction(db,epoch=epoch).items==before_items
                delta=read_experience(db,1111,role_id).experience-before_exp
                assert delta==resources.definitions[route.task_id]['display_rewards']['ExpReward']
                exp_deltas.append(delta)
                effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
                    (role_id,route.task_id)).fetchone()[0])
                assert effect['cart_transfer']['status']=='durable_target_loading'
                assert effect['continuation_fields']['RewardMapXPos']==str(route.destination.x)
                assert 'RewardMapXPos' in effect['continuation_resolved_fields']
            assert accounts.position(1111,role_id)==resolved.target_position
            source_owner.finalize(receipt);active=target_owner.ready(receipt.location)
            assert source_owner.location(role_id) is None and target_owner.location(role_id)==active
            # A later checkpoint must survive an old paid receipt replay.
            later=(1006,active.x+16,active.y)
            accounts.save_checkpoint(1111,role_id,epoch,later,active.version+1)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                credit_experience(db,1111,role_id,7)
                replay=complete(db,now_ms=1001)
                assert replay.replayed and replay.completion.rewards.experience_balance==before_exp+delta+7
                assert not any(k==S_REFRESH_SCENARIO_QUEST_STATE for k,_ in replay.messages)
                assert db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(role_id,)).fetchone()==later
                refuse(lambda:complete(db,replace(intent,request_id='fresh-duplicate-wire')))
            new_epoch=accounts.acquire_lease(1111,role_id)
            with closing(accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');refuse(lambda:complete(db))
                state=load_task_state(db,1111,role_id,new_epoch)[1]
                assert route.task_id in state.completed and route.successor_id in state.active
            assert accounts.position(1111,role_id)==later
            tested.add(route.task_id)
        assert len(tested)==10
        report=dict(routes_completed=len(tested),cart_exp_deltas=exp_deltas,policy=rules.revision,
            policy_fingerprint=rules.fingerprint,
            passed=['startup loader ignores only implementation_status/native_gui_verified/live_server_changed progress metadata; business contract changes alter fingerprint',
                'real explicit intro, actual NPC choice-card and exact received-instance equip prerequisites for10 original cart routes',
                'actual source prepare/reserve/freeze/target loading receipt, public caller-transaction world commit and cart rewards/unique native60001 successor',
                'wrong option/mode/generation/deadline/task revision/receipt and missing world journal refuse',
                'late bag and caller-scene failures roll back world target/decision, cart task/rewards/receipts; retry then commits once',
                'postcommit source cleanup/target ready; duplicate cannot reset later position, repeat state1, grant again or substitute a new transfer identity',
                'new lease reload retains current target checkpoint and original successor; old epoch callback refuses'],
            scope='disposable DB, real public domain/storage/map owners; trusted NPC-position fixtures, no natural navigation/connection send barrier/GUI',
            shared_runtime_integrated=False,client_tested=False)
    (OUT/'evidence/task-cart-transfer-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
