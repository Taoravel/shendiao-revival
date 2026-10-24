"""Family-owned durable maintenance; caller supplies its transaction and clock."""
from dataclasses import dataclass
import hashlib,json
from inspect_client import OUT


@dataclass(frozen=True)
class MaintenanceRules:
    revision: str
    period_ms: int
    partitions: int
    batch_limit: int
    max_lateness_ms: int
    origin: str
    normal_horizon: int
    low_popularity: int
    low_fee_numerator: int
    low_fee_denominator: int
    online_gain: int
    hourly_decay: int
    popularity_max: int
    member_limit: int
    rows: tuple
    downgrade_funds: int
    downgrade_popularity: int
    products_revision: str


@dataclass(frozen=True)
class MaintenanceRow:
    level: int
    base: int
    drug: int
    special: int
    drug_max: int
    special_max: int


@dataclass(frozen=True)
class MaintenanceCommand:
    family: int
    due_ms: int
    online: tuple
    request_id: str
    deadline_ms: int


@dataclass(frozen=True)
class ClockResumeCommand:
    family: int
    due_ms: int
    request_id: str
    deadline_ms: int


@dataclass(frozen=True)
class ClockResumeReceipt:
    family: int
    skipped_from_ms: int
    resumed_ms: int
    next_due_ms: int
    revision: int
    recipe: str


@dataclass(frozen=True)
class MaintenanceReceipt:
    family: int
    due_ms: int
    next_due_ms: int
    mode: str
    fee: int
    online_count: int
    funds_after: int
    popularity_after: int
    drug_after: int
    special_after: int
    revision: int
    level_before: int
    level_after: int
    state: str
    funds_before: int
    popularity_before: int
    drug_before: int
    special_before: int
    recovery_funds: int
    recovery_popularity: int
    recipe: str


@dataclass(frozen=True)
class FamilyDissolution:
    family: int
    due_ms: int
    guild: int | None
    guild_token: str | None
    members: tuple
    state: str


@dataclass(frozen=True)
class FamilyGuildClosureCommand:
    event: FamilyDissolution
    request_id: str
    deadline_ms: int


@dataclass(frozen=True)
class FamilyClock:
    family: int
    created_ms: int
    next_due_ms: int
    revision: int
    state: str
    origin: str
    recipe: str


