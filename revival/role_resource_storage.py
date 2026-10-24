"""One resource carrier with explicit provenance in caller-owned transactions.

Current HP/MP stay solely in role_attribute_snapshots.vitals. The new table
stores policy/source/initialization metadata, never a second current HP/MP.
No connections, commits, schema work in role paths, implicit legacy activation,
network effects or startup grants. Only trusted final projections supply caps.
"""
from dataclasses import asdict,dataclass
import hashlib
import json

from item_effects import VitalState
from role_resource_plan import (ResourceProjection,ResourceCaps,RoleResources,ResourceRules,
    ResourceTransition,plan_resource_caps,plan_resource_values,plan_resource_source,plan_combat_resources)


class ResourceNotInitialized(ValueError):
    pass


class ResourceProfileRequired(ValueError):
    pass


@dataclass(frozen=True)
class ResourceMutationResult:
    request_id:str
    resources:RoleResources
    replayed:bool


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))


def prepare_resource_storage(db):
    """Startup-only metadata schema; no resource profile is granted."""
    db.execute('''CREATE TABLE IF NOT EXISTS role_resource_profiles (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id),policy TEXT NOT NULL,
        source TEXT NOT NULL,origin TEXT NOT NULL,migration_id TEXT NOT NULL,
        initialization_fingerprint TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS role_resource_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL,cause TEXT NOT NULL,before_version INTEGER NOT NULL,
        after_version INTEGER NOT NULL,PRIMARY KEY(role_id,request_id))''')


def _owner(db,account_id,role_id,epoch,rules):
    if (not db.in_transaction or type(rules) is not ResourceRules
            or type(account_id) is not int or account_id<1
            or type(role_id) is not int or not 0<role_id<2**63
            or not ((type(epoch) is int and 0<epoch<2**63)
                    or (type(epoch) is str and 1<=len(epoch)<=128))):
        raise ValueError('Current resource owner transaction required')
    if not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
            'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1 '
            'AND NOT EXISTS(SELECT 1 FROM role_deletions d WHERE d.role_id=r.id)',
            (role_id,account_id,str(epoch))).fetchone():
        raise ValueError('Resource ownership or current lease mismatch')


def _carrier(db,role_id):
    row=db.execute('SELECT vitals FROM role_attribute_snapshots WHERE role_id=?',(role_id,)).fetchone()
    if row is None:raise ValueError('Explicit known attribute/resource carrier required')
    return row[0],VitalState(**json.loads(row[0]))


def _profile(db,role_id):
    return db.execute('SELECT policy,source,origin,migration_id,initialization_fingerprint '
        'FROM role_resource_profiles WHERE role_id=?',(role_id,)).fetchone()


def require_legacy_resource_contract(db,role_id):
    """A migrated carrier has exactly one active contract, never two writers."""
    if _profile(db,role_id) is not None:
        raise ResourceProfileRequired('Use the migrated role resource Interface')


def read_role_resources(db,account_id,role_id,epoch,rules):
    """Read the sole known resource record; never transition caps on a read.

    Its source is the last committed resource projection. A caller changing
    assets/growth retains this complete before value and computes fresh caps
    before persisting a transition; it cannot infer caps from bare attributes.
    """
    _owner(db,account_id,role_id,epoch,rules)
    profile=_profile(db,role_id)
    if profile is None:raise ResourceNotInitialized('Explicit resource profile migration required')
    if profile[0]!=rules.revision:raise ValueError('Resource policy migration required')
    source=ResourceProjection(**json.loads(profile[1]))
    _,vitals=_carrier(db,role_id)
    if source.role_id!=role_id or vitals.target_id!=role_id:
        raise ValueError('Resource carrier belongs to another role')
    return RoleResources(vitals.version,vitals.hp,vitals.mp,
        ResourceCaps(source,vitals.max_hp,vitals.max_mp),rules.revision)


def _validate_caps(db,account_id,role_id,epoch,caps,equipment_rules):
    from role_equipment_storage import current_resource_projection_source
    if (type(caps) is not ResourceCaps or caps.source.role_id!=role_id
            or caps.source!=current_resource_projection_source(db,account_id,role_id,epoch,equipment_rules)):
        raise ValueError('Final resource projection source is stale or foreign')


