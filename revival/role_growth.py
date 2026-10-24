"""Ordinary-phase growth policy and same-transaction persistence Adapter.

No profile is inferred from a level. Initialization is explicit; stored points
are growth increments after that baseline, not invented initial character stats.
"""
from dataclasses import dataclass, replace, asdict
import hashlib
import json
from types import MappingProxyType
from inspect_client import OUT
from role_attribute_storage import sync_growth_attributes


@dataclass(frozen=True)
class GrowthRules:
    revision: str
    costs: object
    cap: int
    automatic_stop: int
    automatic_per_stat: int
    free_per_level: int


@dataclass(frozen=True)
class GrowthState:
    role_id: int
    level: int
    experience: int
    baseline_level: int
    baseline_free: int
    baseline_allocated: tuple | None
    automatic_points: tuple
    allocated_points: tuple
    free_points: int
    revision: int
    policy: str


@dataclass(frozen=True)
class GrowthPlan:
    before: GrowthState
    after: GrowthState
    operation: str
    arguments: tuple


@dataclass(frozen=True)
class GrowthResourceContext:
    """Explicit same-transaction assets and startup rules for migrated growth."""
    inventory_snapshot: object
    equipment_rules: object
    resource_rules: object

    def __post_init__(self):
        from inventory import InventorySnapshot
        from role_equipment import EquipmentAttributeRules
        from role_resource_plan import ResourceRules
        if (type(self.inventory_snapshot) is not InventorySnapshot
                or type(self.equipment_rules) is not EquipmentAttributeRules
                or type(self.resource_rules) is not ResourceRules):
            raise ValueError('Immutable current assets and prepared growth resource rules required')


def load_growth_rules():
    """Startup-only immutable config; keep all original special costs unmapped."""
    policy = json.loads((OUT/'design/role-progression-v1.json').read_text(encoding='utf-8'))
    if policy['revision'] != '2026-10-23.role.1':
        raise ValueError('Growth policy revision requires explicit implementation')
    rows = json.loads((OUT/'catalogs/knight.gsp.role.cresmoneyconfig.json').read_text(encoding='utf-8'))
    return GrowthRules(policy['revision'], MappingProxyType({int(r['attributes']['id']): int(r['attributes']['nextexp']) for r in rows}),
                       policy['experience']['ordinary_level_cap'], 10,
                       policy['potential']['automatic_per_stat'], policy['potential']['free_per_level'])


def prepare_growth_storage(db):
    """Startup-only; no live role profile is created by schema migration."""
    db.executescript('''CREATE TABLE IF NOT EXISTS role_growth (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id), phase TEXT NOT NULL,
        baseline_level INTEGER NOT NULL, baseline_free INTEGER NOT NULL,
        baseline_allocated TEXT NOT NULL, automatic_points TEXT NOT NULL,
        allocated_points TEXT NOT NULL, free_points INTEGER NOT NULL,
        revision INTEGER NOT NULL, policy TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS role_growth_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id), request_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(role_id,request_id));''')


def _owner(db, account_id, role_id, epoch):
    if not db.in_transaction:
        raise ValueError('Growth requires an owner transaction')
    if not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
                      'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
                      (role_id, account_id, epoch)).fetchone():
        raise ValueError('Growth ownership or login lease mismatch')


def read_growth(db, account_id, role_id):
    if not db.in_transaction:
        raise ValueError('Growth requires an owner transaction')
    row = db.execute('SELECT r.level,COALESCE(p.experience,0),g.phase,g.baseline_level,g.baseline_free,'
                     'g.baseline_allocated,g.automatic_points,g.allocated_points,g.free_points,g.revision,g.policy '
                     'FROM roles r JOIN role_growth g ON g.role_id=r.id LEFT JOIN role_progress p ON p.role_id=r.id '
                     'WHERE r.id=? AND r.account_id=?', (role_id, account_id)).fetchone()
    if row is None:
        raise ValueError('Explicit ordinary growth baseline required')
    if row[2] != 'ordinary':
        raise ValueError('Unknown growth phase')
    baseline = json.loads(row[5])
    return GrowthState(role_id,row[0],row[1],row[3],row[4],None if baseline is None else tuple(baseline),
                       tuple(json.loads(row[6])),tuple(json.loads(row[7])),row[8],row[9],row[10])


