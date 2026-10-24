"""Explicit equipment/sealing basis and current projection in a caller transaction.

No connection, commit, implicit old-character migration, live cache or sender.
Final totals are recomputed from current growth/assets, not a second mutable
attribute ledger that must be synchronized with every growth command.
"""
from dataclasses import asdict
import hashlib
import json
from types import MappingProxyType

from role_attribute_storage import read_attribute_snapshot,read_naked_attributes
from role_equipment import (EquipmentAttributeBasis,EquipmentAttributeRules,project_equipment,
    resource_caps_from_projection,project_equipment_totals,combine_equipment_resources)
from role_resource_plan import ResourceProjection
from role_resource_storage import read_role_resources,ResourceNotInitialized,apply_resource_transition
from role_resource_plan import plan_resource_source
from inventory import InventorySnapshot


class EquipmentBasisNotInitialized(ValueError):
    pass


def prepare_equipment_attribute_storage(db):
    """Startup-only schema. No character baseline is created by preparation."""
    db.executescript('''CREATE TABLE IF NOT EXISTS role_equipment_attribute_bases (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id), basis TEXT NOT NULL);''')


def _owner(db, account_id, role_id, epoch, rules):
    if type(epoch) is int and 0 < epoch < 2**63:
        lease_key=str(epoch)
    elif type(epoch) is str and 1 <= len(epoch) <= 128:
        lease_key=epoch  # Opaque strings retain leading zeros and all content.
    else:
        raise ValueError('Valid equipment attribute login lease required')
    if not db.in_transaction:
        raise ValueError('Equipment attribute owner transaction/current lease required')
    row=db.execute('SELECT r.shape FROM roles r JOIN role_leases l ON l.role_id=r.id '
        'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
        (role_id,account_id,lease_key)).fetchone()
    if row is None or row[0] not in rules.shape_characters:
        raise ValueError('Equipment attribute role, lease or original shape mismatch')
    return rules.shape_characters[row[0]]


def _read(db, role_id, character_id, rules):
    row=db.execute('SELECT basis FROM role_equipment_attribute_bases WHERE role_id=?',(role_id,)).fetchone()
    if row is None:
        return None
    basis=EquipmentAttributeBasis(**json.loads(row[0]))
    if (basis.role_id!=role_id or basis.character_id!=character_id or basis.policy!=rules.revision):
        raise ValueError('Stored equipment basis requires explicit policy reconciliation')
    return basis


def read_equipment_attribute_basis(db, account_id, role_id, epoch, rules):
    """Missing is None, never an invented zero sealing value."""
    character_id=_owner(db,account_id,role_id,epoch,rules)
    return _read(db,role_id,character_id,rules)


def equipment_attribute_rules_transaction(db,account_id,role_id,epoch,policies):
    """Select the exact stored basis policy in the caller's current lease.

    Missing basis raises precisely, never supplies a default policy/basis or
    upgrades old unknown1240. Callers use this same frozen result for totals,
    resources and consumers throughout this transaction; no live role cache.
    """
    if (type(policies) is not MappingProxyType or not policies
            or any(type(rules) is not EquipmentAttributeRules or key!=rules.revision
                   for key,rules in policies.items())):
        raise ValueError('Frozen startup equipment policies required')
    reference=next(iter(policies.values()))
    if any(rules.shape_characters!=reference.shape_characters for rules in policies.values()):
        raise ValueError('Equipment policies require the same original shape identities')
    character_id=_owner(db,account_id,role_id,epoch,reference)
    row=db.execute('SELECT basis FROM role_equipment_attribute_bases WHERE role_id=?',(role_id,)).fetchone()
    if row is None:raise EquipmentBasisNotInitialized('Explicit equipment policy basis required')
    basis=EquipmentAttributeBasis(**json.loads(row[0]))
    rules=policies.get(basis.policy)
    if rules is None:raise ValueError('Stored equipment policy is unavailable; explicit reconciliation required')
    if (basis.role_id!=role_id or basis.character_id!=character_id
            or (basis.seal_resistance is None)!=(rules.new_role_seal_resistance is None)):
        raise ValueError('Stored equipment basis and selected policy disagree')
    return rules


def initialize_equipment_attribute_basis(db, account_id, role_id, epoch, basis, rules):
    """Trusted explicit basis only; caller proves its recorded creation/migration.

    A new restoration character uses the documented0 with its creation ID.
    An old character needs a supplied known value/source. Initialization can
    join first-login provenance redemption or an explicitly reconciled asset
    transaction. Repeated exact initialization does not reset the basis.
    """
    character_id=_owner(db,account_id,role_id,epoch,rules)
    if (type(basis) is not EquipmentAttributeBasis or basis.role_id!=role_id
            or basis.character_id!=character_id or basis.policy!=rules.revision or basis.revision!=0):
        raise ValueError('Explicit original-character equipment basis required')
    old=_read(db,role_id,character_id,rules)
    if old is not None:
        if old!=basis:
            raise ValueError('Existing equipment basis cannot be reset or re-sourced')
        return old
    db.execute('INSERT INTO role_equipment_attribute_bases VALUES(?,?)',
        (role_id,json.dumps(asdict(basis),sort_keys=True,separators=(',',':'))))
    return basis


