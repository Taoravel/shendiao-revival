"""Explicit task-side composition of public role resource Interfaces.

No resource migration, private SQL, derived attribute algorithm or second HP/MP
carrier. Source-only inventory stages and ordinary growth remain distinct.
"""
from role_growth import GrowthResourceContext
from role_resource_storage import read_role_resources,ResourceNotInitialized,apply_resource_transition
from role_resource_plan import plan_resource_source
from role_equipment_storage import current_equipment_totals,current_resource_profile
from role_equipment import resource_caps_from_projection


def _profile(db,account_id,role_id,epoch,resource_rules,equipment_rules):
    if resource_rules is None and equipment_rules is None:return None
    if resource_rules is None or equipment_rules is None:
        raise ValueError('Task resource and equipment rules must be supplied together')
    try:return read_role_resources(db,account_id,role_id,epoch,resource_rules)
    except ResourceNotInitialized:return None


def current_task_resource_profile(db,actor,inventory,resource_rules,equipment_rules):
    """Optional migrated profile, strict current source; never fixes a read."""
    if _profile(db,actor.account_id,actor.role_id,actor.login_epoch,resource_rules,equipment_rules) is None:
        return None
    assets=inventory.immutable_snapshot_transaction(db,epoch=actor.login_epoch)
    return current_resource_profile(db,actor.account_id,actor.role_id,actor.login_epoch,assets,
        equipment_rules=equipment_rules,resource_rules=resource_rules)


def synchronize_task_inventory_source(db,account_id,role_id,epoch,task_id,inventory,resource_rules,equipment_rules,*,phase):
    """Explicit mutation stage: settle actual bag/pet-only revision changes.

    Receipt identity follows this task phase and monotonic before/after asset
    revisions. An already current source is a read, including paid replays; no
    new transition is invented from a later HP value using an old receipt key.
    """
    before=_profile(db,account_id,role_id,epoch,resource_rules,equipment_rules)
    if before is None:return None
    if phase not in ('before-exp','after-items','master-card'):
        raise ValueError('Unknown task resource stage')
    assets=inventory.immutable_snapshot_transaction(db,epoch=epoch)
    caps=resource_caps_from_projection(current_equipment_totals(db,account_id,role_id,epoch,assets,equipment_rules))
    if caps!=before.caps:
        transition=plan_resource_source(before,caps,'inventory_change',resource_rules)
        identity=f'task-resource:{task_id}:{phase}:{before.caps.source.inventory_revision}:{caps.source.inventory_revision}'
        apply_resource_transition(db,account_id,role_id,epoch,transition,identity,
            rules=resource_rules,equipment_rules=equipment_rules)
    return GrowthResourceContext(assets,equipment_rules,resource_rules)
