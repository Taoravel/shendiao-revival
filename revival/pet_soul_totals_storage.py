"""Selected pet totals with the EXISTING inventory_pet_growth.state HP/MP.

Only explicit extra/source metadata and receipts live here. Internal snapshots
may carry pending totals during source/asset CAS; ordinary attribute getters,
native encoding and battle entry reject them until source settlement completes.
"""
from dataclasses import dataclass,asdict,replace
import hashlib
import json
from pet_soul_totals import PetSoulTotalsRules,PetSoulExtraBasis,PetSoulAttributes,project
from pet_soul_storage import read_profile_source
from role_mingwen import read_state_source
from pet_growth_store import read_growth_source,PetProgress


@dataclass(frozen=True)
class PetSoulProfile:
    account_id: int
    login_epoch: int | str
    inventory_revision: int
    progress: PetProgress
    metadata: tuple

    def __post_init__(self):
        if (type(self.account_id) is not int or not 0<self.account_id<2**63
                or not (type(self.login_epoch) is int and 0<self.login_epoch<2**63
                    or type(self.login_epoch) is str and 1<=len(self.login_epoch)<=128)
                or type(self.inventory_revision) is not int or not 0<=self.inventory_revision<2**63-1
                or type(self.progress) is not PetProgress or type(self.progress.attributes) is not PetSoulAttributes
                or not self.progress.attributes.settled or type(self.metadata) is not tuple or len(self.metadata)!=8
                or self.metadata[0]!=self.progress.role_id or self.metadata[1]!=self.progress.attributes.policy):
            raise ValueError('Complete frozen settled current pet profile required')


def prepare(db):
    """Startup only. No pet is adopted and no source tables are fabricated."""
    db.execute('''CREATE TABLE IF NOT EXISTS inventory_pet_soul_totals (
        pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),role_id INTEGER NOT NULL REFERENCES roles(id),
        policy TEXT NOT NULL,origin TEXT NOT NULL,baseline TEXT NOT NULL,version INTEGER NOT NULL,
        source TEXT NOT NULL,hp_cap INTEGER NOT NULL,mp_cap INTEGER NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS inventory_pet_soul_resource_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id),pet_id INTEGER NOT NULL REFERENCES inventory_pets(id),
        request_id TEXT NOT NULL,policy TEXT NOT NULL,fingerprint TEXT NOT NULL,
        PRIMARY KEY(role_id,pet_id,request_id))''')


def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def _row(db,role,pet):
    row=db.execute('SELECT role_id,policy,origin,baseline,version,source,hp_cap,mp_cap '
        'FROM inventory_pet_soul_totals WHERE pet_id=?',(pet,)).fetchone()
    if row is not None and (row[0]!=role or row[2]!='explicit_known_pet_soul_extras'
            or type(row[4]) is not int or not 0<=row[4]<2**63-1):
        raise ValueError('Unknown pet soul totals owner/source metadata')
    return row


def is_adopted(db,role,pet):
    """Internal owning growth writer's policy dispatch; not a session permit."""
    return _row(db,role,pet) is not None


def _extra(row,role,pet,rules):
    if type(rules) is not PetSoulTotalsRules or row[1]!=rules.revision:
        raise ValueError('Adopted pet totals require their explicitly selected final policy')
    data=json.loads(row[3]);data['values']=tuple(tuple(p) for p in data['values']);value=PetSoulExtraBasis(**data)
    if (value.role_id,value.pet_id)!=(role,pet):raise ValueError('Pet extra baseline owner mismatch')
    return value


def _parts(db,account,role,pet,rules,bare,extra,baseline):
    state=bare.state
    if (any(type(v) is not int for v in (state.version,state.hp,state.mp))
            or not 0<=state.version<2**63-1 or not 0<=state.hp<=0x7fffffff or not 0<=state.mp<=0x7fffffff):
        raise ValueError('Exact existing sole pet resources and version required')
    souls=read_profile_source(db,account,role,pet,rules.souls)
    mingwen=read_state_source(db,account,role,rules.mingwen)
    if souls is None or mingwen is None:raise ValueError('Complete known soul/inscription sources required for final totals')
    core,extras=project(rules,bare,souls.profile,mingwen.state.soul_cap_increment,extra)
    raw=db.execute('SELECT revision,profile,state FROM inventory_pet_growth WHERE pet_id=?',(pet,)).fetchone()
    payload=[rules.revision,baseline,raw,asdict(bare.attributes),asdict(core),extras,asdict(bare.blood) if bare.blood else None,
        asdict(bare.stones) if bare.stones else None,souls.origin,souls.baseline_source,souls.raw_profile,
        mingwen.origin,mingwen.baseline_source,mingwen.raw_state]
    stamp=hashlib.sha256(_json(payload).encode('utf-8')).hexdigest()
    return core,extras,stamp


