"""Versioned learned pet IDs and atomic ordinary skill-book persistence.

This Module stores exact IDs, not invented numeric skill levels or battle
effects. The Inventory Interface supplies current care inside the same role
transaction and handles logical notification after representation is checked.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from types import MappingProxyType

from inspect_client import OUT
import pet_flags
import pet_skill_progress
import pet_skill_expiry
from pet_protocol import SkillBookOptions


@dataclass(frozen=True)
class PetSkills:
    version: int
    learned: tuple

    def __post_init__(self):
        if (type(self.version) is not int or not 0<=self.version<0x7fffffff
                or type(self.learned) is not tuple or len(self.learned)>12
                or any(type(v) is not int or not 0<v<=0x7fffffff for v in self.learned)
                or len(set(v for v in self.learned if v!=pet_skill_expiry.EMPTY_SKILL_ID))
                   !=sum(v!=pet_skill_expiry.EMPTY_SKILL_ID for v in self.learned)):
            raise ValueError('Invalid known pet skill state')


@dataclass(frozen=True)
class SkillRules:
    revision: str
    skills: object
    presets: object
    books: object
    caps: object
    initial_count: int
    learning_rules: object
    expiry_rules: object

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/pet-skills-v1.json').read_text(encoding='utf-8'))
        generation=policy['generation']
        if policy['revision']!='2026-10-23.pet-skills.1' or generation['maximum_initial_skills']!=2:
            raise ValueError('Pet skill policy requires implementation review')
        def rows(name):
            return json.loads((OUT/('catalogs/knight.gsp.'+name+'.json')).read_text(encoding='utf-8'))
        skills={int(r['attributes']['id']):MappingProxyType(dict(r['attributes'])) for r in rows('skill.cpetskillconfig')}
        presets={}
        for row in rows('pet.cpetattr'):
            source=tuple(dict.fromkeys(int(v) for v in row['lists'].get('skillid',()) if int(v)>0))
            if any(key not in skills for key in source):
                raise ValueError('Original pet skill candidate is unknown')
            presets[int(row['attributes']['id'])]=source
        items={int(r['attributes']['id']):r['attributes'] for r in rows('item.citemattr')}
        books={}
        for row in rows('item.cpetitemeffect'):
            attr=row['attributes'];key=int(attr['id']);skill=int(attr.get('petskillid',0))
            if not skill:continue
            item=items[key]
            if skill not in skills or int(item['itemtypeid'])!=49:
                continue  # Other skill-granting item types need their own action.
            definition=skills[skill]
            declared={int(definition.get('itemid',0)),int(definition.get('canbenid',0))}-{0}
            if declared and key not in declared:
                raise ValueError('Original pet book mapping disagrees with skill definition')
            books[key]=(skill,int(attr.get('petbangding',0)),int(item.get('needLevel',0)))
        caps={int(r['attributes']['id']):int(r['attributes']['skillnumber']) for r in rows('pet.cpetxuemaiconfig')}
        if caps!={1:4,2:4,3:6,4:8,5:10,6:12}:
            raise ValueError('Original pet color skill caps require review')
        return cls(policy['revision'],MappingProxyType(skills),MappingProxyType(presets),
                   MappingProxyType(books),MappingProxyType(caps),generation['maximum_initial_skills'],
                   pet_skill_progress.LearningRules.load(),pet_skill_expiry.ExpiryRules.load())

    def validate(self,state,grade):
        if (not isinstance(state,PetSkills) or type(grade) is not int or grade not in self.caps
                or len(state.learned)>self.caps[grade] or any(key not in self.skills for key in state.learned)):
            raise ValueError('Pet learned skills exceed known color or source definitions')
        return state

    def generate(self,template,grade):
        if template not in self.presets:
            raise ValueError('Unknown pet skill generation template')
        return self.validate(PetSkills(0,self.presets[template][:self.initial_count]),grade)

    def learn(self,state,grade,skill,draws):
        """Compatibility preview with zero progress and no certification.

        Stateful learning uses plan with the actual known progress. Keep one
        implementation of family, chance, replacement and protection decisions.
        """
        plan=self.plan(state,grade,skill,draws,pet_skill_progress.SkillProgress(0,0),SkillBookOptions())
        return plan.after,plan.replaced_skill_id

    def plan(self,state,grade,skill,draws,progress,options,*,expired_ids=()):
        """Current certification/pity learning; no storage or randomness here."""
        self.validate(state,grade)
        if (type(skill) is not int or skill not in self.skills or skill==pet_skill_expiry.EMPTY_SKILL_ID
                or type(expired_ids) is not tuple or len(set(expired_ids))!=len(expired_ids)
                or any(type(key) is not int or key not in state.learned for key in expired_ids)
                or type(draws) is not tuple or len(draws)!=2
                or any(type(v) is not int or not 0<=v<self.learning_rules.draw_upper_exclusive for v in draws)
                or not isinstance(progress,pet_skill_progress.SkillProgress)
                or not isinstance(options,SkillBookOptions)
                or any(v not in state.learned or v in expired_ids or v==pet_skill_expiry.EMPTY_SKILL_ID
                       for v in options.protected_ids)):
            raise ValueError('Known progress, trusted draws and current protected IDs required')
        if skill in state.learned and skill not in expired_ids:raise ValueError('Pet already knows this skill')
        if not state.learned and options.basic_key!=-1:
            raise ValueError('Empty learned list cannot use certification')
        learned=list(state.learned);protected=options.protected_ids
        vacant=[i for i,key in enumerate(learned) if key in expired_ids or key==pet_skill_expiry.EMPTY_SKILL_ID]
        family=[i for i,key in enumerate(learned) if i not in vacant and key//10==skill//10]
        replaced=None;points=progress.points;guaranteed=False
        rules=self.learning_rules
        if family:
            if (skill in expired_ids or len(family)!=1 or learned[family[0]]%10>=skill%10
                    or learned[family[0]] in protected):
                raise ValueError('Pet skill family conflict, weaker book or protected upgrade target')
            index=family[0];replaced=learned[index];learned[index]=skill
            outcome='upgraded'
        elif vacant:
            index=learned.index(skill) if skill in expired_ids else vacant[0]
            replaced=learned[index];learned[index]=skill;outcome='reused_empty'
        else:
            eligible=len(learned)<self.caps[grade]
            threshold=rules.thresholds[len(learned)]
            guaranteed=eligible and threshold>0 and points>=threshold
            mode='both' if options.advanced_key!=-1 else 'basic' if options.basic_key!=-1 else 'none'
            chance=rules.chances[mode][len(learned)] if len(learned)<12 else 0
            if not learned or eligible and (guaranteed or draws[0]<chance):
                learned.append(skill);points=0;outcome='expanded'
            else:
                candidates=[i for i,key in enumerate(learned) if key not in protected]
                if candidates:
                    index=candidates[draws[1]%len(candidates)]
                    replaced=learned[index];learned[index]=skill;outcome='replaced'
                else:outcome='protected_failure'
                if eligible and threshold>0:
                    gain=rules.base_gain+(rules.basic_gain if options.basic_key!=-1 else 0)
                    gain+=rules.advanced_gain if options.advanced_key!=-1 else 0
                    points=min(threshold,points+gain)
        after=self.validate(PetSkills(state.version+1,tuple(learned)),grade)
        return LearningPlan(after,replaced,points,outcome,guaranteed)


@dataclass(frozen=True)
class LearningPlan:
    after: PetSkills
    replaced_skill_id: object
    points: int
    outcome: str
    guaranteed: bool


@dataclass(frozen=True)
class SkillReceipt:
    settlement_id: str
    pet_id: int
    item_key: int
    skill_id: int
    replaced_skill_id: object
    before: PetSkills
    after: PetSkills
    flags_before: object = None
    flags_after: object = None
    progress_before: object = None
    progress_after: object = None
    protected_skill_ids: tuple = ()
    certificate_debits: tuple = ()
    outcome: str = 'learned'
    learning_revision: object = None
    guaranteed: bool = False
    expiry_before: object = None
    expiry_after: object = None
    applied_at_ms: object = None
    expiry_revision: object = None


def prepare(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS inventory_pet_skills (
            pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),
            policy TEXT NOT NULL,state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS inventory_pet_skill_receipts (
            role_id INTEGER NOT NULL REFERENCES roles(id),pet_id INTEGER NOT NULL REFERENCES inventory_pets(id),
            settlement_id TEXT NOT NULL,fingerprint TEXT NOT NULL,result TEXT NOT NULL,
            PRIMARY KEY(role_id,settlement_id));
    ''')
    pet_skill_progress.prepare(db)
    pet_skill_expiry.prepare(db)


def _owner(db,account,role,pet):
    if not db.in_transaction:
        raise ValueError('Pet skills require an owner transaction')
    row=db.execute('SELECT p.template_id FROM inventory_pets p JOIN roles r ON r.id=p.role_id '
        'WHERE p.id=? AND p.role_id=? AND r.account_id=? AND p.released=0',(pet,role,account)).fetchone()
    if not row:raise ValueError('Pet skill ownership mismatch')
    return row[0]


def _decode(data):
    record=json.loads(data);record['learned']=tuple(record['learned'])
    return PetSkills(**record)


def _revision(db,role):
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))


def initialize(db,account,role,pet,rules,state,grade):
    _owner(db,account,role,pet);rules.validate(state,grade)
    if state.version!=0 or db.execute('SELECT 1 FROM inventory_pet_skills WHERE pet_id=?',(pet,)).fetchone():
        raise ValueError('Pet skills cannot be reset')
    db.execute('INSERT INTO inventory_pet_skills VALUES(?,?,?)',(pet,rules.revision,json.dumps(asdict(state))))
    _revision(db,role)
    return state


def load(db,account,role,pet,rules,grade):
    _owner(db,account,role,pet)
    row=db.execute('SELECT policy,state FROM inventory_pet_skills WHERE pet_id=?',(pet,)).fetchone()
    if not row or row[0]!=rules.revision:
        raise ValueError('Pet skills require explicit known initialization or migration')
    return rules.validate(_decode(row[1]),grade)


def learn_book(db,account,role,pet,key,request_id,expected_version,draws,rules,grade,flag_rules=None,*,options=None,now_ms=None):
    """Internal Inventory adapter; its caller already checks current role lease."""
    _owner(db,account,role,pet)
    if now_ms is not None:pet_skill_expiry.require_time(now_ms)
    options=SkillBookOptions() if options is None else options
    if (type(key) is not int or not 0<key<=0x7fffffff or type(request_id) is not str or not 1<=len(request_id)<=160
            or expected_version is not None and (type(expected_version) is not int or expected_version<0)
            or type(draws) is not tuple or len(draws)!=2
            or any(type(v) is not int or not 0<=v<rules.learning_rules.draw_upper_exclusive for v in draws)
            or not isinstance(options,SkillBookOptions)
            or key in (options.basic_key,options.advanced_key)):
        raise ValueError('Invalid pet skill command context')
    legacy_fingerprint=hashlib.sha256(json.dumps([pet,key,expected_version,draws,rules.revision]).encode()).hexdigest()
    previous_fingerprint=hashlib.sha256(json.dumps([pet,key,expected_version,draws,rules.revision,
        rules.learning_rules.revision,options.wire_values]).encode()).hexdigest()
    fingerprint=hashlib.sha256(json.dumps([pet,key,expected_version,draws,rules.revision,
        rules.learning_rules.revision,options.wire_values,rules.expiry_rules.revision]).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result FROM inventory_pet_skill_receipts WHERE role_id=? AND settlement_id=?',
                   (role,request_id)).fetchone()
    if old:
        value=json.loads(old[1])
        if (old[0]!=fingerprint
                and not ('expiry_revision' not in value and old[0]==previous_fingerprint)
                and not (options==SkillBookOptions() and 'learning_revision' not in value
                    and old[0]==legacy_fingerprint)):
            raise ValueError('Pet skill request intent conflict')
        value['before']=_decode(json.dumps(value['before']));value['after']=_decode(json.dumps(value['after']))
        for field in ('flags_before','flags_after'):
            if value.get(field) is not None:value[field]=pet_flags.PetFlags(**value[field])
        for field in ('progress_before','progress_after'):
            if value.get(field) is not None:value[field]=pet_skill_progress.SkillProgress(**value[field])
        for field in ('expiry_before','expiry_after'):
            if value.get(field) is not None:value[field]=pet_skill_expiry.decode(value[field])
        value['protected_skill_ids']=tuple(value.get('protected_skill_ids',()))
        value['certificate_debits']=tuple(tuple(v) for v in value.get('certificate_debits',()))
        return SkillReceipt(**value)
    before=load(db,account,role,pet,rules,grade)
    if expected_version is not None and before.version!=expected_version:
        raise ValueError('Pet skill version mismatch')
    expiry_before=pet_skill_expiry.load(db,account,role,pet,rules.expiry_rules,before)
    if expiry_before.entries and now_ms is None:
        raise ValueError('Timed learned skills require trusted current server milliseconds')
    expired_ids=pet_skill_expiry.view(before,expiry_before,now_ms).expired_ids if now_ms is not None else ()
    item=db.execute('SELECT i.template_id,i.quantity,r.level FROM inventory_items i JOIN roles r ON r.id=i.role_id '
        'WHERE i.id=? AND i.role_id=? AND i.equipment_slot IS NULL',(key,role)).fetchone()
    book=rules.books.get(item[0]) if item else None
    if not book or item[2]<book[2]:raise ValueError('Owned carried skill book and role level required')
    if book[1] not in (0,1):raise ValueError('Unknown book pet-binding mode')
    progress_before=pet_skill_progress.load(db,account,role,pet,rules.learning_rules)
    certificates=[]
    for cert_key,template,level in ((options.basic_key,rules.learning_rules.basic_template,rules.learning_rules.basic_level),
                                  (options.advanced_key,rules.learning_rules.advanced_template,rules.learning_rules.advanced_level)):
        if cert_key==-1:continue
        cert=db.execute('SELECT template_id,quantity FROM inventory_items '
            'WHERE id=? AND role_id=? AND equipment_slot IS NULL',(cert_key,role)).fetchone()
        if not cert or cert[0]!=template or item[2]<level:
            raise ValueError('Owned carried certification instance of correct type/level required')
        certificates.append((cert_key,template,1))
    plan=rules.plan(before,grade,book[0],draws,progress_before,options,expired_ids=expired_ids)
    after,replaced=plan.after,plan.replaced_skill_id
    flags_before=flags_after=None
    if book[1]:
        if flag_rules is None:raise ValueError('Binding book requires prepared pet flag rules')
        pet_flags.load(db,account,role,pet,flag_rules)
        if plan.outcome!='protected_failure':
            flags_before,flags_after=pet_flags.bind_for_learning(db,account,role,pet,flag_rules)
    for debit in (key,)+(tuple(row[0] for row in certificates)):
        quantity=db.execute('SELECT quantity FROM inventory_items WHERE id=? AND role_id=?',(debit,role)).fetchone()[0]
        if quantity==1:db.execute('DELETE FROM inventory_items WHERE id=?',(debit,))
        else:db.execute('UPDATE inventory_items SET quantity=quantity-1 WHERE id=?',(debit,))
    db.execute('UPDATE inventory_pet_skills SET state=? WHERE pet_id=?',(json.dumps(asdict(after)),pet))
    progress_after=pet_skill_progress.save(db,account,role,pet,rules.learning_rules,progress_before,plan.points)
    entries=expiry_before.entries if plan.outcome=='protected_failure' else tuple(
        row for row in expiry_before.entries if row[0] not in (replaced,book[0]))
    expiry_after=pet_skill_expiry.save(db,account,role,pet,rules.expiry_rules,
        expiry_before,before,after,entries)
    receipt=SkillReceipt(request_id,pet,key,book[0],replaced,before,after,flags_before,flags_after,
        progress_before,progress_after,options.protected_ids,tuple(certificates),plan.outcome,
        rules.learning_rules.revision,plan.guaranteed,expiry_before,expiry_after,now_ms,rules.expiry_rules.revision)
    db.execute('INSERT INTO inventory_pet_skill_receipts VALUES(?,?,?,?,?)',
               (role,pet,request_id,fingerprint,json.dumps(asdict(receipt))))
    _revision(db,role)
    return receipt
