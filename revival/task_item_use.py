"""Read-only original task-item inspection, using actual owner snapshots.

Inspection identifies active candidates and unresolved mechanics. It is NOT a
completion permit or a consumption policy. No state writes, timer, send, battle
creation, task enrollment or reward delegation are performed here.
"""
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from inspect_client import OUT
from inventory import ItemState,InventorySnapshot
from task_domain import TaskActor,TaskSnapshot,valid_task_epoch
from task_persistence import load_task_state
from task_item_use_protocol import TaskItemUseRequest
from tasks import _plain
from world_owner import Location,MapAddress


DYNAMIC_SCOPE_ITEMS=frozenset((50081,50029,50204))
QINGGONG_BOOK_TASKS=MappingProxyType({206104:50190,206204:50191,206304:50192})
EXTRA_MECHANICS=('ProcessBarTime','AIInfoAIID','ScenarioInfoAnimationID','RewardMapJumpType',
    'ActiveInfoTimeLimit','ActiveInfoIsRestartTimer','ActiveInfoStepProbability','TransformID',
    'ActiveInfoOtherType','ActiveInfoTargetID','ActiveInfoTargetNum','ActiveInfoGiveBackMoney',
    'ActiveInfoGiveBackPetID','ActiveInfoMiniStep','ActiveInfoMaxStep','QuestionInfoNpcID')


@dataclass(frozen=True)
class TaskItemUseDefinition:
    task_id:int
    item_id:int
    item_kind:int
    map_id:int
    hint_rectangle:tuple
    item_map_id:int
    item_rectangle:tuple
    item_need_level:int
    item_outbattle_use:int
    item_readtime_raw:int
    task_process_time_raw:int
    round_task:bool
    extra_mechanics:tuple
    fingerprint:str


@dataclass(frozen=True)
class TaskItemUseResources:
    definitions:object
    by_item:object


def load_task_item_use_resources(resources,inventory_config,taskrelative_rows=None):
    """Startup-only immutable original58/41 index, never an enablement list.

    Reuse InventoryConfig.items instead of opening another item catalog in the
    hot path. Optional rows let startup reuse an already loaded TaskRelative.
    """
    if taskrelative_rows is None:
        taskrelative_rows=json.loads((OUT/'catalogs/knight.gsp.item.ctaskrelative.json').read_text(encoding='utf-8'))
    relative={}
    for row in taskrelative_rows:
        a=row['attributes'];key=int(a['id'])
        if key in relative:raise ValueError('Duplicate original TaskRelative item')
        relative[key]=a
    definitions={};by_item={}
    for q,task in resources.definitions.items():
        if task['type']!=22:continue
        a=task['attributes'];item_id=int(a.get('ActiveInfoUseItemID',0))
        item=inventory_config.items.get(item_id);r=relative.get(item_id)
        if item is None or r is None or int(item['itemtypeid']) not in (25,73):
            raise ValueError('Original type22 item/TaskRelative definition missing or unsupported')
        if q in QINGGONG_BOOK_TASKS or int(item['itemtypeid'])==73:
            # Original factory/right-click/kind2 path is verified for ONLY
            # these three teaching books, not the distinct master item36843.
            if (QINGGONG_BOOK_TASKS.get(q)!=item_id or int(item['itemtypeid'])!=73
                    or (int(item['needLevel']),int(item['outbattleuse']),int(item['battleuse']),int(item['maxNum']))!=(1,1,0,1)
                    or tuple(int(r.get(k,0)) for k in ('readtime','usemap','ltx','lty','rbx','rby'))!=(15,0,0,0,0,0)):
                raise ValueError('Original teaching-book identity or native use parameters changed')
        rect=tuple(int(a.get(k,0))*16 for k in (
            'ActiveInfoLeftPos','ActiveInfoTopPos','ActiveInfoRightPos','ActiveInfoBottomPos'))
        item_rect=tuple(int(r.get(k,0))*16 for k in ('ltx','lty','rbx','rby'))
        fingerprint=hashlib.sha256(json.dumps([_plain(task),dict(item),dict(r)],
            sort_keys=True,separators=(',',':')).encode()).hexdigest()
        definitions[q]=TaskItemUseDefinition(q,item_id,int(item['itemtypeid']),task['target']['map_id'],rect,
            int(r.get('usemap',0)),item_rect,int(item.get('needLevel',0)),int(item.get('outbattleuse',0)),
            int(r.get('readtime',0)),int(a.get('ProcessBarTime',0)),'$round$' in task['name'],
            tuple((k,int(a[k])) for k in dict.fromkeys(EXTRA_MECHANICS) if int(a.get(k,0))),fingerprint)
        by_item.setdefault(item_id,[]).append(q)
    if not QINGGONG_BOOK_TASKS.keys()<=definitions.keys():
        raise ValueError('Original three teaching-book tasks must remain in the source registry')
    return TaskItemUseResources(MappingProxyType(definitions),MappingProxyType({
        key:tuple(sorted(values)) for key,values in by_item.items()}))