def _write_carrier(db,role_id,encoded_before,after):
    vital=VitalState(role_id,after.version,after.hp,after.caps.hp_max,after.mp,after.caps.mp_max)
    encoded=_json(asdict(vital))
    changed=db.execute('UPDATE role_attribute_snapshots SET vitals=? WHERE role_id=? AND vitals=?',
        (encoded,role_id,encoded_before)).rowcount
    if changed!=1:raise ValueError('Resource carrier changed during caller transaction')


def migrate_role_resources(db,account_id,role_id,epoch,expected_vitals,caps,*,
        origin,migration_id,rules,equipment_rules):
    """Transfer the known carrier contract once, without replaying a heal.

    The trusted caller supplies final caps computed from current real assets.
    We validate their source revisions, compare the complete known old vital
    record, and atomically join source metadata to that same existing carrier.
    A paid initialization retry returns CURRENT resources, never old values.
    """
    _owner(db,account_id,role_id,epoch,rules)
    if (type(expected_vitals) is not VitalState or expected_vitals.target_id!=role_id
            or type(caps) is not ResourceCaps or caps.source.role_id!=role_id
            or origin not in ('explicit_migration','new_restoration_role')
            or type(migration_id) is not str or not 1<=len(migration_id)<=160):
        raise ValueError('Explicit known resource migration intent required')
    fingerprint=hashlib.sha256(_json(dict(policy=rules.revision,origin=origin,
        before=asdict(expected_vitals),caps=asdict(caps))).encode()).hexdigest()
    old=_profile(db,role_id)
    if old is not None:
        if (old[0],old[2],old[3],old[4])!=(rules.revision,origin,migration_id,fingerprint):
            raise ValueError('Existing resource profile cannot be reset or re-sourced')
        return read_role_resources(db,account_id,role_id,epoch,rules)
    _validate_caps(db,account_id,role_id,epoch,caps,equipment_rules)
    if origin=='new_restoration_role' and not db.execute(
            'SELECT 1 FROM role_restoration_origins WHERE role_id=? AND origin=?',
            (role_id,origin)).fetchone():
        raise ValueError('No explicit new-role resource provenance')
    encoded,vitals=_carrier(db,role_id)
    if vitals!=expected_vitals:raise ValueError('Known legacy resource snapshot is stale')
    staged=RoleResources(vitals.version,vitals.hp,vitals.mp,
        ResourceCaps(caps.source,vitals.max_hp,vitals.max_mp),rules.revision)
    after=plan_resource_caps(staged,caps,'explicit_migration',rules).after
    _write_carrier(db,role_id,encoded,after)
    db.execute('INSERT INTO role_resource_profiles VALUES(?,?,?,?,?,?)',
        (role_id,rules.revision,_json(asdict(caps.source)),origin,migration_id,fingerprint))
    return read_role_resources(db,account_id,role_id,epoch,rules)


