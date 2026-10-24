"""Explicit role attribute baselines and transaction-scoped growth snapshots.

The role owner supplies real baselines/vitals. Startup creates no character data.
Snapshot reads refuse stale growth versions; no unknown five stats are invented.
"""
from dataclasses import dataclass,asdict
import json
from role_attributes import AttributeBaseline,RoleAttributes,derive_attributes,growth_vitals
from item_effects import VitalState
from role_resource_storage import prepare_resource_storage,require_legacy_resource_contract,read_role_resources


@dataclass(frozen=True)
class RoleAttributeSnapshot:
    attributes: RoleAttributes
    vitals: VitalState


def prepare_attribute_storage(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS role_attribute_baselines (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id), baseline TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS role_attribute_snapshots (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id), attributes TEXT NOT NULL, vitals TEXT NOT NULL);''')
    prepare_resource_storage(db)


def _owner(db,account_id,role_id,epoch):
    if not db.in_transaction or not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
        'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',(role_id,account_id,epoch)).fetchone():
        raise ValueError('Attribute owner transaction/lease mismatch')


def _growth_scope(db,growth):
    row=db.execute('SELECT r.level,g.baseline_level,g.revision,g.policy,g.automatic_points,g.allocated_points '
        "FROM roles r JOIN role_growth g ON g.role_id=r.id WHERE r.id=? AND g.phase='ordinary'",(growth.role_id,)).fetchone()
    if (row is None or tuple(row[:4])!=(growth.level,growth.baseline_level,growth.revision,growth.policy)
            or tuple(json.loads(row[4]))!=growth.automatic_points or tuple(json.loads(row[5]))!=growth.allocated_points):
        raise ValueError('Attribute growth snapshot is stale')


def _baseline(data):
    record=json.loads(data)
    record['five_stats']=tuple(record['five_stats']);record['values']=tuple(record['values'])
    return AttributeBaseline(**record)


def _checked_attributes(db,role_id,encoded):
    data=json.loads(encoded);data['five_stats']=tuple(data['five_stats'])
    attrs=RoleAttributes(**data)
    current=db.execute('SELECT r.level,g.revision FROM roles r JOIN role_growth g ON g.role_id=r.id WHERE r.id=?',(role_id,)).fetchone()
    if current is None or tuple(current)!=(attrs.level,attrs.growth_revision):
        raise ValueError('Stored attribute snapshot is stale')
    return attrs


def read_naked_attributes(db,account_id,role_id,epoch):
    """Current naked growth only, independent of any resource cap contract."""
    _owner(db,account_id,role_id,epoch)
    row=db.execute('SELECT attributes FROM role_attribute_snapshots WHERE role_id=?',(role_id,)).fetchone()
    if row is None:raise ValueError('Explicit attribute baseline required')
    return _checked_attributes(db,role_id,row[0])


def read_attribute_snapshot(db,account_id,role_id,epoch):
    _owner(db,account_id,role_id,epoch)
    require_legacy_resource_contract(db,role_id)
    row=db.execute('SELECT attributes,vitals FROM role_attribute_snapshots WHERE role_id=?',(role_id,)).fetchone()
    if row is None: raise ValueError('Explicit attribute baseline required')
    return RoleAttributeSnapshot(_checked_attributes(db,role_id,row[0]),VitalState(**json.loads(row[1])))


def initialize_attribute_baseline(db,account_id,role_id,epoch,baseline,growth,rules,vitals):
    _owner(db,account_id,role_id,epoch)
    require_legacy_resource_contract(db,role_id)
    if not isinstance(baseline,AttributeBaseline) or baseline.role_id!=role_id or vitals.target_id!=role_id:
        raise ValueError('Attribute baseline role mismatch')
    _growth_scope(db,growth)
    encoded=json.dumps(asdict(baseline),sort_keys=True)
    old=db.execute('SELECT baseline FROM role_attribute_baselines WHERE role_id=?',(role_id,)).fetchone()
    if old:
        if old[0]!=encoded: raise ValueError('Existing attribute baseline cannot be reset')
        existing=read_attribute_snapshot(db,account_id,role_id,epoch)
        if existing.attributes.policy_revision!=rules.revision:
            raise ValueError('Attribute policy migration required')
        return existing
    attrs=derive_attributes(baseline,growth,rules)
    after=vitals if (vitals.max_hp,vitals.max_mp)==(attrs.hp_max,attrs.mp_max) else growth_vitals(vitals,attrs)
    db.execute('INSERT INTO role_attribute_baselines VALUES(?,?)',(role_id,encoded))
    db.execute('INSERT INTO role_attribute_snapshots VALUES(?,?,?)',
               (role_id,json.dumps(asdict(attrs)),json.dumps(asdict(after))))
    return RoleAttributeSnapshot(attrs,after)


def attribute_snapshot_if_initialized(db,account_id,role_id,epoch):
    table=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='role_attribute_snapshots'").fetchone()
    if not table or not db.execute('SELECT 1 FROM role_attribute_snapshots WHERE role_id=?',(role_id,)).fetchone():
        return None
    return read_attribute_snapshot(db,account_id,role_id,epoch)


def update_role_vitals(db,account_id,role_id,epoch,before,after):
    """Store an authoritative combat/item result; never accept client HP/MP.

    Compare the complete prior vital snapshot and advance its version once.
    Growth then preserves the latest wounds instead of an old login snapshot.
    """
    current=read_attribute_snapshot(db,account_id,role_id,epoch)
    if (not isinstance(after,VitalState) or current.vitals!=before or after.target_id!=role_id
            or after.version!=before.version+1
            or (after.max_hp,after.max_mp)!=(current.attributes.hp_max,current.attributes.mp_max)):
        raise ValueError('Vital snapshot version or maximum mismatch')
    db.execute('UPDATE role_attribute_snapshots SET vitals=? WHERE role_id=?',
               (json.dumps(asdict(after)),role_id))
    return RoleAttributeSnapshot(current.attributes,after)


def sync_growth_attributes(db,account_id,growth,epoch,rules=None):
    """Join growth transaction; skip only roles without an explicit baseline."""
    table=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='role_attribute_baselines'").fetchone()
    if not table: return None
    row=db.execute('SELECT baseline FROM role_attribute_baselines WHERE role_id=?',(growth.role_id,)).fetchone()
    if row is None: return None
    _owner(db,account_id,growth.role_id,epoch)
    require_legacy_resource_contract(db,growth.role_id)
    if rules is None: raise ValueError('Attribute rules required for initialized baseline')
    _growth_scope(db,growth)
    attrs=derive_attributes(_baseline(row[0]),growth,rules)
    old=db.execute('SELECT attributes,vitals FROM role_attribute_snapshots WHERE role_id=?',(growth.role_id,)).fetchone()
    if old is None: raise ValueError('Attribute vital snapshot missing')
    if json.loads(old[0])['policy_revision']!=rules.revision:
        raise ValueError('Attribute policy migration required')
    before=VitalState(**json.loads(old[1]))
    # No maximum change means no artificial HP/MP refresh or vital-version bump.
    after=before if (before.max_hp,before.max_mp)==(attrs.hp_max,attrs.mp_max) else growth_vitals(before,attrs)
    db.execute('UPDATE role_attribute_snapshots SET attributes=?,vitals=? WHERE role_id=?',
               (json.dumps(asdict(attrs)),json.dumps(asdict(after)),growth.role_id))
    return RoleAttributeSnapshot(attrs,after)


def sync_growth_naked_attributes(db,account_id,growth,epoch,rules,resource_rules):
    """Explicit migrated growth writer; changes no resource carrier fields.

    Caller must settle final growth caps and encode the current profile in this
    same transaction. Legacy profiles continue using sync_growth_attributes.
    """
    read_role_resources(db,account_id,growth.role_id,epoch,resource_rules)
    _growth_scope(db,growth)
    row=db.execute('SELECT b.baseline,s.attributes FROM role_attribute_baselines b '
        'JOIN role_attribute_snapshots s ON s.role_id=b.role_id WHERE b.role_id=?',(growth.role_id,)).fetchone()
    if row is None:raise ValueError('Explicit naked attribute baseline required')
    if rules is None or json.loads(row[1])['policy_revision']!=rules.revision:
        raise ValueError('Naked growth attribute policy migration required')
    attrs=derive_attributes(_baseline(row[0]),growth,rules)
    changed=db.execute('UPDATE role_attribute_snapshots SET attributes=? WHERE role_id=? AND attributes=?',
        (json.dumps(asdict(attrs)),growth.role_id,row[1])).rowcount
    if changed!=1:raise ValueError('Naked attributes changed during growth transaction')
    return attrs
