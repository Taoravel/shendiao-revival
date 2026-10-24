"""Wild admission, durable combat outbox and atomic terminal settlement.

Runs on the role persistence worker. No transport, schema hot path or ownership
of another actor's mutable state. Original admission and terminal epochs survive
recovery; only the current role lease can commit their effects.
"""
from contextlib import closing
from dataclasses import asdict,dataclass,replace
import hashlib
import json
from battle import Fighter,Skill
from battle_owner import Participant
from battle_loadout import OwnedBattlePet,selected_pet,CombatResources
from wild_encounters import EncounterTicket,WildMonster
from wild_battle import aborted_result
from world_owner import Location,MapAddress
from training_battle import BattleFinished,DEFAULT_RULES
from inventory import AssetChange
from item_effects import VitalState
from currency import read_wallet
from currency_protocol import encode_currency_balance,encode_yuanbao_balances
from role_resource_storage import (read_role_resources,ResourceNotInitialized,apply_resource_transition)
from role_resource_plan import plan_combat_resources
from role_equipment import resource_caps_from_projection
from role_equipment_storage import current_equipment_totals
from role_attribute_storage import read_attribute_snapshot,update_role_vitals
from task_dialog_protocol import S_REFRESH_USER_EXP,encode_user_experience
from wild_rewards import register_wild_reward,settle_wild_reward,wild_pet_refresh


def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def _digest(value):return hashlib.sha256(_json(value).encode()).hexdigest()