def rules(policy):
    raw=policy['family_maintenance']
    if (not isinstance(raw['revision'],str) or not raw['revision']
            or not isinstance(raw['origin'],str) or not raw['origin']
            or any(type(raw[name]) is not int or not 0<raw[name]<2**31
                for name in ('period_ms','partitions','batch_limit','max_lateness_ms'))):
        raise ValueError('invalid_family_maintenance_policy')
    names=('normal_horizon','low_popularity','low_fee_numerator','low_fee_denominator','online_gain','hourly_decay')
    if any(type(raw[name]) is not int or not 0<raw[name]<2**31 for name in names):
        raise ValueError('invalid_family_maintenance_policy')
    if (any(type(raw[name]) is not int or not 0<raw[name]<2**31 for name in ('downgrade_funds','downgrade_popularity'))
            or type(policy['family_popularity_max']) is not int or not 0<policy['family_popularity_max']<2**31):
        raise ValueError('invalid_family_maintenance_policy')
    source=json.loads((OUT/'catalogs/knight.gsp.faction.cfamilymaintainconfig.json').read_text(encoding='utf-8'))
    rows=tuple(MaintenanceRow(*(int(row['attributes'][name]) for name in
        ('id','baseconsume','drugconsume','productconsume','drugmax','productmax'))) for row in source)
    if len(rows)!=5 or tuple(row.level for row in rows)!=(1,2,3,4,5):raise ValueError('invalid_family_maintenance_table')
    if any(not 0<value<2**31 for row in rows for value in (row.base,row.drug,row.special,row.drug_max,row.special_max)):
        raise ValueError('invalid_family_maintenance_table')
    return MaintenanceRules(*(raw[name] for name in
        ('revision','period_ms','partitions','batch_limit','max_lateness_ms','origin')),
        *(raw[name] for name in names),policy['family_popularity_max'],max(policy['family_capacities']),rows,
        raw['downgrade_funds'],raw['downgrade_popularity'],policy['family_production']['revision'])


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS family_maintenance (
        family INTEGER PRIMARY KEY REFERENCES organizations(id),partition INTEGER NOT NULL,
        created_ms INTEGER NOT NULL,next_due_ms INTEGER NOT NULL,
        revision INTEGER NOT NULL CHECK(revision>0),
        state TEXT NOT NULL CHECK(state IN ('active','dissolution_pending')),
        origin TEXT NOT NULL,recipe TEXT NOT NULL)''')
    db.execute('CREATE INDEX IF NOT EXISTS family_maintenance_due ON family_maintenance(partition,state,next_due_ms,family)')
    db.execute('''CREATE TABLE IF NOT EXISTS family_maintenance_receipts (
        family INTEGER NOT NULL REFERENCES organizations(id),due_ms INTEGER NOT NULL,
        fingerprint TEXT NOT NULL,result TEXT NOT NULL,created_ms INTEGER NOT NULL,
        PRIMARY KEY(family,due_ms))''')
    db.execute('''CREATE TABLE IF NOT EXISTS family_dissolution_outbox (
        family INTEGER NOT NULL REFERENCES organizations(id),due_ms INTEGER NOT NULL,
        guild INTEGER,guild_token TEXT,members TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('pending','committed')),PRIMARY KEY(family,due_ms))''')
    columns={row[1] for row in db.execute('PRAGMA table_info(family_dissolution_outbox)')}
    if 'partition' not in columns:
        db.execute('ALTER TABLE family_dissolution_outbox ADD COLUMN partition INTEGER NOT NULL DEFAULT -1')
        db.execute('''UPDATE family_dissolution_outbox SET partition=(SELECT partition FROM family_maintenance c
            WHERE c.family=family_dissolution_outbox.family)''')
    if 'guild_done' not in columns:
        db.execute('ALTER TABLE family_dissolution_outbox ADD COLUMN guild_done INTEGER NOT NULL DEFAULT 0 CHECK(guild_done IN (0,1))')
    db.execute('CREATE INDEX IF NOT EXISTS family_guild_closure_due ON family_dissolution_outbox(partition,guild_done,due_ms,family)')
    db.execute('''CREATE TABLE IF NOT EXISTS family_maintenance_pauses (
        family INTEGER NOT NULL REFERENCES organizations(id),old_due_ms INTEGER NOT NULL,
        recipe TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(family,old_due_ms))''')


def new_family(db,family,now,policy):
    if type(now) is not int or not 0<=now<2**63-policy.period_ms:raise ValueError('invalid_family_maintenance_time')
    db.execute('INSERT INTO family_maintenance VALUES(?,?,?,?,1,?,?,?)',
        (family,family%policy.partitions,now,now+policy.period_ms,'active',policy.origin,policy.revision))


def snapshot(db,family):
    row=db.execute('''SELECT family,created_ms,next_due_ms,revision,state,origin,recipe
        FROM family_maintenance WHERE family=?''',(family,)).fetchone()
    if not row:raise ValueError('family_maintenance_unknown')
    return FamilyClock(*tuple(row))


def dissolution_pending(db,family):
    row=db.execute('''SELECT family,due_ms,guild,guild_token,members,state FROM family_dissolution_outbox
        WHERE family=? AND state='pending' ORDER BY due_ms LIMIT 1''',(family,)).fetchone()
    if not row:raise ValueError('family_dissolution_missing')
    return FamilyDissolution(*tuple(row[:4]),tuple(tuple(item) for item in json.loads(row[4])),row[5])


def validate_closure_command(command,now,policy):
    if not isinstance(command,FamilyGuildClosureCommand):raise ValueError('frozen_family_guild_closure_command_required')
    event=command.event
    if not isinstance(event,FamilyDissolution):raise ValueError('frozen_family_dissolution_required')
    from guild_dissolution import validate
    # The no-guild event still validates every other immutable event field.
    from dataclasses import replace
    if (event.guild is None)!=(event.guild_token is None):raise ValueError('invalid_family_guild_closure_scope')
    candidate=replace(event,guild=1,guild_token='no-guild') if event.guild is None else event
    validate(candidate,command.request_id,command.deadline_ms,now,policy)


def ack_guild_closure(db,command,now,policy):
    validate_closure_command(command,now,policy)
    event=command.event
    if dissolution_pending(db,event.family)!=event:raise ValueError('family_dissolution_intent_conflict')
    if event.guild is not None:
        from guild_dissolution import receipt
        if receipt(db,event,policy) is None:raise ValueError('guild_dissolution_receipt_missing')
    row=db.execute('SELECT guild_done FROM family_dissolution_outbox WHERE family=? AND due_ms=?',
        (event.family,event.due_ms)).fetchone()
    if not row:raise ValueError('family_dissolution_missing')
    db.execute('UPDATE family_dissolution_outbox SET guild_done=1 WHERE family=? AND due_ms=?',
        (event.family,event.due_ms))
    return True


def resume(db,command,now,policy):
    validate_resume(command,now,policy)
    prior=db.execute('SELECT recipe,result FROM family_maintenance_pauses WHERE family=? AND old_due_ms=?',
        (command.family,command.due_ms)).fetchone()
    if prior:
        if prior[0]!=policy.revision:raise ValueError('family_maintenance_recipe_mismatch')
        return ClockResumeReceipt(**json.loads(prior[1]))
    clock=snapshot(db,command.family)
    if clock.recipe!=policy.revision:raise ValueError('family_maintenance_recipe_mismatch')
    if clock.state!='active':raise ValueError('family_dissolution_pending')
    if command.due_ms!=clock.next_due_ms or now-clock.next_due_ms<=policy.max_lateness_ms:
        raise ValueError('family_clock_resume_not_overdue')
    result=ClockResumeReceipt(command.family,command.due_ms,now,now+policy.period_ms,clock.revision+1,policy.revision)
    db.execute('UPDATE family_maintenance SET next_due_ms=?,revision=revision+1 WHERE family=?',(result.next_due_ms,command.family))
    db.execute('INSERT INTO family_maintenance_pauses VALUES(?,?,?,?)',
        (command.family,command.due_ms,policy.revision,json.dumps(result.__dict__,separators=(',',':'))))
    return result


def validate_resume(command,now,policy):
    if (not isinstance(command,ClockResumeCommand)
            or any(type(value) is not int or not 0<value<2**63 for value in
                (command.family,command.due_ms,command.deadline_ms))
            or type(command.request_id) is not str or not 1<=len(command.request_id)<=160
            or type(now) is not int or not 0<=now<2**63-policy.period_ms):
        raise ValueError('invalid_family_clock_resume')
    if now>command.deadline_ms:raise ValueError('maintenance_deadline')


def validate(command,now,policy):
    if (not isinstance(command,MaintenanceCommand)
            or any(type(v) is not int or not 0<v<2**63 for v in (command.family,command.due_ms,command.deadline_ms))
            or type(now) is not int or not 0<=now<2**63
            or type(command.request_id) is not str or not 1<=len(command.request_id)<=160
            or type(command.online) is not tuple or len(command.online)>policy.member_limit):
        raise ValueError('invalid_family_maintenance_command')
    seen=set()
    for item in command.online:
        if (type(item) is not tuple or len(item)!=2 or type(item[0]) is not int or not 0<item[0]<2**63
                or type(item[1]) not in (int,str) or isinstance(item[1],bool)
                or (type(item[1]) is int and not 0<item[1]<2**63)
                or (type(item[1]) is str and not 1<=len(item[1])<=96) or item[0] in seen):
            raise ValueError('invalid_family_maintenance_observation')
        seen.add(item[0])
    if now>command.deadline_ms:raise ValueError('maintenance_deadline')


def settle(db,command,now,policy):
    validate(command,now,policy)
    fingerprint=hashlib.sha256(json.dumps([command.family,command.due_ms,command.online,policy.revision],
        separators=(',',':')).encode()).hexdigest()
    prior=db.execute('SELECT fingerprint,result FROM family_maintenance_receipts WHERE family=? AND due_ms=?',
        (command.family,command.due_ms)).fetchone()
    if prior:
        if prior[0]!=fingerprint:raise ValueError('maintenance_intent_conflict')
        return MaintenanceReceipt(**json.loads(prior[1]))
    clock=snapshot(db,command.family)
    if clock.recipe!=policy.revision:raise ValueError('family_maintenance_recipe_mismatch')
    if clock.state!='active':raise ValueError('family_dissolution_pending')
    if command.due_ms!=clock.next_due_ms or now<clock.next_due_ms:raise ValueError('maintenance_not_due')
    if now-clock.next_due_ms>policy.max_lateness_ms:raise ValueError('maintenance_overdue_resume_required')
    org=db.execute("SELECT level,revision FROM organizations WHERE id=? AND kind='family'",(command.family,)).fetchone()
    assets=db.execute('SELECT funds,popularity,construction FROM family_assets WHERE family=?',(command.family,)).fetchone()
    if not org or not assets or assets[2] is None:raise ValueError('family_maintenance_state_unknown')
    if type(org[0]) is not int or not 1<=org[0]<=len(policy.rows):raise ValueError('family_level_unknown')
    if (any(type(value) is not int for value in assets)
            or not 0<=assets[0]<2**63 or not 0<=assets[1]<=policy.popularity_max
            or not 0<=assets[2]<2**31):raise ValueError('family_maintenance_state_unknown')
    from family_products import snapshot as products_snapshot
    products=products_snapshot(db,command.family)
    product_recipe=db.execute('SELECT recipe FROM family_products WHERE family=?',(command.family,)).fetchone()[0]
    if product_recipe!=policy.products_revision:raise ValueError('family_product_recipe_mismatch')
    online_count=0
    for rid,epoch in command.online:
        row=db.execute('''SELECT l.epoch,l.active FROM family_members m JOIN role_leases l ON l.role_id=m.role_id
            WHERE m.family=? AND m.role_id=?''',(command.family,rid)).fetchone()
        online_count+=bool(row and str(row[0])==str(epoch) and row[1]==1)
    row=policy.rows[org[0]-1]
    total=row.base+row.drug*products.drug_open+row.special*products.special_open
    if assets[1]<policy.low_popularity:total=total*policy.low_fee_numerator//policy.low_fee_denominator
    normal=assets[0]>policy.normal_horizon*total
    base=row.base
    if assets[1]<policy.low_popularity:base=base*policy.low_fee_numerator//policy.low_fee_denominator
    fee=total if normal else min(assets[0],base)
    popularity=min(policy.popularity_max,max(0,assets[1]+policy.online_gain*online_count-policy.hourly_decay))
    funds=assets[0]-fee
    level=org[0]
    state='active'
    construction=assets[2]
    recovery_funds=0;recovery_popularity=0
    if funds<1 or popularity<1:
        level-=1
        construction=0
        if level:
            recovery_funds=policy.downgrade_funds
            recovery_popularity=min(policy.downgrade_popularity,policy.popularity_max-popularity)
            funds+=policy.downgrade_funds
            if funds>=2**63:raise ValueError('family_maintenance_overflow')
            popularity=min(policy.popularity_max,popularity+policy.downgrade_popularity)
        else:
            state='dissolution_pending'
            members=tuple(tuple(row) for row in db.execute('''SELECT m.role_id,s.generation FROM family_members m
                LEFT JOIN family_member_state s ON s.role_id=m.role_id WHERE m.family=? ORDER BY m.role_id''',(command.family,)))
            if any(not generation for _,generation in members):raise ValueError('family_dissolution_membership_unknown')
            guild=db.execute('''SELECT g.guild,t.generation FROM guild_families g
                LEFT JOIN guild_family_generations t ON t.family=g.family WHERE g.family=?''',(command.family,)).fetchone()
            if guild and not guild[1]:raise ValueError('family_dissolution_guild_unknown')
            db.execute('''INSERT INTO family_dissolution_outbox
                (family,due_ms,guild,guild_token,members,state,partition,guild_done) VALUES(?,?,?,?,?,?,?,0)''',
                (command.family,command.due_ms,guild[0] if guild else None,guild[1] if guild else None,
                 json.dumps(members),'pending',command.family%policy.partitions))
    drug=max(products.drug_stock,row.drug_max) if normal and products.drug_open else products.drug_stock
    special=max(products.special_stock,row.special_max) if normal and products.special_open else products.special_stock
    next_due=command.due_ms+policy.period_ms
    if next_due>=2**63:raise ValueError('invalid_family_maintenance_time')
    db.execute('UPDATE family_assets SET funds=?,popularity=?,construction=? WHERE family=?',(funds,popularity,construction,command.family))
    if (drug,special)!=(products.drug_stock,products.special_stock):
        db.execute('UPDATE family_products SET drug_stock=?,special_stock=?,revision=revision+1 WHERE family=?',
            (drug,special,command.family))
    db.execute('UPDATE organizations SET level=?,revision=revision+1 WHERE id=?',(level,command.family))
    if 0<level<org[0]:
        from family_history import record
        record(db,command.family,f'maintenance:{command.due_ms}',3,now,str(level))
    db.execute('UPDATE family_maintenance SET next_due_ms=?,revision=revision+1,state=? WHERE family=?',(next_due,state,command.family))
    result=MaintenanceReceipt(command.family,command.due_ms,next_due,'normal' if normal else 'simple',fee,online_count,
        funds,popularity,drug,special,org[1]+1,org[0],level,state,
        assets[0],assets[1],products.drug_stock,products.special_stock,recovery_funds,recovery_popularity,policy.revision)
    db.execute('INSERT INTO family_maintenance_receipts VALUES(?,?,?,?,?)',
        (command.family,command.due_ms,fingerprint,json.dumps(result.__dict__,separators=(',',':')),now))
    return result
