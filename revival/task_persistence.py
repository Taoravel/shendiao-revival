"""Task Adapter joining the role owner's transaction; never connects/commits.

Caller fences login_epoch in its owner transaction before invoking this module.
Completion writes an outbox effect, NOT a claim that rewards have been granted.
"""
from dataclasses import dataclass
import hashlib
import json
from task_domain import TaskActor, TaskSnapshot, TaskPlan, valid_task_epoch


@dataclass(frozen=True)
class TaskReceipt:
    request_id: str
    role_id: int
    revision: int
    effect_id: str


def _owner(db, account_id, role_id):
    if not db.in_transaction:
        raise ValueError('Task operation requires the role owner transaction')
    role = db.execute('SELECT level,shape FROM roles WHERE account_id=? AND id=?', (account_id, role_id)).fetchone()
    if role is None:
        raise ValueError('Task role ownership mismatch')
    return role


def load_task_state(db, account_id, role_id, login_epoch):
    """One transaction-consistent immutable role/task snapshot."""
    level, shape = _owner(db, account_id, role_id)
    actor = TaskActor(account_id, role_id, login_epoch, level, shape)
    revision = db.execute('SELECT revision FROM task_versions WHERE role_id=?', (role_id,)).fetchone()
    journal = tuple(db.execute('SELECT task_id,state FROM task_journal WHERE role_id=?', (role_id,)))
    snapshot = TaskSnapshot(role_id, revision[0] if revision else 0,
        frozenset(r[0] for r in db.execute('SELECT task_id FROM task_offers WHERE role_id=?', (role_id,))),
        frozenset(q for q, state in journal if state == 'active'),
        frozenset(q for q, state in journal if state == 'completed'),
        frozenset(r[0] for r in db.execute('SELECT task_id FROM task_tracking WHERE role_id=?', (role_id,))))
    return actor, snapshot


def _snapshot_record(snapshot):
    return {'role_id': snapshot.role_id, 'revision': snapshot.revision,
            **{k: sorted(getattr(snapshot, k)) for k in ('offered', 'active', 'completed', 'tracked')}}


def get_task_receipt(db, account_id, role_id, request_id):
    """Lookup after reconnect before replanning; caller checks its current epoch.

    The original command fingerprint remains immutable. A recovered receipt is
    only an acknowledgement of that operation, not permission for new rewards.
    """
    _owner(db, account_id, role_id)
    row = db.execute('SELECT receipt FROM task_command_receipts WHERE role_id=? AND request_id=?',
                     (role_id, request_id)).fetchone()
    return TaskReceipt(**json.loads(row[0])) if row else None


