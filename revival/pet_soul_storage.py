"""Explicit complete pet soul source CAS in the owning role transaction.

No implicit empty maps, bag exchange, material consumption, receipt, resource
writer, connection, commit or send. Future paid actions must join all of those
and current root inventory-source synchronization in the same caller transaction.
"""
from dataclasses import asdict,dataclass
import json
from inventory import PetState
from pet_souls import SoulBean,SoulProfile,SoulRules


@dataclass(frozen=True)
class SoulBasis:
    account_id: int
    inventory_revision: int
    pet: PetState
    profile: SoulProfile
    origin: str
    raw_profile: str
    baseline_source: str

    def __post_init__(self):
        if (type(self.account_id) is not int or self.account_id<=0
                or type(self.inventory_revision) is not int or not 0<=self.inventory_revision<2**63-1
                or type(self.pet) is not PetState or type(self.profile) is not SoulProfile
                or any(type(value) is not int for value in
                    (self.pet.id,self.pet.role_id,self.pet.template_id,self.pet.fighting,self.pet.released))
                or self.pet.id!=self.profile.pet_id or self.pet.role_id!=self.profile.role_id
                or self.pet.released!=0 or self.pet.fighting not in (0,1)
                or any(type(value) is not str for value in (self.origin,self.raw_profile,self.baseline_source))):
            raise ValueError('Frozen complete same-pet soul source required')


def prepare(db):
    """Startup only, after Inventory preparation. Creates no pet profiles."""
    db.execute('''CREATE TABLE IF NOT EXISTS inventory_pet_souls (
        pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id) ON DELETE CASCADE,
        role_id INTEGER NOT NULL REFERENCES roles(id),policy TEXT NOT NULL,
        origin TEXT NOT NULL,baseline TEXT NOT NULL,state TEXT NOT NULL)''')


def _owned(db,inventory,rules,pet_id):
    if type(rules) is not SoulRules or type(pet_id) is not int or not 0<pet_id<=0x7fffffff:
        raise ValueError('Frozen soul rules and positive pet key required')
    snapshot=inventory.immutable_snapshot_transaction(db)
    pet=next((p for p in snapshot.pets if p.id==pet_id),None)
    if type(pet) is not PetState or pet.template_id not in rules.pet_templates:
        raise ValueError('Current owned unreleased original pet required')
    return snapshot,pet


def _json(profile):
    return json.dumps(asdict(profile),sort_keys=True,separators=(',',':'))


def _decode(raw):
    data=json.loads(raw)
    data['entries']=tuple((slot,SoulBean(**bean)) for slot,bean in data['entries'])
    return SoulProfile(**data)


@dataclass(frozen=True)
class SoulProfileSource:
    profile: SoulProfile
    origin: str
    raw_profile: str
    baseline_source: str


def read_profile_source(db,account_id,role_id,pet_id,rules):
    """Primitive owned read for growth projection, without Inventory recursion.

    Internal caller transaction only. Session admission still requires the
    epoch-fenced read Interface below; this Interface cannot authorize writes.
    """
    if (not db.in_transaction or type(rules) is not SoulRules
            or any(type(v) is not int or not 0<v<2**63 for v in (account_id,role_id))
            or type(pet_id) is not int or not 0<pet_id<=0x7fffffff
            or not db.execute('SELECT 1 FROM inventory_pets p JOIN roles r ON r.id=p.role_id '
                'WHERE p.id=? AND p.role_id=? AND r.account_id=? AND p.released=0',
                (pet_id,role_id,account_id)).fetchone()):
        raise ValueError('Owned primitive pet soul source transaction required')
    row=db.execute('SELECT role_id,policy,origin,baseline,state FROM inventory_pet_souls WHERE pet_id=?',
        (pet_id,)).fetchone()
    if row is None:return None
    if row[:2]!=(role_id,rules.revision) or row[2] not in ('explicit_known_pet_souls','soul_change'):
        raise ValueError('Unknown pet soul owner, policy or provenance')
    baseline,profile=_decode(row[3]),_decode(row[4])
    for value in (baseline,profile):
        rules.validate_profile(value)
        if value.role_id!=role_id or value.pet_id!=pet_id:
            raise ValueError('Stored soul map belongs to another role or pet')
    if (baseline.version!=0 or baseline.source_ref!=profile.source_ref
            or row[2]=='explicit_known_pet_souls' and baseline!=profile):
        raise ValueError('Stored soul baseline/source requires explicit reconciliation')
    return SoulProfileSource(profile,row[2],row[4],row[3])


def read(db,inventory,rules,pet_id):
    """Missing returns None, never known empty; current session epoch fenced."""
    snapshot,pet=_owned(db,inventory,rules,pet_id)
    source=read_profile_source(db,inventory.account_id,inventory.role_id,pet_id,rules)
    if source is None:return None
    return SoulBasis(inventory.account_id,snapshot.inventory_revision,pet,source.profile,
        source.origin,source.raw_profile,source.baseline_source)


def _advance(db,inventory,revision):
    if db.execute('UPDATE inventory_versions SET revision=revision+1 WHERE role_id=? AND revision=?',
            (inventory.role_id,revision)).rowcount!=1:
        raise ValueError('Pet soul inventory source CAS failed')


def initialize(db,inventory,rules,profile,origin):
    """Trusted complete known import, including explicitly supplied empty maps."""
    if type(profile) is not SoulProfile:raise ValueError('Complete explicit soul profile required')
    snapshot,_=_owned(db,inventory,rules,profile.pet_id);rules.validate_profile(profile)
    if (origin!='explicit_known_pet_souls' or profile.role_id!=inventory.role_id or profile.version!=0):
        raise ValueError('Explicit same-role initial soul source required')
    encoded=_json(profile);old=read(db,inventory,rules,profile.pet_id)
    if old is not None:
        if old.baseline_source!=encoded:raise ValueError('Existing pet soul import cannot be reset or re-sourced')
        return old
    db.execute('INSERT INTO inventory_pet_souls VALUES(?,?,?,?,?,?)',
        (profile.pet_id,inventory.role_id,rules.revision,origin,encoded,encoded))
    _advance(db,inventory,snapshot.inventory_revision)
    return read(db,inventory,rules,profile.pet_id)


def replace_profile(db,inventory,rules,before,after):
    """Fresh full-source CAS only; outer paid controller skips this on replay."""
    if (type(before) is not SoulBasis or type(after) is not SoulProfile
            or before.account_id!=inventory.account_id or before.profile.role_id!=inventory.role_id
            or after.role_id!=before.profile.role_id or after.pet_id!=before.profile.pet_id
            or after.source_ref!=before.profile.source_ref or after.policy!=before.profile.policy
            or after.version!=before.profile.version+1):
        raise ValueError('Complete next same-pet soul source required')
    current=read(db,inventory,rules,after.pet_id)
    if current!=before:raise ValueError('Pet soul full source changed')
    rules.validate_profile(after)
    if db.execute('UPDATE inventory_pet_souls SET origin=?,state=? WHERE pet_id=? AND role_id=? '
            'AND policy=? AND origin=? AND baseline=? AND state=?',
            ('soul_change',_json(after),after.pet_id,inventory.role_id,rules.revision,before.origin,
             before.baseline_source,before.raw_profile)).rowcount!=1:
        raise ValueError('Pet soul full map CAS failed')
    _advance(db,inventory,current.inventory_revision)
    return read(db,inventory,rules,after.pet_id)
