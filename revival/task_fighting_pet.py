"""Original selected-fighting-pet objectives using current owner facts.

This Module never selects, grants, releases or enters battle with a pet. The
caller stages any real inventory mutation and its resource source transition
before reconciliation, all in the same leased transaction. Reconnect can read
the current selected state; a historical request/event is not objective proof.
"""
from dataclasses import asdict,dataclass
import hashlib
import json
from types import MappingProxyType
from inventory import InventorySnapshot,PetState
from task_domain import TaskDomain,TaskEvidence,supports_fighting_pet_task
from task_persistence import load_task_state
from task_workflow import complete_task_transaction,replay_completed_task_transaction,completion_messages
from task_growth_resources import current_task_resource_profile
from task_protocol import S_REFRESH_SCENARIO_QUEST_STATE
from tasks import _plain
from world_owner import Location


def _hash(value):
    return hashlib.sha256(json.dumps(_plain(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class FightingPetTaskDefinition:
    task_id:int
    map_id:int
    fingerprint:str


@dataclass(frozen=True)
class FightingPetTaskResources:
    definitions:object


def load_fighting_pet_task_resources(resources):
    """Startup-only exact capabilities; no enrollment, pet grant or schema."""
    return FightingPetTaskResources(MappingProxyType({q:FightingPetTaskDefinition(q,task['target']['map_id'],_hash(task))
        for q,task in resources.definitions.items() if supports_fighting_pet_task(task)}))


@dataclass(frozen=True)
class FightingPetTaskResult:
    task_id:int
    outcome:str
    completion:object=None
    messages:tuple=()
    replayed:bool=False


def _scope(db,account_id,role_id,epoch,inventory):
    if (inventory.account_id,inventory.role_id)!=(account_id,role_id):
        raise ValueError('Fighting-pet objective inventory owner mismatch')
    assets=inventory.immutable_snapshot_transaction(db,epoch=epoch)
    if not isinstance(assets,InventorySnapshot) or assets.role_id!=role_id:
        raise ValueError('Fighting-pet objective requires a current owned asset snapshot')
    actor,state=load_task_state(db,account_id,role_id,epoch)
    return actor,state,assets


def _definition(task_id,resources,fighting):
    definition=fighting.definitions.get(task_id);task=resources.definitions.get(task_id)
    if definition is None or task is None or definition.fingerprint!=_hash(task):
        raise ValueError('Unsupported or changed selected-pet objective')
    return definition


def _reply(db,actor,task_id,completion,inventory,*,replayed):
    messages=completion_messages(completion)
    if replayed:messages=tuple((kind,body) for kind,body in messages if kind!=S_REFRESH_SCENARIO_QUEST_STATE)
    return FightingPetTaskResult(task_id,'completed',completion,
        inventory.equipment_bag_messages(db,actor.login_epoch)+messages,replayed)


def reconcile_fighting_pet_task(db,account_id,role_id,epoch,task_id,resources,fighting,inventory,location,request_id,*,
        growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,
        resource_rules=None,equipment_rules=None):
    """Current state -> one original reward/next, within the caller transaction.

    Active but not currently selected returns waiting without writes. Paid
    tasks acknowledge their durable manifest and current balances; no selected
    pet or old position is needed, and later pet changes are never overwritten.
    No wire task ID, CCommit, pet grant receipt or cached event authorizes this
    trusted operation. Caller validates world ownership and schedules it under
    the role owner, pre-encodes every reply, then commits before delivery.
    """
    if type(request_id) is not str or not 1<=len(request_id)<=160:
        raise ValueError('Stable selected-pet objective request identity required')
    actor,state,assets=_scope(db,account_id,role_id,epoch,inventory)
    definition=_definition(task_id,resources,fighting)
    current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules)
    reward_rules=(growth_rules,attribute_rules,currency_rules,pet_experience_rules)
    if task_id in state.completed:
        row=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,task_id)).fetchone()
        manifest=json.loads(row[0]).get('fighting_pet_objective') if row else None
        if (not isinstance(manifest,dict) or manifest.get('definition_fingerprint')!=definition.fingerprint
                or manifest.get('policy')!='current_selected_owned_pet.1'
                or type(manifest.get('pet_key')) is not int or not 0<manifest['pet_key']<=0x7fffffff):
            raise ValueError('Completed selected-pet objective requires its durable evidence')
        completion=replay_completed_task_transaction(db,actor,task_id,resources,inventory,*reward_rules,
            resource_rules=resource_rules,equipment_rules=equipment_rules)
        return _reply(db,actor,task_id,completion,inventory,replayed=True)
    if task_id not in state.active:
        raise ValueError('Selected-pet objective is not active')
    if (not isinstance(location,Location) or (location.role_id,location.login_epoch)!=(role_id,epoch)
            or location.state!='active' or location.address.map_id!=definition.map_id):
        raise ValueError('Selected-pet objective requires its current active world location')
    selected=inventory.selected_fighting_pet(db)
    candidates=tuple(p for p in assets.pets if p.fighting==1)
    if not candidates:
        if selected is not None:raise ValueError('Selected pet differs from the current inventory snapshot')
        return FightingPetTaskResult(task_id,'waiting')
    if (len(candidates)!=1 or not isinstance(selected,PetState) or selected!=candidates[0]
            or selected.role_id!=role_id or selected.released!=0 or type(selected.id) is not int
            or not 0<selected.id<=0x7fffffff or type(selected.fighting) is not int or selected.fighting!=1):
        raise ValueError('Selected-pet objective requires exactly one current owned fighting pet')
    evidence=TaskEvidence(task_id,role_id,epoch,'pet_set_fighting',f'fighting-pet:{role_id}:{task_id}',
        location.address.map_id,reference_id=selected.id)
    plan=TaskDomain(resources).plan(actor,state,'complete',task_id,evidence=evidence)
    completion=complete_task_transaction(db,actor,plan,request_id,resources,inventory,*reward_rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    manifest={'policy':'current_selected_owned_pet.1','definition_fingerprint':definition.fingerprint,
        'pet_key':selected.id,'pet_template':selected.template_id,'inventory_revision':assets.inventory_revision,
        'location':asdict(location)}
    effect=json.loads(db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',(role_id,task_id)).fetchone()[0])
    effect['fighting_pet_objective']=manifest
    db.execute('UPDATE task_effects SET payload=? WHERE role_id=? AND task_id=?',
        (json.dumps(effect,ensure_ascii=False),role_id,task_id))
    return _reply(db,actor,task_id,completion,inventory,replayed=False)