def current_equipment_projection(db, account_id, role_id, epoch, inventory_snapshot, rules):
    """Read current naked growth/basis; validate caller's same-transaction assets.

    Call Inventory.immutable_snapshot_transaction(db) after any equip/wear/repair
    or task mutations, then encode this projection before committing. Repeated
    commands read current assets; old equipment event receipts are insufficient.
    """
    basis=_current_equipment_basis(db,account_id,role_id,epoch,inventory_snapshot,rules)
    bare=read_attribute_snapshot(db,account_id,role_id,epoch)
    return project_equipment(bare,inventory_snapshot,basis,rules)


def _current_equipment_basis(db,account_id,role_id,epoch,inventory_snapshot,rules):
    character_id=_owner(db,account_id,role_id,epoch,rules)
    basis=_read(db,role_id,character_id,rules)
    if basis is None:
        raise EquipmentBasisNotInitialized('Explicit equipment attribute basis required')
    row=db.execute('SELECT revision FROM inventory_versions WHERE role_id=?',(role_id,)).fetchone()
    revision=row[0] if row else 0
    if (type(inventory_snapshot) is not InventorySnapshot or inventory_snapshot.role_id!=role_id
            or type(inventory_snapshot.inventory_revision) is not int
            or inventory_snapshot.inventory_revision!=revision):
        raise ValueError('Inventory snapshot is stale or foreign to equipment projection')
    return basis


def current_equipment_totals(db,account_id,role_id,epoch,inventory_snapshot,rules):
    """Current transaction stats, independent of either resource contract."""
    basis=_current_equipment_basis(db,account_id,role_id,epoch,inventory_snapshot,rules)
    attrs=read_naked_attributes(db,account_id,role_id,epoch)
    return project_equipment_totals(attrs,inventory_snapshot,basis,rules)


def current_resource_profile(db,account_id,role_id,epoch,inventory_snapshot,*,equipment_rules,resource_rules):
    """Read one exact final profile; pending source changes refuse, never heal.

    Caller settles asset/growth and resource transitions in this same role
    transaction before encoding. Missing explicit resource provenance refuses.
    """
    totals=current_equipment_totals(db,account_id,role_id,epoch,inventory_snapshot,equipment_rules)
    resources=read_role_resources(db,account_id,role_id,epoch,resource_rules)
    return combine_equipment_resources(totals,resources)


def synchronize_inventory_resource_source(db,account_id,role_id,epoch,inventory_snapshot,request_id,*,
        resource_rules,equipment_rules,replayed):
    """Join a real inventory mutation's caller transaction, never a login read.

    The owning domain validates its durable request intent and supplies its
    actual replay decision. Fresh no-cap mutations settle only provenance;
    paid replays strictly read current profile and never repair pending source.
    Unmigrated roles return None without requiring a fabricated gear baseline.
    Caller still pre-encodes native replies and commits/rolls back all writes.
    """
    if (type(equipment_rules) is not EquipmentAttributeRules
            or type(inventory_snapshot) is not InventorySnapshot or inventory_snapshot.role_id!=role_id
            or type(request_id) is not str or not 1<=len(request_id)<=160 or type(replayed) is not bool):
        raise ValueError('Current inventory and durable domain replay decision required')
    try:before=read_role_resources(db,account_id,role_id,epoch,resource_rules)
    except ResourceNotInitialized:return None
    totals=current_equipment_totals(db,account_id,role_id,epoch,inventory_snapshot,equipment_rules)
    if replayed:
        combine_equipment_resources(totals,before)
        return before
    transition=plan_resource_source(before,resource_caps_from_projection(totals),'inventory_change',resource_rules)
    if not transition.changed:return before
    identity='inventory-source:'+hashlib.sha256(request_id.encode('utf-8')).hexdigest()
    return apply_resource_transition(db,account_id,role_id,epoch,transition,identity,
        rules=resource_rules,equipment_rules=equipment_rules).resources


def current_resource_projection_source(db,account_id,role_id,epoch,rules):
    """Current source identity without reading or modifying resource values."""
    character_id=_owner(db,account_id,role_id,epoch,rules)
    basis=_read(db,role_id,character_id,rules)
    if basis is None:raise EquipmentBasisNotInitialized('Explicit equipment attribute basis required')
    attrs=read_naked_attributes(db,account_id,role_id,epoch)
    if attrs.policy_revision!=rules.attribute_policy:
        raise ValueError('Resource source attribute policy mismatch')
    row=db.execute('SELECT revision FROM inventory_versions WHERE role_id=?',(role_id,)).fetchone()
    return ResourceProjection(role_id,attrs.baseline_revision,attrs.growth_revision,attrs.policy_revision,
        row[0] if row else 0,basis.revision,basis.policy)


