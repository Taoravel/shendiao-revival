"""Guild-owned hourly source. Caller owns transaction, no role/map writes.

Only explicit new-guild policies initialize clocks and resources. Research,
building fees and the independent practice-material account retain ownership.
"""
from dataclasses import dataclass,asdict,replace
import hashlib,json
from guild_buildings import snapshot as buildings,normal_cost


@dataclass(frozen=True)
class GuildMaintenanceRules:
    revision: str
    origin: str
    period_ms: int
    partitions: int
    batch_limit: int
    member_limit: int
    scheduler_enabled: bool
    scan_interval_ms: int
    max_lateness_ms: int
    popularity_max: int
    online_gain: int
    hourly_decay: int
    basic_costs: tuple
    initial_resources: int
    resource_growth: tuple
    resource_caps: tuple
    fund_caps: tuple
    research_power: tuple
    research_experience: tuple
    digest: str


@dataclass(frozen=True)
class GuildClock:
    guild: int
    created_ms: int
    next_due_ms: int
    state: str
    revision: int
    recipe: str
    origin: str


@dataclass(frozen=True)
class GuildResources:
    guild: int
    amount: int
    revision: int
    origin: str


@dataclass(frozen=True)
class GuildMaintenanceView:
    clock: GuildClock
    resources: GuildResources
    funds: int
    popularity: int
    level: int
    research_power: int
    normal_fee: int


@dataclass(frozen=True)
class GuildClockResumeCommand:
    guild: int
    due_ms: int
    deadline_ms: int

    @property
    def request_id(self):return f'guild-maintenance:{self.guild}:{self.due_ms}'


@dataclass(frozen=True)
class GuildMaintenanceCommand(GuildClockResumeCommand):
    online: tuple = ()


@dataclass(frozen=True)
class GuildMaintenanceValues:
    funds: int
    popularity: int
    resources: int
    level: int
    power: int
    normal_fee: int
    state: str


@dataclass(frozen=True)
class GuildMaintenanceReceipt:
    guild: int
    due_ms: int
    next_due_ms: int
    mode: str
    fee: int
    online_count: int
    status: str
    before: GuildMaintenanceValues
    after: GuildMaintenanceValues
    research: object
    recovery_funds: int
    recovery_popularity: int
    revision: int
    recipe: str


@dataclass(frozen=True)
class GuildMaintenancePage:
    entries: tuple
    ceiling: tuple | None


def page(db,partition,now,after,ceiling,policy):
    def valid_key(key):return type(key) is tuple and len(key)==2 and all(type(v) is int and 0<v<2**63 for v in key)
    if (policy is None or type(partition) is not int or not 0<=partition<policy.partitions
            or type(now) is not int or not 0<=now<2**63
            or (after is not None and not valid_key(after)) or (ceiling is not None and not valid_key(ceiling))
            or (after is not None and (ceiling is None or after>ceiling))):
        raise ValueError('invalid_guild_maintenance_directory')
    if ceiling is None:
        row=db.execute('''SELECT next_due_ms,guild FROM guild_maintenance_clocks
            WHERE partition=? AND state='active' AND next_due_ms<=?
            ORDER BY next_due_ms DESC,guild DESC LIMIT 1''',(partition,now)).fetchone()
        if row is None:return GuildMaintenancePage((),None)
        ceiling=tuple(row)
    entries=tuple(tuple(row) for row in db.execute('''SELECT guild,next_due_ms FROM guild_maintenance_clocks
        WHERE partition=? AND state='active' AND next_due_ms<=? AND (next_due_ms,guild)>(?,?)
        AND (next_due_ms,guild)<=(?,?) ORDER BY next_due_ms,guild LIMIT ?''',
        (partition,now,*(after or (0,0)),*ceiling,policy.batch_limit)))
    return GuildMaintenancePage(entries,ceiling)


