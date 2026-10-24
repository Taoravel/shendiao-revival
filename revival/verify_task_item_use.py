"""Necessary read-only task-item inspection, original58 and actual inventory."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import json
import hashlib
import importlib
import struct
import tempfile
from accounts import AccountStore
from inventory import Inventory,AssetChange
from tasks import prepare_task_store
from task_persistence import load_task_state,apply_task_plan
from task_domain import TaskDomain
from task_item_use_protocol import decode_task_item_use,task_item_use_failure_message,TaskItemUseRequest
from task_item_use import (load_task_item_use_resources,inspect_task_item_use,inspect_task_item_use_transaction,
    TaskItemUseCommand,QINGGONG_BOOK_TASKS)
from staging.research_qinggong_book_use_native import native_qinggong_book_use
from world_owner import MapAddress,Location
from inspect_client import OUT


def refuse(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid task item inspection accepted')


def source_hashes():
    names=('task_item_use','task_item_use_protocol','task_domain','task_persistence','tasks','inventory','accounts',
        'world_owner','staging.research_qinggong_book_use_native','research_battle','verify_social_native','native_inspect',
        'verify_task_item_use')
    result={n:hashlib.sha256(Path(importlib.import_module(n).__file__).read_bytes()).hexdigest() for n in names}
    for name in ('tasks','knight.gsp.item.citemattr','knight.gsp.item.ctaskrelative'):
        result['catalogs/'+name+'.json']=hashlib.sha256((OUT/('catalogs/'+name+'.json')).read_bytes()).hexdigest()
    return result


def main():
    inputs=source_hashes()
    request=decode_task_item_use(bytes.fromhex('0000007b000000001122334455667788'))
    assert request==TaskItemUseRequest(123,0,0x1122334455667788)
    for body in (b'',b'\0'*15,b'\0'*16,struct.pack('>iiQ',1,1,123),struct.pack('>iiQ',1,0,2**63)):
        refuse(lambda:decode_task_item_use(body))
    assert task_item_use_failure_message()==(0xc4a53,b'')
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'item-inspection.sqlite3')
        tasks=prepare_task_store(accounts);config=Inventory.prepare(accounts)
        registry=load_task_item_use_resources(tasks,config)
        assert len(registry.definitions)==58 and len(registry.by_item)==41
        assert sum(d.item_kind==25 for d in registry.definitions.values())==55
        changed=dict(config.items);changed[50190]=dict(changed[50190],itemtypeid='25')
        refuse(lambda:load_task_item_use_resources(tasks,replace(config,items=changed)))
        refuse(lambda:load_task_item_use_resources(replace(tasks,definitions={
            q:t for q,t in tasks.definitions.items() if q!=206104}),config))
        role_id=accounts.create_role(1111,'原任务物品检查',11,1010109)['id'];epoch=accounts.acquire_lease(1111,role_id)
        inventory=Inventory(accounts,1111,role_id,config,epoch=epoch)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');db.execute('UPDATE roles SET level=100 WHERE id=?',(role_id,))
            actor,state=load_task_state(db,1111,role_id,epoch)
            # Inspect one real template at a time, keeping the actual bag limit.
            for template,ids in registry.by_item.items():
                inventory.apply_settlement(db,AssetChange(f'fixture-grant:{template}',grants=((template,1,1),)))
                assets=inventory.immutable_snapshot_transaction(db,epoch=epoch)
                item=next(x for x in assets.items if x.template_id==template)
                for q in ids:
                    d=registry.definitions[q]
                    location=Location(role_id,epoch,MapAddress(d.map_id or d.item_map_id or 1007,1,0),1,0,0)
                    command=TaskItemUseCommand(TaskItemUseRequest(item.id,0,role_id),location,1,'pure-check',1000,False)
                    observation=inspect_task_item_use(registry,actor,replace(state,active=frozenset((q,))),assets,command,generation=1,now_ms=1)
                    assert observation.unique_candidate_id==q and not observation.completion_authorized
                    candidate=observation.candidates[0]
                    assert candidate.item_readtime_raw==d.item_readtime_raw and candidate.task_process_time_raw==d.task_process_time_raw
                    assert {'server_completion_rule_unconfirmed','consumption_rule_unconfirmed'}<=set(candidate.blockers)
                    if d.item_kind==73:
                        assert candidate.item_scope=='no_static_map_restriction'
                        assert 'server_learning_rule_unconfirmed' in candidate.blockers
                        assert 'server_timing_rule_unconfirmed' in candidate.blockers
                    if d.item_id==50204:assert candidate.item_scope=='dynamic_item_scope_unimplemented'
                inventory.apply_settlement(db,AssetChange(f'fixture-cleanup:{template}',debits=((item.id,1),)))
            book_packets=[]
            for q,template in QINGGONG_BOOK_TASKS.items():
                inventory.apply_settlement(db,AssetChange(f'fixture-native-book:{template}',grants=((template,1,1),)))
                assets=inventory.immutable_snapshot_transaction(db,epoch=epoch)
                key=next(x.id for x in assets.items if x.template_id==template)
                native=native_qinggong_book_use(template,key,role_id)
                assert native['packet_type']==0xc03ff and native['progress_kind']==2 and native['threshold_raw']==15.0
                for action in ('offer','accept'):
                    actor,state=load_task_state(db,1111,role_id,epoch)
                    apply_task_plan(db,actor,TaskDomain(tasks).plan(actor,state,action,q),f'fixture-book:{q}:{action}')
                d=registry.definitions[q]
                location=Location(role_id,epoch,MapAddress(d.map_id,d.map_id,0),1,0,0)
                command=TaskItemUseCommand(decode_task_item_use(native['body']),location,1,f'native-book:{q}',1000,False)
                before=tuple(db.iterdump())
                inspection=inspect_task_item_use_transaction(db,1111,role_id,epoch,registry,inventory,command,generation=1,now_ms=2)
                assert tuple(db.iterdump())==before
                assert inspection.unique_candidate_id==q and inspection.quantity==1 and inspection.binding==1
                assert not inspection.completion_authorized and inspection.candidates[0].item_scope=='no_static_map_restriction'
                assert 'server_learning_rule_unconfirmed' in inspection.candidates[0].blockers
                assert inventory.immutable_snapshot_transaction(db,epoch=epoch)==assets
                book_packets.append(dict(task_id=q,item_id=template,item_key=key,body_hex=native['body'].hex(),
                    completed_timer_is_fixture=True,task_completion_authorized=False))
                inventory.apply_settlement(db,AssetChange(f'fixture-native-book-cleanup:{template}',debits=((key,1),)))
            inventory.apply_settlement(db,AssetChange('fixture-actual-bomb',grants=((50057,1,1),)))
            assets=inventory.immutable_snapshot_transaction(db,epoch=epoch)
            key=next(x.id for x in assets.items if x.template_id==50057)
            # Actual journal and inventory reads share one caller transaction.
            for action in ('offer','accept'):
                actor,state=load_task_state(db,1111,role_id,epoch)
                apply_task_plan(db,actor,TaskDomain(tasks).plan(actor,state,action,102109),'fixture-'+action)
            actor,state=load_task_state(db,1111,role_id,epoch)
            location=Location(role_id,epoch,MapAddress(1013,1,0),1,1300,800)
            command=TaskItemUseCommand(decode_task_item_use(struct.pack('>iiQ',key,0,role_id)),location,1,'actual-inspection',1000,False)
            before=tuple(db.iterdump())
            observation=inspect_task_item_use_transaction(db,1111,role_id,epoch,registry,inventory,command,generation=1,now_ms=2)
            assert tuple(db.iterdump())==before
            candidate=observation.candidates[0]
            assert candidate.item_scope=='inside_static_item_scope'
            assert candidate.task_hint_scope=='outside_original_task_hint'
            assert observation.quantity==1 and observation.binding==1 and not observation.completion_authorized
            right=replace(command,location=replace(location,x=2320))
            outside=inspect_task_item_use(registry,actor,state,assets,right,generation=1,now_ms=2)
            assert outside.candidates[0].item_scope=='outside_static_item_scope'
            # A location hint cannot resolve two active uses of the same item.
            ambiguous=inspect_task_item_use(registry,actor,replace(state,active=frozenset((102109,102110))),assets,
                replace(command,location=replace(location,x=1360,y=960)),generation=1,now_ms=2)
            assert ambiguous.selection_status=='ambiguous_active_objectives' and ambiguous.unique_candidate_id is None
            assert {x.task_hint_scope for x in ambiguous.candidates}=={'inside_original_task_hint','outside_original_task_hint'}
            no_active=inspect_task_item_use(registry,actor,replace(state,active=frozenset()),assets,command,generation=1,now_ms=2)
            assert no_active.selection_status=='no_active_objective' and not no_active.candidates
            for changed in (replace(command,in_battle=True),replace(command,generation=2),
                    replace(command,request=replace(command.request,target_id=role_id+1)),
                    replace(command,request=replace(command.request,item_key=999999)),
                    replace(command,location=replace(location,state='loading'))):
                refuse(lambda:inspect_task_item_use(registry,actor,state,assets,changed,generation=1,now_ms=2))
            refuse(lambda:inspect_task_item_use(registry,actor,state,assets,command,generation=1,now_ms=1000))
            equipped=replace(assets,items=tuple(replace(x,equipment_slot=0) if x.id==key else x for x in assets.items))
            refuse(lambda:inspect_task_item_use(registry,actor,state,equipped,command,generation=1,now_ms=2))
            foreign=replace(assets,items=tuple(replace(x,role_id=role_id+1) if x.id==key else x for x in assets.items))
            refuse(lambda:inspect_task_item_use(registry,actor,state,foreign,command,generation=1,now_ms=2))
        accounts.acquire_lease(1111,role_id)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            refuse(lambda:inspect_task_item_use_transaction(db,1111,role_id,epoch,registry,inventory,command,generation=1,now_ms=2))
        report=dict(original_tasks_indexed=58,original_templates=41,task_completion_enabled=0,
            passed=['original16-byte CUseItem retains full64-bit role target; empty native fail body; invalid request layouts refuse',
                'all58 original task definitions and41 templates inspected against real granted inventory rows; every result keeps completion unauthorized',
                'actual current fenced InventorySnapshot and journal inspection performs zero database writes or debits',
                '50057 static item scope admits1300/800 while102109 hint does not; exact right boundary2320 excludes; ambiguous two-task hint cannot choose a winner',
                'three exact type73 teaching books have verified native use/no static item-map restriction; server learning/timing/consumption/completion remain blocked; dynamic50204/round/AI/animation/transfer remain separate',
                'three actual segmented-native book requests decode into real Inventory/current journal inspection with full database and owned asset snapshots unchanged',
                'wrong role/key, equipped/foreign item, battle/loading, old generation/deadline and old lease refuse'],
            native_book_requests=book_packets,source_sha256=inputs,
            scope='read-only Interface, actual disposable inventory/current journal and pure original58 metadata; trusted position and item grants are fixtures',
            shared_runtime_tested=False,client_tested=False)
    assert source_hashes()==inputs,'Task-item verification source changed during this run'
    report['inputs_stable']=True
    (OUT/'evidence/task-item-use-inspection-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
