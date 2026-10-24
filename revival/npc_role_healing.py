"""Dedicated doctor294 admission, fee and sole-resource settlement.

Startup loads the approved recipe and schema. A role owner supplies a fresh
map-proved command; one fenced transaction includes native reply validation.
No legacy initialization, injury carrier, inn effect or other-owner wait.
"""
from contextlib import closing
from dataclasses import asdict,dataclass
import hashlib
import json
import time
from inspect_client import OUT
from currency import CurrencyChange,apply_currency,read_wallet
from currency_protocol import encode_currency_balance
from npc_services import NpcServiceCommand,ServiceBinding
from role_attribute_protocol import growth_refresh
from role_equipment import resource_caps_from_projection
from role_equipment_storage import current_resource_profile
from role_growth import read_growth
from role_resource_plan import plan_resource_values
from role_resource_storage import read_role_resources,apply_resource_transition
from world_owner import MapAddress


@dataclass(frozen=True)
class HealingRules:
    revision: str
    npc_ids: tuple
    service_id: int
    handler: str
    coefficient: int
    minimum_level: int
    maximum_level: int
    map_id: int
    placement_id: int
    cause: str
    currency: str
    purpose: str


def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


def _digest(value):return hashlib.sha256(_json(value).encode()).hexdigest()


def prepare(accounts):
    """Startup only; return explicit bindings without activating a role profile."""
    p=json.loads((OUT/'design/npc-role-healing-v1.json').read_text(encoding='utf-8'))
    place=p['npc_placement']
    rules=HealingRules(p['revision'],tuple(p['npc_ids']),p['service_id'],p['handler'],
        p['fee_coefficient'],p['ordinary_level_min'],p['ordinary_level_max'],
        place['map_id'],place['placement_id'],p['resource_cause'],p['fee_currency'],p['fee_purpose'])
    numeric=(rules.coefficient,rules.minimum_level,rules.maximum_level,rules.map_id,rules.placement_id,
        rules.service_id,*rules.npc_ids,place['x'],place['y'])
    if (any(type(v) is not int for v in numeric)
            or rules!=HealingRules('2026-10-23.npc-role-healing.1',(10380,),294,'role.heal',30,1,155,
                1007,34,'npc_heal','cash','npc_role_heal')
            or (place['x'],place['y'])!=(1996,3963)):
        raise ValueError('NPC role healing recipe requires explicit implementation review')
    placements,definitions=accounts.npc_resources
    if (any(npc not in definitions for npc in rules.npc_ids)
            or not any((v.placement_id,v.npc_id,v.x,v.y)==(34,10380,1996,3963)
                for v in placements.get(rules.map_id,()))):
        raise ValueError('Original doctor placement is missing')
    with closing(accounts.connect()) as db,db:
        db.execute('''CREATE TABLE IF NOT EXISTS npc_role_healing_receipts (
            role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
            intent TEXT NOT NULL,admission TEXT NOT NULL,fingerprint TEXT NOT NULL,
            fee INTEGER NOT NULL,PRIMARY KEY(role_id,request_id))''')
    accounts.npc_role_healing_rules=rules
    return tuple(ServiceBinding(npc,rules.service_id,rules.handler,'designed',
        'design/npc-role-healing-v1.json; original CNpcService294 and explicit doctor placement')
        for npc in rules.npc_ids)


def _intent(rules,command,inventory):
    if (type(command) is not NpcServiceCommand or type(command.address) is not MapAddress
            or (command.role_id,command.login_epoch)!=(inventory.role_id,inventory.epoch)
            or (command.service_id,command.handler,command.address.map_id,command.placement_id)
                !=(rules.service_id,rules.handler,rules.map_id,rules.placement_id)
            or command.npc_id not in rules.npc_ids
            or type(command.entity_key) is not int or not 0<=command.entity_key<2**63
            or type(command.deadline_ms) is not int or command.deadline_ms<=0
            or type(command.request_id) is not str or not 1<=len(command.request_id)<=128):
        raise ValueError('NPC role healing owner or admission scope mismatch')
    return dict(policy=rules.revision,role_id=command.role_id,npc_id=command.npc_id,
        service_id=command.service_id,entity_key=command.entity_key,placement_id=command.placement_id,
        address=asdict(command.address))