def rules(raw,building_rules,research_rules):
    if raw is None:return None
    if type(raw) is not dict or building_rules is None or research_rules is None:
        raise ValueError('explicit_guild_maintenance_dependencies_required')
    values={key:raw.get(key) for key in GuildMaintenanceRules.__dataclass_fields__ if key!='digest'}
    for key in ('basic_costs','resource_growth','resource_caps','fund_caps','research_power','research_experience'):
        if type(values[key]) not in (list,tuple):raise ValueError('invalid_guild_maintenance_policy')
        values[key]=tuple(values[key])
    if (any(type(values[k]) is not str or not 1<=len(values[k])<=160 or '\0' in values[k] for k in ('revision','origin'))
            or type(values['period_ms']) is not int or values['period_ms']!=3600000
            or any(type(values[k]) is not int or not 1<=values[k]<=256 for k in ('partitions','batch_limit'))
            or type(values['member_limit']) is not int or not 1<=values['member_limit']<=4096
            or type(values['scheduler_enabled']) is not bool
            or type(values['scan_interval_ms']) is not int or not 10<=values['scan_interval_ms']<=60000
            or type(values['max_lateness_ms']) is not int or not 0<values['max_lateness_ms']<values['period_ms']
            or type(values['popularity_max']) is not int or not building_rules.initial_popularity<=values['popularity_max']<2**31
            or any(type(values[k]) is not int or not 0<=values[k]<2**31 for k in ('online_gain','hourly_decay','initial_resources'))
            or len(values['basic_costs'])!=len(building_rules.caps)
            or any(type(n) is not int or not 0<n<2**63 for n in values['basic_costs'])):
        raise ValueError('invalid_guild_maintenance_policy')
    for key in ('resource_growth','resource_caps','fund_caps','research_power','research_experience'):
        limit=2**63 if key=='fund_caps' else 2**31
        array=values[key]
        if len(array)!=21 or any(type(n) is not int or not 0<=n<limit for n in array) or tuple(sorted(array))!=array:
            raise ValueError('invalid_guild_maintenance_curve')
    if values['initial_resources']>values['resource_caps'][building_rules.initial_levels[1]]:
        raise ValueError('invalid_guild_resource_baseline')
    # Polling controls change execution cadence, never the economic recipe.
    economic={k:v for k,v in values.items() if k not in ('scheduler_enabled','scan_interval_ms')}
    digest=hashlib.sha256(json.dumps([economic,building_rules.fingerprint,research_rules.digest],
        ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return GuildMaintenanceRules(**values,digest=digest)


def prepare(db):
    from guild_maintenance_closure import prepare as prepare_closure
    prepare_closure(db)
    db.execute('''CREATE TABLE IF NOT EXISTS guild_maintenance_clocks (
        guild INTEGER PRIMARY KEY REFERENCES organizations(id),partition INTEGER NOT NULL,
        created_ms INTEGER NOT NULL,next_due_ms INTEGER NOT NULL,state TEXT NOT NULL CHECK(state IN ('active','retired')),
        revision INTEGER NOT NULL,recipe TEXT NOT NULL,origin TEXT NOT NULL)''')
    db.execute('CREATE INDEX IF NOT EXISTS guild_maintenance_directory ON guild_maintenance_clocks(partition,state,next_due_ms,guild)')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_resources (
        guild INTEGER PRIMARY KEY REFERENCES organizations(id),amount INTEGER NOT NULL CHECK(amount>=0 AND amount<2147483648),
        revision INTEGER NOT NULL,origin TEXT NOT NULL,recipe TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_maintenance_receipts (
        guild INTEGER NOT NULL REFERENCES organizations(id),due_ms INTEGER NOT NULL,
        recipe TEXT NOT NULL,result TEXT NOT NULL,digest TEXT NOT NULL,created_ms INTEGER NOT NULL,
        PRIMARY KEY(guild,due_ms))''')
    db.execute('CREATE INDEX IF NOT EXISTS guild_maintenance_fund_source ON organization_fund_ledger(organization,request_id)')


def new_guild(db,guild,now,policy):
    if policy is None:return
    if type(now) is not int or not 0<=now<2**63-policy.period_ms:raise ValueError('invalid_guild_maintenance_time')
    db.execute('INSERT INTO guild_maintenance_clocks VALUES(?,?,?,?,?,1,?,?)',
        (guild,guild%policy.partitions,now,now+policy.period_ms,'active',policy.digest,policy.origin))
    db.execute('INSERT INTO guild_resources VALUES(?,?,1,?,?)',(guild,policy.initial_resources,policy.origin,policy.digest))


def snapshot(db,guild,policy,building_rules):
    row=db.execute('''SELECT guild,created_ms,next_due_ms,state,revision,recipe,origin
        FROM guild_maintenance_clocks WHERE guild=?''',(guild,)).fetchone()
    if row is None:raise ValueError('guild_maintenance_unknown')
    if policy is None:raise ValueError('guild_maintenance_policy_unknown')
    clock=GuildClock(*tuple(row))
    resource=db.execute('SELECT guild,amount,revision,origin,recipe FROM guild_resources WHERE guild=?',(guild,)).fetchone()
    if clock.recipe!=policy.digest or clock.origin!=policy.origin:raise ValueError('guild_maintenance_recipe_changed')
    if (not resource or resource[3:]!=(policy.origin,policy.digest)
            or type(resource[1]) is not int or not 0<=resource[1]<2**31
            or type(resource[2]) is not int or not 0<resource[2]<2**63
            or type(clock.created_ms) is not int or not 0<=clock.created_ms<2**63
            or type(clock.next_due_ms) is not int or not clock.created_ms<clock.next_due_ms<2**63
            or type(clock.revision) is not int or not 0<clock.revision<2**63 or clock.state not in ('active','retired')):
        raise ValueError('guild_maintenance_state_invalid')
    state=buildings(db,guild,building_rules)
    org=db.execute("SELECT level FROM organizations WHERE id=? AND kind='guild'",(guild,)).fetchone()
    funds=db.execute('SELECT funds FROM guild_assets WHERE guild=?',(guild,)).fetchone()
    if (not org or type(org[0]) is not int or not 0<=org[0]<=len(policy.basic_costs)
            or not funds or type(funds[0]) is not int or not 0<=funds[0]<2**63
            or state.popularity>policy.popularity_max):raise ValueError('guild_maintenance_state_invalid')
    return GuildMaintenanceView(clock,GuildResources(*tuple(resource[:4])),funds[0],state.popularity,org[0],
        policy.research_power[state.buildings[2].level],normal_cost(state,building_rules))


def validate(command,now,policy,*,resume=False):
    expected=GuildClockResumeCommand if resume else GuildMaintenanceCommand
    if (type(command) is not expected
            or any(type(v) is not int or not 0<v<2**63 for v in (command.guild,command.due_ms,command.deadline_ms))
            or type(now) is not int or not 0<=now<2**63-3600000):
        raise ValueError('invalid_guild_maintenance_command')
    if now>command.deadline_ms:raise ValueError('guild_maintenance_deadline')
    if resume:return
    if type(command.online) is not tuple or len(command.online)>4096:
        raise ValueError('invalid_guild_maintenance_observation')
    seen=set()
    for item in command.online:
        if (type(item) is not tuple or len(item)!=2 or type(item[0]) is not int or not 0<item[0]<2**63
                or type(item[1]) not in (int,str) or isinstance(item[1],bool)
                or (type(item[1]) is int and not 0<item[1]<2**63)
                or (type(item[1]) is str and (not 1<=len(item[1])<=96 or '\0' in item[1])) or item[0] in seen):
            raise ValueError('invalid_guild_maintenance_observation')
        seen.add(item[0])


def _json(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def _values(view):
    return GuildMaintenanceValues(view.funds,view.popularity,view.resources.amount,view.level,
        view.research_power,view.normal_fee,view.clock.state)


def _prior(db,command):
    row=db.execute('SELECT recipe,result,digest,created_ms FROM guild_maintenance_receipts WHERE guild=? AND due_ms=?',
        (command.guild,command.due_ms)).fetchone()
    if row is None:return None
    raw=json.loads(row[1])
    if hashlib.sha256(_json(raw).encode()).hexdigest()!=row[2]:raise ValueError('guild_maintenance_receipt_invalid')
    for name in ('before','after'):raw[name]=GuildMaintenanceValues(**raw[name])
    if raw['research'] is not None:
        from guild_research import ResearchReceipt,ResearchSkill
        child=raw['research']
        for name in ('before','after'):
            if child[name] is not None:child[name]=ResearchSkill(**child[name])
        raw['research']=ResearchReceipt(**child)
    result=GuildMaintenanceReceipt(**raw)
    if (type(result.guild) is not int or type(result.due_ms) is not int
            or (result.guild,result.due_ms)!=(command.guild,command.due_ms) or result.recipe!=row[0]
            or result.mode not in ('normal','basic','none') or result.status not in ('maintained','degraded','retired','resumed')
            or any(type(v) is not int or not 0<=v<2**63 for v in (result.next_due_ms,result.fee,
                result.online_count,result.recovery_funds,result.recovery_popularity,result.revision))
            or result.next_due_ms<=result.due_ms or result.revision<1):
        raise ValueError('guild_maintenance_receipt_invalid')
    for value in (result.before,result.after):
        if (any(type(v) is not int or not 0<=v<2**63 for v in (value.funds,value.normal_fee))
                or any(type(v) is not int or not 0<=v<2**31 for v in (value.popularity,value.resources,value.power))
                or type(value.level) is not int or not 0<=value.level<=32 or value.state not in ('active','retired')):
            raise ValueError('guild_maintenance_receipt_invalid')
    child=db.execute('SELECT experience,result FROM guild_research_receipts WHERE guild=? AND request_id=?',
        (command.guild,command.request_id)).fetchone()
    if result.research is not None:
        if (child is None or type(child[0]) is not int or child[0]!=result.research.accepted+result.research.discarded
                or _json(json.loads(child[1]))!=_json(asdict(result.research))):
            raise ValueError('guild_maintenance_outcome_unknown')
    elif child is not None:raise ValueError('guild_maintenance_outcome_unknown')
    ledger=tuple(tuple(r) for r in db.execute('''SELECT reason,delta,balance,created_ms FROM organization_fund_ledger
        WHERE organization=? AND request_id=? LIMIT 2''',(command.guild,command.request_id)))
    if result.status=='resumed':
        if (ledger or result.research is not None or result.mode!='none' or result.fee!=0
                or result.online_count!=0 or result.before!=result.after or result.recovery_funds or result.recovery_popularity):
            raise ValueError('guild_maintenance_outcome_unknown')
    elif ledger!=(('guild-maintenance',result.after.funds-result.before.funds,result.after.funds,row[3]),):
        raise ValueError('guild_maintenance_outcome_unknown')
    return result


def _record(db,command,result,now):
    encoded=_json(asdict(result));digest=hashlib.sha256(encoded.encode()).hexdigest()
    db.execute('INSERT INTO guild_maintenance_receipts VALUES(?,?,?,?,?,?)',
        (command.guild,command.due_ms,result.recipe,encoded,digest,now))
    return result


def resume(db,command,now,policy,building_rules):
    validate(command,now,policy,resume=True)
    if not db.in_transaction:raise ValueError('guild_maintenance_transaction_required')
    prior=_prior(db,command)
    if prior:return prior
    from guild_dissolution import require_active
    require_active(db,command.guild)
    view=snapshot(db,command.guild,policy,building_rules);clock=view.clock
    if clock.state!='active':raise ValueError('guild_maintenance_retired')
    if command.due_ms!=clock.next_due_ms or now-clock.next_due_ms<=policy.max_lateness_ms:
        raise ValueError('guild_maintenance_resume_not_required')
    if clock.revision==2**63-1:raise ValueError('guild_maintenance_state_invalid')
    if (db.execute('SELECT 1 FROM guild_research_receipts WHERE guild=? AND request_id=?',(command.guild,command.request_id)).fetchone()
            or db.execute('SELECT 1 FROM organization_fund_ledger WHERE organization=? AND request_id=? LIMIT 1',
                (command.guild,command.request_id)).fetchone()):raise ValueError('guild_maintenance_outcome_unknown')
    next_due=now+policy.period_ms
    db.execute('UPDATE guild_maintenance_clocks SET next_due_ms=?,revision=revision+1 WHERE guild=?',(next_due,command.guild))
    revision=db.execute('SELECT revision FROM organizations WHERE id=?',(command.guild,)).fetchone()[0]
    result=GuildMaintenanceReceipt(command.guild,command.due_ms,next_due,'none',0,0,'resumed',
        _values(view),_values(view),None,0,0,revision,policy.digest)
    return _record(db,command,result,now)


def settle(db,command,now,policy,building_rules,research_rules,history_partitions):
    validate(command,now,policy)
    if not db.in_transaction:raise ValueError('guild_maintenance_transaction_required')
    prior=_prior(db,command)
    if prior:return prior
    from guild_dissolution import require_active
    require_active(db,command.guild)
    view=snapshot(db,command.guild,policy,building_rules);clock=view.clock
    if len(command.online)>policy.member_limit:raise ValueError('invalid_guild_maintenance_observation')
    if clock.state!='active':raise ValueError('guild_maintenance_retired')
    if command.due_ms!=clock.next_due_ms or now<clock.next_due_ms:raise ValueError('guild_maintenance_not_due')
    if now-clock.next_due_ms>policy.max_lateness_ms:raise ValueError('guild_maintenance_overdue_resume_required')
    if clock.revision==2**63-1 or not 1<=view.level<=len(policy.basic_costs):raise ValueError('guild_maintenance_state_invalid')
    if (db.execute('SELECT 1 FROM guild_research_receipts WHERE guild=? AND request_id=?',(command.guild,command.request_id)).fetchone()
            or db.execute('SELECT 1 FROM organization_fund_ledger WHERE organization=? AND request_id=? LIMIT 1',
                (command.guild,command.request_id)).fetchone()):raise ValueError('guild_maintenance_outcome_unknown')
    org=db.execute("SELECT * FROM organizations WHERE id=? AND kind='guild'",(command.guild,)).fetchone()
    if type(org['revision']) is not int or not 0<org['revision']<2**63-1:raise ValueError('guild_revision_overflow')
    online=0
    for role,epoch in command.online:
        row=db.execute('''SELECT l.epoch,l.active FROM family_members m JOIN guild_families g ON g.family=m.family
            JOIN role_leases l ON l.role_id=m.role_id LEFT JOIN family_maintenance c ON c.family=m.family
            WHERE g.guild=? AND m.role_id=? AND COALESCE(c.state,'active')='active' ''',(command.guild,role)).fetchone()
        online+=bool(row and str(row[0])==str(epoch) and row[1]==1)
    popularity=min(policy.popularity_max,max(0,view.popularity+policy.online_gain*online-policy.hourly_decay))
    state=buildings(db,command.guild,building_rules)
    normal_fee=normal_cost(replace(state,popularity=popularity),building_rules)
    normal=view.funds>=48*normal_fee
    basic=policy.basic_costs[view.level-1]
    if popularity<1000:basic=(basic*3+1)//2
    fee=normal_fee if normal else min(view.funds,basic)
    funds=view.funds-fee
    recovery_funds=0;recovery_popularity=0;status='maintained'
    if funds<1 or popularity<1:
        if state.generation==2**63-1:raise ValueError('guild_building_generation_exhausted')
        db.execute('UPDATE guild_building_state SET selected=-1,generation=generation+1 WHERE guild=?',(command.guild,))
        if view.level==1:
            from guild_maintenance_closure import close
            close(db,command,now,policy,history_partitions,org['revision']+1)
            status='retired'
        else:
            level=view.level-1;cap=building_rules.caps[level-1]
            for b in state.buildings:
                if b.level>cap:
                    db.execute('UPDATE guild_buildings SET level=?,construction=0 WHERE guild=? AND building_type=?',
                        (cap,command.guild,b.building_type))
            db.execute('UPDATE organizations SET level=? WHERE id=?',(level,command.guild))
            reduced=buildings(db,command.guild,building_rules)
            recovery_funds=min(5000000,max(0,policy.fund_caps[reduced.buildings[0].level]-funds))
            recovery_popularity=min(500,policy.popularity_max-popularity)
            funds+=recovery_funds;popularity+=recovery_popularity;status='degraded'
    resources=view.resources.amount;research=None
    if normal and status=='maintained':
        growth=min(policy.resource_growth[state.buildings[1].level],
            max(0,policy.resource_caps[state.buildings[1].level]-resources))
        resources+=growth
        if growth:
            if view.resources.revision==2**63-1:raise ValueError('guild_resource_revision_overflow')
            db.execute('UPDATE guild_resources SET amount=?,revision=revision+1 WHERE guild=?',(resources,command.guild))
        from guild_research import award,ResearchAward
        research=award(db,ResearchAward(command.guild,command.request_id,
            policy.research_experience[state.buildings[2].level],command.deadline_ms),now,research_rules)
    db.execute('UPDATE guild_assets SET funds=? WHERE guild=?',(funds,command.guild))
    db.execute('UPDATE guild_building_state SET popularity=? WHERE guild=?',(popularity,command.guild))
    if research is None or research.status!='advanced':
        db.execute('UPDATE organizations SET revision=revision+1 WHERE id=?',(command.guild,))
    next_due=command.due_ms+policy.period_ms
    if next_due>=2**63:raise ValueError('invalid_guild_maintenance_time')
    db.execute('UPDATE guild_maintenance_clocks SET next_due_ms=?,revision=revision+1 WHERE guild=?',(next_due,command.guild))
    revision=db.execute('SELECT revision FROM organizations WHERE id=?',(command.guild,)).fetchone()[0]
    db.execute('INSERT INTO organization_fund_ledger VALUES(?,?,?,?,?,?,?)',
        (command.guild,org['leader'],command.request_id,'guild-maintenance',funds-view.funds,funds,now))
    after=snapshot(db,command.guild,policy,building_rules)
    result=GuildMaintenanceReceipt(command.guild,command.due_ms,next_due,'normal' if normal else 'basic',fee,online,
        status,_values(view),_values(after),research,recovery_funds,recovery_popularity,revision,policy.digest)
    return _record(db,command,result,now)