@dataclass(frozen=True)
class TaskItemUseCommand:
    request:TaskItemUseRequest
    location:Location
    generation:int
    request_id:str
    deadline_ms:int
    in_battle:bool


@dataclass(frozen=True)
class TaskItemUseCandidate:
    task_id:int
    definition_fingerprint:str
    item_scope:str
    task_map_matches:bool | None
    task_hint_scope:str
    item_readtime_raw:int
    task_process_time_raw:int
    extra_mechanics:tuple
    blockers:tuple


@dataclass(frozen=True)
class TaskItemUseInspection:
    role_id:int
    login_epoch:int | str
    generation:int
    request_id:str
    location:Location
    item_key:int
    item_id:int
    quantity:int
    binding:int
    inventory_revision:int
    task_revision:int
    selection_status:str
    unique_candidate_id:int | None
    candidates:tuple
    completion_authorized:bool=False


def _rectangle(rectangle):
    return 0<=rectangle[0]<rectangle[2] and 0<=rectangle[1]<rectangle[3]


def _inside(location,rectangle):
    return rectangle[0]<=location.x<rectangle[2] and rectangle[1]<=location.y<rectangle[3]


def _candidate(definition,location):
    d=definition
    blockers=['server_completion_rule_unconfirmed','consumption_rule_unconfirmed']
    book=QINGGONG_BOOK_TASKS.get(d.task_id)==d.item_id and d.item_kind==73
    if book:
        item_scope='no_static_map_restriction'
        blockers.append('server_learning_rule_unconfirmed')
    elif d.item_kind!=25:
        item_scope='type73_native_use_unconfirmed';blockers.append(item_scope)
    elif d.item_id in DYNAMIC_SCOPE_ITEMS:
        item_scope='dynamic_item_scope_unimplemented';blockers.append(item_scope)
    elif d.item_map_id<=0:
        item_scope='no_static_map_restriction'
    elif not _rectangle(d.item_rectangle):
        item_scope='invalid_static_item_rectangle';blockers.append(item_scope)
    elif location.address.map_id==d.item_map_id and _inside(location,d.item_rectangle):
        item_scope='inside_static_item_scope'
    else:
        item_scope='outside_static_item_scope';blockers.append(item_scope)
    task_map=None if d.map_id<=0 else location.address.map_id==d.map_id
    if d.map_id<=0 or not _rectangle(d.hint_rectangle):
        hint='unspecified_original_task_hint'
    elif task_map and _inside(location,d.hint_rectangle):
        hint='inside_original_task_hint'
    else:
        hint='outside_original_task_hint'
    if d.round_task:blockers.append('cyclic_task_instance_unimplemented')
    if d.item_readtime_raw>0:blockers.append('server_timing_rule_unconfirmed')
    blockers.extend('extra_mechanic:'+key for key,_ in d.extra_mechanics)
    return TaskItemUseCandidate(d.task_id,d.fingerprint,item_scope,task_map,hint,
        d.item_readtime_raw,d.task_process_time_raw,d.extra_mechanics,tuple(blockers))


