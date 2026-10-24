"""Versioned pet care, original food/caps and explicit restoration generation.

Persistence joins the caller's fenced role transaction; no sends or commits.
"""
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from types import MappingProxyType
from inspect_client import OUT


@dataclass(frozen=True)
class PetCare:
    version: int
    grade: int
    loyalty: int
    lifetime: int

    def __post_init__(self):
        if (any(type(v) is not int for v in (self.version,self.grade,self.loyalty,self.lifetime))
                or not 0 <= self.version <= 0x7fffffff or not 1 <= self.grade <= 6
                or not 0 <= self.loyalty <= 0x7fffffff or not 0 <= self.lifetime <= 0x7fffffff):
            raise ValueError('Invalid pet care snapshot')


@dataclass(frozen=True)
class CareRules:
    revision: str
    initial_grade: int
    caps: object
    food: object
    death_loyalty: int
    death_lifetime: int
    lifetime_food: object
    quality_lifetime_food: object
    minimum_battle_lifetime: int
    kind_revision: str
    template_kinds: object
    immortal_kinds: tuple

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/pet-care-v1.json').read_text(encoding='utf-8'))
        if policy['revision'] != '2026-10-23.pet-care.1':
            raise ValueError('Pet care policy needs implementation review')
        if (type(policy['ordinary_death']['loyalty_loss']) is not int
                or type(policy['ordinary_death']['lifetime_loss']) is not int
                or (policy['ordinary_death']['loyalty_loss'],policy['ordinary_death']['lifetime_loss'])!=(20,50)):
            raise ValueError('Pet ordinary death values require review')
        if (type(policy['limits']['ordinary_battle_lifetime_minimum']) is not int
                or policy['limits']['ordinary_battle_lifetime_minimum']!=50
                or policy['limits']['selection_requires_positive_loyalty'] is not True):
            raise ValueError('Pet care selection/combat policy requires review')
        rows=json.loads((OUT/'catalogs/knight.gsp.pet.cpetxuemaiconfig.json').read_text(encoding='utf-8'))
        caps=MappingProxyType({int(r['attributes']['id']):int(r['attributes']['maxloy']) for r in rows})
        lifetime=policy['food']['lifetime_fixed']
        effects=json.loads((OUT/'catalogs/knight.gsp.item.cfoodanddrugeffect.json').read_text(encoding='utf-8'))
        fixed=next(r for r in effects if int(r['attributes']['id'])==32036)
        if (lifetime!={'32036':1000} or fixed['lists']['effect']!=['1000']
                or int(fixed['attributes']['funtionid'])!=0):
            raise ValueError('Original fixed pet lifetime food requires review')
        quality=policy['food']['lifetime_quality']
        formulas=json.loads((OUT/'catalogs/knight.gsp.item.cfooddrugeffectformula.json').read_text(encoding='utf-8'))
        formula=next(r['lists'] for r in formulas if int(r['attributes']['id'])==32007)
        leaf=next(r for r in effects if int(r['attributes']['id'])==32007)
        if (quality['templates']!=[32007] or formula!={'ai':['0.5','0.0','0.0'],'bi':['0','0','0']}
                or int(leaf['attributes']['funtionid'])!=0):
            raise ValueError('Original quality pet lifetime food requires review')
        ratio=Fraction(Decimal(formula['ai'][0]))
        kind_policy=json.loads((OUT/'design/pet-kind-care-v1.json').read_text(encoding='utf-8'))
        if (kind_policy['revision']!='2026-10-23.pet-kind-care.1'
                or kind_policy['immortal_kinds']!=[2] or kind_policy['ordinary_kinds']!=[1,3]
                or kind_policy['lifetime_gate']['immortal_bypasses_minimum_lifetime'] is not True
                or kind_policy['lifetime_gate']['known_positive_loyalty_still_required'] is not True):
            raise ValueError('Pet kind care policy requires review')
        pets=json.loads((OUT/'catalogs/knight.gsp.pet.cpetattr.json').read_text(encoding='utf-8'))
        kinds={int(row['attributes']['id']):int(row['attributes']['kind']) for row in pets}
        if len(kinds)!=len(pets) or set(kinds.values())!={1,2,3}:
            raise ValueError('Original pet kind classification requires review')
        return cls(policy['revision'],policy['generation']['grade'],caps,
                   MappingProxyType({int(k):v for k,v in policy['food']['loyalty'].items()}),
                   policy['ordinary_death']['loyalty_loss'],policy['ordinary_death']['lifetime_loss'],
                   MappingProxyType({int(k):v for k,v in lifetime.items()}),
                   MappingProxyType({32007:(ratio.numerator,ratio.denominator,int(formula['bi'][0]))}),
                   policy['limits']['ordinary_battle_lifetime_minimum'],kind_policy['revision'],
                   MappingProxyType(kinds),tuple(kind_policy['immortal_kinds']))

    def maximum(self, grade):
        if type(grade) is not int or grade not in self.caps:
            raise ValueError('Unknown pet care grade')
        return self.caps[grade]

    def validate(self, state):
        if not isinstance(state,PetCare) or state.loyalty > self.maximum(state.grade):
            raise ValueError('Pet loyalty exceeds its original grade cap')
        return state

    def ordinary_battle_care_ready(self, state):
        """Care gate only; caller still owns HP, level, skills and pet identity."""
        self.validate(state)
        return state.loyalty>0 and state.lifetime>=self.minimum_battle_lifetime

    def has_immortal_care(self, template_id):
        if type(template_id) is not int or template_id not in self.template_kinds:
            raise ValueError('Known original pet template required for care qualification')
        return self.template_kinds[template_id] in self.immortal_kinds

    def battle_care_ready(self, state, template_id):
        """Template-aware care gate; no HP, level, selection or skills guarantee."""
        self.validate(state)
        immortal=self.has_immortal_care(template_id)
        return state.loyalty>0 and (immortal or state.lifetime>=self.minimum_battle_lifetime)

    def apply(self, state, operation, value, *, template_id=None):
        self.validate(state)
        if operation=='feed' and type(value) is int and value in self.food:
            loyalty=min(self.maximum(state.grade),state.loyalty+self.food[value])
            if loyalty==state.loyalty:
                raise ValueError('Pet loyalty already full; food not consumed')
            result=replace(state,version=state.version+1,loyalty=loyalty)
        elif operation in ('feed_lifetime','feed_lifetime_quality'):
            if operation=='feed_lifetime' and type(value) is int and value in self.lifetime_food:
                amount=self.lifetime_food[value]
            elif (operation=='feed_lifetime_quality' and type(value) is tuple and len(value)==2
                    and type(value[0]) is int and value[0] in self.quality_lifetime_food
                    and type(value[1]) is int and 0<=value[1]<=0x7fffffff):
                numerator,denominator,offset=self.quality_lifetime_food[value[0]]
                amount=abs(value[1]*numerator+offset*denominator)//denominator
            else:raise ValueError('Known original lifetime food and persisted quality required')
            if amount<=0:raise ValueError('Lifetime food would have no effect; not consumed')
            lifetime=state.lifetime+amount
            if lifetime>0x7fffffff:
                raise ValueError('Pet lifetime exceeds signed32 representation; food not consumed')
            result=replace(state,version=state.version+1,lifetime=lifetime)
        elif operation=='increase_lifetime' and type(value) is int and 0<value<=0x7fffffff:
            result=replace(state,version=state.version+1,lifetime=state.lifetime+value)
        elif operation=='defeat' and type(value) is int and value==1:
            result=state if self.has_immortal_care(template_id) else replace(state,version=state.version+1,
                loyalty=max(0,state.loyalty-self.death_loyalty),
                lifetime=max(0,state.lifetime-self.death_lifetime))
        elif (operation=='battle_loss' and type(value) is tuple and len(value)==2
                and all(type(v) is int for v in value)
                and (value in ((0,0),(1,0),(1,1)) or value[0]>0
                     and value[0]%self.death_lifetime==0
                     and value[1] in (0,self.death_loyalty*(value[0]//self.death_lifetime)))):
            result=state if self.has_immortal_care(template_id) or value==(0,0) else replace(
                state,version=state.version+1,lifetime=max(0,state.lifetime-value[0]),
                loyalty=max(0,state.loyalty-value[1]))
        elif operation=='restore_loyalty' and type(value) is int and value==1:
            maximum=self.maximum(state.grade)
            if state.loyalty==maximum:raise ValueError('Pet loyalty already full')
            result=replace(state,version=state.version+1,loyalty=maximum)
        else:
            raise ValueError('Unsupported pet care operation')
        return self.validate(result)


def prepare(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS inventory_pet_care (
            pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),
            revision TEXT NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS inventory_pet_care_receipts (
            role_id INTEGER NOT NULL REFERENCES roles(id),
            pet_id INTEGER NOT NULL REFERENCES inventory_pets(id),
            settlement_id TEXT NOT NULL, fingerprint TEXT NOT NULL, result TEXT NOT NULL,
            PRIMARY KEY(role_id,pet_id,settlement_id));
    ''')


def _owned(db, account_id, role_id, pet_id):
    if type(pet_id) is not int or pet_id<=0 or not db.in_transaction:
        raise ValueError('Pet care requires an owned active pet transaction')
    row=db.execute(
            'SELECT p.template_id FROM inventory_pets p JOIN roles r ON r.id=p.role_id '
            'WHERE p.id=? AND r.id=? AND r.account_id=? AND p.released=0',
            (pet_id,role_id,account_id)).fetchone()
    if not row:
        raise ValueError('Pet care requires an owned active pet transaction')
    return row[0]


def initialize(db, account_id, role_id, pet_id, rules, grade, loyalty, lifetime):
    _owned(db,account_id,role_id,pet_id)
    state=rules.validate(PetCare(0,grade,loyalty,lifetime))
    if db.execute('SELECT 1 FROM inventory_pet_care WHERE pet_id=?',(pet_id,)).fetchone():
        raise ValueError('Pet care already initialized; reroll forbidden')
    db.execute('INSERT INTO inventory_pet_care VALUES(?,?,?)',
               (pet_id,rules.revision,json.dumps(asdict(state))))
    _revision(db,role_id)
    return state


def load(db, account_id, role_id, pet_id, rules):
    _owned(db,account_id,role_id,pet_id)
    row=db.execute('SELECT revision,state FROM inventory_pet_care WHERE pet_id=?',(pet_id,)).fetchone()
    if row is None or row[0]!=rules.revision:
        raise ValueError('Pet care needs explicit initialization or revision migration')
    return rules.validate(PetCare(**json.loads(row[1])))


def _revision(db,role_id):
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role_id,))


def change(db, account_id, role_id, pet_id, rules, settlement_id, expected_version, operation, value):
    template_id=_owned(db,account_id,role_id,pet_id)
    quality_value=(operation=='feed_lifetime_quality' and type(value) is tuple and len(value)==2
                   and all(type(x) is int for x in value))
    battle_value=(operation=='battle_loss' and type(value) is tuple and len(value)==2
                  and all(type(x) is int for x in value))
    if (type(settlement_id) is not str or not 1<=len(settlement_id)<=160
            or type(expected_version) is not int or expected_version<0
            or not (quality_value or battle_value or type(value) is int)):
        raise ValueError('Invalid pet care settlement')
    fingerprint=hashlib.sha256(json.dumps([operation,value],separators=(',',':')).encode()).hexdigest()
    row=db.execute('SELECT fingerprint,result FROM inventory_pet_care_receipts '
                   'WHERE role_id=? AND pet_id=? AND settlement_id=?',
                   (role_id,pet_id,settlement_id)).fetchone()
    if row:
        if row[0]!=fingerprint:
            raise ValueError('Pet care settlement payload conflict')
        saved=json.loads(row[1])
        if 'format' in saved:
            if (saved['format']!=2 or saved['kind_policy']!=rules.kind_revision
                    or type(saved['template_id']) is not int or type(saved['kind']) is not int
                    or saved['kind']!=rules.template_kinds.get(saved['template_id'])):
                raise ValueError('Pet care receipt needs explicit policy reconciliation')
            saved=saved['care']
        return rules.validate(PetCare(**saved))
    rules.has_immortal_care(template_id)  # Unknown fresh identities cannot produce ambiguous receipts.
    old=load(db,account_id,role_id,pet_id,rules)
    if old.version!=expected_version:
        raise ValueError('Pet care version mismatch')
    result=rules.apply(old,operation,value,template_id=template_id)
    body=json.dumps(asdict(result))
    if result!=old:
        db.execute('UPDATE inventory_pet_care SET state=? WHERE pet_id=?',(body,pet_id))
        _revision(db,role_id)
    receipt=json.dumps({'format':2,'care':asdict(result),'kind_policy':rules.kind_revision,
                        'template_id':template_id,'kind':rules.template_kinds.get(template_id)})
    db.execute('INSERT INTO inventory_pet_care_receipts VALUES(?,?,?,?,?)',
               (role_id,pet_id,settlement_id,fingerprint,receipt))
    return result
