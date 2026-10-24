"""Exact original expiry metadata and immutable, explicitly timed skill views."""
from dataclasses import asdict,dataclass
import json
import hashlib

from inspect_client import OUT

MAX_TIME_MS=32535215999999  # Original _localtime64_s upper calendar range.
EMPTY_SKILL_ID=200534


def require_time(now_ms):
    if type(now_ms) is not int or not 0<=now_ms<=MAX_TIME_MS:
        raise ValueError('Trusted Unix milliseconds in original calendar range required')
    return now_ms


@dataclass(frozen=True)
class ExpiryRules:
    revision: str

    @classmethod
    def load(cls):
        p=json.loads((OUT/'design/pet-skill-expiry-v1.json').read_text(encoding='utf-8'))
        if (p['revision']!='2026-10-23.pet-skill-expiry.1'
                or p['clock']!={'unit':'unix_milliseconds','minimum':0,'maximum':MAX_TIME_MS,'source_status':'client_verified'}
                or type(p['empty_skill_id']) is not int or p['empty_skill_id']!=EMPTY_SKILL_ID
                or p['expiry_comparison']!='now_ms > deadline_ms' or p['duration'] is not None
                or p['persistence']!={'missing_row':'unknown','new_pet':'explicit_empty_map','source_status':'designed'}
                or p['learning']!={'expired_slot':'reuse_before_expansion','permanent_book':'remove_replaced_expiry','source_status':'designed'}):
            raise ValueError('Pet skill expiry policy requires implementation review')
        return cls(p['revision'])


@dataclass(frozen=True)
class SkillExpiry:
    version: int
    entries: tuple

    def __post_init__(self):
        if (type(self.version) is not int or not 0<=self.version<0x7fffffff
                or type(self.entries) is not tuple or len(self.entries)>12
                or any(type(row) is not tuple or len(row)!=2
                    or type(row[0]) is not int or not 0<row[0]<=0x7fffffff
                    or row[0]==EMPTY_SKILL_ID or type(row[1]) is not int
                    or not 0<=row[1]<=MAX_TIME_MS for row in self.entries)
                or self.entries!=tuple(sorted(self.entries))
                or len({row[0] for row in self.entries})!=len(self.entries)):
            raise ValueError('Invalid complete pet skill expiry map')


@dataclass(frozen=True)
class SkillTimeView:
    skill_version: int
    expiry_version: int
    as_of_ms: int
    active_ids: tuple
    expired_ids: tuple
    slot_ids: tuple
    next_change_ms: object


@dataclass(frozen=True)
class TimedSkillGrant:
    settlement_id: str
    pet_id: int
    skill_id: int
    expires_at_ms: int
    source: str
    expected_version: int

    def __post_init__(self):
        require_time(self.expires_at_ms)
        if (type(self.settlement_id) is not str or not 1<=len(self.settlement_id)<=160
                or type(self.source) is not str or not 1<=len(self.source)<=160 or not self.source.strip()
                or type(self.pet_id) is not int or not 0<self.pet_id<=0x7fffffff
                or type(self.skill_id) is not int or not 0<self.skill_id<=0x7fffffff or self.skill_id==EMPTY_SKILL_ID
                or type(self.expected_version) is not int or not 0<=self.expected_version<0x7fffffff):
            raise ValueError('Trusted timed skill grant context required')


@dataclass(frozen=True)
class TimedSkillReceipt:
    command: TimedSkillGrant
    before: object
    after: object
    expiry_before: SkillExpiry
    expiry_after: SkillExpiry
    applied_at_ms: int


def validate(state,skills):
    if not isinstance(state,SkillExpiry) or any(key not in skills.learned for key,_ in state.entries):
        raise ValueError('Expiry entries require the complete current learned skill list')
    return state


def view(skills,state,now_ms):
    require_time(now_ms);validate(state,skills)
    deadlines=dict(state.entries)
    expired=tuple(key for key in skills.learned if key in deadlines and now_ms>deadlines[key])
    active=tuple(key for key in skills.learned if key!=EMPTY_SKILL_ID and key not in expired)
    changes=[deadline+1 for key,deadline in state.entries if now_ms<=deadline and deadline<MAX_TIME_MS]
    return SkillTimeView(skills.version,state.version,now_ms,active,expired,
        tuple(EMPTY_SKILL_ID if key in expired else key for key in skills.learned),min(changes) if changes else None)


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_skill_expiry (
        pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),
        policy TEXT NOT NULL,state TEXT NOT NULL);''')
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_timed_skill_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id),pet_id INTEGER NOT NULL REFERENCES inventory_pets(id),
        settlement_id TEXT NOT NULL,fingerprint TEXT NOT NULL,result TEXT NOT NULL,
        PRIMARY KEY(role_id,settlement_id));''')


