"""Trusted per-pet ordinary/sparring care settlement in the caller's role txn."""
from dataclasses import dataclass,asdict,replace
import hashlib
import json
from inspect_client import OUT
import pet_care
import pet_growth_store


@dataclass(frozen=True)
class BattleCareRules:
    revision: str
    lifetime: int
    every: int
    loyalty: int
    death_lifetime: int
    death_loyalty: int
    free_level: int

    @classmethod
    def load(cls):
        p=json.loads((OUT/'design/pet-battle-care-v1.json').read_text(encoding='utf-8'))
        keys=('participation_lifetime','loyalty_every_survived_battles','participation_loyalty',
              'death_lifetime','death_loyalty','loyalty_free_through_level')
        values=tuple(p[k] for k in keys)
        if (p['revision']!='2026-10-23.pet-battle-care.1' or any(type(v) is not int for v in values)
                or values!=(1,3,1,50,20,30)
                or any(p['counter_decisions'][k] is not True for k in (
                    'death_preserves_previous_mod3','free_level_preserves_previous_mod3','sparring_preserves_previous_mod3'))
                or p['counter_decisions']['new_pet_mod3']!=0):
            raise ValueError('Pet battle care policy requires review')
        return cls(p['revision'],*values)


@dataclass(frozen=True)
class BattleCareCounter:
    version: int
    mod3: int

    def __post_init__(self):
        if (type(self.version) is not int or not 0<=self.version<=0x7fffffff
                or type(self.mod3) is not int or not 0<=self.mod3<3):
            raise ValueError('Known pet battle care counter required')


@dataclass(frozen=True)
class BattleCareEvent:
    settlement_id: str
    pet_id: int
    template_id: int
    expected_care_version: int
    expected_growth_version: int
    expected_counter_version: int
    mode: str = 'ordinary'
    participated: bool = True
    death_count: int = 0

    def __post_init__(self):
        if (type(self.settlement_id) is not str or not 1<=len(self.settlement_id)<=160
                or any(type(v) is not int or not 0<v<=0x7fffffff for v in (self.pet_id,self.template_id))
                or any(type(v) is not int or not 0<=v<2**63 for v in (
                    self.expected_care_version,self.expected_growth_version,self.expected_counter_version))
                or type(self.mode) is not str or self.mode not in ('ordinary','sparring')
                or type(self.participated) is not bool
                or type(self.death_count) is not int or not 0<=self.death_count<=0x7fffffff
                or self.death_count and not self.participated):
            raise ValueError('Invalid trusted pet battle care outcome')


@dataclass(frozen=True)
class BattleCareReceipt:
    settlement_id: str
    pet_id: int
    template_id: int
    level: int
    care_before: object
    care_after: object
    counter_before: object
    counter_after: object
    policy: str
    replayed: bool = False


