"""Original NPC recovery requests, owned snapshots and atomic care payments."""
from contextlib import closing
from dataclasses import asdict,dataclass,replace
import hashlib
import json
from pathlib import Path
import struct
import time
from inspect_client import OUT
from pet_care import CareRules
from pet_blood import BloodRules,load as load_pet_blood
from npc_services import ServiceBinding
from currency import CurrencyChange,apply_currency,read_wallet,WalletNotInitialized
from currency_protocol import encode_currency_balance
from inventory import REFRESH_PET,pet_record
import role_vigor
from role_attribute_storage import read_attribute_snapshot,update_role_vitals
from item_effect_protocol import role_resource_refresh
from role_resource_storage import ResourceNotInitialized,read_role_resources,apply_resource_transition
from role_resource_plan import plan_resource_values
from role_equipment_storage import (current_resource_profile,current_equipment_totals,
    synchronize_inventory_resource_source)
from role_equipment import resource_caps_from_projection
from role_growth import read_growth
from role_attribute_protocol import growth_refresh

RECOVERY=0xc2333
SERVICES={1:3,2:10,3:11,4:12}


@dataclass(frozen=True)
class LoyaltyRules:
    revision: str
    base_unit_fee: int
    power_remainder_coefficient: int
    power_modulus: int
    care_rules: CareRules
    blood_rules: BloodRules

    def __post_init__(self):
        numbers=(self.base_unit_fee,self.power_remainder_coefficient,self.power_modulus)
        if (self.revision!='2026-10-24.npc-pet-loyalty.2'
                or any(type(value) is not int for value in numbers) or numbers!=(45,2,10)
                or type(self.care_rules) is not CareRules or type(self.blood_rules) is not BloodRules
                or self.care_rules.revision!='2026-10-23.pet-care.1'
                or self.blood_rules.revision!='2026-10-23.pet-blood.1'
                or dict(self.care_rules.caps)!={1:100,2:100,3:125,4:200,5:300,6:400}):
            raise ValueError('Explicit supported loyalty recipe and original pet rules required')


def load_loyalty_rules(config,service_policy,*,path=None):
    """Freeze the price recipe alongside the existing care/blood authority."""
    policy=json.loads((Path(path) if path is not None else OUT/'design/npc-pet-loyalty-v2.json')
        .read_text(encoding='utf-8'))
    if (type(policy) is not dict or policy.get('base_service_policy')!=service_policy['revision']
            or service_policy['revision']!='2026-10-23.npc.1'
            or type(policy.get('free_through_level')) is not int
            or policy['free_through_level']!=service_policy['recovery']['free_through_level']
            or type(policy.get('native_free_sentinel')) is not int or policy['native_free_sentinel']!=-3
            or type(policy.get('maximum_total_fee')) is not int or policy['maximum_total_fee']!=0x7fffffff
            or policy.get('currency')!='cash' or policy.get('payment_purpose')!='npc_shop'):
        raise ValueError('Loyalty fee recipe differs from the existing recovery contract')
    return LoyaltyRules(*(policy.get(key) for key in
        ('revision','base_unit_fee','power_remainder_coefficient','power_modulus')),
        config.care_rules,config.blood_rules)


@dataclass(frozen=True)
class RecoveryRules:
    revision: str
    free_through_level: int
    pet_level_coefficient: int
    pet_base_fee: int
    loyalty_unit_fee: int
    inn_fee: int
    vigor_fraction: float
    loyalty: LoyaltyRules


@dataclass(frozen=True)
class RecoveryIntent:
    service: object
    kind: int


