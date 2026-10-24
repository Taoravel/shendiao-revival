"""Known evolution metadata and ordinary stage/material plans in owner transactions."""
from dataclasses import dataclass,asdict,replace
from types import MappingProxyType
import hashlib
import json
from inspect_client import OUT
import pet_traits
import pet_growth_store


@dataclass(frozen=True)
class PetEvolution:
    version: int
    stage: int

    def __post_init__(self):
        if (type(self.version) is not int or not 0<=self.version<=0x7fffffff
                or type(self.stage) is not int or not 0<=self.stage<=56):
            raise ValueError('Known representable evolution version/stage required')


@dataclass(frozen=True)
class EvolutionPlan:
    stage: int
    growth_gain: int
    costs: tuple
    shape: int


@dataclass(frozen=True)
class EvolutionRules:
    revision: str
    templates: object
    finals: tuple
    labels: tuple

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/pet-evolution-v1.json').read_text(encoding='utf-8'))
        if policy['revision']!='2026-10-24.pet-evolution.1':raise ValueError('Evolution policy requires review')
        def rows(name):return json.loads((OUT/f'catalogs/knight.gsp.{name}.json').read_text(encoding='utf-8'))
        kinds={int(r['attributes']['id']):int(r['attributes']['kind']) for r in rows('pet.cpetattr')}
        templates={}
        for r in rows('pet.cpetevolution'):
            template=int(r['attributes']['id']);levels,counts,shapes=(tuple(map(int,r['lists'][n])) for n in ('needlevel','needitemnum','shape'))
            if any(len(v)!=7 for v in (levels,counts,shapes)) or levels[0]!=0 or min(counts)<0 or min(shapes)<0:
                raise ValueError('Original evolution table shape changed')
            cap=levels.index(-1)-1 if levels[-1]==-1 else 6
            templates[template]=(kinds[template],levels,counts,shapes,cap)
        final=rows('pet.cpetfinal')
        if tuple(int(r['attributes']['id']) for r in final)!=tuple(range(1,51)):
            raise ValueError('Original final progression index changed')
        finals=tuple((int(r['attributes']['gaoji']),int(r['attributes']['zhongji'])) for r in final)
        if any(min(pair)<=0 for pair in finals):raise ValueError('Known positive final costs required')
        strings={int(r['attributes']['id']):r['attributes']['msg'] for r in rows('message.cstringres')}
        return cls(policy['revision'],MappingProxyType(templates),finals,tuple(strings[2485+i] for i in range(7)))

    def bonus(self,template,state):
        if type(state) is not PetEvolution or template not in self.templates:
            raise ValueError('Known ordinary evolution source required')
        if state.stage==0:return 0
        kind,levels,counts,shapes,cap=self.templates[template]
        stages=tuple(i for i in range(1,cap+1) if levels[i]>0 and shapes[i]>0)
        if (kind not in (1,3) or state.stage not in (*stages,*range(cap+1,cap+51))
                or not shapes[cap]):raise ValueError('Unknown special or invalid evolution state')
        return 5*sum(i<=state.stage for i in stages)+max(0,state.stage-cap)

    def plan(self,template,state,level):
        self.bonus(template,state)
        if type(level) is not int or not 0<=level<=150:raise ValueError('Current pet level required')
        kind,levels,counts,shapes,cap=self.templates[template]
        if kind not in (1,3):raise ValueError('Special god evolution is not ordinary progression')
        if state.stage>=cap:
            index=state.stage-cap+1
            if index>50:raise ValueError('Original final evolution limit reached')
            a,b=self.finals[index-1]
            return EvolutionPlan(state.stage+1,1,((31228,a),(31229,b)),shapes[cap])
        target=state.stage+1
        if levels[target]<=0:target=6
        if target>cap or levels[target]<=0 or shapes[target]<=0 or counts[target]<=0 or level<levels[target]:
            raise ValueError('Original next evolution level/stage requirement unmet')
        item=31227 if target<=2 else 31228 if target<6 else 31229
        return EvolutionPlan(target,5,((item,counts[target]),),shapes[target])


