"""Guild-owned membership projection. Call inside the persistence Adapter.

New guild memberships get explicit baselines once. Existing unknown values
are never filled during reads. No connections, commits, wallet or network.
"""
from dataclasses import dataclass,field
from datetime import datetime,timezone,timedelta
import guild_protocol as p
from guild_offices import position,authority
from guild_research import ResearchSnapshot
from guild_buildings import BuildingSnapshot


@dataclass(frozen=True)
class GuildAudience:
    identity: int
    members: tuple  # (role_id, guild-family generation, family-member generation)


@dataclass(frozen=True)
class GuildProjection:
    view: p.GuildView
    members: tuple
    authority: int
    research: ResearchSnapshot | None = field(default=None,kw_only=True)
    buildings: BuildingSnapshot | None = field(default=None,kw_only=True)


@dataclass(frozen=True)
class GuildChange:
    before: GuildAudience
    after: GuildAudience


@dataclass(frozen=True)
class ProjectionRules:
    reserved: int
    metadata: tuple
    prestige: tuple
    dues: tuple
    origin: str


def rules(policy):
    r=ProjectionRules(policy['guild_data_reserved'],tuple(policy['guild_new_member_metadata']),
        tuple(policy['guild_new_member_prestige']),tuple(policy['guild_new_member_dues']),policy['guild_member_origin'])
    if (type(r.reserved) is not int or not -2**31<=r.reserved<2**31
        or len(r.metadata)!=3 or len(r.prestige)!=2 or len(r.dues)!=2
        or any(type(n) is not int or not -2**31<=n<2**31 for n in r.metadata)
        or any(type(n) is not int or not 0<=n<2**31 for n in r.prestige)
        or any(type(n) is not int or not 0<=n<2**63 for n in r.dues)
        or type(r.origin) is not str or not r.origin):raise ValueError('invalid_guild_projection_policy')
    return r


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS guild_view_state (
        guild INTEGER PRIMARY KEY REFERENCES organizations(id),reserved INTEGER NOT NULL,
        origin TEXT NOT NULL,join_cursor INTEGER NOT NULL DEFAULT 0)''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_member_state (
        guild INTEGER NOT NULL REFERENCES guild_view_state(guild),role_id INTEGER NOT NULL REFERENCES roles(id),
        family_token TEXT NOT NULL,member_token TEXT NOT NULL,
        metadata1 INTEGER NOT NULL,metadata2 INTEGER NOT NULL,metadata3 INTEGER NOT NULL,
        prestige INTEGER NOT NULL CHECK(prestige>=0),prestige_upper INTEGER NOT NULL CHECK(prestige_upper>=0),
        weekly_dues INTEGER NOT NULL CHECK(weekly_dues>=0),historical_dues INTEGER NOT NULL CHECK(historical_dues>=0),
        origin TEXT NOT NULL,active INTEGER NOT NULL CHECK(active IN(0,1)),
        PRIMARY KEY(guild,role_id,family_token,member_token))''')


def current_members(db,guild):
    return tuple(db.execute('''SELECT m.role_id,m.family,m.position AS family_position,r.name,r.level,r.school,
        f.name AS family_name,t.generation AS family_token,
        COALESCE(s.generation,'legacy:'||m.joined_ms) AS member_token,s.offline_ms,l.epoch,l.active
        FROM family_members m JOIN guild_families g ON g.family=m.family
        JOIN guild_family_generations t ON t.family=m.family JOIN organizations f ON f.id=m.family
        JOIN roles r ON r.id=m.role_id LEFT JOIN family_member_state s ON s.role_id=m.role_id
        LEFT JOIN role_leases l ON l.role_id=m.role_id LEFT JOIN family_maintenance c ON c.family=m.family
        WHERE g.guild=? AND COALESCE(c.state,'active')='active' ORDER BY m.role_id''',(guild,)))


def baseline(db,guild,m,policy):
    db.execute('''UPDATE guild_member_state SET active=0 WHERE guild=? AND role_id=?
        AND (family_token!=? OR member_token!=?)''',(guild,m['role_id'],m['family_token'],m['member_token']))
    db.execute('''INSERT OR IGNORE INTO guild_member_state VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1)''',
        (guild,m['role_id'],m['family_token'],m['member_token'],*policy.metadata,*policy.prestige,*policy.dues,policy.origin))


def new_guild(db,guild,policy):
    cursor=db.execute('SELECT COALESCE(MAX(sequence),0) FROM family_join_events').fetchone()[0]
    db.execute('INSERT INTO guild_view_state VALUES(?,?,?,?)',(guild,policy.reserved,policy.origin,cursor))
    for m in current_members(db,guild):baseline(db,guild,m,policy)


def admitted_family(db,guild,family,policy):
    # Unknown old guilds stay unknown, without blocking their existing domain
    # admission path or claiming that missing historical member data is zero.
    if not db.execute('SELECT 1 FROM guild_view_state WHERE guild=?',(guild,)).fetchone():return
    for m in current_members(db,guild):
        if m['family']==family:baseline(db,guild,m,policy)


def scope(db,actor,epoch):
    lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(actor,)).fetchone()
    if not lease or str(lease[0])!=str(epoch) or lease[1]!=1:raise ValueError('stale_epoch')
    row=db.execute('''SELECT g.guild,t.generation,COALESCE(s.generation,'legacy:'||m.joined_ms)
        FROM family_members m JOIN guild_families g ON g.family=m.family
        JOIN guild_family_generations t ON t.family=m.family
        LEFT JOIN family_member_state s ON s.role_id=m.role_id LEFT JOIN family_maintenance c ON c.family=m.family
        WHERE m.role_id=? AND COALESCE(c.state,'active')='active' ''',(actor,)).fetchone()
    if not row:raise ValueError('not_in_guild')
    from guild_dissolution import lifecycle
    if lifecycle(db,row[0]).state!='active':raise ValueError('not_in_guild')
    return tuple(row)


def audience(db,guild):
    if not db.execute('SELECT 1 FROM guild_view_state WHERE guild=?',(guild,)).fetchone():return None
    from guild_dissolution import lifecycle
    if lifecycle(db,guild).state!='active':return GuildAudience(guild,())
    members=tuple(tuple(r) for r in db.execute('''SELECT role_id,family_token,member_token FROM guild_member_state
        WHERE guild=? AND active=1 ORDER BY role_id''',(guild,)))
    return GuildAudience(guild,members)


def refresh(db,guild,requester,policy):
    if requester and scope(db,*requester)[0]!=guild:raise ValueError('stale_guild_membership')
    meta=db.execute('SELECT * FROM guild_view_state WHERE guild=?',(guild,)).fetchone()
    if not meta:raise ValueError('guild_panel_unknown')
    before=audience(db,guild)
    last=max(meta['join_cursor'],db.execute('SELECT COALESCE(MAX(sequence),0) FROM family_join_events').fetchone()[0])
    events={r[0] for r in db.execute('''SELECT e.generation FROM family_join_events e
        JOIN family_member_state s ON s.generation=e.generation
        JOIN family_members m ON m.role_id=s.role_id JOIN guild_families g ON g.family=m.family
        WHERE g.guild=? AND e.sequence>? AND e.sequence<=?''',(guild,meta['join_cursor'],last))}
    db.execute('UPDATE guild_member_state SET active=0 WHERE guild=?',(guild,))
    # Retain the guild owner's consumption proof for fresh joins whose family
    # has just become pending. Advancing the cursor without issuing their
    # explicit new-member baseline would otherwise erase the only safe proof
    # before the durable dissolution consumer gets its turn.
    pending=tuple(db.execute('''SELECT e.role_id,t.generation AS family_token,e.generation AS member_token
        FROM family_join_events e JOIN family_members m ON m.role_id=e.role_id AND m.family=e.family
        JOIN family_member_state s ON s.role_id=e.role_id AND s.generation=e.generation
        JOIN guild_families g ON g.family=e.family JOIN guild_family_generations t ON t.family=e.family
        JOIN family_maintenance c ON c.family=e.family
        WHERE g.guild=? AND c.state='dissolution_pending' AND e.sequence>? AND e.sequence<=?''',
        (guild,meta['join_cursor'],last)))
    for m in pending:
        baseline(db,guild,m,policy)
        db.execute('''UPDATE guild_member_state SET active=0 WHERE guild=? AND role_id=?
            AND family_token=? AND member_token=?''',(guild,m['role_id'],m['family_token'],m['member_token']))
    for m in current_members(db,guild):
        args=(guild,m['role_id'],m['family_token'],m['member_token'])
        present=db.execute('''SELECT 1 FROM guild_member_state WHERE guild=? AND role_id=?
            AND family_token=? AND member_token=?''',args).fetchone()
        if not present:
            if m['member_token'] not in events:raise ValueError('guild_member_state_unknown')
            baseline(db,guild,m,policy)
        db.execute('''UPDATE guild_member_state SET active=1 WHERE guild=? AND role_id=?
            AND family_token=? AND member_token=?''',args)
    db.execute('UPDATE guild_view_state SET join_cursor=? WHERE guild=?',(last,guild))
    return GuildChange(before,audience(db,guild))


def projection(db,actor,epoch,guild,family_token,member_token,online,policy):
    if scope(db,actor,epoch)!=(guild,family_token,member_token):raise ValueError('stale_guild_membership')
    meta=db.execute('SELECT * FROM guild_view_state WHERE guild=?',(guild,)).fetchone()
    org=db.execute("SELECT * FROM organizations WHERE id=? AND kind='guild'",(guild,)).fetchone()
    if not meta or not org:raise ValueError('guild_panel_unknown')
    view=p.GuildView(guild,org['name'],org['aim'],org['level'],meta['reserved'])
    online={rid:str(value) for rid,value in online}
    zone=timezone(timedelta(minutes=policy['family_utc_offset_minutes']))
    members=[];own_position='member'
    for m in current_members(db,guild):
        state=db.execute('''SELECT * FROM guild_member_state WHERE guild=? AND role_id=?
            AND family_token=? AND member_token=? AND active=1''',
            (guild,m['role_id'],m['family_token'],m['member_token'])).fetchone()
        if not state:raise ValueError('guild_member_state_unknown')
        offline='' if m['active']==1 and online.get(m['role_id'])==str(m['epoch']) else (
            datetime.fromtimestamp(m['offline_ms']/1000,zone).strftime(policy['family_offline_time_format'])
            if m['offline_ms'] is not None else policy['family_unknown_offline_text'])
        rank=position(db,org,m['role_id'])
        if m['family_position']=='leader' and rank in policy['guild_family_leader_overrides']:
            rank='family_leader'
        if m['role_id']==actor:own_position=rank
        members.append(p.GuildMemberWire(m['role_id'],m['name'],m['level'],m['school'],m['family'],m['family_name'],
            m['family_position'],rank,(state['metadata1'],state['metadata2'],state['metadata3']),
            (state['prestige'],state['prestige_upper']),state['weekly_dues'],state['historical_dues'],offline))
    mask=authority(db,org) if own_position in ('leader','deputy') else 0
    return GuildProjection(view,tuple(members),mask)