def inspect_task_item_use(registry,actor,tasks,assets,command,*,generation,now_ms):
    """Pure snapshot Interface; unique candidate means identity, never success.

    The caller supplies ordered role/battle eligibility and the authoritative
    world Location. Neither task hint rectangles nor a client-side read bar
    provide original server completion evidence. Multiple active tasks using
    one template remain ambiguous even if only one hint currently matches.
    """
    if (not isinstance(actor,TaskActor) or not isinstance(tasks,TaskSnapshot)
            or not isinstance(assets,InventorySnapshot) or not valid_task_epoch(actor.login_epoch)
            or type(actor.role_id) is not int or not 0<actor.role_id<2**63
            or type(actor.level) is not int or actor.level<1
            or (tasks.role_id,assets.role_id)!=(actor.role_id,actor.role_id)
            or type(assets.inventory_revision) is not int or assets.inventory_revision<0
            or type(assets.items) is not tuple or type(assets.bag_capacity) is not int or assets.bag_capacity<=0):
        raise ValueError('Current owned task and immutable inventory snapshots required')
    if (not isinstance(command,TaskItemUseCommand) or not isinstance(command.request,TaskItemUseRequest)
            or type(generation) is not int or generation<=0 or command.generation!=generation
            or type(command.generation) is not int or type(now_ms) is not int or not 0<=now_ms<2**63
            or type(command.deadline_ms) is not int or not now_ms<command.deadline_ms<2**63
            or type(command.request_id) is not str or not 1<=len(command.request_id)<=128
            or type(command.in_battle) is not bool or command.in_battle):
        raise ValueError('Fresh out-of-battle owner command required')
    r=command.request;location=command.location
    if (type(r.item_key) is not int or not 0<r.item_key<=0x7fffffff
            or type(r.target_kind) is not int or r.target_kind!=0
            or type(r.target_id) is not int or r.target_id!=actor.role_id
            or not isinstance(location,Location) or not isinstance(location.address,MapAddress)
            or (location.role_id,location.login_epoch)!=(actor.role_id,actor.login_epoch)
            or location.state!='active' or type(location.version) is not int or location.version<=0
            or any(type(v) is not int or v<0 for v in (location.address.map_id,
                location.address.instance_id,location.address.partition_id,location.x,location.y))
            or location.address.map_id<=0 or max(location.x,location.y)>=32768):
        raise ValueError('Task use requires self target and authoritative active world location')
    if (any(not isinstance(x,ItemState) or x.role_id!=actor.role_id
            or any(type(v) is not int or v<=0 for v in (x.id,x.template_id,x.quantity))
            or type(x.binding) is not int or x.binding not in (0,1) for x in assets.items)
            or len({x.id for x in assets.items})!=len(assets.items)):
        raise ValueError('Current unique owned item rows required')
    item=next((x for x in assets.items if x.id==r.item_key),None)
    if (item is None or item.equipment_slot is not None or type(item.slot) is not int
            or not 0<=item.slot<assets.bag_capacity or item.template_id not in registry.by_item):
        raise ValueError('Carried original task item instance unavailable')
    definition=registry.definitions[registry.by_item[item.template_id][0]]
    if actor.level<definition.item_need_level or definition.item_outbattle_use!=1:
        raise ValueError('Task item level or outside-battle use restriction')
    ids=tuple(q for q in registry.by_item[item.template_id] if q in tasks.active)
    status='no_active_objective' if not ids else 'unique_active_candidate' if len(ids)==1 else 'ambiguous_active_objectives'
    return TaskItemUseInspection(actor.role_id,actor.login_epoch,generation,command.request_id,location,
        item.id,item.template_id,item.quantity,item.binding,assets.inventory_revision,tasks.revision,
        status,ids[0] if len(ids)==1 else None,tuple(_candidate(registry.definitions[q],location) for q in ids))


def inspect_task_item_use_transaction(db,account_id,role_id,epoch,registry,inventory,command,*,generation,now_ms):
    """Read actual current inventory/tasks in ONE caller-owned fenced txn.

    Returning an inspection performs no write and creates no usable permit.
    The inventory owner keeps CUseItem routing; shared integration is separate.
    """
    if inventory.account_id!=account_id or inventory.role_id!=role_id:
        raise ValueError('Task use inventory owner mismatch')
    assets=inventory.immutable_snapshot_transaction(db,epoch=epoch)
    actor,tasks=load_task_state(db,account_id,role_id,epoch)
    return inspect_task_item_use(registry,actor,tasks,assets,command,generation=generation,now_ms=now_ms)
