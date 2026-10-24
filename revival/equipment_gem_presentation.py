"""Public equipment-domain adapter for paired gem score/color persistence.

Joins the same role transaction immediately after the socket source CAS. This
extends the equipment writer without changing its frozen clean provider files.
No receipt, assets, connection, commit, root-resource write or network send.
"""
from dataclasses import asdict
import json
from equipment_gem_storage import EquipmentGemBasis
import equipment_gem_storage as sockets
import equipment_gem_score_storage as scores
from equipment_gem_score import GemScoreChange,project
from inventory import ItemState
from equipment_detail import EquipmentDetail
from equipment_condition import EquipmentCondition


def _immutable_item(item):
    return (type(item) is ItemState and all(type(v) is int for v in
        (item.id,item.role_id,item.template_id,item.quantity,item.slot,item.binding))
        and (item.equipment_slot is None or type(item.equipment_slot) is int)
        and item.quality is None and type(item.detail) is EquipmentDetail and type(item.condition) is EquipmentCondition)


def apply(db,inventory,gem_rules,score_rules,before,saved,change):
    """CAS the presentation of the just-saved complete gem state.

    Caller must roll back the entire outer transaction on any exception. Paid
    settlement must skip this writer and read current sources without repair.
    """
    if (type(before) is not EquipmentGemBasis or type(saved) is not EquipmentGemBasis
            or type(change) is not GemScoreChange or type(change.old_contribution) is not int
            or type(change.new_contribution) is not int or not _immutable_item(change.before) or not _immutable_item(change.after)
            or before.account_id!=inventory.account_id
            or saved.account_id!=inventory.account_id or before.item.role_id!=inventory.role_id
            or saved.item.role_id!=inventory.role_id or before.item!=saved.item
            or saved.state.version!=before.state.version+1
            or saved.inventory_revision!=before.inventory_revision+1
            or saved.equipment_skill!=before.equipment_skill or saved.origin!='socket_change'
            or before.detail_source!=saved.detail_source or before.condition_source!=saved.condition_source):
        raise ValueError('Complete immediate socket-CAS transition required before presentation')
    current=sockets.read(db,inventory,gem_rules,saved.item.id)
    if current!=saved:raise ValueError('Current score/color source changed after socket CAS')
    baseline=scores.read(db,inventory,score_rules,saved.item.id)
    if baseline is None:raise ValueError('Explicit durable pre-gem score baseline required')
    expected=project(score_rules,gem_rules,current.item,before.state,current.state,baseline)
    if change!=expected:raise ValueError('Gem presentation differs from the authoritative score policy')
    detail_changed=expected.after.detail!=current.item.detail
    condition_changed=expected.after.condition!=current.item.condition
    if not detail_changed and not condition_changed:return current
    if detail_changed:
        count=db.execute('UPDATE inventory_equipment_details SET detail=? WHERE item_key=? AND revision=? AND origin=? AND detail=? '
            'AND EXISTS(SELECT 1 FROM inventory_items WHERE id=? AND role_id=? AND quantity=1)',
            (json.dumps(asdict(expected.after.detail)),current.item.id,*current.detail_source,current.item.id,inventory.role_id)).rowcount
        if count!=1:raise ValueError('Equipment detail score source CAS failed')
    if condition_changed:
        count=db.execute('UPDATE inventory_equipment_conditions SET state=? WHERE item_key=? AND revision=? AND state=? '
            'AND EXISTS(SELECT 1 FROM inventory_items WHERE id=? AND role_id=? AND quantity=1)',
            (json.dumps(asdict(expected.after.condition)),current.item.id,*current.condition_source,current.item.id,inventory.role_id)).rowcount
        if count!=1:raise ValueError('Equipment condition color source CAS failed')
    if db.execute('UPDATE inventory_versions SET revision=revision+1 WHERE role_id=? AND revision=?',
            (inventory.role_id,current.inventory_revision)).rowcount!=1:
        raise ValueError('Equipment presentation inventory source CAS failed')
    return sockets.read(db,inventory,gem_rules,current.item.id)