def project_loaded(db,account,role,pet,rules,bare):
    """Shared growth-read Seam; default old policy refuses adopted metadata."""
    row=_row(db,role,pet)
    if row is None:return bare
    extra=_extra(row,role,pet,rules)
    core,extras,stamp=_parts(db,account,role,pet,rules,bare,extra,row[3])
    settled=(row[5:]==(stamp,core.max_hp,core.max_mp)
        and 0<=bare.state.hp<=core.max_hp and 0<=bare.state.mp<=core.max_mp)
    attrs=PetSoulAttributes(core,extras,rules.revision,stamp,settled)
    return replace(bare,attributes=attrs)


def _bare(db,inventory,pet):
    grade=None
    if db.execute('SELECT 1 FROM inventory_pet_blood WHERE pet_id=?',(pet,)).fetchone():
        import pet_care
        grade=pet_care.load(db,inventory.account_id,inventory.role_id,pet,inventory.care_rules).grade
    return read_growth_source(db,inventory.account_id,inventory.role_id,pet,inventory.growth_rules,
        blood_rules=inventory.blood_rules,grade=grade)


def _advance(db,inventory,revision):
    if db.execute('UPDATE inventory_versions SET revision=revision+1 WHERE role_id=? AND revision=?',
            (inventory.role_id,revision)).rowcount!=1:raise ValueError('Pet totals inventory source changed')


def initialize(db,inventory,rules,extra,origin):
    """Trusted known extras adoption only, never guessed old/new-role zeros.

    Return the immutable baseline, not a historical resource acknowledgement.
    The caller selects totals_rules on Inventory before reading adopted pets.
    """
    if (type(rules) is not PetSoulTotalsRules or type(extra) is not PetSoulExtraBasis
            or extra.role_id!=inventory.role_id or extra.policy!=rules.revision
            or origin!='explicit_known_pet_soul_extras'):
        raise ValueError('Explicit complete selected pet extras source required')
    snapshot=inventory.immutable_snapshot_transaction(db)
    if not any(p.id==extra.pet_id for p in snapshot.pets):raise ValueError('Owned unreleased pet required')
    body=_json(asdict(extra));old=_row(db,inventory.role_id,extra.pet_id)
    if old is not None:
        if old[1:4]!=(rules.revision,origin,body):raise ValueError('Existing pet extra baseline cannot be reset')
        read_profile(db,inventory,rules,extra.pet_id)
        return extra
    bare=_bare(db,inventory,extra.pet_id)
    if not 0<=bare.state.hp<=bare.attributes.max_hp or not 0<=bare.state.mp<=bare.attributes.max_mp:
        raise ValueError('Known original bare pet resources required for explicit adoption')
    core,_,stamp=_parts(db,inventory.account_id,inventory.role_id,extra.pet_id,rules,bare,extra,body)
    db.execute('INSERT INTO inventory_pet_soul_totals VALUES(?,?,?,?,?,?,?,?,?)',
        (extra.pet_id,inventory.role_id,rules.revision,origin,body,0,stamp,core.max_hp,core.max_mp))
    _advance(db,inventory,snapshot.inventory_revision)
    return extra


def read_profile(db,inventory,rules,pet):
    if type(rules) is not PetSoulTotalsRules or type(pet) is not int or not 0<pet<=0x7fffffff:
        raise ValueError('Selected pet totals rules and native owned pet key required')
    snapshot=inventory.immutable_snapshot_transaction(db)
    current=next((p.progress for p in snapshot.pets if p.id==pet),None)
    row=_row(db,inventory.role_id,pet)
    if (row is None or row[1]!=getattr(rules,'revision',None) or current is None
            or type(current.attributes) is not PetSoulAttributes or not current.attributes.settled):
        raise ValueError('Complete settled current pet totals/resources required')
    return PetSoulProfile(inventory.account_id,inventory.epoch,snapshot.inventory_revision,current,row)


