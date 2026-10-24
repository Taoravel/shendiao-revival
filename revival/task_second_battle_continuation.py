"""Original CG10001 task activation after an actually settled AI8027 victory.

RoleOwner calls in the SAME victory consumer transaction. No movie, CEnd,
map change, combat result or reward is produced by this continuation Module.
"""
from task_second_battle import SecondBattleRules
from task_persistence import load_task_state,apply_task_plan
from task_battle import read_completed_task_battle_proof
from task_first_skill_proof import read_completed_first_skill_proof
from task_newbie_chapter import read_newbie_chapter
from task_domain import TaskDomain
from task_chains import continue_task_chain
from world_story_instances import StoryInstanceIntent,load_story_instance_transaction
from world_transfer_storage import load_map_instance_transaction
from tasks import _plain


def reconcile_second_battle_successor_transaction(db,aid,rid,epoch,resources,rules,previous_task_id):
    """Return only a newly active original CG task, never finish or play it.

    Requires the original unique durable victory receipt, original creation
    route, actual teaching and unchanged adopted private directory. Main still
    owns raw combat resources, producer/consumer/outbox and final message
    encoding in this same transaction; any later failure requires rollback.
    Settled retries should use the existing pure current-state battle query.
    """
    if type(rules) is not SecondBattleRules:raise ValueError('Prepared second-dream rules required')
    task=rules.definitions.get(previous_task_id)
    if task is None or _plain(task)!=_plain(resources.definitions.get(previous_task_id)):
        raise ValueError('No original second-dream battle continuation')
    actor,state=load_task_state(db,aid,rid,epoch)
    chapter=read_newbie_chapter(db,aid,rid,epoch,rules.first_skills.chapter_rules)
    if chapter is None or chapter.phase!='completed':
        raise ValueError('Second-dream continuation needs its original completed creation chapter')
    origin=chapter.origin;route=origin.route;key=(route.character_id,route.school_id)
    if rules.route_tasks.get(key)!=previous_task_id:
        raise ValueError('Second-dream continuation differs from original creation route')
    read_completed_task_battle_proof(db,aid,rid,epoch,resources,rules.battles,previous_task_id)
    teaching=read_completed_first_skill_proof(db,aid,rid,epoch,resources,rules.first_skills,task['incoming_ids'][0])
    edges=tuple(task['next_ids'])
    if len(edges)!=1:raise ValueError('Second-dream battle has no unique original CG successor')
    q=edges[0];cg=resources.definitions[q]
    if (cg['type']!=10 or int(cg['attributes']['ScenarioInfoAnimationID'])!=10001
            or (cg['target']['map_id'],cg['target']['npc_id'])!=(1501,10084)):
        raise ValueError('Second-dream successor is not the separate original CG10001 task')
    if q in state.active|state.completed:return ()
    if (any(100000<=x<200000 for x in state.active)
            or any(x in state.active|state.completed for x in cg['next_ids'])):
        raise ValueError('Another main task or later CG successor already started')
    checkpoint=load_map_instance_transaction(db,aid,rid,epoch)
    if checkpoint is None or checkpoint.address.map_id!=1501 or teaching.source_address!=checkpoint.address:
        raise ValueError('Second-dream continuation needs its adopted private source')
    bloodmark=rules.first_skills.story_rules.source_tasks[key]
    if bloodmark not in state.completed:raise ValueError('Original bloodmark completion required')
    canonical=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,origin.route_fingerprint,bloodmark)
    load_story_instance_transaction(db,aid,rid,epoch,canonical,rules.first_skills.story_rules,
        expected_address=checkpoint.address)
    for action in ('offer','accept'):
        actor,state=load_task_state(db,aid,rid,epoch)
        if action=='offer' and q in state.offered:continue
        apply_task_plan(db,actor,TaskDomain(resources).plan(actor,state,action,q),
            f'second-dream-next:{previous_task_id}:{q}:{action}')
    continue_task_chain(db,aid,rid,epoch,previous_task_id,resources)
    return (q,)