def settle(accounts,inventory,command):
    """Fresh treatment mutates once; a paid intent reads current authority only.

    Level/fee/before-resource admission is frozen in the same transaction, not
    recomputed when replaying an old receipt after wounds, full health or growth.
    The role owner has already re-proved current NPC presence before admission.
    """
    rules=accounts.npc_role_healing_rules
    intent=_intent(rules,command,inventory)
    rr,gear=accounts.resource_rules,accounts.equipment_attribute_rules
    if (rules.cause not in rr.resource_causes
            or rules.purpose not in accounts.currency_rules.spend_purposes[rules.currency]):
        raise ValueError('NPC role healing dependencies are not enabled')
    if int(time.monotonic()*1000)>=command.deadline_ms:raise ValueError('NPC role healing admission expired')
    account,role,epoch=inventory.account_id,inventory.role_id,inventory.epoch
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if int(time.monotonic()*1000)>=command.deadline_ms:raise ValueError('NPC role healing expired waiting for storage')
        old=db.execute('SELECT intent,admission,fingerprint,fee FROM npc_role_healing_receipts '
            'WHERE role_id=? AND request_id=?',(role,command.request_id)).fetchone()
        common=db.execute('SELECT fingerprint FROM npc_command_receipts WHERE role_id=? AND request_id=?',
            (role,command.request_id)).fetchone()
        if (old is None)!=(common is None):raise ValueError('NPC role healing receipt is incomplete or conflicts')
        if old:
            admission=json.loads(old[1])
            if (old[0]!=_json(intent) or admission['fee']!=old[3]
                    or old[2]!=_digest(dict(intent=intent,admission=admission)) or common[0]!=old[2]):
                raise ValueError('NPC role healing retry intent conflict')
        snapshot=inventory.immutable_snapshot_transaction(db)
        profile=current_resource_profile(db,account,role,epoch,snapshot,
            equipment_rules=gear,resource_rules=rr)
        resources=read_role_resources(db,account,role,epoch,rr)
        growth=read_growth(db,account,role)
        if not old:
            if resources.hp==0:raise ValueError('Ordinary doctor healing does not authorize revival')
            caps=resource_caps_from_projection(profile)
            if (resources.hp,resources.mp)==(caps.hp_max,caps.mp_max):
                raise ValueError('Role resources already full')
            if type(growth.level) is not int or not rules.minimum_level<=growth.level<=rules.maximum_level:
                raise ValueError('NPC role healing requires an ordinary known level')
            fee=growth.level*rules.coefficient
            admission=dict(level=growth.level,fee=fee,currency=rules.currency,purpose=rules.purpose,
                cause=rules.cause,before=asdict(resources),target_hp=caps.hp_max,target_mp=caps.mp_max)
            fingerprint=_digest(dict(intent=intent,admission=admission))
            identity='nh:'+hashlib.sha256(command.request_id.encode()).hexdigest()
            apply_currency(db,account,role,epoch,CurrencyChange(identity,rules.purpose,
                f'npc:{command.npc_id}:service:{command.service_id}',((rules.currency,-fee),)),accounts.currency_rules)
            transition=plan_resource_values(resources,caps.hp_max,caps.mp_max,rules.cause,rr,current_caps=caps)
            result=apply_resource_transition(db,account,role,epoch,transition,identity,rules=rr,equipment_rules=gear)
            if result.replayed:raise ValueError('Resource receipt exists without its doctor receipt')
            db.execute('INSERT INTO npc_role_healing_receipts VALUES(?,?,?,?,?,?)',
                (role,command.request_id,_json(intent),_json(admission),fingerprint,fee))
            db.execute('INSERT INTO npc_command_receipts VALUES(?,?,?)',(role,command.request_id,fingerprint))
        # Actual native encoding stays inside the fee/effect/receipt transaction.
        current=current_resource_profile(db,account,role,epoch,snapshot,equipment_rules=gear,resource_rules=rr)
        messages=[growth_refresh(growth,current)]
        wallet=read_wallet(db,account,role,epoch,accounts.currency_rules)
        messages.extend(encode_currency_balance(row.currency,row.balance) for row in wallet if row.currency==rules.currency)
    return messages
