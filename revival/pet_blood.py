"""Ordinary blood metadata and projection; original source, explicit design math."""
from dataclasses import dataclass,asdict,replace
from decimal import Decimal
from fractions import Fraction
from types import MappingProxyType
import json
import hashlib

from inspect_client import OUT
from pet_growth import Profile


@dataclass(frozen=True)
class PetBlood:
    version: int
    power: int

    def __post_init__(self):
        if (type(self.version) is not int or not 0<=self.version<0x7fffffff
                or type(self.power) is not int or not 0<=self.power<=52611):
            raise ValueError('Invalid known ordinary pet blood state')


@dataclass(frozen=True)
class BloodProgress:
    state: PetBlood
    grade: int
    level: int
    maximum_level: int
    maximum_power: int
    bonus_potential: int
    policy: str


@dataclass(frozen=True)
class BloodRules:
    revision: str
    rows: tuple
    caps: object
    essence_template: int
    essence_power: int
    essence_need_level: int
    potential_per_level: int

    @classmethod
    def load(cls):
        p=json.loads((OUT/'design/pet-blood-v1.json').read_text(encoding='utf-8'))
        if (p['revision']!='2026-10-23.pet-blood.1' or p['branch']!='ordinary_only'
                or p['generation']!={'power':0,'source_status':'designed'}
                or p['essence']!={'template_id':36117,'power_per_item':200,'source_status':'client_verified'}
                or type(p['potential_per_level']) is not int or p['potential_per_level']!=10
                or p['aptitudes']!={'formula':'base + floor(base * original_level_ratio)','source_status':'designed'}
                or p['cap']!={'power':'upper_bound_of_colour_max_level','overflow':'discard_after_one_item','source_status':'designed'}
                or p['resources']!={'advance':'preserve_missing_amount_dead_stays_dead','import':'preserve_current_absolute','source_status':'designed'}
                or p['role_level']!={'rule':'current_item_needLevel','conflicting_historical_help':45,'source_status':'designed'}):
            raise ValueError('Pet blood policy requires implementation review')
        def catalog(name):return json.loads((OUT/f'catalogs/knight.gsp.{name}.json').read_text(encoding='utf-8'))
        levels=sorted((r['attributes'] for r in catalog('pet.cpetbloodconfig')),key=lambda a:int(a['id']))
        bounds=((0,63),(64,229),(230,565),(566,1139),(1140,2019),(2020,3273),
            (3274,4969),(4970,7761),(7762,11284),(11285,15625),(15626,20870),
            (20871,27105),(27106,34416),(34417,42889),(42890,52610),(52611,52611))
        if (tuple(int(a['id']) for a in levels)!=tuple(range(16))
                or tuple((int(a['lowpower']),int(a['uppower'])) for a in levels)!=bounds):
            raise ValueError('Original ordinary blood ranges require review')
        rows=[]
        for a in levels:
            ratio=Fraction(Decimal(a['ratio']))
            if not 0<=ratio<=Fraction(15,100):raise ValueError('Original blood ratio out of range')
            rows.append((int(a['lowpower']),int(a['uppower']),ratio.numerator,ratio.denominator))
        caps={int(r['attributes']['id']):int(r['attributes']['maxstarnum']) for r in catalog('pet.cpetxuemaiconfig')}
        if caps!={1:3,2:5,3:7,4:9,5:12,6:15}:raise ValueError('Original colour blood limits require review')
        item=next(r['attributes'] for r in catalog('item.citemattr') if int(r['attributes']['id'])==36117)
        if (int(item['itemtypeid'])!=1510 or int(item['needLevel'])!=1 or int(item['outbattleuse'])!=2):
            raise ValueError('Original blood essence item gate requires review')
        return cls(p['revision'],tuple(rows),MappingProxyType(caps),36117,200,1,10)

    def progress(self,state,grade):
        if not isinstance(state,PetBlood) or type(grade) is not int or grade not in self.caps:
            raise ValueError('Known ordinary blood state and current colour required')
        cap=self.caps[grade];maximum=self.rows[cap][1]
        if state.power>maximum:raise ValueError('Blood power exceeds its explicit colour ceiling')
        level=next(i for i,row in enumerate(self.rows) if row[0]<=state.power<=row[1])
        return BloodProgress(state,grade,level,cap,maximum,level*self.potential_per_level,self.revision)

    def effective_profile(self,profile,blood):
        if (type(profile) is not Profile or type(blood) is not BloodProgress or blood.policy!=self.revision
                or blood!=self.progress(blood.state,blood.grade) or type(profile.aptitudes) is not tuple
                or len(profile.aptitudes)!=5 or any(type(v) is not int or not 0<=v<=0x7fffffff for v in profile.aptitudes)):
            raise ValueError('Known base profile and current blood projection required')
        _,_,numerator,denominator=self.rows[blood.level]
        values=tuple(value+value*numerator//denominator for value in profile.aptitudes)
        if max(values)>0x7fffffff:raise ValueError('Effective pet aptitudes overflow')
        return replace(profile,aptitudes=values)


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_blood (
        pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),policy TEXT NOT NULL,state TEXT NOT NULL);''')
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_blood_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id),pet_id INTEGER NOT NULL REFERENCES inventory_pets(id),
        settlement_id TEXT NOT NULL,fingerprint TEXT NOT NULL,result TEXT NOT NULL,
        PRIMARY KEY(role_id,settlement_id));''')