def apply_resource_transition(db,account_id,role_id,epoch,transition,request_id,*,rules,equipment_rules):
    """Full-before CAS, resource carrier/source metadata and retry receipt.

    Caller joins effect/asset/fee writes and validates native encoding before
    committing. This function never commits. Identical accepted retries only
    read current resources; they do not replay a historical heal/cap change.
    """
    _owner(db,account_id,role_id,epoch,rules)
    if (type(transition) is not ResourceTransition
            or any(type(state) is not RoleResources or state.policy!=rules.revision
                   or state.caps.source.role_id!=role_id for state in (transition.before,transition.after))
            or type(transition.cause) is not str or not 1<=len(transition.cause)<=80
            or type(request_id) is not str or not 1<=len(request_id)<=160):
        raise ValueError('Immutable current role resource transition required')
    fingerprint=hashlib.sha256(_json(asdict(transition)).encode()).hexdigest()
    old=db.execute('SELECT fingerprint FROM role_resource_receipts WHERE role_id=? AND request_id=?',
        (role_id,request_id)).fetchone()
    if old:
        if old[0]!=fingerprint:raise ValueError('Resource request ID reused with another intent')
        return ResourceMutationResult(request_id,read_role_resources(db,account_id,role_id,epoch,rules),True)
    current=read_role_resources(db,account_id,role_id,epoch,rules)
    if current!=transition.before:raise ValueError('Resource complete before snapshot is stale')
    _validate_caps(db,account_id,role_id,epoch,transition.after.caps,equipment_rules)
    if transition.cause in rules.combat_causes:
        expected=plan_combat_resources(current,transition.after.hp,transition.after.mp,rules)
    elif transition.cause in rules.source_causes:
        expected=plan_resource_source(current,transition.after.caps,transition.cause,rules)
    elif transition.cause in rules.resource_causes:
        expected=plan_resource_values(current,transition.after.hp,transition.after.mp,transition.cause,rules,
            current_caps=transition.after.caps)
    elif transition.cause in rules.equipment_causes or transition.cause=='ordinary_growth':
        expected=plan_resource_caps(current,transition.after.caps,transition.cause,rules)
    else:
        raise ValueError('Resource migration cannot be replayed as an ordinary mutation')
    if expected!=transition:raise ValueError('Resource transition differs from its reason policy')
    profile=_profile(db,role_id)
    encoded,_=_carrier(db,role_id)
    _write_carrier(db,role_id,encoded,transition.after)
    changed=db.execute('UPDATE role_resource_profiles SET source=? WHERE role_id=? AND policy=? AND source=?',
        (_json(asdict(transition.after.caps.source)),role_id,profile[0],profile[1])).rowcount
    if changed!=1:raise ValueError('Resource source changed during caller transaction')
    db.execute('INSERT INTO role_resource_receipts VALUES(?,?,?,?,?,?)',
        (role_id,request_id,fingerprint,transition.cause,transition.before.version,transition.after.version))
    return ResourceMutationResult(request_id,read_role_resources(db,account_id,role_id,epoch,rules),False)


def revive_task_dream_resources(db,account_id,role_id,epoch,expected,permit,*,rules,equipment_rules):
    """Trusted first-dream raw-death recovery in the caller's asset transaction.

    The Task host validates its durable admission/engine terminal before issuing
    the permit and joins task rewards/outbox to this same transaction. No Task
    private schema, connection, commit, migration or generic revive permission
    lives here. Retry receipts read the current carrier instead of healing again.
    """
    from task_dream_resources import plan_task_dream_revival
    _owner(db,account_id,role_id,epoch,rules)
    transition=plan_task_dream_revival(expected,permit)
    if role_id!=permit.role_id or expected.policy!=rules.revision:
        raise ValueError('Dream recovery role or current resource policy mismatch')
    request_id=permit.settlement_id+':dream-revive'
    fingerprint=hashlib.sha256(_json(dict(permit=asdict(permit),before=asdict(expected))).encode()).hexdigest()
    old=db.execute('SELECT fingerprint FROM role_resource_receipts WHERE role_id=? AND request_id=?',
                   (role_id,request_id)).fetchone()
    if old is not None:
        if old[0]!=fingerprint:raise ValueError('Dream revival receipt conflicts with its original terminal')
        return ResourceMutationResult(request_id,read_role_resources(db,account_id,role_id,epoch,rules),True)
    if type(epoch) is not type(permit.login_epoch) or epoch!=permit.login_epoch:
        raise ValueError('A new lease may only acknowledge an already committed dream recovery')
    current=read_role_resources(db,account_id,role_id,epoch,rules)
    if current!=expected:raise ValueError('Raw-dead dream resources or their source have changed')
    _validate_caps(db,account_id,role_id,epoch,expected.caps,equipment_rules)
    encoded,_=_carrier(db,role_id)
    _write_carrier(db,role_id,encoded,transition.after)
    db.execute('INSERT INTO role_resource_receipts VALUES(?,?,?,?,?,?)',
        (role_id,request_id,fingerprint,transition.cause,expected.version,transition.after.version))
    return ResourceMutationResult(request_id,read_role_resources(db,account_id,role_id,epoch,rules),False)