def initialize_growth(db, account_id, role_id, epoch, rules, *, expected_level, free_points, known_allocated=None):
    """One explicit baseline, preserving level/XP; no historical point grant."""
    _owner(db, account_id, role_id, epoch)
    if (type(expected_level) is not int or not 1 <= expected_level <= rules.cap
            or type(free_points) is not int or not 0 <= free_points < 2**63
            or known_allocated is not None and (type(known_allocated) is not tuple or len(known_allocated) != 5
                or any(type(x) is not int or not 0 <= x < 2**63 for x in known_allocated))):
        raise ValueError('Invalid ordinary baseline')
    if db.execute('SELECT 1 FROM role_growth WHERE role_id=?', (role_id,)).fetchone():
        old = read_growth(db,account_id,role_id)
        if (old.baseline_level,old.baseline_free,old.baseline_allocated,old.policy) != (expected_level,free_points,known_allocated,rules.revision):
            raise ValueError('Existing growth baseline cannot be reset')
        return old
    level = db.execute('SELECT level FROM roles WHERE id=?', (role_id,)).fetchone()[0]
    if level != expected_level:
        raise ValueError('Baseline level changed')
    db.execute('INSERT INTO role_growth VALUES(?,?,?,?,?,?,?,?,?,?)',
               (role_id,'ordinary',level,free_points,json.dumps(known_allocated),'[0,0,0,0,0]',
                '[0,0,0,0,0]',free_points,0,rules.revision))
    return read_growth(db,account_id,role_id)


def _valid(state, rules):
    if (state.policy != rules.revision or not 1 <= state.level <= rules.cap
            or not 0 <= state.experience < 2**63 or state.level < state.baseline_level
            or not 0 <= state.free_points < 2**63 or state.revision < 0
            or any(type(v) is not tuple or len(v) != 5 or any(type(x) is not int or not 0 <= x < 2**63 for x in v)
                   for v in (state.automatic_points,state.allocated_points))):
        raise ValueError('Unsupported or stale ordinary growth policy')


def _advance(state, rules):
    if state.level >= rules.cap:
        raise ValueError('Ordinary level cap reached')
    cost = rules.costs.get(state.level)
    if cost is None or cost <= 0:
        raise ValueError('Missing or terminal level cost')
    if state.experience < cost:
        raise ValueError('Insufficient experience')
    if state.free_points > 2**63 - 1 - rules.free_per_level:
        raise ValueError('Potential point overflow')
    if any(x > 2**63 - 1 - rules.automatic_per_stat for x in state.automatic_points):
        raise ValueError('Automatic point overflow')
    return replace(state, level=state.level+1, experience=state.experience-cost,
                   automatic_points=tuple(x+rules.automatic_per_stat for x in state.automatic_points),
                   free_points=state.free_points+rules.free_per_level)


def plan_growth_credit(state, amount, rules):
    _valid(state,rules)
    if type(amount) is not int or amount < 0 or state.experience > 2**63 - 1 - amount:
        raise ValueError('Invalid or overflowing experience credit')
    after = replace(state,experience=state.experience+amount)
    # Auto-upgrade is triggered by new positive income, not a balance query/zero grant.
    while amount and after.level < rules.automatic_stop:
        cost = rules.costs.get(after.level)
        if cost is None or cost <= 0:
            raise ValueError('Missing ordinary automatic level cost')
        if after.experience < cost:
            break
        after = _advance(after,rules)
    after = replace(after,revision=state.revision+int(after != state))
    return GrowthPlan(state,after,'credit',(amount,))


def plan_manual_level(state, opaque_field, rules):
    _valid(state,rules)
    if type(opaque_field) is not int or opaque_field != 0:
        raise ValueError('Unconfirmed level-up request mode')
    if state.level < rules.automatic_stop:
        raise ValueError('Ordinary low levels use automatic credit advancement')
    after = _advance(state,rules)
    return GrowthPlan(state,replace(after,revision=state.revision+1),'manual_level',(opaque_field,))


def plan_potential_allocation(state, deltas, expected_revision, rules):
    _valid(state,rules)
    if (state.revision != expected_revision or type(deltas) is not tuple or len(deltas) != 5
            or any(type(x) is not int or x < 0 for x in deltas) or not 0 < sum(deltas) <= state.free_points
            or any(a > 2**63 - 1 - b for a,b in zip(state.allocated_points,deltas))):
        raise ValueError('Invalid potential allocation or version')
    after = replace(state,allocated_points=tuple(a+b for a,b in zip(state.allocated_points,deltas)),
                    free_points=state.free_points-sum(deltas),revision=state.revision+1)
    return GrowthPlan(state,after,'allocate',deltas)