def prepare(accounts,policy,*,loyalty_path=None):
    p=policy['recovery']
    if (p['free_through_level']!=20 or p['pet_level_coefficient']!=20 or p['pet_base_fee']!=20
            or p['loyalty_unit_fee']!=45 or p['inn_fee']!=500 or p['payment_purpose']!='npc_shop'):
        raise ValueError('Recovery recipe requires explicit implementation review')
    fraction=float.fromhex(p['inn_vigor_fraction_hex'])
    if fraction!=0.15000000596046448:raise ValueError('Inn vigor multiplier differs from native constant')
    accounts.npc_recovery_rules=RecoveryRules(policy['revision'],p['free_through_level'],
        p['pet_level_coefficient'],p['pet_base_fee'],p['loyalty_unit_fee'],p['inn_fee'],fraction,
        load_loyalty_rules(accounts.inventory_config,policy,path=loyalty_path))
    bindings=[]
    for npc in p['trainer_npc_ids']:
        if npc not in accounts.npc_resources[1]:raise ValueError('Unknown pet recovery NPC')
        bindings.extend(ServiceBinding(npc,s,'recovery.pet','designed',
            'design/npc-services-v1.json#recovery; native service10/11/12 dispatch') for s in (10,11,12))
    for npc in p['inn_npc_ids']:
        if npc not in accounts.npc_resources[1]:raise ValueError('Unknown inn NPC')
        bindings.append(ServiceBinding(npc,3,'recovery.rest','designed',
            'design/npc-services-v1.json#recovery; native service3 dispatch'))
    with closing(accounts.connect()) as db,db:
        accounts.vigor_rules=role_vigor.prepare(db,p['vigor'])
        db.execute('''CREATE TABLE IF NOT EXISTS npc_recovery_receipts (
            role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL,targets TEXT NOT NULL,fee INTEGER NOT NULL,detail TEXT NOT NULL,
            PRIMARY KEY(role_id,request_id))''')
    return tuple(bindings)


def decode_request(body):
    if type(body) is not bytes or len(body)!=12:raise ValueError('CRecovery requires 12 bytes')
    key,kind=struct.unpack('>qi',body)
    if key<0 or kind not in SERVICES:raise ValueError('Invalid recovery NPC or kind')
    return key,kind


def plan(resources,body,proof,current,*,request_id,now_ms,deadline_ms):
    key,kind=decode_request(body)
    command=resources.services.plan(struct.pack('>qi',key,SERVICES[kind]),proof,current,
        request_id=request_id,now_ms=now_ms,deadline_ms=deadline_ms)
    if command.handler!=('recovery.rest' if kind==1 else 'recovery.pet'):
        raise ValueError('Recovery NPC does not own this kind')
    return RecoveryIntent(command,kind)


def _pet_changes(db,inventory,snapshot,kind,rules,role_level):
    if not snapshot.pets:raise ValueError('No owned pets to recover')
    changes=[];fee=0
    for pet in snapshot.pets:
        resources=kind in (2,4);loyalty=kind in (3,4)
        if resources and pet.progress is None:raise ValueError('Unknown legacy pet resources')
        if loyalty and pet.care is None:raise ValueError('Unknown legacy pet care')
        restore_hp=resources and (pet.progress.state.hp,pet.progress.state.mp)!=(
            pet.progress.attributes.max_hp,pet.progress.attributes.max_mp)
        deficit=0;quote=None
        if loyalty:
            pricing=rules.loyalty
            if inventory.care_rules is not pricing.care_rules or inventory.blood_rules is not pricing.blood_rules:
                raise ValueError('Loyalty requires the exact startup pet authorities')
            pricing.care_rules.validate(pet.care)
            deficit=pricing.care_rules.maximum(pet.care.grade)-pet.care.loyalty
            blood=pet.progress.blood if pet.progress is not None else None
            if pet.progress is None:
                # The snapshot cannot project orphaned blood without growth.
                # Read the public asset Interface so malformed present data is
                # rejected instead of being mistaken for a missing old state.
                if load_pet_blood(db,inventory.account_id,inventory.role_id,pet.id,
                        pricing.blood_rules,pet.care.grade) is not None:
                    raise ValueError('Known blood requires supported pet growth')
            if blood is None:
                power=None;remainder=0;source='legacy_unknown_remainder_zero'
            else:
                if blood!=pricing.blood_rules.progress(blood.state,pet.care.grade):
                    raise ValueError('Loyalty requires current ordinary pet blood')
                power=blood.state.power;remainder=power%pricing.power_modulus;source='known_ordinary_power'
            unit=pricing.base_unit_fee+pricing.power_remainder_coefficient*remainder
            quote={'fee_recipe':pricing.revision,'power':power,'remainder':remainder,
                'unit_fee':unit,'source':source,'deficit':deficit,'contribution':deficit*unit}
        if restore_hp:fee+=rules.pet_base_fee+rules.pet_level_coefficient*pet.progress.state.level
        if quote is not None:fee+=quote['contribution']
        if restore_hp or deficit:
            changes.append((pet,restore_hp,deficit,quote))
    if not changes:raise ValueError('All requested pet states are already full')
    if role_level<=rules.free_through_level:fee=0
    if not 0<=fee<=0x7fffffff:raise ValueError('Recovery fee exceeds original signed32 quote')
    return tuple(changes),fee


