"""Guild-owned consumer of a durable family closure; no role or map writes."""
from dataclasses import dataclass,asdict
import hashlib,json
from family_maintenance import FamilyDissolution
from guild_offices import position,prune,clear
from guild_projection import current_members


@dataclass(frozen=True)
class GuildClosureRules:
    revision: str
    succession_order: tuple
    member_limit: int
    history_partitions: int


@dataclass(frozen=True)
class GuildClosureReceipt:
    guild: int
    family: int
    due_ms: int
    family_token: str
    old_leader: int
    new_leader: int
    state: str
    revision: int
    closed_memberships: tuple
    recipe: str


@dataclass(frozen=True)
class GuildLifecycle:
    guild: int
    state: str
    revision: int
    recipe: str


def rules(policy):
    raw=policy['guild_dissolution'];order=tuple(raw['succession_order'])
    partitions=policy['family_maintenance']['partitions']
    if (type(raw['revision']) is not str or not raw['revision']
            or len(order)!=6 or set(order)!={'deputy','left_elder','right_elder','patrol','family_leader','member'}
            or raw['funds_on_close']!='retire_no_refund'
            or type(partitions) is not int or not 0<partitions<2**31):
        raise ValueError('invalid_guild_dissolution_policy')
    return GuildClosureRules(raw['revision'],order,max(policy['family_capacities']),partitions)


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS guild_lifecycle (
        guild INTEGER PRIMARY KEY REFERENCES organizations(id),
        state TEXT NOT NULL CHECK(state IN ('active','succession_pending','dissolution_pending')),
        revision INTEGER NOT NULL CHECK(revision>0),recipe TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_family_dissolution_receipts (
        guild INTEGER NOT NULL REFERENCES organizations(id),family INTEGER NOT NULL,due_ms INTEGER NOT NULL,
        fingerprint TEXT NOT NULL,result TEXT NOT NULL,created_ms INTEGER NOT NULL,
        PRIMARY KEY(guild,family,due_ms))''')


def new_guild(db,guild,policy):
    db.execute('INSERT INTO guild_lifecycle VALUES(?,?,?,?)',(guild,'active',1,policy.revision))


def lifecycle(db,guild):
    org=db.execute("SELECT revision FROM organizations WHERE id=? AND kind='guild'",(guild,)).fetchone()
    if not org:raise ValueError('organization_missing')
    row=db.execute('SELECT guild,state,revision,recipe FROM guild_lifecycle WHERE guild=?',(guild,)).fetchone()
    return GuildLifecycle(*tuple(row)) if row else GuildLifecycle(guild,'active',org[0],'legacy_no_closure')


def require_active(db,guild):
    state=lifecycle(db,guild).state
    if state!='active':raise ValueError('guild_'+state)


def validate(event,request_id,deadline,now,policy):
    if (not isinstance(event,FamilyDissolution)
            or any(type(v) is not int or not 0<v<2**63 for v in (event.family,event.guild,event.due_ms,deadline))
            or type(event.guild_token) is not str or not 1<=len(event.guild_token)<=96
            or event.state!='pending' or type(request_id) is not str or not 1<=len(request_id)<=160
            or type(now) is not int or not 0<=now<2**63
            or type(event.members) is not tuple or len(event.members)>policy.member_limit):
        raise ValueError('invalid_guild_dissolution_event')
    seen=set()
    for item in event.members:
        if (type(item) is not tuple or len(item)!=2 or type(item[0]) is not int or not 0<item[0]<2**63
                or type(item[1]) is not str or not 1<=len(item[1])<=96 or item[0] in seen):
            raise ValueError('invalid_guild_dissolution_members')
        seen.add(item[0])
    if now>deadline:raise ValueError('guild_dissolution_deadline')


def fingerprint(event,policy):
    return hashlib.sha256(json.dumps([event.guild,event.family,event.due_ms,event.guild_token,event.members,policy.revision],
        separators=(',',':')).encode()).hexdigest()


def receipt(db,event,policy):
    row=db.execute('SELECT fingerprint,result FROM guild_family_dissolution_receipts WHERE guild=? AND family=? AND due_ms=?',
        (event.guild,event.family,event.due_ms)).fetchone()
    if not row:return None
    if row[0]!=fingerprint(event,policy):raise ValueError('guild_dissolution_intent_conflict')
    raw=json.loads(row[1]);raw['closed_memberships']=tuple(tuple(item) for item in raw['closed_memberships'])
    return GuildClosureReceipt(**raw)


def apply(db,event,request_id,deadline,now,policy):
    validate(event,request_id,deadline,now,policy)
    old=receipt(db,event,policy)
    if old:return old
    source=db.execute('''SELECT guild,guild_token,members,state FROM family_dissolution_outbox
        WHERE family=? AND due_ms=?''',(event.family,event.due_ms)).fetchone()
    if (not source or source[3]!='pending' or (source[0],source[1])!=(event.guild,event.guild_token)
            or tuple(tuple(item) for item in json.loads(source[2]))!=event.members):
        raise ValueError('guild_dissolution_source_missing')
    clock=db.execute('SELECT state FROM family_maintenance WHERE family=?',(event.family,)).fetchone()
    if not clock or clock[0]!='dissolution_pending':raise ValueError('guild_dissolution_source_inactive')
    link=db.execute('''SELECT g.guild,t.generation FROM guild_families g
        LEFT JOIN guild_family_generations t ON t.family=g.family WHERE g.family=?''',(event.family,)).fetchone()
    if not link:
        from guild_maintenance_closure import retired_family
        if not retired_family(db,event.guild,event.family,event.guild_token):raise ValueError('stale_guild_family_generation')
        org=db.execute("SELECT * FROM organizations WHERE id=? AND kind='guild'",(event.guild,)).fetchone()
        result=GuildClosureReceipt(event.guild,event.family,event.due_ms,event.guild_token,org['leader'],0,
            'dissolution_pending',org['revision'],event.members,policy.revision)
        db.execute('INSERT INTO guild_family_dissolution_receipts VALUES(?,?,?,?,?,?)',
            (event.guild,event.family,event.due_ms,fingerprint(event,policy),json.dumps(asdict(result)),now))
        return result
    if tuple(link)!=(event.guild,event.guild_token):raise ValueError('stale_guild_family_generation')
    org=db.execute("SELECT * FROM organizations WHERE id=? AND kind='guild'",(event.guild,)).fetchone()
    if not org:raise ValueError('organization_missing')
    if type(org['revision']) is not int or not 0<org['revision']<2**63-1:raise ValueError('guild_revision_overflow')
    for role,token in event.members:
        known=db.execute('''SELECT 1 FROM guild_member_state WHERE guild=? AND role_id=?
            AND family_token=? AND member_token=?''',(event.guild,role,event.guild_token,token)).fetchone()
        if not known:
            # A family may dissolve before the guild consumes a fresh join.
            # Its still-unconsumed durable event proves no guild baseline was
            # issued for this membership; do not invent a zero-valued profile.
            fresh=db.execute('''SELECT 1 FROM family_join_events e JOIN guild_view_state v ON v.guild=?
                JOIN family_member_state s ON s.role_id=e.role_id AND s.generation=e.generation
                JOIN family_members m ON m.role_id=e.role_id AND m.family=e.family
                WHERE e.role_id=? AND e.family=? AND e.generation=? AND e.sequence>v.join_cursor''',
                (event.guild,role,event.family,token)).fetchone()
            if not fresh:raise ValueError('guild_member_state_unknown')
        db.execute('''UPDATE guild_member_state SET prestige=0,prestige_upper=0,active=0
            WHERE guild=? AND role_id=? AND family_token=? AND member_token=?''',(event.guild,role,event.guild_token,token))
    db.execute('UPDATE guild_member_state SET active=0 WHERE guild=? AND family_token=?',(event.guild,event.guild_token))
    from family_guild_history import emit
    emit(db,event.guild,event.family,6,f'family-dissolution:{event.family}:{event.due_ms}',now,policy.history_partitions)
    db.execute('DELETE FROM guild_families WHERE family=? AND guild=?',(event.family,event.guild))
    prune(db,org)
    candidates=current_members(db,event.guild)
    leader=org['leader'];state='active'
    if leader not in {row['role_id'] for row in candidates}:
        def rank(row):
            office=position(db,org,row['role_id'])
            if office=='member' and row['family_position']=='leader':office='family_leader'
            joined=db.execute('''SELECT MAX(m.joined_ms,g.joined_ms) FROM family_members m
                JOIN guild_families g ON g.family=m.family WHERE m.role_id=? AND g.guild=?''',
                (row['role_id'],event.guild)).fetchone()[0]
            return (policy.succession_order.index(office),joined,row['role_id'])
        if candidates:
            leader=min(candidates,key=rank)['role_id']
            clear(db,event.guild,leader)
        else:
            leader=0
            remaining=db.execute('SELECT 1 FROM guild_families WHERE guild=? LIMIT 1',(event.guild,)).fetchone()
            state='succession_pending' if remaining else 'dissolution_pending'
        # Delegation was granted by the departing leader, even if the new
        # leader is a different elder and the old deputy still survives.
        db.execute('DELETE FROM guild_deputy_authority WHERE guild=?',(event.guild,))
    # Preserve the historical role FK while no eligible leader exists. The
    # lifecycle revokes all authority; the receipt exposes no active leader.
    db.execute('UPDATE organizations SET leader=?,revision=revision+1 WHERE id=?',
        (leader or org['leader'],event.guild))
    db.execute('INSERT INTO guild_lifecycle VALUES(?,?,?,?) ON CONFLICT(guild) DO UPDATE SET '
        'state=excluded.state,revision=excluded.revision,recipe=excluded.recipe',
        (event.guild,state,org['revision']+1,policy.revision))
    if state!='active':
        from guild_maintenance_closure import retire_clock
        retire_clock(db,event.guild)
    result=GuildClosureReceipt(event.guild,event.family,event.due_ms,event.guild_token,org['leader'],leader,
        state,org['revision']+1,event.members,policy.revision)
    db.execute('INSERT INTO guild_family_dissolution_receipts VALUES(?,?,?,?,?,?)',
        (event.guild,event.family,event.due_ms,fingerprint(event,policy),json.dumps(asdict(result)),now))
    return result