@dataclass(frozen=True)
class EvolutionReceipt:
    request_id: str
    pet_id: int
    before: PetEvolution
    after: PetEvolution
    growth_before: int
    growth_after: int
    debits: tuple
    policy: str
    replayed: bool=False


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_evolution(
        pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),policy TEXT NOT NULL,
        source TEXT NOT NULL,state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS inventory_pet_evolution_receipts(
        role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(role_id,request_id));''')


def initialize(db,account,role,pet,rules,stage,*,source):
    pet_traits._owned(db,account,role,pet)
    template=db.execute('SELECT template_id FROM inventory_pets WHERE id=?',(pet,)).fetchone()[0]
    state=PetEvolution(0,stage);rules.bonus(template,state)
    if source not in ('new_restoration_pet','explicit_known_import'):
        raise ValueError('Explicit complete evolution source required')
    if db.execute('SELECT 1 FROM inventory_pet_evolution WHERE pet_id=?',(pet,)).fetchone():
        raise ValueError('Evolution state cannot be initialized twice')
    db.execute('INSERT INTO inventory_pet_evolution VALUES(?,?,?,?)',(pet,rules.revision,source,json.dumps(asdict(state))))
    _revision(db,role)
    return state


def load(db,account,role,pet,rules):
    pet_traits._owned(db,account,role,pet)
    row=db.execute('SELECT policy,source,state FROM inventory_pet_evolution WHERE pet_id=?',(pet,)).fetchone()
    if not row or row[0]!=rules.revision or row[1] not in ('new_restoration_pet','explicit_known_import'):
        raise ValueError('Unknown evolution requires explicit reconciliation')
    state=PetEvolution(**json.loads(row[2]))
    template=db.execute('SELECT template_id FROM inventory_pets WHERE id=?',(pet,)).fetchone()[0]
    rules.bonus(template,state)
    return state


def _revision(db,role):
    db.execute('INSERT INTO inventory_versions VALUES(?,1) ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))


def change(db,inv,pet,request_id,expected_version):
    if (type(pet) is not int or not 0<pet<=0x7fffffff or type(request_id) is not str or not 1<=len(request_id)<=160
            or expected_version is not None and (type(expected_version) is not int or not 0<=expected_version<0x7fffffff)):
        raise ValueError('Stable admitted evolution identity/version required')
    rules=inv.evolution_rules
    fingerprint=hashlib.sha256(json.dumps([pet,expected_version,rules.revision,inv.growth_rules.revision,inv.blood_rules.revision]).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result FROM inventory_pet_evolution_receipts WHERE role_id=? AND request_id=?',(inv.role_id,request_id)).fetchone()
    if old:
        if old[0]!=fingerprint:raise ValueError('Evolution intent conflict')
        value=json.loads(old[1])
        for n in ('before','after'):value[n]=PetEvolution(**value[n])
        value['debits']=tuple(tuple(row) for row in value['debits'])
        return EvolutionReceipt(**value,replayed=True)
    current=inv.read_pet_state(db,pet)
    if (current is None or current.fighting or any(v is None for v in (current.progress,current.care,current.traits,
            current.skills,current.flags,current.skill_expiry,current.skill_progress,current.cake,current.evolution))
            or not current.traits.baby or current.progress.blood is None or current.progress.stones is None
            or not 0<=current.progress.state.version<0x7fffffff
            or expected_version is not None and expected_version!=current.progress.state.version):
        raise ValueError('Nonfighting known ordinary baby evolution state required')
    before=current.progress;plan=rules.plan(current.template_id,current.evolution,before.state.level)
    debits=[]
    for template,needed in plan.costs:
        rows=db.execute('SELECT id,quantity,binding FROM inventory_items WHERE role_id=? AND template_id=? AND equipment_slot IS NULL ORDER BY binding DESC,id',
            (inv.role_id,template)).fetchall()
        if sum(r[1] for r in rows)<needed:raise ValueError('Insufficient original evolution materials')
        for key,count,binding in rows:
            take=min(needed,count)
            if take:debits.append((key,take,binding));needed-=take
            if not needed:break
    profile=replace(before.profile,growth_raw=before.profile.growth_raw+plan.growth_gain)
    state=replace(before.state,version=before.state.version+1)
    after=pet_growth_store._project(inv.role_id,pet,profile,state,inv.growth_rules,inv.blood_rules,before.blood,before.stones)
    if (not 0<=state.hp<=before.attributes.max_hp or not 0<=state.mp<=before.attributes.max_mp
            or after.attributes.max_hp<before.attributes.max_hp or after.attributes.max_mp<before.attributes.max_mp):
        raise ValueError('Valid current resources/nondecreasing evolution caps required')
    evolution=PetEvolution(current.evolution.version+1,plan.stage)
    old_growth=db.execute('SELECT profile,state FROM inventory_pet_growth WHERE pet_id=? AND revision=?',(pet,inv.growth_rules.revision)).fetchone()
    old_evolution=db.execute('SELECT state FROM inventory_pet_evolution WHERE pet_id=? AND policy=?',(pet,rules.revision)).fetchone()
    if db.execute('UPDATE inventory_pet_growth SET profile=?,state=? WHERE pet_id=? AND revision=? AND profile=? AND state=?',
            (json.dumps(asdict(profile)),json.dumps(asdict(state)),pet,inv.growth_rules.revision,*old_growth)).rowcount!=1:
        raise ValueError('Evolution growth source changed')
    if db.execute('UPDATE inventory_pet_evolution SET state=? WHERE pet_id=? AND policy=? AND state=?',
            (json.dumps(asdict(evolution)),pet,rules.revision,old_evolution[0])).rowcount!=1:raise ValueError('Evolution source changed')
    for key,take,binding in debits:inv._consume_item(db,key,take)
    _revision(db,inv.role_id)
    receipt=EvolutionReceipt(request_id,pet,current.evolution,evolution,before.profile.growth_raw,profile.growth_raw,tuple(debits),rules.revision)
    value=asdict(receipt);value.pop('replayed')
    db.execute('INSERT INTO inventory_pet_evolution_receipts VALUES(?,?,?,?)',(inv.role_id,request_id,fingerprint,json.dumps(value)))
    return receipt
