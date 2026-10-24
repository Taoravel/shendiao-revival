"""Role growth request Adapter joining the caller's fenced transaction.

The role owner gates world state and publishes current level after commit.
No connection, commit, startup configuration read, mailbox or native send.
"""
from dataclasses import dataclass
from role_growth import request_manual_level,request_potential_allocation,read_growth
from role_attribute_storage import read_attribute_snapshot
from role_attribute_protocol import growth_refresh
from task_dialog_protocol import S_REFRESH_USER_EXP,encode_user_experience


@dataclass(frozen=True)
class GrowthActionResult:
    role_id: int
    request_id: str
    growth: object
    attributes: object
    messages: tuple


def _profile(db,account_id,role_id,epoch,resource_context):
    if resource_context is None:
        return read_attribute_snapshot(db,account_id,role_id,epoch)
    from role_growth import GrowthResourceContext
    from role_equipment_storage import current_resource_profile
    if type(resource_context) is not GrowthResourceContext:
        raise ValueError('Explicit current growth resource context required')
    return current_resource_profile(db,account_id,role_id,epoch,resource_context.inventory_snapshot,
        equipment_rules=resource_context.equipment_rules,resource_rules=resource_context.resource_rules)


def _require_profile(db,account_id,role_id,epoch,growth_rules,attribute_rules,resource_context):
    if growth_rules is None or attribute_rules is None:
        raise ValueError('Prepared ordinary growth and attribute policy required')
    before=_profile(db,account_id,role_id,epoch,resource_context)
    if (before.attributes.policy_revision!=attribute_rules.revision
            or attribute_rules.growth_policy!=growth_rules.revision):
        raise ValueError('Role growth display policy requires explicit migration')


def _result(db,account_id,role_id,epoch,request_id,resource_context):
    current=read_growth(db,account_id,role_id)
    attributes=_profile(db,account_id,role_id,epoch,resource_context)
    messages=((S_REFRESH_USER_EXP,encode_user_experience(current.experience)),growth_refresh(current,attributes))
    return GrowthActionResult(role_id,request_id,current,attributes,messages)


def manual_level_transaction(db,account_id,role_id,epoch,opaque_field,request_id,growth_rules,attribute_rules,*,resource_context=None):
    """One designed ordinary level per successful request, with durable replay.

    Explicit growth AND attributes are required. The old request receipt is an
    acknowledgement, never the authority for a new cache or display snapshot.
    Native encoding errors occur while all level/XP/point writes can roll back.
    The caller must roll back on any exception and send only after committing.
    """
    # Current role lease, complete explicit profile and existing growth revision
    # are checked before any mutation; this cannot create a legacy baseline.
    _require_profile(db,account_id,role_id,epoch,growth_rules,attribute_rules,resource_context)
    request_manual_level(db,account_id,role_id,epoch,opaque_field,request_id,growth_rules,attribute_rules,
        resource_context=resource_context)
    return _result(db,account_id,role_id,epoch,request_id,resource_context)


def allocation_transaction(db,account_id,role_id,epoch,deltas,request_id,growth_rules,attribute_rules,*,resource_context=None):
    """Commit internal V/I/S/END/AGI increments, not native wire field order.

    The role owner supplies its trusted request key; the domain helper resolves
    old receipts BEFORE choosing a current revision. New identical wire clicks
    are distinct operations and remain limited by the current free-point balance.
    """
    _require_profile(db,account_id,role_id,epoch,growth_rules,attribute_rules,resource_context)
    request_potential_allocation(db,account_id,role_id,epoch,deltas,request_id,growth_rules,attribute_rules,
        resource_context=resource_context)
    return _result(db,account_id,role_id,epoch,request_id,resource_context)