def _owner(db,account,role,pet):
    if (not db.in_transaction or type(pet) is not int or not 0<pet<=0x7fffffff
            or not db.execute('SELECT 1 FROM inventory_pets p JOIN roles r ON r.id=p.role_id '
            'WHERE p.id=? AND p.role_id=? AND r.account_id=? AND p.released=0',(pet,role,account)).fetchone()):
        raise ValueError('Pet blood requires an owned live pet transaction')


def initialize(db,account,role,pet,rules,power,grade):
    _owner(db,account,role,pet);state=PetBlood(0,power);progress=rules.progress(state,grade)
    if db.execute('SELECT 1 FROM inventory_pet_blood WHERE pet_id=?',(pet,)).fetchone():
        raise ValueError('Known blood cannot be reset or re-sourced')
    db.execute('INSERT INTO inventory_pet_blood VALUES(?,?,?)',(pet,rules.revision,json.dumps(asdict(state))))
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))
    return progress


def load(db,account,role,pet,rules,grade):
    _owner(db,account,role,pet)
    row=db.execute('SELECT policy,state FROM inventory_pet_blood WHERE pet_id=?',(pet,)).fetchone()
    if row is None:return None
    if type(rules) is not BloodRules or row[0]!=rules.revision:
        raise ValueError('Known blood requires prepared rules or explicit policy migration')
    return rules.progress(PetBlood(**json.loads(row[1])),grade)


def save(db,account,role,pet,rules,before,after):
    """Internal growth writer saves one verified ordinary essence step."""
    if (type(before) is not BloodProgress or type(after) is not BloodProgress
            or before.grade!=after.grade or after.state.version!=before.state.version+1
            or after!=rules.progress(after.state,after.grade)
            or load(db,account,role,pet,rules,before.grade)!=before
            or after.state.power!=min(before.maximum_power,before.state.power+rules.essence_power)
            or after.state.power<=before.state.power):
        raise ValueError('Blood progression differs from its current one-essence plan')
    row=db.execute('SELECT policy,state FROM inventory_pet_blood WHERE pet_id=?',(pet,)).fetchone()
    changed=db.execute('UPDATE inventory_pet_blood SET state=? WHERE pet_id=? AND policy=? AND state=?',
        (json.dumps(asdict(after.state)),pet,row[0],row[1])).rowcount
    if changed!=1:raise ValueError('Blood state changed during the role transaction')


@dataclass(frozen=True)
class BloodReceipt:
    settlement_id: str
    pet_id: int
    item_key: int
    before: object
    after: object
    policy: str
    replayed: bool = False


def use_essence(db,account,role,pet,key,request_id,expected_version,growth_rules,blood_rules,care_rules):
    """Trusted role transaction; no new connection, commit, sender or RNG."""
    import pet_care
    import pet_growth_store
    _owner(db,account,role,pet)
    if (type(key) is not int or not 0<key<=0x7fffffff
            or type(request_id) is not str or not 1<=len(request_id)<=160
            or expected_version is not None and (type(expected_version) is not int or not 0<=expected_version<2**63)):
        raise ValueError('Trusted ordinary blood essence command required')
    fingerprint=hashlib.sha256(json.dumps([pet,key,expected_version,growth_rules.revision,blood_rules.revision]).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result FROM inventory_pet_blood_receipts WHERE role_id=? AND settlement_id=?',
        (role,request_id)).fetchone()
    if old:
        if old[0]!=fingerprint:raise ValueError('Blood request intent conflict')
        value=json.loads(old[1])
        if value['policy']!=blood_rules.revision:raise ValueError('Historical blood policy requires reconciliation')
        before=pet_growth_store.decode_progress(value['before'],role,pet,growth_rules,blood_rules)
        after=pet_growth_store.decode_progress(value['after'],role,pet,growth_rules,blood_rules)
        return BloodReceipt(request_id,pet,key,before,after,value['policy'],True)
    care=pet_care.load(db,account,role,pet,care_rules)
    before=pet_growth_store.load_pet(db,account,role,pet,growth_rules,blood_rules=blood_rules,grade=care.grade)
    if before.blood is None:raise ValueError('Legacy blood power and BASE profile need explicit known initialization')
    if expected_version is not None and before.state.version!=expected_version:
        raise ValueError('Pet blood command growth version mismatch')
    item=db.execute('SELECT i.template_id,i.quantity,r.level FROM inventory_items i JOIN roles r ON r.id=i.role_id '
        'WHERE i.id=? AND i.role_id=? AND i.equipment_slot IS NULL',(key,role)).fetchone()
    if not item or item[0]!=blood_rules.essence_template or item[1]<1 or item[2]<blood_rules.essence_need_level:
        raise ValueError('Owned carried original essence and role item level required')
    after=pet_growth_store.advance_blood(db,account,role,pet,growth_rules,blood_rules,care.grade,before)
    if item[1]==1:db.execute('DELETE FROM inventory_items WHERE id=? AND role_id=?',(key,role))
    else:db.execute('UPDATE inventory_items SET quantity=quantity-1 WHERE id=? AND role_id=?',(key,role))
    value={'before':pet_growth_store.encode_progress(before),'after':pet_growth_store.encode_progress(after),'policy':blood_rules.revision}
    db.execute('INSERT INTO inventory_pet_blood_receipts VALUES(?,?,?,?,?)',
        (role,pet,request_id,fingerprint,json.dumps(value)))
    return BloodReceipt(request_id,pet,key,before,after,blood_rules.revision)
