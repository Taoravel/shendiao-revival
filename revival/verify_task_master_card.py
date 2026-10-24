"""Controlled offline caller transactions; no shared runtime/client operations."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory,AssetChange
from tasks import prepare_task_store
from task_rewards import prepare_reward_storage
from task_persistence import load_task_state
from task_domain import supports_plain_dialogue
from task_session import TaskIntent
from task_protocol import (C_COMMIT_SCENARIO_QUEST,C_QUEST_DIALOG_END,decode_accept_scenario_quest,
    S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state,SCENARIO_READY)
from task_newbie_chapter import (load_newbie_chapter_rules,prepare_newbie_chapter_storage,
    record_newbie_creation,initialize_newbie_chapter,authorize_newbie_playback,finish_newbie_chapter)
from task_master_card import (load_master_card_rules,prepare_master_card_storage,open_master_dialogue,
    authorize_master_card,choose_master_card,equip_master_transaction,reconcile_master_equipment,master_resume_messages)
from world_newbie import NewbieFlow,load_newbie_routes
from world_catalog import maps,maze_grids
from world_owner import Location,MapAddress
from world_npcs import NpcInteraction,NpcScene,load_placements
from task_cart_dialogue import load_cart_resources,open_cart_dialogue_transaction,authorize_cart_transfer_transaction
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet
from inspect_client import OUT
from research_task_existing_quest import assert_ready_before_visit


def refuse(call,match=None):
    try:call()
    except ValueError as e:
        if match:assert match in str(e),str(e)
        return
    raise AssertionError('Invalid card operation accepted')


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'master.sqlite3')
        resources=prepare_task_store(accounts)
        config=Inventory.prepare(accounts)
        routes=load_newbie_routes()
        chapter_rules=load_newbie_chapter_rules(resources,routes,maps(),maze_grids())
        rules=load_master_card_rules(resources,chapter_rules,config)
        carts=load_cart_resources(resources,rules)
        cart_checked=set()
        native_ready_checks=[]
        placements=load_placements()
        cash=load_currency_rules()
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db);prepare_newbie_chapter_storage(db);prepare_master_card_storage(db);prepare_wallet_storage(db)
        count=0
        for route in routes.values():
            for option in (0,1):
                count+=1
                shape=next(s for s,c in resources.shape_to_role_config.items() if c==route.character_id)
                with closing(accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    role_id=db.execute('INSERT INTO roles(account_id,name,school,shape) VALUES(1111,?,?,?)',
                        (f'首武器{count}',route.school_id,shape)).lastrowid
                    origin=record_newbie_creation(db,1111,role_id,f'controlled-create:{count}',resources,chapter_rules)
                    db.execute('INSERT INTO role_positions VALUES(?,?,?,?)',(role_id,*origin.spawn))
                epoch=accounts.acquire_lease(1111,role_id)
                location=Location(role_id,epoch,MapAddress(route.home_map_id,1,0),1,*origin.spawn[1:])
                inv=Inventory(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
                flow=NewbieFlow(resources,routes)
                with closing(accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    initialize_wallet(db,1111,role_id,epoch,(31,0,0,0),'explicit_migration',cash)
                    initialize_newbie_chapter(db,1111,role_id,epoch,flow,chapter_rules)
                    playback=authorize_newbie_playback(db,1111,role_id,epoch,flow,chapter_rules,location,generation=1,request_id='intro',now_ms=1)
                    finish_newbie_chapter(db,1111,role_id,epoch,NewbieFlow.from_ticket(resources,routes,playback.ticket),
                        chapter_rules,struct.pack('>i',route.intro_movie_id),location,inv,generation=1,now_ms=2,currency_rules=cash)
                card=rules.routes[(route.character_id,route.school_id)]
                assert not supports_plain_dialogue(resources.definitions[card.master_task_id])
                selected=card.choices[option][0]
                body=struct.pack('>ii',card.card_effect_id,selected)
                generation=1
                proof=NpcInteraction(f'master:{role_id}',role_id,epoch,location.address,location.version,9000+role_id,card.npc_id,1)
                def choose(db,**overrides):
                    args=dict(generation=generation,now_ms=10,currency_rules=cash);args.update(overrides)
                    return choose_master_card(db,1111,role_id,epoch,resources,rules,body,location,inv,**args)
                with closing(accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    refuse(lambda:choose(db),'Unsolicited')
                    refuse(lambda:open_master_dialogue(db,1111,role_id,epoch,resources,rules,replace(proof,npc_id=99999),location,generation=1,now_ms=3))
                    dialogue=open_master_dialogue(db,1111,role_id,epoch,resources,rules,proof,location,generation=1,now_ms=3)
                    assert decode_accept_scenario_quest(dialogue.messages[0][1]).state==3
                    assert (S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state(card.master_task_id,SCENARIO_READY)) in dialogue.messages[:-1], 'Existing first-master bean remains active: duplicate acceptance cannot enable Start dialogue'
                    if count==1:
                        native_ready_checks.append(assert_ready_before_visit(dialogue.messages,card.master_task_id))
                    ack=TaskIntent(C_COMMIT_SCENARIO_QUEST,card.master_task_id,proof.entity_key,0)
                    end=TaskIntent(C_QUEST_DIALOG_END,card.master_task_id)
                    refuse(lambda:authorize_master_card(db,1111,role_id,epoch,resources,rules,dialogue.ticket,end,location,generation=1,now_ms=4))
                    assert db.execute('SELECT COUNT(*) FROM task_master_choices WHERE role_id=?',(role_id,)).fetchone()[0]==0
                    assert authorize_master_card(db,1111,role_id,epoch,resources,rules,dialogue.ticket,ack,location,generation=1,now_ms=4)==((0xc001c,struct.pack('>i',card.card_effect_id)),)
                    refuse(lambda:choose(db,generation=2))
                    refuse(lambda:choose(db,now_ms=dialogue.ticket.deadline_ms))
                    refuse(lambda:choose_master_card(db,1111,role_id,epoch,resources,rules,body,replace(location,version=2),inv,generation=1,now_ms=5))
                    refuse(lambda:choose_master_card(db,1111,role_id,epoch,resources,rules,body+b'\x00',location,inv,generation=1,now_ms=5))
                if count==2:
                    # A new connection has to visit the real master again; the
                    # old durable permit cannot authorize the new session.
                    old_epoch=epoch
                    old_location=location
                    epoch=accounts.acquire_lease(1111,role_id)
                    generation=2
                    location=replace(location,login_epoch=epoch,version=2)
                    proof=replace(proof,login_epoch=epoch,position_version=2,source_id=f'master-reconnect:{role_id}')
                    inv=Inventory(accounts,1111,role_id,config,epoch=epoch,currency_rules=cash)
                    with closing(accounts.connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE')
                        refuse(lambda:choose_master_card(db,1111,role_id,old_epoch,resources,rules,body,old_location,inv,generation=1,now_ms=5))
                        refuse(lambda:choose(db))
                        refuse(lambda:authorize_master_card(db,1111,role_id,epoch,resources,rules,dialogue.ticket,ack,location,generation=2,now_ms=5))
                        renewed=open_master_dialogue(db,1111,role_id,epoch,resources,rules,proof,location,generation=2,now_ms=6)
                        authorize_master_card(db,1111,role_id,epoch,resources,rules,renewed.ticket,ack,location,generation=2,now_ms=7)
                        assert db.execute('SELECT COUNT(*) FROM task_master_choices WHERE role_id=?',(role_id,)).fetchone()[0]==1
                if count==1:
                    # Full bag must leave the pending authorization/source intact.
                    with closing(accounts.connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE')
                        inv.apply_settlement(db,AssetChange('fill-bag',grants=((card.choices[1][0],1,1),)))
                    small=replace(config,policy=dict(config.policy,bag_capacity=1))
                    full=Inventory(accounts,1111,role_id,small,epoch=epoch,currency_rules=cash)
                    with closing(accounts.connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE')
                        refuse(lambda:choose_master_card(db,1111,role_id,epoch,resources,rules,body,location,full,generation=1,now_ms=5),'Bag full')
                    try:
                        with closing(accounts.connect()) as db,db:
                            db.execute('BEGIN IMMEDIATE')
                            result=choose(db)
                            raise RuntimeError('after card/item/task/next write')
                    except RuntimeError:pass
                    with closing(accounts.connect()) as db,db:
                        db.execute('BEGIN')
                        assert db.execute('SELECT selected_item FROM task_master_choices WHERE role_id=?',(role_id,)).fetchone()==(None,)
                        _,state=load_task_state(db,1111,role_id,epoch)
                        assert card.master_task_id in state.active and card.equipment_task_id not in state.active
                with closing(accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    result=choose(db)
                    key=result.choice.item_key
                    current=inv.immutable_snapshot_transaction(db,epoch=epoch)
                    selected_item=next(x for x in current.items if x.id==key)
                    assert selected_item.binding==1 and selected_item.condition is not None and selected_item.equipment_slot is None
                    _,state=load_task_state(db,1111,role_id,epoch)
                    assert card.master_task_id in state.completed and card.equipment_task_id in state.active
                    assert tuple(decode_accept_scenario_quest(b).quest_id for _,b in master_resume_messages(
                        db,1111,role_id,epoch,resources,rules))==(card.equipment_task_id,)
                    assert card.cart_task_id not in state.active
                    assert reconcile_master_equipment(db,1111,role_id,epoch,resources,rules,inv).completion is None
                with closing(accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    assert choose(db).replayed
                    other=struct.pack('>ii',card.card_effect_id,card.choices[1-option][0])
                    refuse(lambda:choose_master_card(db,1111,role_id,epoch,resources,rules,other,location,inv,generation=generation,now_ms=8),'Committed')
                if count==1:
                    try:
                        with closing(accounts.connect()) as db,db:
                            db.execute('BEGIN IMMEDIATE')
                            equip_master_transaction(db,1111,role_id,epoch,resources,rules,inv,key,0,'equip-selected',currency_rules=cash)
                            raise RuntimeError('after equip/59/cart')
                    except RuntimeError:pass
                    with closing(accounts.connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE')
                        assert next(x for x in inv.immutable_snapshot_transaction(db,epoch=epoch).items if x.id==key).equipment_slot is None
                        _,state=load_task_state(db,1111,role_id,epoch)
                        assert card.equipment_task_id in state.active and card.cart_task_id not in state.active
                        wrong=next(x.id for x in inv.immutable_snapshot_transaction(db,epoch=epoch).items if x.id!=key)
                        assert equip_master_transaction(db,1111,role_id,epoch,resources,rules,inv,wrong,0,'equip-other',currency_rules=cash).completion is None
                with closing(accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    if count==2:
                        # Trusted recovery reads the actual already-equipped
                        # selected instance; a historical event is unnecessary.
                        inv.equip_transaction(db,key,0,epoch,'equip-selected')
                        done=reconcile_master_equipment(db,1111,role_id,epoch,resources,rules,inv,currency_rules=cash)
                    else:
                        done=equip_master_transaction(db,1111,role_id,epoch,resources,rules,inv,key,0,'equip-selected',currency_rules=cash)
                    assert done.completion is not None
                    _,state=load_task_state(db,1111,role_id,epoch)
                    assert card.equipment_task_id in state.completed and card.cart_task_id in state.active
                    assert tuple(decode_accept_scenario_quest(b).quest_id for _,b in master_resume_messages(
                        db,1111,role_id,epoch,resources,rules))==(card.cart_task_id,)
                    assert done.completion.started_tasks==(card.cart_task_id,)
                if card.cart_task_id not in cart_checked:
                    cart_route=carts.routes[card.cart_task_id]
                    npc=next(p for p in placements[card.home_map_id] if p.npc_id==cart_route.npc_id)
                    cart_location=replace(location,version=location.version+10,x=npc.x,y=npc.y)
                    cart_scene=NpcScene(cart_location.address,placements[card.home_map_id],maps(),interaction_radius=32,binding_capacity=1)
                    cart_scene.bind(900000+role_id,npc.placement_id)
                    cart_proof=cart_scene.interact(struct.pack('>Q',900000+role_id),cart_location,cart_location,
                        request_id=f'actual-cart-proof:{role_id}',deadline_ms=1000,now_ms=20)
                    with closing(accounts.connect()) as db,db:
                        db.execute('BEGIN IMMEDIATE')
                        before_state=load_task_state(db,1111,role_id,epoch)[1]
                        before_position=db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(role_id,)).fetchone()
                        opened=open_cart_dialogue_transaction(db,1111,role_id,epoch,resources,carts,cart_proof,cart_location,
                            generation=generation,now_ms=21,deadline_ms=1000)
                        assert decode_accept_scenario_quest(opened.messages[0][1]).state==3
                        assert (S_REFRESH_SCENARIO_QUEST_STATE,encode_scenario_state(cart_route.task_id,SCENARIO_READY)) in opened.messages[:-1], 'Existing cart bean remains active: duplicate acceptance cannot enable Start dialogue'
                        native_ready_checks.append(assert_ready_before_visit(opened.messages,cart_route.task_id))
                        intent=TaskIntent(C_COMMIT_SCENARIO_QUEST,cart_route.task_id,cart_proof.entity_key,0)
                        def select(branch=intent,where=cart_location,gen=generation):
                            return authorize_cart_transfer_transaction(db,1111,role_id,epoch,resources,carts,opened.ticket,
                                branch,where,generation=gen,now_ms=22)
                        request=select()
                        assert select()==request and request.request_id==opened.ticket.request_id
                        assert request.destination.coordinate_space=='original_reward_fields_unresolved'
                        assert request.destination.map_id==1006 and (request.destination.x,request.destination.y) in ((36,221),(71,242))
                        refuse(lambda:select(replace(intent,opaque=1)))
                        refuse(lambda:select(replace(intent,opaque=10003)))
                        refuse(lambda:select(replace(intent,kind=C_QUEST_DIALOG_END)))
                        refuse(lambda:select(replace(intent,npc_key=999)))
                        refuse(lambda:select(where=replace(cart_location,version=cart_location.version+1)))
                        refuse(lambda:select(gen=generation+1))
                        assert load_task_state(db,1111,role_id,epoch)[1]==before_state
                        assert db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?',(role_id,)).fetchone()==before_position
                    cart_checked.add(cart_route.task_id)
                with closing(accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    duplicate=equip_master_transaction(db,1111,role_id,epoch,resources,rules,inv,key,0,'equip-selected',currency_rules=cash)
                    assert duplicate.completion is None and duplicate.equipment_event.replayed
                    assert db.execute('SELECT COUNT(*) FROM inventory_settlements WHERE role_id=? AND settlement_id LIKE ?',
                        (role_id,'master-card:%')).fetchone()[0]==1
        report=dict(passed=['43 original routes, both original choices each:86 actual bound grants and actual equip completions',
            'existing active master/cart beans receive explicit ready refresh before the original NPC menu; duplicate acceptance alone cannot update them',
            'original Start CCommit authorizes card; Finish-only DialogEnd cannot authorize; unsolicited/wrong NPC/session/expiry/location rejects',
            'source/card/instance/59 and equip/59/cart roll back together; bag-full retains pending choice',
            'no auto-equip; arbitrary other weapon does not satisfy; exact received instance completes once',
            'same choice/equip replay returns current state; second weapon button rejects; ordinary factory condition retained',
            'reconnect keeps one durable pending choice, rejects old epoch/ticket, reauthorizes via same master; exact already-equipped recovery completes once',
            'all10 actual cart NPC menus: only current option0 authorization yields a stable frozen raw-destination intent; no completion/reward/movement'],
            cart_dialogue_routes_checked=len(cart_checked),
            native_existing_quest_checks=native_ready_checks,
            adapter='actual Inventory.immutable_snapshot_transaction/apply_settlement/equip_transaction/equipment_bag_messages, no private snapshot Adapter',
            epoch_tested='actual AccountStore.acquire_lease positive integer identity; persisted TEXT is not the public input type',
            runtime_tested=False,native_gui_tested=False,policy=rules.revision)
    (OUT/'evidence/task-master-card-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