def _write_growth(db, account_id, plan, attribute_rules=None, epoch=None,resource_context=None):
    if read_growth(db,account_id,plan.before.role_id) != plan.before:
        raise ValueError('Stale growth snapshot')
    if resource_context is not None:
        from role_equipment_storage import current_resource_profile,current_equipment_totals
        from role_equipment import resource_caps_from_projection
        from role_resource_storage import read_role_resources,apply_resource_transition
        from role_resource_plan import plan_resource_caps
        from role_attribute_storage import sync_growth_naked_attributes
        if type(resource_context) is not GrowthResourceContext:
            raise ValueError('Explicit growth resource context required')
        ctx=resource_context
        current_resource_profile(db,account_id,plan.before.role_id,epoch,ctx.inventory_snapshot,
            equipment_rules=ctx.equipment_rules,resource_rules=ctx.resource_rules)
        resources=read_role_resources(db,account_id,plan.before.role_id,epoch,ctx.resource_rules)
    state = plan.after
    db.execute('UPDATE roles SET level=? WHERE id=? AND account_id=?',(state.level,state.role_id,account_id))
    db.execute('INSERT INTO role_progress VALUES(?,?) ON CONFLICT(role_id) DO UPDATE SET experience=excluded.experience',
               (state.role_id,state.experience))
    db.execute('UPDATE role_growth SET automatic_points=?,allocated_points=?,free_points=?,revision=? WHERE role_id=?',
               (json.dumps(state.automatic_points),json.dumps(state.allocated_points),state.free_points,state.revision,state.role_id))
    if resource_context is None:
        sync_growth_attributes(db,account_id,state,epoch,attribute_rules)
    else:
        sync_growth_naked_attributes(db,account_id,state,epoch,attribute_rules,ctx.resource_rules)
        caps=resource_caps_from_projection(current_equipment_totals(db,account_id,state.role_id,epoch,
            ctx.inventory_snapshot,ctx.equipment_rules))
        transition=plan_resource_caps(resources,caps,'ordinary_growth',ctx.resource_rules)
        if transition.changed:
            apply_resource_transition(db,account_id,state.role_id,epoch,transition,
                f'growth-resource:{plan.before.revision}:{state.revision}',
                rules=ctx.resource_rules,equipment_rules=ctx.equipment_rules)
    return state


def apply_growth_plan(db, account_id, role_id, epoch, plan, request_id, rules, attribute_rules=None,*,resource_context=None):
    _owner(db,account_id,role_id,epoch)
    if plan.before.role_id != role_id or plan.after.role_id != role_id or type(request_id) is not str or not 1 <= len(request_id) <= 160:
        raise ValueError('Growth plan scope or request ID mismatch')
    intent = [plan.operation,plan.arguments,plan.before.policy,
              plan.before.revision if plan.operation == 'allocate' else None]
    fingerprint = hashlib.sha256(json.dumps(intent,sort_keys=True).encode()).hexdigest()
    old = db.execute('SELECT fingerprint,result FROM role_growth_receipts WHERE role_id=? AND request_id=?',(role_id,request_id)).fetchone()
    if old:
        if old[0] != fingerprint:
            raise ValueError('Growth request ID reused with different intent')
        data = json.loads(old[1])
        for key in ('baseline_allocated','automatic_points','allocated_points'):
            if data[key] is not None: data[key] = tuple(data[key])
        return GrowthState(**data)
    # Recompute at the public seam; a caller cannot forge extra levels/points.
    if plan.operation == 'credit': expected = plan_growth_credit(plan.before,*plan.arguments,rules)
    elif plan.operation == 'manual_level': expected = plan_manual_level(plan.before,*plan.arguments,rules)
    elif plan.operation == 'allocate': expected = plan_potential_allocation(plan.before,plan.arguments,plan.before.revision,rules)
    else: raise ValueError('Unknown growth operation')
    if expected != plan:
        raise ValueError('Growth plan differs from policy')
    state = _write_growth(db,account_id,plan,attribute_rules,epoch,resource_context)
    db.execute('INSERT INTO role_growth_receipts VALUES(?,?,?,?)',(role_id,request_id,fingerprint,json.dumps(asdict(state))))
    return state


