"""Persistent task journal and trusted gameplay-event seam for local restoration.

Client configuration supplies content, not authoritative activation/reward rules.
Only server callers activate missions or confirm events. Wire handlers must not
turn arbitrary client IDs into these trusted calls. Rewards are queued for the
inventory/progression modules, never fabricated or silently discarded here.
"""
from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from inspect_client import OUT


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _plain(value):
    if isinstance(value, (dict, MappingProxyType)):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    return value


@dataclass(frozen=True)
class TaskResources:
    """Startup-loaded immutable configuration, safe to share between owners."""
    definitions: object
    shape_to_role_config: object


def prepare_task_store(accounts, catalog=None):
    """Startup migration/loading hook; execute before accepting connections.

    This performs blocking I/O. The integration owner must call it during startup
    or in its bounded persistence executor, never in the network event loop.
    Inject its result into each role-owned TaskStore to avoid all per-login DDL
    and configuration reads. The legacy constructor below remains synchronous.
    """
    doc = json.loads(Path(catalog or OUT / 'catalogs/tasks.json').read_text(encoding='utf-8'))
    choices = json.loads((OUT / 'catalogs/knight.gsp.role.createroleconfig.json').read_text(encoding='utf-8'))
    resources = TaskResources(
        _freeze({r['id']: r for r in doc['missions']}),
        _freeze({int(r['attributes'][c]): int(r['attributes']['id'])
                 for r in choices for c in ('color1', 'color2', 'color3')}))
    with closing(accounts.connect()) as db, db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS task_journal (
                role_id INTEGER NOT NULL REFERENCES roles(id),
                task_id INTEGER NOT NULL, state TEXT NOT NULL,
                PRIMARY KEY(role_id,task_id),
                CHECK(state IN ('active','completed')));
            CREATE TABLE IF NOT EXISTS task_effects (
                role_id INTEGER NOT NULL REFERENCES roles(id),
                task_id INTEGER NOT NULL, payload TEXT NOT NULL,
                delivered INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(role_id,task_id));
            CREATE TABLE IF NOT EXISTS task_offers (
                role_id INTEGER NOT NULL REFERENCES roles(id),
                task_id INTEGER NOT NULL, PRIMARY KEY(role_id,task_id));
            CREATE TABLE IF NOT EXISTS task_tracking (
                role_id INTEGER NOT NULL REFERENCES roles(id),
                task_id INTEGER NOT NULL, PRIMARY KEY(role_id,task_id));
            CREATE TABLE IF NOT EXISTS task_versions (
                role_id INTEGER PRIMARY KEY REFERENCES roles(id), revision INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS task_command_receipts (
                role_id INTEGER NOT NULL REFERENCES roles(id), request_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL, receipt TEXT NOT NULL,
                PRIMARY KEY(role_id,request_id));
        ''')
        # Legacy mutations must also invalidate an already prepared snapshot.
        for table in ('task_journal', 'task_offers', 'task_tracking'):
            for action in ('INSERT', 'UPDATE', 'DELETE'):
                row = 'OLD' if action == 'DELETE' else 'NEW'
                db.executescript(f'''
                    CREATE TRIGGER IF NOT EXISTS {table}_revision_{action}
                    AFTER {action} ON {table} BEGIN
                        INSERT INTO task_versions(role_id,revision) VALUES({row}.role_id,1)
                        ON CONFLICT(role_id) DO UPDATE SET revision=revision+1;
                    END;
                ''')
    return resources


class TaskStore:
    """Synchronous SQLite compatibility Adapter, NOT an async role owner.

    Runtime methods perform blocking storage. Route them through the role owner
    and its bounded persistence Adapter. No method may run on the network loop.
    """
    def __init__(self, accounts, catalog=None, *, resources=None):
        self.accounts = accounts
        if resources is not None and catalog is not None:
            raise ValueError('Choose prepared resources or a catalog path')
        self.resources = resources if resources is not None else prepare_task_store(accounts, catalog)
        self.definitions = self.resources.definitions

    def _role(self, account_id, role_id):
        role = self.accounts.owned_role(account_id, role_id)
        if role is None:
            raise ValueError('Task role ownership mismatch')
        return role

    def journal(self, account_id, role_id):
        self._role(account_id, role_id)
        with closing(self.accounts.connect()) as db:
            return [{'task_id': ident, 'state': state} for ident, state in db.execute(
                'SELECT task_id,state FROM task_journal WHERE role_id=? ORDER BY task_id', (role_id,))]

    def activate(self, account_id, role_id, task_id):
        """Trusted server activation. No client accept-request calls this directly.

        Original RequestMissionList semantics are unknown, so callers must supply
        an established activation rule; graph predecessors alone are not enough.
        This operation is idempotent and never resets a completed task.
        """
        role = self._role(account_id, role_id)
        task = self.definitions[task_id]
        level = task['level']
        if role['level'] < level['min'] or level['max'] and role['level'] > level['max']:
            raise ValueError('Task level requirement')
        if task['role_config_ids']:
            role_config = self.resources.shape_to_role_config.get(role['shape'])
            if role_config not in task['role_config_ids']:
                raise ValueError('Task character requirement')
        with closing(self.accounts.connect()) as db, db:
            inserted = db.execute('INSERT OR IGNORE INTO task_journal VALUES(?,?,?)',
                                  (role_id, task_id, 'active')).rowcount
        return bool(inserted)

    def offer(self, account_id, role_id, task_id):
        """Register a server-authorized offer after the caller checks its rules."""
        self._role(account_id, role_id)
        if task_id not in self.definitions:
            raise ValueError('Task definition missing')
        with closing(self.accounts.connect()) as db, db:
            db.execute('INSERT OR IGNORE INTO task_offers VALUES(?,?)', (role_id, task_id))

    def available(self, account_id, role_id):
        role = self._role(account_id, role_id)
        with closing(self.accounts.connect()) as db:
            ids = [r[0] for r in db.execute('''SELECT task_id FROM task_offers o WHERE role_id=?
                AND NOT EXISTS(SELECT 1 FROM task_journal j WHERE j.role_id=o.role_id AND j.task_id=o.task_id)
                ORDER BY task_id''', (role_id,))]
        result = []
        for ident in ids:
            task = self.definitions.get(ident)
            if task is None:
                continue
            minimum = max(task['level']['min'], int((task.get('offer') or {}).get('attributes', {}).get('minilevel', 0)))
            if role['level'] >= minimum and (not task['level']['max'] or role['level'] <= task['level']['max']):
                result.append(ident)
        return result

    def track(self, account_id, role_id, task_id, tracked):
        self._role(account_id, role_id)
        if tracked not in (0, 1):
            raise ValueError('Invalid task tracking flag')
        with closing(self.accounts.connect()) as db, db:
            if tracked:
                if not db.execute("SELECT 1 FROM task_journal WHERE role_id=? AND task_id=? AND state='active'",
                                  (role_id, task_id)).fetchone():
                    raise ValueError('Task is not active')
                db.execute('INSERT OR IGNORE INTO task_tracking VALUES(?,?)', (role_id, task_id))
            else:
                db.execute('DELETE FROM task_tracking WHERE role_id=? AND task_id=?', (role_id, task_id))

    def dialogue(self, account_id, role_id, task_id, npc_id, map_id):
        """Return original dialogue only for an active task at its exact target.

        The map/position and NPC identity are supplied by the world handler after
        validating proximity, never taken as proof from client request fields.
        """
        self._role(account_id, role_id)
        task = self.definitions[task_id]
        target = task['target']
        if not target['npc_id'] or npc_id != target['npc_id'] or map_id != target['map_id']:
            raise ValueError('Task NPC or map mismatch')
        journal = self.journal(account_id, role_id)
        if {'task_id': task_id, 'state': 'active'} not in journal:
            raise ValueError('Task is not active')
        return _plain(task['dialogue']['start'])

    def complete_dialogue(self, account_id, role_id, task_id, npc_id, map_id):
        """Trusted completion of a plain type-10 NPC dialogue.

        Animation, branch, progress bar, teleport and other action types remain
        pending until their gameplay modules confirm the original behavior.
        This restriction prevents marking a battle or minigame complete by talk.
        """
        self.dialogue(account_id, role_id, task_id, npc_id, map_id)
        task = self.definitions[task_id]
        a = task['attributes']
        blockers = ('ScenarioInfoAnimationID', 'ScenarioInfoBranchNpcID', 'ProcessBarTime',
                    'RewardMapJumpType', 'ActiveInfoTargetID', 'ActiveInfoTargetNum',
                    'ActiveInfoTimeLimit', 'ActiveInfoGiveBackMoney', 'ActiveInfoGiveBackPetID',
                    'ActiveInfoUseItemID', 'ActiveInfoOtherType', 'AIInfoAIID', 'TransformID',
                    'ActiveInfoMaxStep', 'ActiveInfoMiniStep', 'QuestionInfoNpcID')
        if task['type'] != 10 or any(int(a.get(k, 0)) for k in blockers):
            raise ValueError('Task requires an unimplemented gameplay event')
        effects = _plain({'task_id': task_id, 'display_rewards': task['display_rewards'],
                   'display_items': task['display_items'], 'next_ids': task['next_ids'],
                   'display_npc_ids': task['lists'].get('DisPlayNPCID', []),
                   'status': 'pending_integration', 'reward_rule': 'client_display_only'})
        with closing(self.accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            changed = db.execute("UPDATE task_journal SET state='completed' WHERE role_id=? AND task_id=? AND state='active'",
                                 (role_id, task_id)).rowcount
            if not changed:
                raise ValueError('Task already completed or inactive')
            db.execute('INSERT INTO task_effects(role_id,task_id,payload) VALUES(?,?,?)',
                       (role_id, task_id, json.dumps(effects, ensure_ascii=False)))
            db.execute('DELETE FROM task_tracking WHERE role_id=? AND task_id=?', (role_id, task_id))
        return effects

    def pending_effects(self, account_id, role_id):
        self._role(account_id, role_id)
        with closing(self.accounts.connect()) as db:
            return [json.loads(row[0]) for row in db.execute(
                'SELECT payload FROM task_effects WHERE role_id=? AND delivered=0 ORDER BY task_id', (role_id,))]