def prepare(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS inventory_pet_battle_care (
            pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),revision TEXT NOT NULL,
            version INTEGER NOT NULL,mod3 INTEGER NOT NULL CHECK(mod3 BETWEEN 0 AND 2));
        CREATE TABLE IF NOT EXISTS inventory_pet_battle_care_receipts (
            role_id INTEGER NOT NULL REFERENCES roles(id),pet_id INTEGER NOT NULL REFERENCES inventory_pets(id),
            settlement_id TEXT NOT NULL,fingerprint TEXT NOT NULL,result TEXT NOT NULL,
            PRIMARY KEY(role_id,pet_id,settlement_id));
    ''')


def initialize(db,account,role,pet,rules,mod3):
    pet_care._owned(db,account,role,pet)
    state=BattleCareCounter(0,mod3)
    if db.execute('SELECT 1 FROM inventory_pet_battle_care WHERE pet_id=?',(pet,)).fetchone():
        raise ValueError('Pet battle care counter cannot be rerolled')
    db.execute('INSERT INTO inventory_pet_battle_care VALUES(?,?,?,?)',(pet,rules.revision,0,mod3))
    pet_care._revision(db,role)
    return state


def load(db,account,role,pet,rules):
    pet_care._owned(db,account,role,pet)
    row=db.execute('SELECT revision,version,mod3 FROM inventory_pet_battle_care WHERE pet_id=?',(pet,)).fetchone()
    if not row or row[0]!=rules.revision:
        raise ValueError('Pet battle care counter requires explicit initialization/reconciliation')
    return BattleCareCounter(*row[1:])


def settle(db,account,role,event,rules,care_rules,growth_rules,blood_rules):
    if not isinstance(event,BattleCareEvent):raise ValueError('Frozen trusted battle outcome required')
    if not db.in_transaction:raise ValueError('Pet battle care requires the role transaction')
    owned=db.execute('SELECT p.template_id,p.released FROM inventory_pets p JOIN roles r ON r.id=p.role_id '
        'WHERE p.id=? AND r.id=? AND r.account_id=?',(event.pet_id,role,account)).fetchone()
    if not owned:raise ValueError('Pet battle care requires an owned pet')
    template,released=owned
    fingerprint=hashlib.sha256(json.dumps([asdict(event),rules.revision,care_rules.revision,
        care_rules.kind_revision,growth_rules.revision,blood_rules.revision],sort_keys=True).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result FROM inventory_pet_battle_care_receipts '
        'WHERE role_id=? AND pet_id=? AND settlement_id=?',(role,event.pet_id,event.settlement_id)).fetchone()
    if old:
        if old[0]!=fingerprint:raise ValueError('Pet battle settlement intent conflict')
        data=json.loads(old[1])
        if data['policy']!=rules.revision:raise ValueError('Pet battle receipt needs policy reconciliation')
        for key in ('care_before','care_after'):data[key]=care_rules.validate(pet_care.PetCare(**data[key]))
        for key in ('counter_before','counter_after'):data[key]=BattleCareCounter(**data[key])
        return BattleCareReceipt(**data,replayed=True)
    if released:raise ValueError('Released pet cannot receive a fresh battle settlement')
    if template!=event.template_id:raise ValueError('Pet battle template changed after admission')
    care=pet_care.load(db,account,role,event.pet_id,care_rules)
    meter=load(db,account,role,event.pet_id,rules)
    progress=pet_growth_store.load_pet(db,account,role,event.pet_id,growth_rules,
                                     blood_rules=blood_rules,grade=care.grade)
    if (care.version!=event.expected_care_version or meter.version!=event.expected_counter_version
            or progress.state.version!=event.expected_growth_version):
        raise ValueError('Pet battle admission versions no longer current')
    if event.participated and (progress.state.hp<=0 or not care_rules.battle_care_ready(care,template)):
        raise ValueError('Pet battle care admission was not eligible')
    life=loyalty=0;after=meter
    if event.participated and event.mode=='ordinary' and not care_rules.has_immortal_care(template):
        life=rules.death_lifetime*event.death_count if event.death_count else rules.lifetime
        if progress.state.level>rules.free_level:
            if event.death_count:loyalty=rules.death_loyalty*event.death_count
            else:
                count=meter.mod3+1
                loyalty=rules.loyalty if count==rules.every else 0
                after=BattleCareCounter(meter.version+1,count%rules.every)
    child='battle-care:'+hashlib.sha256(event.settlement_id.encode()).hexdigest()
    cared=pet_care.change(db,account,role,event.pet_id,care_rules,child,care.version,'battle_loss',(life,loyalty))
    if after!=meter:
        changed=db.execute('UPDATE inventory_pet_battle_care SET version=?,mod3=? WHERE pet_id=? AND revision=? AND version=?',
            (after.version,after.mod3,event.pet_id,rules.revision,meter.version)).rowcount
        if changed!=1:raise ValueError('Pet battle counter version conflict')
        pet_care._revision(db,role)
    receipt=BattleCareReceipt(event.settlement_id,event.pet_id,template,progress.state.level,care,cared,meter,after,rules.revision)
    saved=asdict(receipt);saved.pop('replayed')
    db.execute('INSERT INTO inventory_pet_battle_care_receipts VALUES(?,?,?,?,?)',
        (role,event.pet_id,event.settlement_id,fingerprint,json.dumps(saved)))
    return receipt
