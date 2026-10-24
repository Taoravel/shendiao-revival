"""Full ordinary rebirth at the existing fenced role transaction Seam."""
from dataclasses import dataclass,asdict,replace
from types import MappingProxyType
import hashlib
import json
from inspect_client import OUT
from pet_growth import PetGrowth
from pet_care import PetCare
from pet_traits import PetTraits
from pet_skills import PetSkills
from pet_skill_progress import SkillProgress
from pet_skill_expiry import SkillExpiry
from pet_cake import PetCakeHistory
from pet_blood import PetBlood
import pet_growth_store
import pet_battle_care
import pet_care


@dataclass(frozen=True)
class OrdinaryRules:
    revision: str
    templates: object
    weights: tuple
    guaranteed: object

    @classmethod
    def load(cls):
        p=json.loads((OUT/'design/pet-ordinary-return-v1.json').read_text(encoding='utf-8'))
        if (p['revision'],p['item_templates'],p['template_uselevel_boundary'],p['draw_count'],p['draw_denominator'],
                p['wild_grade_weights'])!=('2026-10-23.pet-ordinary-return.1',[31002,31087],95,15,10000,[6000,2500,1000,400,90,10]):
            raise ValueError('Ordinary rebirth policy requires review')
        def catalog(name):return json.loads((OUT/f'catalogs/knight.gsp.{name}.json').read_text(encoding='utf-8'))
        pets={int(r['attributes']['id']):r for r in catalog('pet.cpetattr')}
        battle={int(r['attributes']['id']):int(r['attributes']['battlelevel']) for r in catalog('pet.cpetnamebattlelevelconfig')}
        items={int(r['attributes']['id']):r['attributes'] for r in catalog('item.citemattr')}
        for key in (31002,31087):
            if tuple(int(items[key][n]) for n in ('itemtypeid','needLevel','outbattleuse'))!=(33,1,2):
                raise ValueError('Original ordinary pill data changed')
        templates={}
        for key,row in pets.items():
            a=row['attributes'];kind,uselevel,life=(int(a[n]) for n in ('kind','uselevel','life'))
            if battle.get(key)!=uselevel or kind not in (1,2,3) or not 0<=life<=0x7fffffff:
                raise ValueError('Original pet template/battle-level fields require review')
            candidates=tuple(dict.fromkeys(int(v) for v in row['lists']['skillid'] if int(v)>0))
            if not 1<=len(candidates)<=6:raise ValueError('Original ordinary skill candidates require review')
            templates[key]=(kind,uselevel,life,candidates)
        npc={int(r['attributes']['id']):r['attributes'].get('servicedescribe','') for r in catalog('npc.cnpcserverconfig')}
        skills={int(r['attributes']['id']):r['attributes']['skillname'] for r in catalog('skill.cpetskillconfig')}
        guaranteed={}
        for source,template,skill in p['guaranteed_skill_sources']:
            if (template in guaranteed or templates[template][0]!=3 or skill not in templates[template][3]
                    or '还童' not in npc[source] or skills[skill] not in npc[source]):
                raise ValueError('Original ordinary guaranteed skill text/mapping requires review')
            guaranteed[template]=skill
        if len(guaranteed)!=13:raise ValueError('Ordinary guaranteed species policy requires review')
        return cls(p['revision'],MappingProxyType(templates),tuple(p['wild_grade_weights']),MappingProxyType(guaranteed))

    def validate_draws(self,draws):
        if type(draws) is not tuple or len(draws)!=15 or any(type(v) is not int or not 0<=v<10000 for v in draws):
            raise ValueError('Fifteen immutable captured server draws required')

    def grade(self,draw):
        if type(draw) is not int or not 0<=draw<10000:raise ValueError('Captured ordinary colour draw required')
        total=0
        for grade,weight in enumerate(self.weights,1):
            total+=weight
            if draw<total:return grade
        raise ValueError('Ordinary colour draw out of range')

    def skills(self,template,grade,draws,skill_rules):
        self.validate_draws(draws)
        candidates=list(self.templates[template][3]);required=self.guaranteed.get(template)
        selected=[required] if required is not None else []
        if required is not None:candidates.remove(required)
        cap=min(len(self.templates[template][3]),skill_rules.caps[grade]);minimum=len(selected)
        count=minimum+draws[8]*(cap-minimum+1)//10000
        for draw in draws[9:9+count-minimum]:selected.append(candidates.pop(draw*len(candidates)//10000))
        return tuple(selected)


@dataclass(frozen=True)
class OrdinaryReceipt:
    request_id: str
    pet_id: int
    item_key: int
    item_template: int
    source_origin: int
    draws: tuple
    policy: str
    replayed: bool=False


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_ordinary_return_receipts(
        role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(role_id,request_id));''')


def _cas(db,pet,table,policy_column,policy,before_raw,after):
    if db.execute(f'UPDATE {table} SET state=? WHERE pet_id=? AND {policy_column}=? AND state=?',
            (json.dumps(asdict(after)),pet,policy,before_raw)).rowcount!=1:
        raise ValueError('Ordinary return source changed: '+table)


def change(db,inv,pet,key,request_id,draws,expected_version):
    rules=inv.ordinary_return_rules
    if (type(pet) is not int or not 0<pet<=0x7fffffff or type(key) is not int or not 0<key<=0x7fffffff
            or type(request_id) is not str or not 1<=len(request_id)<=160
            or expected_version is not None and (type(expected_version) is not int or not 0<=expected_version<2**63)):
        raise ValueError('Owned pet/item and stable ordinary-return context required')
    if draws is not None:rules.validate_draws(draws)
    fingerprint=hashlib.sha256(json.dumps([pet,key,expected_version,rules.revision,inv.return_rules.revision]).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result FROM inventory_pet_ordinary_return_receipts WHERE role_id=? AND request_id=?',
        (inv.role_id,request_id)).fetchone()
    if old:
        value=json.loads(old[1]);receipt=value['receipt'];receipt['draws']=tuple(receipt['draws'])
        if old[0]!=fingerprint or draws is not None and draws!=receipt['draws']:
            raise ValueError('Ordinary-return intent or captured draws conflict')
        return OrdinaryReceipt(**receipt,replayed=True)
    rules.validate_draws(draws)
    current=inv.read_pet_state(db,pet)
    if (current is None or current.fighting or any(v is None for v in (
            current.progress,current.care,current.traits,current.skills,current.flags,current.skill_progress,current.skill_expiry,current.cake,current.evolution))
            or current.progress.blood is None or current.progress.stones is None or current.progress.profile.template_id!=current.template_id
            or not 0<=current.progress.state.hp<=current.progress.attributes.max_hp
            or not 0<=current.progress.state.mp<=current.progress.attributes.max_mp
            or type(current.progress.state.version) is not int or not 0<=current.progress.state.version<0x7fffffff
            or expected_version is not None and expected_version!=current.progress.state.version):
        raise ValueError('Nonfighting pet with known complete rebirth state required')
    counter=pet_battle_care.load(db,inv.account_id,inv.role_id,pet,inv.battle_care_rules)
    item=db.execute('SELECT template_id,quantity FROM inventory_items WHERE id=? AND role_id=? AND equipment_slot IS NULL',
        (key,inv.role_id)).fetchone()
    template=current.template_id;kind,uselevel,life,candidates=rules.templates[template]
    required=31087 if uselevel>=95 else 31002
    role=db.execute('SELECT level FROM roles WHERE id=? AND account_id=?',(inv.role_id,inv.account_id)).fetchone()
    if not item or item[0]!=required or not role or role[0]<1:
        raise ValueError('Original template-uselevel95 pill and role item level required')
    profile,insight=inv.return_rules.roll(template,draws[:7])
    profile=replace(profile,growth_raw=profile.growth_raw+inv.evolution_rules.bonus(template,current.evolution)
        +inv.stone_rules.growth_per_stone*current.progress.stones.count)
    baby=current.traits.baby
    grade=current.care.grade if baby else rules.grade(draws[7])
    blood=current.progress.blood if baby else inv.blood_rules.progress(PetBlood(current.progress.blood.state.version+1,0),grade)
    care=inv.care_rules.validate(PetCare(current.care.version+1,grade,inv.care_rules.maximum(grade),life))
    traits=PetTraits(current.traits.version+1,2,insight)
    skills=inv.skill_rules.validate(PetSkills(current.skills.version+1,rules.skills(template,grade,draws,inv.skill_rules)),grade)
    expiry=SkillExpiry(current.skill_expiry.version+1,())
    progress=SkillProgress(current.skill_progress.version+1,0)
    cake=PetCakeHistory(current.cake.version+1,0,(0,)*5)
    meter=pet_battle_care.BattleCareCounter(counter.version+1,0)
    # Rebirth has its own explicit resources policy, independent of ordinary XP healing.
    zero=PetGrowth(current.progress.state.version+1,0,0,(0,)*5,0,0)
    planned=pet_growth_store._project(inv.role_id,pet,profile,zero,inv.growth_rules,inv.blood_rules,blood,current.progress.stones)
    state=replace(zero,hp=planned.attributes.max_hp,mp=planned.attributes.max_mp)
    sources=(('inventory_pet_care','revision',inv.care_rules.revision,care),
        ('inventory_pet_traits','policy',inv.trait_rules.revision,traits),
        ('inventory_pet_skills','policy',inv.skill_rules.revision,skills),
        ('inventory_pet_skill_expiry','policy',inv.skill_rules.expiry_rules.revision,expiry),
        ('inventory_pet_skill_progress','policy',inv.skill_rules.learning_rules.revision,progress),
        ('inventory_pet_cakes','policy',inv.cake_rules.revision,cake))
    captured=[]
    for table,column,policy,after in sources:
        row=db.execute(f'SELECT state FROM {table} WHERE pet_id=? AND {column}=?',(pet,policy)).fetchone()
        if not row:raise ValueError('Complete ordinary-return source missing')
        captured.append((table,column,policy,row[0],after))
    old_growth=db.execute('SELECT profile,state FROM inventory_pet_growth WHERE pet_id=? AND revision=?',
        (pet,inv.growth_rules.revision)).fetchone()
    old_blood=db.execute('SELECT state FROM inventory_pet_blood WHERE pet_id=? AND policy=?',(pet,inv.blood_rules.revision)).fetchone()
    before={'profile':asdict(current.progress.profile),'growth':asdict(current.progress.state),
        'blood':asdict(current.progress.blood),'care':asdict(current.care),'traits':asdict(current.traits),
        'skills':asdict(current.skills),'expiry':asdict(current.skill_expiry),'progress':asdict(current.skill_progress),
        'cake':asdict(current.cake),'counter':asdict(counter),'flags_preserved':asdict(current.flags),
        'evolution_preserved':asdict(current.evolution),'stones_preserved':asdict(current.progress.stones)}
    if db.execute('UPDATE inventory_pet_growth SET profile=?,state=? WHERE pet_id=? AND revision=? AND profile=? AND state=?',
            (json.dumps(asdict(profile)),json.dumps(asdict(state)),pet,inv.growth_rules.revision,old_growth[0],old_growth[1])).rowcount!=1:
        raise ValueError('Ordinary return growth source changed')
    for table,column,policy,raw,after in captured:_cas(db,pet,table,column,policy,raw,after)
    if not baby:_cas(db,pet,'inventory_pet_blood','policy',inv.blood_rules.revision,old_blood[0],blood.state)
    if db.execute('UPDATE inventory_pet_battle_care SET version=?,mod3=0 WHERE pet_id=? AND revision=? AND version=? AND mod3=?',
            (meter.version,pet,inv.battle_care_rules.revision,counter.version,counter.mod3)).rowcount!=1:
        raise ValueError('Ordinary return battle counter changed')
    db.execute('DELETE FROM inventory_pet_return_candidates WHERE pet_id=? AND role_id=?',(pet,inv.role_id))
    if item[1]==1:db.execute('DELETE FROM inventory_items WHERE id=? AND role_id=?',(key,inv.role_id))
    else:db.execute('UPDATE inventory_items SET quantity=quantity-1 WHERE id=? AND role_id=?',(key,inv.role_id))
    pet_care._revision(db,inv.role_id)
    receipt=OrdinaryReceipt(request_id,pet,key,item[0],current.traits.origin,draws,rules.revision)
    value=asdict(receipt);value.pop('replayed')
    db.execute('INSERT INTO inventory_pet_ordinary_return_receipts VALUES(?,?,?,?)',
        (inv.role_id,request_id,fingerprint,json.dumps({'receipt':value,'before':before,
         'after_profile':asdict(profile),'after_grade':grade,'after_skills':asdict(skills),'after_insight':insight})))
    return receipt