def request_manual_level(db, account_id, role_id, epoch, opaque_field, request_id, rules, attribute_rules=None,*,resource_context=None):
    """Network routing helper: replay a successful request before replanning.

    Caller decodes CReqLevelUp and schedules this in the role transaction.
    Rejected requests raise without changing balances/points; success receipts
    remain valid after reconnect and later unrelated progression commands.
    Returned replay state is the historical receipt. Read read_growth again for
    live cache/client refresh; never overwrite newer state with an old receipt.
    """
    _owner(db,account_id,role_id,epoch)
    if type(request_id) is not str or not 1 <= len(request_id) <= 160:
        raise ValueError('Invalid growth request ID')
    fingerprint = hashlib.sha256(json.dumps(['manual_level',(opaque_field,),rules.revision,None],sort_keys=True).encode()).hexdigest()
    old = db.execute('SELECT fingerprint,result FROM role_growth_receipts WHERE role_id=? AND request_id=?',
                     (role_id,request_id)).fetchone()
    if old:
        if old[0] != fingerprint:
            raise ValueError('Growth request ID reused with different intent')
        data = json.loads(old[1])
        for key in ('baseline_allocated','automatic_points','allocated_points'):
            if data[key] is not None: data[key] = tuple(data[key])
        return GrowthState(**data)
    before = read_growth(db,account_id,role_id)
    return apply_growth_plan(db,account_id,role_id,epoch,
        plan_manual_level(before,opaque_field,rules),request_id,rules,attribute_rules,resource_context=resource_context)


def request_potential_allocation(db, account_id, role_id, epoch, deltas, request_id, rules, attribute_rules=None,*,resource_context=None):
    """Allocate once per request, returning the current state even on replay.

    Deltas use internal vitality/inner/strength/endurance/agility order. Network
    field order belongs to its codec. The stored successful result identifies
    the original before_revision, so later commands cannot change this intent.
    Caller owns the transaction and publishes attributes only after commit.
    """
    _owner(db,account_id,role_id,epoch)
    if (type(request_id) is not str or not 1<=len(request_id)<=160
            or type(deltas) is not tuple or len(deltas)!=5
            or any(type(x) is not int or x<0 for x in deltas) or sum(deltas)<=0):
        raise ValueError('Invalid potential allocation request')
    old=db.execute('SELECT fingerprint,result FROM role_growth_receipts WHERE role_id=? AND request_id=?',
                   (role_id,request_id)).fetchone()
    if old:
        result=json.loads(old[1])
        if (result.get('role_id')!=role_id or type(result.get('revision')) is not int
                or result['revision']<=0 or result.get('policy')!=rules.revision):
            raise ValueError('Potential allocation receipt requires reconciliation')
        original=['allocate',deltas,rules.revision,result['revision']-1]
        fingerprint=hashlib.sha256(json.dumps(original,sort_keys=True).encode()).hexdigest()
        if old[0]!=fingerprint:
            raise ValueError('Growth request ID reused with different intent')
        current=read_growth(db,account_id,role_id)
        _valid(current,rules)
        return current
    before=read_growth(db,account_id,role_id)
    plan=plan_potential_allocation(before,deltas,before.revision,rules)
    return apply_growth_plan(db,account_id,role_id,epoch,plan,request_id,rules,attribute_rules,resource_context=resource_context)


def auto_credit_profile(db, account_id, role_id, amount, rules, attribute_rules=None, epoch=None,*,resource_context=None):
    """For an outer uniquely receipted task reward transaction, never standalone.

    Role lease and idempotency must already be checked by that outer operation.
    No profile means legacy experience credit continues without inferred phase.
    """
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='role_growth'").fetchone()
    if not exists or not db.execute('SELECT 1 FROM role_growth WHERE role_id=?',(role_id,)).fetchone():
        if resource_context is not None:
            raise ValueError('Resource-aware credit requires explicit ordinary growth')
        return None
    if rules is None:
        raise ValueError('Growth config required for initialized profile')
    state = read_growth(db,account_id,role_id)
    plan = plan_growth_credit(state,amount,rules)
    return _write_growth(db,account_id,plan,attribute_rules,epoch,resource_context)
