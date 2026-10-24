"""Guild-owned research/practice settings inside the caller's transaction.

No connections, commits, role assets or network. Unknown existing guild state
is kept unknown; only a newly created guild receives the designed baseline.
"""
from dataclasses import dataclass
from guild_offices import member,position,authority


@dataclass(frozen=True)
class TrainingRules:
    research_skills: tuple
    initial_research: int
    origin: str
    research_authority_bit: int
    practice_skills: tuple
    practice_authority_bit: int
    practice_level_offset: int
    open_fee: int
    open_min_funds: int


@dataclass(frozen=True)
class GuildTrainingSnapshot:
    guild: int
    research_skill: int
    origin: str
    open_practices: tuple


def rules(policy):
    skills=tuple(policy['guild_research_skill_ids'])
    practices=tuple(policy['guild_practice_skill_ids'])
    if (not skills or len(skills)!=len(set(skills))
        or any(type(s) is not int or s<=0 for s in skills)
        or policy['guild_initial_research_skill']!=0 or not policy['guild_training_origin']
        or policy['guild_research_authority_bit']!=0
        or not practices or len(practices)!=len(set(practices))
        or any(type(s) is not int or s<=0 for s in practices)
        or policy['guild_practice_authority_bit']!=1
        or policy['guild_practice_open_level_offset']!=1
        or type(policy['guild_practice_open_fee']) is not int or not 0<policy['guild_practice_open_fee']<2**63
        or type(policy['guild_practice_open_min_funds']) is not int
        or not policy['guild_practice_open_fee']<=policy['guild_practice_open_min_funds']<2**63
        or policy['guild_practice_open_funding']!='organization_funds'
        or policy['guild_practice_close_fee']!=0 or policy['guild_research_change_fee']!=0
        or type(policy['guild_initial_open_practices']) not in (list,tuple)
        or len(policy['guild_initial_open_practices'])!=0):
        raise ValueError('invalid_guild_training_policy')
    return TrainingRules(skills,0,policy['guild_training_origin'],policy['guild_research_authority_bit'],
        practices,policy['guild_practice_authority_bit'],policy['guild_practice_open_level_offset'],
        policy['guild_practice_open_fee'],policy['guild_practice_open_min_funds'])


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS guild_training (
        guild INTEGER PRIMARY KEY REFERENCES organizations(id),
        research_skill INTEGER NOT NULL CHECK(research_skill>=0),origin TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_practice_open (
        guild INTEGER NOT NULL REFERENCES guild_training(guild) ON DELETE CASCADE,
        skill_id INTEGER NOT NULL,PRIMARY KEY(guild,skill_id))''')


def new_guild(db,guild,policy):
    db.execute('INSERT INTO guild_training VALUES(?,?,?)',(guild,policy.initial_research,policy.origin))


def snapshot(db,guild):
    row=db.execute('SELECT * FROM guild_training WHERE guild=?',(guild,)).fetchone()
    if not row:raise ValueError('guild_training_state_unknown')
    active=tuple(r[0] for r in db.execute('SELECT skill_id FROM guild_practice_open WHERE guild=? ORDER BY skill_id',(guild,)))
    return GuildTrainingSnapshot(guild,row[1],row[2],active)


def authorize(db,org,actor,bit):
    member(db,org['id'],actor)
    if actor==org['leader']:return
    if position(db,org,actor)=='deputy' and authority(db,org)&(1<<bit):return
    raise ValueError('permission_denied')


def set_research(db,org,actor,skill,policy):
    authorize(db,org,actor,policy.research_authority_bit)
    if type(skill) is not int or skill not in policy.research_skills:raise ValueError('invalid_research_skill')
    current=snapshot(db,org['id'])
    if current.research_skill==skill:raise ValueError('research_unchanged')
    db.execute('UPDATE guild_training SET research_skill=? WHERE guild=?',(skill,org['id']))


def set_practice_open(db,org,actor,skill,enabled,policy):
    authorize(db,org,actor,policy.practice_authority_bit)
    if type(skill) is not int or skill not in policy.practice_skills or type(enabled) is not bool:
        raise ValueError('invalid_practice_choice')
    current=snapshot(db,org['id'])
    already=skill in current.open_practices
    if already==enabled:raise ValueError('practice_already_open' if enabled else 'practice_already_closed')
    if enabled:
        if org['level']<1:raise ValueError('guild_level_unknown')
        if len(current.open_practices)>=max(0,org['level']-policy.practice_level_offset):
            raise ValueError('practice_slots_full')
        db.execute('INSERT INTO guild_practice_open VALUES(?,?)',(org['id'],skill))
    else:db.execute('DELETE FROM guild_practice_open WHERE guild=? AND skill_id=?',(org['id'],skill))
