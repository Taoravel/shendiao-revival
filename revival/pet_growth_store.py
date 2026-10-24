"""Pet-growth persistence joining the fenced role owner's transaction."""
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pet_growth import Profile, PetGrowth
import pet_blood
import pet_stones


@dataclass(frozen=True)
class PetProgress:
    role_id: int
    pet_id: int
    profile: Profile
    state: PetGrowth
    attributes: object
    effective_profile: object = None
    blood: object = None
    stones: object = None


def prepare_pet_growth(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS inventory_pet_growth (
            pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),
            revision TEXT NOT NULL, profile TEXT NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS inventory_pet_growth_receipts (
            role_id INTEGER NOT NULL REFERENCES roles(id),
            pet_id INTEGER NOT NULL REFERENCES inventory_pets(id),
            settlement_id TEXT NOT NULL, fingerprint TEXT NOT NULL, result TEXT NOT NULL,
            PRIMARY KEY(role_id,pet_id,settlement_id));
    ''')
    pet_blood.prepare(db)
    pet_stones.prepare(db)
    from pet_soul_totals_storage import prepare
    prepare(db)


def _owner(db, account_id, role_id, pet_id):
    if not db.in_transaction:
        raise ValueError('Pet growth requires an owner transaction')
    row = db.execute('SELECT p.template_id FROM inventory_pets p JOIN roles r ON r.id=p.role_id '
                     'WHERE p.id=? AND r.id=? AND r.account_id=? AND p.released=0', (pet_id,role_id,account_id)).fetchone()
    if not row:
        raise ValueError('Pet growth ownership mismatch')
    return row[0]


def _decode(body):
    p,s = json.loads(body)
    p['aptitudes'] = tuple(p['aptitudes'])
    s['allocated'] = tuple(s['allocated'])
    return Profile(**p), PetGrowth(**s)


def effective_profile(profile,rules,blood_rules,blood,stones):
    effective=blood_rules.effective_profile(profile,blood) if blood is not None else profile
    return rules.stone_rules.effective_profile(effective,stones)


def _project(role,pet,profile,state,rules,blood_rules,blood,stones=None):
    effective=effective_profile(profile,rules,blood_rules,blood,stones) if blood is not None or stones is not None else None
    attr=rules.attributes(effective or profile,state.level,state.allocated,
                          bonus_potential=blood.bonus_potential if blood else 0)
    return PetProgress(role,pet,profile,state,attr,effective,blood,stones)


def encode_progress(progress):
    """Frozen historical growth data; not a current-state notification."""
    value=[asdict(progress.profile),asdict(progress.state)]
    if progress.blood is not None or progress.stones is not None:
        value.append(asdict(progress.blood) if progress.blood is not None else None)
    if progress.stones is not None:
        value.append(asdict(progress.stones))
    return value


def decode_progress(body,role,pet,rules,blood_rules):
    value=json.loads(body) if type(body) is str else body
    if type(value) is not list or len(value) not in (2,3,4):raise ValueError('Unknown growth receipt shape')
    profile,state=_decode(json.dumps(value[:2]));blood=None;stones=None
    if len(value)>=3 and value[2] is not None:
        data=dict(value[2]);data['state']=pet_blood.PetBlood(**data['state'])
        blood=pet_blood.BloodProgress(**data)
        if blood_rules is None or blood!=blood_rules.progress(blood.state,blood.grade):
            raise ValueError('Historical blood policy requires explicit reconciliation')
    if len(value)==4:stones=pet_stones.decode(value[3])
    return _project(role,pet,profile,state,rules,blood_rules,blood,stones)


def initialize_pet(db, account_id, role_id, pet_id, profile, rules):
    if _owner(db,account_id,role_id,pet_id) != profile.template_id:
        raise ValueError('Pet growth template mismatch')
    if db.execute('SELECT 1 FROM inventory_pet_growth WHERE pet_id=?', (pet_id,)).fetchone():
        raise ValueError('Pet already has persisted growth; reroll forbidden')
    state = rules.generate(profile)
    db.execute('INSERT INTO inventory_pet_growth VALUES(?,?,?,?)',
               (pet_id,rules.revision,json.dumps(asdict(profile)),json.dumps(asdict(state))))
    return PetProgress(role_id,pet_id,profile,state,rules.attributes(profile,state.level,state.allocated))


def read_growth_source(db, account_id, role_id, pet_id, rules, *, blood_rules=None,grade=None):
    """Owned canonical growth/blood/stone source, not a final native profile."""
    _owner(db,account_id,role_id,pet_id)
    row = db.execute('SELECT revision,profile,state FROM inventory_pet_growth WHERE pet_id=?', (pet_id,)).fetchone()
    if row is None:
        raise ValueError('Legacy pet requires explicit growth initialization')
    if row[0] != rules.revision:
        raise ValueError('Pet growth revision migration required')
    profile,state = _decode('['+row[1]+','+row[2]+']')
    blood=pet_blood.load(db,account_id,role_id,pet_id,blood_rules,grade)
    stones=pet_stones.load(db,account_id,role_id,pet_id,rules.stone_rules)
    return _project(role_id,pet_id,profile,state,rules,blood_rules,blood,stones)


def load_pet(db, account_id, role_id, pet_id, rules, *, blood_rules=None,grade=None):
    bare=read_growth_source(db,account_id,role_id,pet_id,rules,blood_rules=blood_rules,grade=grade)
    from pet_soul_totals_storage import project_loaded
    return project_loaded(db,account_id,role_id,pet_id,rules.totals_rules,bare)


def change_pet(db, account_id, role_id, pet_id, rules, settlement_id,
               expected_version, operation, value, *, blood_rules=None,grade=None):
    _owner(db,account_id,role_id,pet_id)
    if type(settlement_id) is not str or not 1 <= len(settlement_id) <= 160:
        raise ValueError('Invalid pet settlement ID')
    if operation not in ('experience','experience_capped','allocate','resources'):
        raise ValueError('Unsupported pet growth operation')
    from pet_soul_totals_storage import is_adopted
    if is_adopted(db,role_id,pet_id):
        raise ValueError('Adopted pet soul totals require source-aware commands, including historical replay')
    if operation=='experience_capped' and (type(value) is not tuple or len(value)!=2
            or any(type(x) is not int for x in value)):
        raise ValueError('Capped experience requires immutable integer amount and cap')
    fingerprint = hashlib.sha256(json.dumps([operation,value],separators=(',',':')).encode()).hexdigest()
    previous = db.execute('SELECT fingerprint,result FROM inventory_pet_growth_receipts '
                          'WHERE role_id=? AND pet_id=? AND settlement_id=?',
                          (role_id,pet_id,settlement_id)).fetchone()
    if previous:
        if previous[0] != fingerprint:
            raise ValueError('Pet settlement payload conflict')
        return decode_progress(previous[1],role_id,pet_id,rules,blood_rules)
    old = load_pet(db,account_id,role_id,pet_id,rules,blood_rules=blood_rules,grade=grade)
    if getattr(old.attributes,'policy',None) is not None:
        raise ValueError('Adopted pet soul totals require a source-aware growth/resource command')
    if old.state.version != expected_version:
        raise ValueError('Pet growth version mismatch')
    profile=old.effective_profile or old.profile
    bonus=old.blood.bonus_potential if old.blood else 0
    if operation == 'experience':
        state = rules.award(profile,old.state,value,bonus_potential=bonus)
    elif operation == 'experience_capped':
        state = rules.award(profile,old.state,value[0],award_cap=value[1],bonus_potential=bonus)
    elif operation == 'allocate':
        state = rules.allocate(profile,old.state,value,bonus_potential=bonus)
    else:
        if (type(value) is not tuple or len(value) != 2 or any(type(x) is not int for x in value)
                or not 0 <= value[0] <= old.attributes.max_hp
                or not 0 <= value[1] <= old.attributes.max_mp):
            raise ValueError('Invalid authoritative pet resources')
        state = replace(old.state,version=old.state.version+1,hp=value[0],mp=value[1])
    db.execute('UPDATE inventory_pet_growth SET state=? WHERE pet_id=?', (json.dumps(asdict(state)),pet_id))
    result=_project(role_id,pet_id,old.profile,state,rules,blood_rules,old.blood,old.stones)
    body = json.dumps(encode_progress(result))
    db.execute('INSERT INTO inventory_pet_growth_receipts VALUES(?,?,?,?,?)',
               (role_id,pet_id,settlement_id,fingerprint,body))
    # Revision and resources share this caller-owned transaction.
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1', (role_id,))
    return result


def damage_base_aptitudes(db,account,role,pet,rules,blood_rules,grade,before,amount):
    """Permanent food effect on current base, before the blood projection."""
    current=load_pet(db,account,role,pet,rules,blood_rules=blood_rules,grade=grade)
    if getattr(current.attributes,'policy',None) is not None:
        raise ValueError('Adopted pet soul totals require source-aware aptitude settlement')
    if (type(before) is not PetProgress or current!=before or before.blood is None
            or type(amount) is not int or amount!=1 or type(before.state.version) is not int
            or not 0<=before.state.version<2**63-1):
        raise ValueError('Current complete growth and supported aptitude-loss policy required')
    profile=replace(before.profile,aptitudes=tuple(max(0,value-amount) for value in before.profile.aptitudes))
    if profile==before.profile:return before
    planned=_project(role,pet,profile,before.state,rules,blood_rules,before.blood,before.stones)
    if (planned.attributes.max_hp>before.attributes.max_hp or planned.attributes.max_mp>before.attributes.max_mp
            or not 0<=before.state.hp<=before.attributes.max_hp or not 0<=before.state.mp<=before.attributes.max_mp):
        raise ValueError('Aptitude loss requires valid resources and nonincreasing caps')
    state=replace(before.state,version=before.state.version+1,
        hp=min(before.state.hp,planned.attributes.max_hp),mp=min(before.state.mp,planned.attributes.max_mp))
    old=db.execute('SELECT profile,state FROM inventory_pet_growth WHERE pet_id=?',(pet,)).fetchone()
    changed=db.execute('UPDATE inventory_pet_growth SET profile=?,state=? WHERE pet_id=? AND revision=? AND profile=? AND state=?',
        (json.dumps(asdict(profile)),json.dumps(asdict(state)),pet,rules.revision,old[0],old[1])).rowcount
    if changed!=1:raise ValueError('Base aptitude source changed in the role transaction')
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))
    return _project(role,pet,profile,state,rules,blood_rules,before.blood,before.stones)


def advance_blood(db,account,role,pet,rules,blood_rules,grade,before):
    """One essence's growth projection/write; caller joins item and receipts."""
    current=load_pet(db,account,role,pet,rules,blood_rules=blood_rules,grade=grade)
    if getattr(current.attributes,'policy',None) is not None:
        raise ValueError('Adopted pet soul totals require source-aware blood settlement')
    if (current!=before or before.blood is None or type(before.state.version) is not int
            or not 0<=before.state.version<2**63-1):
        raise ValueError('Current complete ordinary blood/growth snapshot required')
    if before.blood.state.power>=before.blood.maximum_power:
        raise ValueError('Pet blood energy has reached its colour ceiling')
    state=pet_blood.PetBlood(before.blood.state.version+1,
        min(before.blood.maximum_power,before.blood.state.power+blood_rules.essence_power))
    blood=blood_rules.progress(state,grade)
    projected=_project(role,pet,before.profile,before.state,rules,blood_rules,blood,before.stones)
    if projected.attributes.max_hp<before.attributes.max_hp or projected.attributes.max_mp<before.attributes.max_mp:
        raise ValueError('Ordinary blood progression cannot lower effective resource caps')
    if not 0<=before.state.hp<=before.attributes.max_hp or not 0<=before.state.mp<=before.attributes.max_mp:
        raise ValueError('Current pet resources exceed their known effective caps')
    hp=0 if before.state.hp==0 else before.state.hp+projected.attributes.max_hp-before.attributes.max_hp
    mp=before.state.mp+projected.attributes.max_mp-before.attributes.max_mp
    growth=replace(before.state,version=before.state.version+1,hp=hp,mp=mp)
    result=_project(role,pet,before.profile,growth,rules,blood_rules,blood,before.stones)
    encoded_before=db.execute('SELECT state FROM inventory_pet_growth WHERE pet_id=?',(pet,)).fetchone()[0]
    pet_blood.save(db,account,role,pet,blood_rules,before.blood,blood)
    changed=db.execute('UPDATE inventory_pet_growth SET state=? WHERE pet_id=? AND state=?',
        (json.dumps(asdict(growth)),pet,encoded_before)).rowcount
    if changed!=1:raise ValueError('Pet growth changed during ordinary blood progression')
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))
    return result