def _current_role(db,inventory,snapshot,resource_rules,equipment_rules,*,totals_only=False):
    """One explicit contract per character; missing legacy profile stays legacy.

    Probe the resource provenance before requiring an equipment baseline. This
    preserves an untransferred old role even when the startup caller injects
    the new dependencies globally. Other policy/source errors never fall back.
    """
    if resource_rules is not None:
        try:resources=read_role_resources(db,inventory.account_id,inventory.role_id,inventory.epoch,resource_rules)
        except ResourceNotInitialized:pass
        else:
            if totals_only:
                return current_equipment_totals(db,inventory.account_id,inventory.role_id,inventory.epoch,
                    snapshot,equipment_rules),resources
            return current_resource_profile(db,inventory.account_id,inventory.role_id,inventory.epoch,snapshot,
                equipment_rules=equipment_rules,resource_rules=resource_rules),resources
    return read_attribute_snapshot(db,inventory.account_id,inventory.role_id,inventory.epoch),None


def _rest(db,accounts,inventory,rules,level,identity,snapshot,resource_rules,equipment_rules):
    before,resources=_current_role(db,inventory,snapshot,resource_rules,equipment_rules,totals_only=True)
    if before.attributes.policy_revision!=accounts.attribute_rules.revision:
        raise ValueError('Inn requires a current explicit role attribute policy')
    if resources is None:
        vitals=before.vitals
        hp,mp,max_hp,max_mp=vitals.hp,vitals.mp,vitals.max_hp,vitals.max_mp
    else:
        caps=resource_caps_from_projection(before)
        hp,mp,max_hp,max_mp=resources.hp,resources.mp,caps.hp_max,caps.mp_max
    if hp==0:raise ValueError('Ordinary inn rest does not authorize role revival')
    if (hp,mp)==(max_hp,max_mp):raise ValueError('Role resources already full')
    if resources is not None:
        # This may fold a newer carried-asset source into a real heal. The root
        # planner still rejects any hidden equip/growth cap transition.
        transition=plan_resource_values(resources,max_hp,max_mp,'inn_rest',resource_rules,current_caps=caps)
    vigor=role_vigor.advance(db,inventory,accounts.vigor_rules,int(time.monotonic()*1000))
    if vigor is None:raise ValueError('Inn requires an explicit known vigor profile')
    spent=int(vigor.maximum*rules.vigor_fraction)
    after_vigor=role_vigor.consume(db,inventory,accounts.vigor_rules,spent)
    fee=rules.inn_fee if level>rules.free_through_level else 0
    if fee:
        apply_currency(db,inventory.account_id,inventory.role_id,inventory.epoch,
            CurrencyChange(identity,'npc_shop','npc:inn:rest',(('cash',-fee),)),accounts.currency_rules)
    if resources is None:
        after=update_role_vitals(db,inventory.account_id,inventory.role_id,inventory.epoch,vitals,
            replace(vitals,version=vitals.version+1,hp=vitals.max_hp,mp=vitals.max_mp))
        resource_detail={}
    else:
        result=apply_resource_transition(db,inventory.account_id,inventory.role_id,inventory.epoch,
            transition,identity,rules=resource_rules,equipment_rules=equipment_rules)
        if result.replayed:raise ValueError('Inn resource receipt exists without its domain receipt')
        after,_=_current_role(db,inventory,snapshot,resource_rules,equipment_rules)
        resource_detail={'resource_policy':resource_rules.revision,'resources_before':asdict(resources),
                         'resources_after':asdict(result.resources)}
    return fee,{'role_before':asdict(before),'role_after':asdict(after),**resource_detail,
        'vigor_before':asdict(vigor),'vigor_after':asdict(after_vigor),'vigor_cost':spent}


