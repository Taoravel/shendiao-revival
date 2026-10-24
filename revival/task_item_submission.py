"""Pure validation of explicitly selected NPC task items.

The role owner supplies current frozen ItemState rows from its transaction.
Client instance keys are requests, never inventory evidence. Actual debits are
carried by TaskPlan and applied by the common completion transaction.
"""
from inventory import ItemState
from task_domain import TaskDomain, TaskEvidence, supports_item_submission
from task_item_protocol import NpcItemSubmission


def _items(role_id, items):
    if (type(items) is not tuple or any(not isinstance(x,ItemState) or x.role_id!=role_id
            or any(type(v) is not int or v<=0 for v in (x.id,x.template_id,x.quantity))
            or type(x.binding) is not int or x.binding not in (0,1) for x in items)
            or len({x.id for x in items})!=len(items)):
        raise ValueError('Current immutable owned task item rows required')
    return {x.id:x for x in items}


def item_objective_available(actor, task, items):
    """Current carried count, not a durable collection counter or client claim."""
    rows=_items(actor.role_id,items)
    if not supports_item_submission(task):
        return False
    return sum(x.quantity for x in rows.values() if x.template_id==task['target']['id']
               and x.equipment_slot is None and x.binding in (0,1)) >= task['target']['count']


def plan_item_objective(actor, snapshot, command, ticket, current, items, resources, *, now_ms):
    """Validate the native selected keys, same NPC ticket and original objective.

    Exact total and duplicate-key refusal are server restoration policy. We do
    not consume an overselected stack or invent a priority for other items.
    """
    if (not isinstance(command,NpcItemSubmission) or command.submit_type!=1
            or ticket is None or now_ms>=ticket.deadline_ms
            or (ticket.role_id,ticket.login_epoch)!=(actor.role_id,actor.login_epoch)
            or (current.role_id,current.login_epoch)!=(actor.role_id,actor.login_epoch)
            or current.address!=ticket.address or current.version!=ticket.position_version
            or current.state!='active' or command.task_id!=ticket.task_id
            or command.npc_key!=ticket.entity_key):
        raise ValueError('Stale or mismatched NPC item submission')
    task=resources.definitions.get(command.task_id)
    if (task is None or not supports_item_submission(task)
            or task['target']['npc_id']!=ticket.npc_id or task['target']['map_id']!=ticket.address.map_id):
        raise ValueError('Unsupported task item objective')
    units=command.units
    if (type(units) is not tuple or not 1<=len(units)<=256
            or any(type(x) is not tuple or len(x)!=2 or any(type(v) is not int or not 0<v<=0x7fffffff for v in x) for x in units)
            or len({key for key,_ in units})!=len(units)
            or sum(amount for _,amount in units)!=task['target']['count']):
        raise ValueError('Task requires the exact original quantity and distinct selected keys')
    rows=_items(actor.role_id,items)
    for key,amount in units:
        item=rows.get(key)
        if (item is None or item.template_id!=task['target']['id'] or item.quantity<amount
                or item.equipment_slot is not None or type(item.binding) is not int or item.binding not in (0,1)):
            raise ValueError('Selected task item is unavailable, equipped or the wrong template')
    evidence=TaskEvidence(command.task_id,actor.role_id,actor.login_epoch,'npc_items_submitted',
        ticket.source_id,ticket.address.map_id,ticket.npc_id,task['target']['id'],tuple(sorted(units)))
    return TaskDomain(resources).plan(actor,snapshot,'complete',command.task_id,evidence=evidence)
