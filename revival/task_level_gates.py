"""Trusted ordinary role-level goals, joining the existing role transaction.

No client reward request is an event here. The current actor is loaded inside
the transaction after committed/planned character growth, or during role resume.
"""
from dataclasses import dataclass
from task_domain import TaskDomain,TaskEvidence,supports_level_gate
from task_persistence import load_task_state
from task_workflow import complete_task_transaction,completion_messages
from task_protocol import S_REFRESH_SCENARIO_QUEST_VALUE,encode_scenario_values


@dataclass(frozen=True)
class TaskLevelAdvancement:
    completions: tuple
    progress: tuple
    ready_remaining: tuple


def _scope(db,account_id,role_id,epoch,inventory):
    if (not db.in_transaction or inventory.account_id!=account_id or inventory.role_id!=role_id
            or not db.execute('SELECT 1 FROM role_leases WHERE role_id=? AND epoch=? AND active=1',(role_id,epoch)).fetchone()):
        raise ValueError('Current role transaction required for level goals')


def _ready(actor,snapshot,resources):
    return tuple(q for q in sorted(snapshot.active) if q in resources.definitions
                 and supports_level_gate(resources.definitions[q])
                 and resources.definitions[q]['level']['min']<=actor.level<=155)


def advance_level_gates(db,account_id,role_id,epoch,resources,inventory,*,growth_rules=None,
                        attribute_rules=None,currency_rules=None,pet_experience_rules=None,budget=32):
    """Check only enrolled goals, at most budget completions in this transaction.

    Call after trusted role growth, chapter activation or resume, never from an
    untrusted claimed level. Failure rolls back the caller's growth/reward work.
    A nonempty ready_remaining requests a later bounded role-owner continuation.
    """
    _scope(db,account_id,role_id,epoch,inventory)
    if type(budget) is not int or not 1<=budget<=32:
        raise ValueError('Level goal completion budget must be1..32')
    completed=[]
    for _ in range(budget):
        actor,snapshot=load_task_state(db,account_id,role_id,epoch)
        ready=_ready(actor,snapshot,resources)
        if not ready:
            break
        ident=ready[0]
        evidence=TaskEvidence(ident,role_id,epoch,'role_level_reached',
                              f'level-goal:{role_id}:{ident}',reference_id=actor.level)
        plan=TaskDomain(resources).plan(actor,snapshot,'complete',ident,evidence=evidence)
        completed.append(complete_task_transaction(db,actor,plan,f'level-goal:{ident}',resources,inventory,
            growth_rules,attribute_rules,currency_rules,pet_experience_rules))
    actor,snapshot=load_task_state(db,account_id,role_id,epoch)
    progress=tuple((S_REFRESH_SCENARIO_QUEST_VALUE,encode_scenario_values(q,actor.level,0))
                   for q in sorted(snapshot.active) if q in resources.definitions and supports_level_gate(resources.definitions[q]))
    return TaskLevelAdvancement(tuple(completed),progress,_ready(actor,snapshot,resources))


def level_gate_messages(result):
    """Send only after the encompassing role transaction commits successfully."""
    return tuple(message for completion in result.completions for message in completion_messages(completion))+result.progress
