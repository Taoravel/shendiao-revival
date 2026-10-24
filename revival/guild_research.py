"""Guild-owned research state. Caller owns transaction, event proof and recipe.

No default progression curve, maintenance eligibility, role assets or network.
An explicit recipe initializes only genuinely new guilds, never unknown saves.
"""
from dataclasses import dataclass,asdict
import hashlib,json


@dataclass(frozen=True)
class ResearchRules:
    revision: str
    origin: str
    costs: tuple
    digest: str


@dataclass(frozen=True)
class ResearchSkill:
    skill_id: int
    level: int
    cap: int
    experience: int
    next_experience: int


@dataclass(frozen=True)
class ResearchSnapshot:
    guild: int
    selected_skill: int
    skills: tuple
    revision: int
    origin: str
    recipe: str


@dataclass(frozen=True)
class ResearchAward:
    guild: int
    request_id: str       # trusted source event key, not a client retry token
    experience: int
    deadline_ms: int


@dataclass(frozen=True)
class ResearchReceipt:
    guild: int
    request_id: str
    skill_id: int
    before: ResearchSkill | None
    after: ResearchSkill | None
    accepted: int
    discarded: int
    status: str
    revision: int
    recipe: str


def rules(raw,allowed):
    if raw is None:return None
    if (type(raw) is not dict or type(raw.get('revision')) is not str or not 1<=len(raw['revision'])<=160
            or type(raw.get('origin')) is not str or not 1<=len(raw['origin'])<=256
            or type(raw.get('costs')) not in (tuple,list)):
        raise ValueError('invalid_guild_research_policy')
    costs=[]
    for row in raw['costs']:
        if (type(row) not in (tuple,list) or len(row)!=2 or type(row[0]) is not int
                or row[0] not in allowed or type(row[1]) not in (tuple,list)
                or not 1<=len(row[1])<=155  # local bounded curve budget, not an original universal cap
                or any(type(n) is not int or not 0<n<2**31 for n in row[1])):
            raise ValueError('invalid_guild_research_policy')
        costs.append((row[0],tuple(row[1])))
    if len(costs)!=len(allowed) or {s for s,_ in costs}!=set(allowed):
        raise ValueError('incomplete_guild_research_policy')
    costs=tuple(sorted(costs))
    digest=hashlib.sha256(json.dumps([raw['revision'],raw['origin'],costs],separators=(',',':')).encode()).hexdigest()
    return ResearchRules(raw['revision'],raw['origin'],costs,digest)


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS guild_research_state (
        guild INTEGER PRIMARY KEY REFERENCES organizations(id),revision INTEGER NOT NULL CHECK(revision>0),
        origin TEXT NOT NULL,recipe TEXT NOT NULL,recipe_digest TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_research_skills (
        guild INTEGER NOT NULL REFERENCES guild_research_state(guild),skill_id INTEGER NOT NULL,
        level INTEGER NOT NULL CHECK(level>=0),experience INTEGER NOT NULL CHECK(experience>=0),
        PRIMARY KEY(guild,skill_id))''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_research_receipts (
        guild INTEGER NOT NULL REFERENCES organizations(id),request_id TEXT NOT NULL,
        experience INTEGER NOT NULL,result TEXT NOT NULL,created_ms INTEGER NOT NULL,
        PRIMARY KEY(guild,request_id))''')


def new_guild(db,guild,policy):
    if policy is None:return
    db.execute('INSERT INTO guild_research_state VALUES(?,1,?,?,?)',(guild,policy.origin,policy.revision,policy.digest))
    db.executemany('INSERT INTO guild_research_skills VALUES(?,?,0,0)',((guild,skill) for skill,_ in policy.costs))


def snapshot(db,guild,policy):
    row=db.execute('SELECT revision,origin,recipe,recipe_digest FROM guild_research_state WHERE guild=?',(guild,)).fetchone()
    if row is None or policy is None:raise ValueError('guild_research_state_unknown')
    if tuple(row)[1:]!=(policy.origin,policy.revision,policy.digest):raise ValueError('guild_research_recipe_conflict')
    rows=tuple(db.execute('SELECT skill_id,level,experience FROM guild_research_skills WHERE guild=? ORDER BY skill_id',(guild,)))
    if tuple(r[0] for r in rows)!=tuple(s for s,_ in policy.costs):raise ValueError('guild_research_state_incomplete')
    skills=[]
    for record,(_,costs) in zip(rows,policy.costs):
        skill,level,xp=record;cap=len(costs)
        if (not 0<=level<=cap or not 0<=xp<(costs[level] if level<cap else 1)):
            raise ValueError('invalid_guild_research_state')
        skills.append(ResearchSkill(skill,level,cap,xp,costs[level] if level<cap else 0))
    from guild_training import snapshot as training_snapshot
    selected=training_snapshot(db,guild).research_skill
    if selected and selected not in {s.skill_id for s in skills}:raise ValueError('invalid_research_skill')
    return ResearchSnapshot(guild,selected,tuple(skills),row[0],row[1],row[2])


def validate(command,now):
    if (not isinstance(command,ResearchAward) or type(command.guild) is not int or not 0<command.guild<2**63
            or type(command.request_id) is not str or not 1<=len(command.request_id)<=160 or '\0' in command.request_id
            or type(command.experience) is not int or not 0<=command.experience<2**31
            or type(command.deadline_ms) is not int or not 0<=command.deadline_ms<2**63
            or type(now) is not int or not 0<=now<2**63):
        raise ValueError('invalid_guild_research_award')
    if now>command.deadline_ms:raise ValueError('guild_research_deadline')


def award(db,command,now,policy):
    """Trusted caller only, in its guild transaction after proving the source.

    This does not authorize maintenance, calculate hourly research power or
    verify another owner's source receipt. No wire route may call it directly.
    """
    validate(command,now)
    old=db.execute('SELECT experience,result FROM guild_research_receipts WHERE guild=? AND request_id=?',
        (command.guild,command.request_id)).fetchone()
    if old:
        if old[0]!=command.experience:raise ValueError('guild_research_intent_conflict')
        value=json.loads(old[1])
        for name in ('before','after'):
            if value[name] is not None:value[name]=ResearchSkill(**value[name])
        return ResearchReceipt(**value)
    from guild_dissolution import require_active
    require_active(db,command.guild)
    state=snapshot(db,command.guild,policy)
    before=next((s for s in state.skills if s.skill_id==state.selected_skill),None)
    after=before;accepted=0
    status='idle' if before is None else 'capped' if before.level==before.cap else 'no_gain'
    if before is not None and before.level<before.cap and command.experience:
        costs=dict(policy.costs)[before.skill_id]
        level=before.level;xp=before.experience+command.experience
        while level<before.cap and xp>=costs[level]:
            xp-=costs[level];level+=1
        discarded=xp if level==before.cap else 0
        if level==before.cap:xp=0
        accepted=command.experience-discarded
        after=ResearchSkill(before.skill_id,level,before.cap,xp,costs[level] if level<before.cap else 0)
        db.execute('UPDATE guild_research_skills SET level=?,experience=? WHERE guild=? AND skill_id=?',
            (level,xp,command.guild,before.skill_id))
        db.execute('UPDATE guild_research_state SET revision=revision+1 WHERE guild=?',(command.guild,))
        db.execute('UPDATE organizations SET revision=revision+1 WHERE id=?',(command.guild,))
        status='advanced'
    revision=db.execute('SELECT revision FROM organizations WHERE id=?',(command.guild,)).fetchone()[0]
    result=ResearchReceipt(command.guild,command.request_id,state.selected_skill,before,after,
        accepted,command.experience-accepted,status,revision,state.recipe)
    # Last write shares the caller's source/state transaction; failure rolls back.
    db.execute('INSERT INTO guild_research_receipts VALUES(?,?,?,?,?)',
        (command.guild,command.request_id,command.experience,json.dumps(asdict(result),separators=(',',':')),now))
    return result


def native_skills(state):
    from guild_detail_protocol import GuildSkill
    return tuple(GuildSkill(s.skill_id,(s.level,s.cap,s.experience,s.next_experience)) for s in state.skills)
