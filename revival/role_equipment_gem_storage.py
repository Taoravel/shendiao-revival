"""Current complete gem profile in a caller-owned role transaction.

Only explicit extra-attribute provenance is stored here. HP/MP, source CAS and
resource receipts remain in the root's sole resource carrier. Startup prepares
schema; role paths neither connect/commit nor send. This optional policy must
be routed through this projector by every consumer before runtime activation.
"""
from dataclasses import asdict,dataclass
import hashlib
import json

from role_attribute_storage import read_naked_attributes
from role_equipment import EquipmentRoleSnapshot,resource_caps_from_projection,combine_equipment_resources
from role_equipment_storage import read_equipment_attribute_basis,EquipmentBasisNotInitialized
from role_resource_plan import plan_resource_caps,plan_resource_source
from role_resource_storage import read_role_resources,apply_resource_transition
from role_equipment_gems import GemEquipmentRules,GemExtraBasis,GemEquipmentSource,project
import equipment_gem_storage as sockets
import equipment_gem_score_storage as scores


@dataclass(frozen=True)
class GemEquipmentProfile:
    core: EquipmentRoleSnapshot
    extras: tuple
    raw_modifiers: tuple
    source_items: tuple


def prepare(db):
    """Startup-only metadata; no automatic historical or new-role baseline."""
    db.execute('''CREATE TABLE IF NOT EXISTS role_equipment_gem_extra_bases (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id),origin TEXT NOT NULL,
        basis TEXT NOT NULL)''')


def _basis(db,inventory,rules):
    if type(rules) is not GemEquipmentRules:
        raise ValueError('Frozen complete gem rules required')
    inventory.immutable_snapshot_transaction(db)
    basis=read_equipment_attribute_basis(db,inventory.account_id,inventory.role_id,inventory.epoch,rules.carrier_rules)
    if basis is None:raise EquipmentBasisNotInitialized('Explicit complete gem equipment basis required')
    return basis


def _check(extra,basis,rules):
    if (type(extra) is not GemExtraBasis or extra.role_id!=basis.role_id
            or extra.policy!=rules.revision or extra.equipment_basis_revision!=basis.revision
            or extra.source_ref!=basis.source_id):
        raise ValueError('Extra baseline must share the explicit equipment policy and source')


def read_extra(db,inventory,rules):
    """Missing stays unknown; reads never initialize or reconcile provenance."""
    basis=_basis(db,inventory,rules)
    row=db.execute('SELECT origin,basis FROM role_equipment_gem_extra_bases WHERE role_id=?',
        (inventory.role_id,)).fetchone()
    if row is None:return None
    if row[0]!='explicit_known_ungemmed_extras':raise ValueError('Unknown extra baseline provenance')
    record=json.loads(row[1]);record['values']=tuple(tuple(pair) for pair in record['values'])
    extra=GemExtraBasis(**record);_check(extra,basis,rules)
    return extra


def initialize_extra(db,inventory,rules,extra,origin):
    """Trusted explicit source only; exact initialization retries are read-only."""
    basis=_basis(db,inventory,rules);_check(extra,basis,rules)
    if origin!='explicit_known_ungemmed_extras':raise ValueError('Explicit known ungemmed extra source required')
    old=read_extra(db,inventory,rules)
    if old is not None:
        if old!=extra:raise ValueError('Extra baseline cannot be reset or re-sourced')
        return old
    db.execute('INSERT INTO role_equipment_gem_extra_bases VALUES(?,?,?)',
        (inventory.role_id,origin,json.dumps(asdict(extra),sort_keys=True,separators=(',',':'))))
    return extra


def read_totals(db,inventory,rules):
    """Recompute from actual current assets and all known worn socket sources."""
    basis=_basis(db,inventory,rules);extra=read_extra(db,inventory,rules)
    if extra is None:raise EquipmentBasisNotInitialized('Explicit complete extra baseline required')
    snapshot=inventory.immutable_snapshot_transaction(db)
    attrs=read_naked_attributes(db,inventory.account_id,inventory.role_id,inventory.epoch)
    sources=[]
    for item in snapshot.items:
        if item.equipment_slot is None:continue
        socket=sockets.read(db,inventory,rules.gem_rules,item.id)
        score=scores.read(db,inventory,rules.score_rules,item.id)
        if socket is None or score is None:raise EquipmentBasisNotInitialized('Known worn socket and pre-gem score required')
        sources.append(GemEquipmentSource(socket,score))
    return project(rules,attrs,snapshot,basis,extra,tuple(sources))


def _resources(db,inventory,resource_rules):
    return read_role_resources(db,inventory.account_id,inventory.role_id,inventory.epoch,resource_rules)


def _profile(totals,resources):
    return GemEquipmentProfile(combine_equipment_resources(totals.core,resources),
        totals.extras,totals.raw_modifiers,totals.source_items)


def read_profile(db,inventory,rules,resource_rules):
    """Strict current read; pending source/cap changes refuse instead of healing."""
    return _profile(read_totals(db,inventory,rules),_resources(db,inventory,resource_rules))


def _identity(prefix,request_id):
    if type(request_id) is not str or not 1<=len(request_id)<=160:
        raise ValueError('Stable admitted domain request identity required')
    return prefix+hashlib.sha256(request_id.encode('utf-8')).hexdigest()


def settle_equipment(db,inventory,rules,resource_rules,before,request_id):
    """Fresh equipment-effect mutation only, joined to the caller's transaction.

    The owning domain must establish its durable replay decision first. Paid
    replays call read_profile, never reconstruct a transition from current HP.
    The designed equip cause preserves absolute resources, clips lowered caps
    and never revives. No task EquipmentEvent is fabricated by this Module.
    """
    identity=_identity('gem-equipment:',request_id)
    totals=read_totals(db,inventory,rules)
    transition=plan_resource_caps(before,resource_caps_from_projection(totals.core),'equip',resource_rules)
    result=apply_resource_transition(db,inventory.account_id,inventory.role_id,inventory.epoch,
        transition,identity,rules=resource_rules,equipment_rules=rules.carrier_rules)
    return _profile(totals,result.resources)


def synchronize_inventory_source(db,inventory,rules,resource_rules,request_id,*,replayed):
    """Unchanged-cap asset mutation; paid replays strictly read current source."""
    identity=_identity('gem-inventory-source:',request_id)
    if type(replayed) is not bool:raise ValueError('Durable domain replay decision required')
    totals=read_totals(db,inventory,rules);before=_resources(db,inventory,resource_rules)
    if replayed:
        _profile(totals,before)
        return before
    transition=plan_resource_source(before,resource_caps_from_projection(totals.core),'inventory_change',resource_rules)
    if not transition.changed:return before
    return apply_resource_transition(db,inventory.account_id,inventory.role_id,inventory.epoch,
        transition,identity,rules=resource_rules,equipment_rules=rules.carrier_rules).resources