def settle(accounts,inventory,intent,*,resource_rules=None,equipment_rules=None):
    """NPC-owned outer role transaction; injected rules never activate a profile.

    Both dependencies are startup-loaded and must be supplied together. An
    explicitly transferred role uses its sole resource carrier and final caps;
    an untransferred role retains the old Interface. Paid retries only encode
    CURRENT authority. No configuration load, migration or heal occurs on read.
    """
    if (resource_rules is None)!=(equipment_rules is None):
        raise ValueError('Inn resource and equipment startup rules must be injected together')
    command=intent.service;rules=accounts.npc_recovery_rules
    if ((command.role_id,command.login_epoch)!=(inventory.role_id,inventory.epoch)
            or command.handler!=('recovery.rest' if intent.kind==1 else 'recovery.pet')):
        raise ValueError('Recovery owner scope mismatch')
    fingerprint=hashlib.sha256(json.dumps(('recovery',rules.revision,command.npc_id,intent.kind),
        separators=(',',':')).encode()).hexdigest()
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if int(time.monotonic()*1000)>=command.deadline_ms:raise ValueError('NPC recovery expired')
        snapshot=inventory.immutable_snapshot_transaction(db)
        old=db.execute('SELECT fingerprint,targets FROM npc_recovery_receipts WHERE role_id=? AND request_id=?',
            (inventory.role_id,command.request_id)).fetchone()
        common=db.execute('SELECT fingerprint FROM npc_command_receipts WHERE role_id=? AND request_id=?',
            (inventory.role_id,command.request_id)).fetchone()
        if ((old is None)!=(common is None) or old and (old[0]!=fingerprint or common[0]!=fingerprint)):
            raise ValueError('Recovery receipt or retry intent conflict')
        if old:
            targets=tuple(json.loads(old[1]))
        else:
            level=db.execute('SELECT level FROM roles WHERE id=?',(inventory.role_id,)).fetchone()[0]
            identity='nc:'+hashlib.sha256(command.request_id.encode()).hexdigest()
            if intent.kind==1:
                fee,detail=_rest(db,accounts,inventory,rules,level,identity,snapshot,resource_rules,equipment_rules)
                targets=()
            else:
                changes,fee=_pet_changes(db,inventory,snapshot,intent.kind,rules,level)
                if fee:
                    apply_currency(db,inventory.account_id,inventory.role_id,inventory.epoch,
                        CurrencyChange(identity,'npc_shop',f'npc:{command.npc_id}:recovery:{intent.kind}',(('cash',-fee),)),accounts.currency_rules)
                detail=[]
                for pet,resources,deficit,quote in changes:
                    detail.append({'pet_id':pet.id,'before':asdict(pet),'resources':resources,'loyalty_deficit':deficit})
                    if quote is not None:detail[-1]['loyalty_quote']=quote
                    if resources:
                        progress=pet.progress
                        inventory.change_pet_growth(db,pet.id,identity,progress.state.version,'resources',
                            (progress.attributes.max_hp,progress.attributes.max_mp))
                    if deficit:
                        inventory.change_pet_care(db,pet.id,identity,pet.care.version,'restore_loyalty',1)
                targets=tuple(pet.id for pet,_,_,_ in changes)
            db.execute('INSERT INTO npc_recovery_receipts VALUES(?,?,?,?,?,?)',
                (inventory.role_id,command.request_id,fingerprint,json.dumps(targets),fee,json.dumps(detail)))
            db.execute('INSERT INTO npc_command_receipts VALUES(?,?,?)',
                (inventory.role_id,command.request_id,fingerprint))
        current=inventory.immutable_snapshot_transaction(db)
        pet_resources=None
        if intent.kind!=1 and resource_rules is not None:
            pet_resources=synchronize_inventory_resource_source(db,inventory.account_id,inventory.role_id,
                inventory.epoch,current,command.request_id,resource_rules=resource_rules,
                equipment_rules=equipment_rules,replayed=old is not None)
        messages=[(REFRESH_PET,pet_record(vars(pet))) for pet in current.pets if pet.id in targets]
        if intent.kind==1:
            current_role,resources=_current_role(db,inventory,current,resource_rules,equipment_rules)
            vigor=role_vigor.read(db,inventory,accounts.vigor_rules)
            refresh=(role_resource_refresh(current_role.vitals) if resources is None else
                growth_refresh(read_growth(db,inventory.account_id,inventory.role_id),current_role))
            messages.extend((refresh,role_vigor.refresh(vigor)))
        elif pet_resources is not None:
            profile=current_resource_profile(db,inventory.account_id,inventory.role_id,inventory.epoch,current,
                equipment_rules=equipment_rules,resource_rules=resource_rules)
            messages.append(growth_refresh(read_growth(db,inventory.account_id,inventory.role_id),profile))
        try:wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,accounts.currency_rules)
        except WalletNotInitialized:wallet=()
        messages.extend(encode_currency_balance(r.currency,r.balance) for r in wallet if r.currency=='cash')
        return messages