def apply_task_plan(db, actor, plan, request_id):
    """Apply a trusted pure plan, with stale-version refusal and durable retry ID.

    Role owner begins/commits/rolls back; it can join other asset changes before
    commit. This function makes no cross-module calls and returns no ciphertext.
    Retrying the same request returns its recorded receipt; reusing an ID with
    different intent fails, including changed evidence or reward instructions.
    """
    _owner(db, actor.account_id, actor.role_id)
    if (not isinstance(plan, TaskPlan) or plan.role_id != actor.role_id
            or plan.login_epoch != actor.login_epoch or not valid_task_epoch(actor.login_epoch)
            or plan.before.role_id != actor.role_id or plan.after.role_id != actor.role_id
            or type(request_id) is not str or not 1 <= len(request_id) <= 160):
        raise ValueError('Invalid task plan scope or retry key')
    record = {'role': actor.role_id, 'epoch': actor.login_epoch, 'action': plan.action,
              'task_id': plan.task_id, 'before': _snapshot_record(plan.before),
              'after': _snapshot_record(plan.after), 'rewards': plan.reward_scalars,
              'items': plan.reward_items, 'next_ids': plan.next_ids, 'event': plan.source_event,
              'continuation_fields': plan.continuation_fields}
    if plan.objective_debits:
        record['objective_debits']=plan.objective_debits
    if plan.reward_item_selectors:
        record['reward_item_selectors']=plan.reward_item_selectors
        record['reward_role_config_id']=plan.reward_role_config_id
    if plan.completion_effect_id:
        record['completion_effect_id']=plan.completion_effect_id
    if plan.completion_finish_dialogue:
        record['completion_finish_dialogue']=plan.completion_finish_dialogue
    fingerprint = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    existing = db.execute('SELECT fingerprint,receipt FROM task_command_receipts WHERE role_id=? AND request_id=?',
                          (actor.role_id, request_id)).fetchone()
    if existing:
        if existing[0] != fingerprint:
            raise ValueError('Task request ID reused with different intent')
        return TaskReceipt(**json.loads(existing[1]))
    fresh_actor, current = load_task_state(db, actor.account_id, actor.role_id, actor.login_epoch)
    if current != plan.before or fresh_actor != actor:
        raise ValueError('Stale task or character snapshot')
    if plan.after.revision != plan.before.revision + int(plan.after != plan.before):
        raise ValueError('Invalid task revision')
    # Execute set differences so an unrelated role never shares a mutable state.
    for table, key in (('task_offers', 'offered'), ('task_tracking', 'tracked')):
        before, after = getattr(plan.before, key), getattr(plan.after, key)
        for ident in sorted(before - after):
            db.execute(f'DELETE FROM {table} WHERE role_id=? AND task_id=?', (actor.role_id, ident))
        for ident in sorted(after - before):
            db.execute(f'INSERT INTO {table} VALUES(?,?)', (actor.role_id, ident))
    for ident in sorted(plan.after.active - plan.before.active):
        db.execute("INSERT INTO task_journal VALUES(?,?,'active')", (actor.role_id, ident))
    for ident in sorted(plan.after.completed - plan.before.completed):
        db.execute("UPDATE task_journal SET state='completed' WHERE role_id=? AND task_id=? AND state='active'",
                   (actor.role_id, ident))
    effect_id = ''
    if plan.action == 'complete':
        effect_id = f'task:{actor.role_id}:{plan.task_id}'
        payload = {'task_id': plan.task_id, 'settlement_id': effect_id,
                   'display_rewards': dict(plan.reward_scalars),
                   'display_items': [{'id': q, 'count': n, 'bind': b} for q, n, b in plan.reward_items],
                   'next_ids': list(plan.next_ids), 'source_event': plan.source_event,
                   'continuation_fields': dict(plan.continuation_fields),
                   'status': 'pending_integration', 'reward_rule': 'client_display_only'}
        if plan.objective_debits:
            payload['objective_debits']=plan.objective_debits
        if plan.reward_item_selectors:
            payload['reward_item_selectors']=plan.reward_item_selectors
            payload['reward_role_config_id']=plan.reward_role_config_id
        if plan.completion_effect_id:
            if plan.completion_effect_id!=60001:
                raise ValueError('Unverified native completion effect')
            # Resolves server work only. Neither network receipt nor GUI display
            # is acknowledged by this original local title effect.
            payload['continuation_resolved_fields']=['ScenarioInfoAnimationID']
            payload['native_completion_effect']={'id':60001,'handler':'original_state1',
                'status':'delegated_to_original_client','gui_confirmed':False}
        if plan.completion_finish_dialogue:
            if plan.completion_finish_dialogue is not True:
                raise ValueError('Invalid native finish-dialogue delegation')
            payload['continuation_resolved_fields']=sorted(set(payload.get('continuation_resolved_fields',()))|{
                'ScenarioInfoFinishConversationList','ScenarioInfoFinishNpcID'})
            payload['native_finish_dialogue']={'handler':'original_state1',
                'status':'delegated_to_original_client','gui_confirmed':False}
        db.execute('INSERT INTO task_effects(role_id,task_id,payload) VALUES(?,?,?)',
                   (actor.role_id, plan.task_id, json.dumps(payload, ensure_ascii=False)))
    # Triggers detect legacy writes; one domain command publishes one revision.
    db.execute('INSERT INTO task_versions VALUES(?,?) ON CONFLICT(role_id) DO UPDATE SET revision=excluded.revision',
               (actor.role_id, plan.after.revision))
    receipt = TaskReceipt(request_id, actor.role_id, plan.after.revision, effect_id)
    db.execute('INSERT INTO task_command_receipts VALUES(?,?,?,?)',
               (actor.role_id, request_id, fingerprint, json.dumps(receipt.__dict__)))
    return receipt