@dataclass(frozen=True)
class WildCommit:
    role: object
    packets: tuple
    replayed: bool


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS wild_runtime_battles(
        role_id INTEGER NOT NULL,battle_id TEXT NOT NULL,accepted_epoch TEXT NOT NULL,
        participant TEXT NOT NULL,ticket TEXT NOT NULL,before_vitals TEXT NOT NULL,
        fighters TEXT NOT NULL,round_number INTEGER NOT NULL,state_version INTEGER NOT NULL,
        terminal TEXT,terminal_hash TEXT,status TEXT NOT NULL,
        PRIMARY KEY(role_id,battle_id))''')


def _inventory(accounts,account,role,epoch):
    import runtime_storage as storage
    return storage._inventory(accounts,account,role,epoch)


def _snapshot(db,accounts,account,role,epoch,generation):
    import runtime_storage as storage
    inv=_inventory(accounts,account,role,epoch)
    profile=storage._role_profile_transaction(db,accounts,account,role,epoch,inv)
    if profile.attributes is None:raise ValueError('Wild combat requires known current role attributes')
    attrs=profile.attributes.attributes;vitals=profile.attributes.vitals
    if vitals.hp<=0:raise ValueError('Dead role cannot encounter wild monsters')
    # Preserve the role's existing contract. Encounter admission is not an
    # authorization to migrate legacy resources or activate new-role policies.
    snapshot=inv.immutable_snapshot_transaction(db,epoch=epoch)
    try:resources=read_role_resources(db,account,role,epoch,accounts.resource_rules)
    except ResourceNotInitialized:
        resources=None
        bare=read_attribute_snapshot(db,account,role,epoch)
        if bare.vitals!=vitals:
            raise ValueError('Legacy equipped resource caps need explicit migration before combat')
    role_row=db.execute('SELECT name,shape FROM roles WHERE id=? AND account_id=?',(role,account)).fetchone()
    pet=selected_pet(snapshot,role_id=role,role_level=profile.role.level,templates=DEFAULT_RULES.pet_templates,
                     growth_revision=inv.growth_rules.revision)
    participant=Participant(role,epoch,generation,max(1,vitals.version),role_row[0],role_row[1],profile.role.level,
        Fighter(1,0,vitals.hp,vitals.max_hp,vitals.mp,attrs.physical_attack,attrs.physical_defense,attrs.speed,
                max_mp=vitals.max_mp),pet=pet)
    read_wallet(db,account,role,epoch,accounts.currency_rules)
    return participant,vitals,inv,resources


def participant(accounts,account,role,epoch,generation):
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM wild_runtime_battles WHERE role_id=? AND status!='settled'",(role,)).fetchone():
            raise ValueError('Prior wild battle awaits durable settlement')
        return _snapshot(db,accounts,account,role,epoch,generation)[0]


def admit(accounts,account,participant,ticket,battle_id):
    role,epoch=participant.role_id,participant.login_epoch
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        current,before,inv,resources=_snapshot(db,accounts,account,role,epoch,participant.connection_generation)
        if current!=participant:raise ValueError('Role combat snapshot changed before wild admission')
        if db.execute("SELECT 1 FROM wild_runtime_battles WHERE role_id=? AND status!='settled'",(role,)).fetchone():
            raise ValueError('Wild battle already admitted')
        register_wild_reward(db,account,participant,ticket,battle_id,inv,accounts.wild_reward_rules)
        plan=json.loads(db.execute('SELECT plan FROM wild_reward_admissions WHERE role_id=? AND battle_id=?',
                                  (role,battle_id)).fetchone()[0])
        # Preflight the FIXED drops while inventory changes are about to freeze.
        # A full bag declines before battle, rather than trapping a won battle.
        db.execute('SAVEPOINT wild_drop_capacity')
        try:inv.apply_settlement(db,AssetChange('wild-capacity:'+battle_id,tuple(tuple(g) for g in plan['grants'])))
        finally:db.execute('ROLLBACK TO wild_drop_capacity');db.execute('RELEASE wild_drop_capacity')
        fighters=(participant.stats,ticket.enemy)+((participant.pet.stats,) if participant.pet else ())
        db.execute('INSERT INTO wild_runtime_battles VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (role,battle_id,str(epoch),_json(asdict(participant)),_json(asdict(ticket)),
             _json(dict(format=2,vitals=asdict(before),resources=asdict(resources) if resources is not None else None)),
             _json([asdict(f) for f in fighters]),0,1,None,None,'active'))


def checkpoint(accounts,account,role,epoch,snapshot,finished=None):
    """Persist combat copy before delivery. Terminal result is immutable."""
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT accepted_epoch,state_version,terminal_hash FROM wild_runtime_battles '
            'WHERE role_id=? AND battle_id=?',(role,snapshot.battle_id)).fetchone()
        if row is None or row[0]!=str(epoch):raise ValueError('Wild checkpoint identity mismatch')
        digest=_digest(asdict(finished)) if finished else None
        if row[2]:
            if digest!=row[2]:raise ValueError('Wild terminal result changed')
            return
        if snapshot.state_version<row[1]:raise ValueError('Wild checkpoint version moved backwards')
        db.execute('UPDATE wild_runtime_battles SET fighters=?,round_number=?,state_version=?,terminal=?,terminal_hash=?,status=? '
            'WHERE role_id=? AND battle_id=?',(_json([asdict(f) for f in snapshot.fighters]),snapshot.round_number,
            snapshot.state_version,_json(asdict(finished)) if finished else None,digest,'terminal' if finished else 'active',
            role,snapshot.battle_id))


def _fighter(row):
    row=dict(row);row['skills']=tuple(Skill(**s) for s in row.get('skills',()))
    return Fighter(**row)


def _participant(row):
    row=dict(row);row['stats']=_fighter(row['stats']);row['authorized_skills']=tuple(row['authorized_skills'])
    if row['pet']:
        pet=dict(row['pet']);pet['stats']=_fighter(pet['stats']);row['pet']=OwnedBattlePet(**pet)
    return Participant(**row)


def _ticket(row):
    row=dict(row);location=dict(row['location']);location['address']=MapAddress(**location['address'])
    row['location']=Location(**location);row['monster']=WildMonster(**row['monster']);row['enemy']=_fighter(row['enemy'])
    return EncounterTicket(**row)


def _finished(row):
    row=dict(row);row['item_rewards']=tuple(row['item_rewards'])
    row['combat_resources']=tuple(CombatResources(**r) for r in row['combat_resources'])
    return BattleFinished(**row)


def _messages(db,accounts,account,role,epoch,inv,receipt):
    import runtime_storage as storage
    profile=storage._role_profile_transaction(db,accounts,account,role,epoch,inv)
    messages=[(S_REFRESH_USER_EXP,encode_user_experience(profile.role.experience))]
    if profile.refresh:messages.append(profile.refresh)
    balances=read_wallet(db,account,role,epoch,accounts.currency_rules)
    amounts={b.currency:b.balance for b in balances}
    messages.extend(encode_currency_balance(b.currency,b.balance) for b in balances if b.currency in ('cash','bound_silver'))
    if 'yuanbao' in amounts and 'bound_yuanbao' in amounts:
        messages.append(encode_yuanbao_balances(amounts['yuanbao'],amounts['bound_yuanbao']))
    messages.append(inv._bag_reply(db,1,epoch=epoch))
    messages.extend(wild_pet_refresh(db,account,role,epoch,receipt,inv))
    return WildCommit(profile.role,tuple(messages),receipt['replayed'])


def _settle(db,accounts,account,role,epoch,battle_id):
    import runtime_storage as storage
    row=db.execute('SELECT before_vitals,terminal,terminal_hash,status FROM wild_runtime_battles '
                   'WHERE role_id=? AND battle_id=?',(role,battle_id)).fetchone()
    if not row or not row[1]:raise ValueError('Durable wild terminal required')
    result=_finished(json.loads(row[1]));inv=_inventory(accounts,account,role,epoch)
    if row[3]=='settled':
        receipt=json.loads(db.execute('SELECT receipt FROM wild_reward_admissions WHERE role_id=? AND battle_id=?',
                                    (role,battle_id)).fetchone()[0]);receipt['replayed']=True
        return _messages(db,accounts,account,role,epoch,inv,receipt)
    if row[2]!=_digest(asdict(result)):raise ValueError('Wild terminal outbox fingerprint mismatch')
    admission=json.loads(row[0])
    before=VitalState(**(admission['vitals'] if admission.get('format')==2 else admission))
    try:resources=read_role_resources(db,account,role,epoch,accounts.resource_rules)
    except ResourceNotInitialized:resources=None
    if admission.get('format')==2:
        current=asdict(resources) if resources is not None else None
        if current!=admission['resources']:
            raise ValueError('Wild admission resource source changed outside battle ownership')
    elif resources is not None:
        # Old staged rows did not capture source. Do not retrospectively bind
        # their combat to today's projection or silently migrate a legacy row.
        raise ValueError('Wild admission resource source missing; explicit reconciliation required')
    if resources is None:
        if read_attribute_snapshot(db,account,role,epoch).vitals!=before:
            raise ValueError('Wild terminal legacy resources changed outside battle ownership')
    elif (resources.version,resources.hp,resources.mp,resources.caps.hp_max,resources.caps.mp_max)!=(
            before.version,before.hp,before.mp,before.max_hp,before.max_mp):
        raise ValueError('Wild terminal resources changed outside battle ownership')
    roles=tuple(r for r in result.combat_resources if r.kind=='role')
    if len(roles)!=1:raise ValueError('One owned role terminal required')
    terminal=roles[0]
    if (terminal.entity_id,terminal.position,terminal.source_version,terminal.max_hp,terminal.max_mp)!=(
            role,1,result.snapshot_version,before.max_hp,before.max_mp):
        raise ValueError('Wild role terminal differs from admission')
    if resources is not None:
        transition=plan_combat_resources(resources,terminal.hp,terminal.mp,accounts.resource_rules)
        apply_resource_transition(db,account,role,epoch,transition,'wild:'+battle_id+':role_resources',
            rules=accounts.resource_rules,equipment_rules=accounts.equipment_attribute_rules)
    elif (terminal.hp,terminal.mp)!=(before.hp,before.mp):
        if not 0<=terminal.hp<=before.hp or not 0<=terminal.mp<=before.mp:
            raise ValueError('Ordinary combat cannot heal or revive legacy role')
        update_role_vitals(db,account,role,epoch,before,replace(before,version=before.version+1,hp=terminal.hp,mp=terminal.mp))
    receipt=settle_wild_reward(db,account,role,epoch,result,inv,accounts.currency_rules,
        accounts.growth_rules,accounts.attribute_rules,resource_context=storage._growth_context(db,accounts,account,role,epoch,inv),
        recovery_from_epoch=result.login_epoch if result.login_epoch!=epoch else None)
    storage._synchronize_source(db,accounts,inv,result.settlement_id,replayed=receipt['replayed'])
    committed=_messages(db,accounts,account,role,epoch,inv,receipt)
    db.execute("UPDATE wild_runtime_battles SET status='settled' WHERE role_id=? AND battle_id=?",(role,battle_id))
    return committed


def settle(accounts,account,role,epoch,battle_id):
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');return _settle(db,accounts,account,role,epoch,battle_id)


def recover(accounts,account,role,epoch):
    """Current fenced owner recovers saved terminal or aborts saved live copy."""
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        rows=db.execute("SELECT battle_id,participant,ticket,fighters,round_number,terminal FROM wild_runtime_battles "
                        "WHERE role_id=? AND status!='settled'",(role,)).fetchall()
        if len(rows)>1:raise ValueError('Multiple pending wild battles require reconciliation')
        for battle_id,participant,ticket,fighters,round_number,terminal in rows:
            if terminal is None:
                result=aborted_result(_participant(json.loads(participant)),_ticket(json.loads(ticket)),battle_id,
                    tuple(_fighter(f) for f in json.loads(fighters)),round_number)
                db.execute("UPDATE wild_runtime_battles SET terminal=?,terminal_hash=?,status='terminal' WHERE role_id=? AND battle_id=?",
                    (_json(asdict(result)),_digest(asdict(result)),role,battle_id))
            _settle(db,accounts,account,role,epoch,battle_id)