def _owner(db,account,role,pet):
    if (type(pet) is not int or not 0<pet<=0x7fffffff or not db.in_transaction
            or not db.execute('SELECT 1 FROM inventory_pets p JOIN roles r ON r.id=p.role_id '
            'WHERE p.id=? AND p.role_id=? AND r.account_id=? AND p.released=0',(pet,role,account)).fetchone()):
        raise ValueError('Pet expiry requires an owned live pet transaction')


def initialize(db,account,role,pet,rules,skills,entries):
    _owner(db,account,role,pet)
    state=validate(SkillExpiry(0,entries),skills)
    if db.execute('SELECT 1 FROM inventory_pet_skill_expiry WHERE pet_id=?',(pet,)).fetchone():
        raise ValueError('Known pet expiry cannot be reset')
    db.execute('INSERT INTO inventory_pet_skill_expiry VALUES(?,?,?)',(pet,rules.revision,json.dumps(asdict(state))))
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))
    return state


def decode(value):
    if type(value) is str:value=json.loads(value)
    return SkillExpiry(value['version'],tuple(tuple(row) for row in value['entries']))


def load(db,account,role,pet,rules,skills):
    _owner(db,account,role,pet)
    row=db.execute('SELECT policy,state FROM inventory_pet_skill_expiry WHERE pet_id=?',(pet,)).fetchone()
    if not row or row[0]!=rules.revision:
        raise ValueError('Pet expiry requires explicit complete initialization or migration')
    return validate(decode(row[1]),skills)


def save(db,account,role,pet,rules,before,old_skills,new_skills,entries):
    """Caller owns the transaction and the shared asset revision."""
    if load(db,account,role,pet,rules,old_skills)!=before:
        raise ValueError('Pet skill expiry version mismatch')
    after=before if entries==before.entries else SkillExpiry(before.version+1,entries)
    validate(after,new_skills)
    if after!=before:
        db.execute('UPDATE inventory_pet_skill_expiry SET state=? WHERE pet_id=?',
                   (json.dumps(asdict(after)),pet))
    return after


def grant(db,account,role,command,now_ms,rules,grade):
    """Trusted reward Interface only: no client command, default duration or RNG."""
    from pet_skills import PetSkills,load as load_skills
    if not isinstance(command,TimedSkillGrant):raise ValueError('Immutable timed skill command required')
    require_time(now_ms);pet=command.pet_id
    _owner(db,account,role,pet)
    fingerprint=hashlib.sha256(json.dumps([asdict(command),rules.revision,rules.expiry_rules.revision],sort_keys=True).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result FROM inventory_pet_timed_skill_receipts WHERE role_id=? AND settlement_id=?',
                   (role,command.settlement_id)).fetchone()
    if old:
        if old[0]!=fingerprint:raise ValueError('Timed skill grant intent conflict')
        value=json.loads(old[1]);value['command']=TimedSkillGrant(**value['command'])
        for field in ('before','after'):
            v=value[field];value[field]=PetSkills(v['version'],tuple(v['learned']))
        for field in ('expiry_before','expiry_after'):value[field]=decode(value[field])
        return TimedSkillReceipt(**value)
    before=load_skills(db,account,role,pet,rules,grade)
    expiry=load(db,account,role,pet,rules.expiry_rules,before)
    if (before.version!=command.expected_version or command.skill_id not in rules.skills
            or command.expires_at_ms<=now_ms):
        raise ValueError('Current skill version, known ability and future deadline required')
    current=view(before,expiry,now_ms);learned=list(before.learned);deadlines=dict(expiry.entries)
    skill=command.skill_id;replaced=None
    if any(key!=skill and key//10==skill//10 for key in current.active_ids):
        raise ValueError('Timed skill family conflict requires explicit content rules')
    if skill in learned:
        if skill not in deadlines or command.expires_at_ms<=deadlines[skill]:
            raise ValueError('A timed grant cannot shorten or replace a permanent ability')
    else:
        vacant=[i for i,key in enumerate(learned) if key==EMPTY_SKILL_ID or key in current.expired_ids]
        if vacant:
            index=vacant[0];replaced=learned[index];learned[index]=skill
        elif len(learned)<rules.caps[grade]:learned.append(skill)
        else:raise ValueError('Timed grant cannot overwrite an active ability in a full pet')
    if replaced is not None:deadlines.pop(replaced,None)
    deadlines[skill]=command.expires_at_ms
    after=rules.validate(PetSkills(before.version+1,tuple(learned)),grade)
    expiry_after=save(db,account,role,pet,rules.expiry_rules,expiry,before,after,tuple(sorted(deadlines.items())))
    db.execute('UPDATE inventory_pet_skills SET state=? WHERE pet_id=?',(json.dumps(asdict(after)),pet))
    result=TimedSkillReceipt(command,before,after,expiry,expiry_after,now_ms)
    db.execute('INSERT INTO inventory_pet_timed_skill_receipts VALUES(?,?,?,?,?)',
               (role,pet,command.settlement_id,fingerprint,json.dumps(asdict(result))))
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))
    return result