def _settle(db,inventory,rules,before,request_id,cause,values):
    snapshot=inventory.immutable_snapshot_transaction(db)
    if (type(rules) is not PetSoulTotalsRules or type(before) is not PetSoulProfile
            or before.account_id!=inventory.account_id or before.progress.role_id!=inventory.role_id
            or type(request_id) is not str or not 1<=len(request_id.encode('utf-8'))<=120
            or cause not in ('soul_change','medicine','combat')):
        raise ValueError('Frozen owned current pet resource command required')
    pet=before.progress.pet_id
    fingerprint=hashlib.sha256(_json([asdict(before),cause,values]).encode('utf-8')).hexdigest()
    old=db.execute('SELECT policy,fingerprint FROM inventory_pet_soul_resource_receipts '
        'WHERE role_id=? AND pet_id=? AND request_id=?',(inventory.role_id,pet,request_id)).fetchone()
    if old is not None:
        if old!=(rules.revision,fingerprint):raise ValueError('Conflicting pet resource/source receipt')
        return read_profile(db,inventory,rules,pet)
    row=_row(db,inventory.role_id,pet)
    bare=_bare(db,inventory,pet)
    if (before.login_epoch!=inventory.epoch or row!=before.metadata
            or (bare.profile,bare.state,bare.effective_profile,bare.blood,bare.stones)!=(
                before.progress.profile,before.progress.state,before.progress.effective_profile,before.progress.blood,before.progress.stones)):
        raise ValueError('Pet source/resource command is stale')
    extra=_extra(row,inventory.role_id,pet,rules)
    core,_,current_stamp=_parts(db,inventory.account_id,inventory.role_id,pet,rules,bare,extra,row[3])
    if cause!='soul_change' and row[5:]!=(current_stamp,core.max_hp,core.max_mp):
        raise ValueError('Pet resource operation requires an already settled source')
    hp,mp=bare.state.hp,bare.state.mp
    if cause=='soul_change':
        if values is not None:raise ValueError('Soul source change cannot supply arbitrary resource values')
        hp,mp=min(hp,core.max_hp),min(mp,core.max_mp)
    else:
        if (type(values) is not tuple or len(values)!=2 or any(type(v) is not int for v in values)
                or not 0<=values[0]<=core.max_hp or not 0<=values[1]<=core.max_mp
                or hp==0 and values[0]!=0
                or cause=='combat' and (values[0]>hp or values[1]>mp)
                or cause=='medicine' and (values[0]<hp or values[1]<mp)):
            raise ValueError('Current caps and selected nonreviving pet resource cause required')
        hp,mp=values
    if (hp,mp)!=(bare.state.hp,bare.state.mp):
        state=replace(bare.state,version=bare.state.version+1,hp=hp,mp=mp)
        if state.version>=2**63-1:raise ValueError('Pet resource version exhausted')
        raw=db.execute('SELECT state FROM inventory_pet_growth WHERE pet_id=?',(pet,)).fetchone()[0]
        if db.execute('UPDATE inventory_pet_growth SET state=? WHERE pet_id=? AND state=?',
                (json.dumps(asdict(state)),pet,raw)).rowcount!=1:raise ValueError('Sole pet resource CAS failed')
        bare=replace(bare,state=state)
    core,_,stamp=_parts(db,inventory.account_id,inventory.role_id,pet,rules,bare,extra,row[3])
    if row[4]>=2**63-2:raise ValueError('Pet source version exhausted')
    if db.execute('UPDATE inventory_pet_soul_totals SET version=?,source=?,hp_cap=?,mp_cap=? '
            'WHERE pet_id=? AND role_id=? AND version=? AND source=? AND baseline=?',
            (row[4]+1,stamp,core.max_hp,core.max_mp,pet,inventory.role_id,row[4],row[5],row[3])).rowcount!=1:
        raise ValueError('Pet final source CAS failed')
    _advance(db,inventory,snapshot.inventory_revision)
    db.execute('INSERT INTO inventory_pet_soul_resource_receipts VALUES(?,?,?,?,?)',
        (inventory.role_id,pet,request_id,rules.revision,fingerprint))
    return read_profile(db,inventory,rules,pet)


def settle_source(db,inventory,rules,before,request_id):
    """After same-Tx map/assets, keep absolute values and clip down; no heal."""
    return _settle(db,inventory,rules,before,request_id,'soul_change',None)


def change_resources(db,inventory,rules,before,request_id,values,*,cause):
    """Low-level trusted medicine/combat settlement, not item/battle permission."""
    if cause not in ('medicine','combat'):raise ValueError('Explicit medicine/combat pet resource cause required')
    return _settle(db,inventory,rules,before,request_id,cause,values)
