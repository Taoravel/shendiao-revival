"""Durable per-pet super-return candidates inside the role owner's transaction."""
from dataclasses import dataclass,asdict,replace
from types import MappingProxyType
import json
import hashlib
from inspect_client import OUT
from pet_growth import Profile
from pet_protocol import super_return_preview_message
import pet_growth_store
import pet_cake
import pet_traits


@dataclass(frozen=True)
class ReturnRules:
    revision: str
    templates: object
    insight_minimum: int
    insight_maximum: int

    @classmethod
    def load(cls):
        p=json.loads((OUT/'design/pet-super-return-v1.json').read_text(encoding='utf-8'))
        if (p['revision'],p['item_template'],p['draw_denominator'],p['insight_minimum'],p['insight_maximum'])!=('2026-10-23.pet-super-return.1',31576,10000,0,100):
            raise ValueError('Super-return policy requires review')
        items=json.loads((OUT/'catalogs/knight.gsp.item.citemattr.json').read_text(encoding='utf-8'))
        item=next(r['attributes'] for r in items if int(r['attributes']['id'])==31576)
        if tuple(int(item[k]) for k in ('itemtypeid','needLevel','outbattleuse'))!=(33,1,2):
            raise ValueError('Original super-return pill changed')
        pets=json.loads((OUT/'catalogs/knight.gsp.pet.cpetattr.json').read_text(encoding='utf-8'))
        templates={}
        for row in pets:
            a=row['attributes']
            ranges=tuple((int(a[n+'aptmin']),int(a[n+'aptmax'])) for n in ('attack','defend','phyforce','magic','speed'))
            growth=tuple(map(int,row['lists']['growrate']))
            if any(lo<0 or hi<lo for lo,hi in ranges) or not growth or min(growth)<500:continue
            templates[int(a['id'])]=(int(a['kind']),ranges,growth)
        return cls(p['revision'],MappingProxyType(templates),0,100)

    def roll(self,template,draws):
        if (template not in self.templates or type(draws) is not tuple or len(draws)!=7
                or any(type(v) is not int or not 0<=v<10000 for v in draws)):
            raise ValueError('Seven immutable captured server draws required')
        kind,ranges,growth=self.templates[template]
        aptitudes=tuple(lo+d*(hi-lo+1)//10000 for (lo,hi),d in zip(ranges,draws))
        return Profile(template,growth[draws[5]*len(growth)//10000],aptitudes),draws[6]*101//10000


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    pet_id: int
    profile: Profile
    display_aptitudes: tuple
    insight: int
    score: int
    baseline: str

    def message(self):
        return super_return_preview_message(self.pet_id,self.display_aptitudes,self.insight,self.profile.growth_raw,self.score)


@dataclass(frozen=True)
class ReturnReceipt:
    request_id: str
    action: str
    pet_id: int
    candidate: object
    replayed: bool=False


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_return_candidates(
        pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),role_id INTEGER NOT NULL REFERENCES roles(id),
        policy TEXT NOT NULL,candidate TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS inventory_pet_return_receipts(
        role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,fingerprint TEXT NOT NULL,
        result TEXT NOT NULL,PRIMARY KEY(role_id,request_id));''')


def _encode(candidate):return asdict(candidate) if candidate is not None else None


def _decode(value):
    if value is None:return None
    p=dict(value['profile']);p['aptitudes']=tuple(p['aptitudes'])
    return Candidate(**dict(value,profile=Profile(**p),display_aptitudes=tuple(value['display_aptitudes'])))


def pending(db,inv,pet):
    if inv.read_pet_state(db,pet) is None:raise ValueError('Owned live pet required for pending return')
    row=db.execute('SELECT policy,candidate FROM inventory_pet_return_candidates WHERE pet_id=? AND role_id=?',(pet,inv.role_id)).fetchone()
    if row and row[0]!=inv.return_rules.revision:raise ValueError('Pending return policy requires reconciliation')
    return _decode(json.loads(row[1])) if row else None


def _baseline(pet):
    return json.dumps([asdict(pet.progress.profile),asdict(pet.traits),asdict(pet.cake),
        asdict(pet.progress.blood),pet.care.grade,asdict(pet.evolution),asdict(pet.progress.stones)],sort_keys=True,separators=(',',':'))


def change(db,inv,pet,request_id,action,*,item_key=None,draws=None,expected_candidate=None):
    if (action not in ('preview','save','clear') or type(request_id) is not str or not 1<=len(request_id)<=160
            or type(pet) is not int or not 0<pet<=0x7fffffff
            or draws is not None and (type(draws) is not tuple or len(draws)!=7
                or any(type(v) is not int or not 0<=v<10000 for v in draws))
            or action=='preview' and (type(item_key) is not int or not 0<item_key<=0x7fffffff or expected_candidate is not None)
            or action!='preview' and (item_key is not None or draws is not None
                or not (action=='clear' and expected_candidate is None)
                and (type(expected_candidate) is not str or not 1<=len(expected_candidate)<=160))):
        raise ValueError('Stable accepted super-return command context required')
    intent=[pet,action,item_key,expected_candidate,inv.return_rules.revision]
    fingerprint=hashlib.sha256(json.dumps(intent).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result FROM inventory_pet_return_receipts WHERE role_id=? AND request_id=?',
        (inv.role_id,request_id)).fetchone()
    if old:
        value=json.loads(old[1])
        if old[0]!=fingerprint or draws is not None and list(draws)!=value['draws']:
            raise ValueError('Super-return command intent or captured draws conflict')
        return ReturnReceipt(request_id,action,pet,_decode(value['candidate']),True)
    current=inv.read_pet_state(db,pet)
    if current is None:raise ValueError('Owned live pet required for fresh return command')
    if action=='preview':
        if (current.fighting or current.progress is None or current.progress.blood is None or current.progress.stones is None or current.traits is None
                or not current.traits.baby or current.cake is None or current.skills is None or current.care is None
                or current.flags is None or current.skill_progress is None or current.skill_expiry is None or current.evolution is None
                or inv.return_rules.templates.get(current.template_id,(0,))[0] not in (1,3)):
            raise ValueError('Eligible nonfighting baby with known complete return state required')
        profile,insight=inv.return_rules.roll(current.template_id,draws)
        profile=replace(profile,growth_raw=profile.growth_raw+inv.evolution_rules.bonus(current.template_id,current.evolution)
            +inv.stone_rules.growth_per_stone*current.progress.stones.count)
        item=db.execute('SELECT quantity FROM inventory_items WHERE id=? AND role_id=? AND template_id=31576 AND equipment_slot IS NULL',
            (item_key,inv.role_id)).fetchone()
        role=db.execute('SELECT level FROM roles WHERE id=? AND account_id=?',(inv.role_id,inv.account_id)).fetchone()
        if not item or not role or role[0]<1:raise ValueError('Owned carried super-return pill and item level required')
        effective=pet_growth_store.effective_profile(profile,inv.growth_rules,inv.blood_rules,current.progress.blood,current.progress.stones)
        score=inv.score_rules.project(current.template_id,effective.aptitudes,profile.growth_raw,insight,
            current.skills.learned,current.progress.blood.level,evolution_stage=current.evolution.stage)
        candidate=Candidate(request_id,pet,profile,effective.aptitudes,insight,score,_baseline(current))
        candidate.message() # validate original wire before spending
        if item[0]==1:db.execute('DELETE FROM inventory_items WHERE id=? AND role_id=?',(item_key,inv.role_id))
        else:db.execute('UPDATE inventory_items SET quantity=quantity-1 WHERE id=? AND role_id=?',(item_key,inv.role_id))
        db.execute('INSERT INTO inventory_pet_return_candidates VALUES(?,?,?,?) ON CONFLICT(pet_id) DO UPDATE SET policy=excluded.policy,candidate=excluded.candidate',
            (pet,inv.role_id,inv.return_rules.revision,json.dumps(_encode(candidate))))
    else:
        candidate=pending(db,inv,pet)
        if (candidate is None and (action!='clear' or expected_candidate is not None)
                or candidate is not None and candidate.candidate_id!=expected_candidate):
            raise ValueError('Captured pending candidate was cleared, saved or replaced')
        if action=='save':
            if (current.fighting or current.progress is None or current.progress.blood is None or current.progress.stones is None
                    or current.traits is None or current.cake is None or current.care is None or current.evolution is None
                    or _baseline(current)!=candidate.baseline):
                raise ValueError('Return source fields changed; generate a fresh candidate')
            before=current.progress
            if not (0<=before.state.hp<=before.attributes.max_hp and 0<=before.state.mp<=before.attributes.max_mp
                    and type(before.state.version) is int and 0<=before.state.version<0x7fffffff):
                raise ValueError('Known current resources and representable growth version required')
            planned=pet_growth_store._project(inv.role_id,pet,candidate.profile,before.state,
                inv.growth_rules,inv.blood_rules,before.blood,before.stones)
            state=replace(before.state,version=before.state.version+1,
                hp=min(before.state.hp,planned.attributes.max_hp),mp=min(before.state.mp,planned.attributes.max_mp))
            old_growth=db.execute('SELECT profile,state FROM inventory_pet_growth WHERE pet_id=?',(pet,)).fetchone()
            if db.execute('UPDATE inventory_pet_growth SET profile=?,state=? WHERE pet_id=? AND revision=? AND profile=? AND state=?',
                    (json.dumps(asdict(candidate.profile)),json.dumps(asdict(state)),pet,inv.growth_rules.revision,
                     old_growth[0],old_growth[1])).rowcount!=1:raise ValueError('Growth source changed during return save')
            traits=replace(current.traits,version=current.traits.version+1,insight=candidate.insight)
            old_traits=db.execute('SELECT state FROM inventory_pet_traits WHERE pet_id=?',(pet,)).fetchone()
            if db.execute('UPDATE inventory_pet_traits SET state=? WHERE pet_id=? AND policy=? AND state=?',
                    (json.dumps(asdict(traits)),pet,inv.trait_rules.revision,old_traits[0])).rowcount!=1:
                raise ValueError('Insight source changed during return save')
            pet_cake.reset(db,inv.account_id,inv.role_id,pet,inv.cake_rules,current.cake)
            pet_cake._revision(db,inv.role_id)
        if candidate is not None and db.execute('DELETE FROM inventory_pet_return_candidates WHERE pet_id=? AND role_id=? AND candidate=?',
                (pet,inv.role_id,json.dumps(_encode(candidate)))).rowcount!=1:
            raise ValueError('Pending candidate changed during return commit')
    result={'candidate':_encode(candidate),'draws':list(draws) if draws is not None else None}
    db.execute('INSERT INTO inventory_pet_return_receipts VALUES(?,?,?,?)',(inv.role_id,request_id,fingerprint,json.dumps(result)))
    return ReturnReceipt(request_id,action,pet,candidate)
