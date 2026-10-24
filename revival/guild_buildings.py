"""Guild-owned construction state in the caller's transaction.

No connections, commits, role assets or sends. An explicit versioned policy is
required for genuinely new guilds; historical unknown state stays unknown.
"""
from dataclasses import dataclass,asdict
import hashlib,json


@dataclass(frozen=True)
class BuildingRules:
    revision: str
    origin: str
    initial_levels: tuple
    initial_popularity: int
    caps: tuple
    maintenance_base: int
    maintenance_per_level: tuple
    fingerprint: str


@dataclass(frozen=True)
class Building:
    building_type: int
    level: int
    construction: int


@dataclass(frozen=True)
class BuildingSnapshot:
    guild: int
    selected: int
    generation: int
    popularity: int
    buildings: tuple
    origin: str


@dataclass(frozen=True)
class BuildingCost:
    construction: int
    funds: int
    popularity: int


@dataclass(frozen=True)
class ConstructionWork:
    guild: int
    generation: int
    request_id: str
    deadline_ms: int


@dataclass(frozen=True)
class ConstructionResult:
    guild: int
    generation: int
    building_type: int
    level: int
    construction: int
    upgraded: bool
    revision: int


def requirements(building):
    """Original 1486d70/1486d00/1486d50 arithmetic, IDs0..2.

    The level20 zero branch is a client calculation fact, not a universal
    server cap. The explicit policy separately adopts its supported range.
    """
    if (not isinstance(building,Building) or type(building.building_type) is not int
            or building.building_type not in (0,1,2)
            or type(building.level) is not int or not 0<=building.level<=20):
        raise ValueError('invalid_guild_building')
    if building.level==20:return BuildingCost(0,0,0)
    return BuildingCost((building.level+2)*50,(building.level+5)*(100000,300000,400000)[building.building_type],200)


def rules(raw):
    if raw is None:return None
    initial=tuple(raw['initial_levels']);caps=tuple(raw['caps']);costs=tuple(raw['maintenance_per_level'])
    if (any(type(raw[k]) is not str or not 1<=len(raw[k])<=96 or '\0' in raw[k] for k in ('revision','origin'))
            or len(initial)!=3 or any(type(v) is not int or not 0<=v<=20 for v in initial)
            or not 1<=len(caps)<=32 or any(type(v) is not int or not 1<=v<=20 for v in caps)
            or tuple(sorted(caps))!=caps or any(v>caps[0] for v in initial)
            or type(raw['initial_popularity']) is not int or not 0<=raw['initial_popularity']<2**31
            or type(raw['maintenance_base']) is not int or not 0<raw['maintenance_base']<=10**9
            or len(costs)!=3 or any(type(v) is not int or not 0<=v<=10**9 for v in costs)):
        raise ValueError('invalid_guild_building_policy')
    values=dict(revision=raw['revision'],origin=raw['origin'],initial_levels=initial,
        initial_popularity=raw['initial_popularity'],caps=caps,maintenance_base=raw['maintenance_base'],maintenance_per_level=costs)
    digest=hashlib.sha256(json.dumps(values,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return BuildingRules(**values,fingerprint=digest)


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS guild_building_state (
        guild INTEGER PRIMARY KEY REFERENCES organizations(id),selected INTEGER NOT NULL,
        generation INTEGER NOT NULL,popularity INTEGER NOT NULL,origin TEXT NOT NULL,recipe TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_buildings (
        guild INTEGER NOT NULL REFERENCES guild_building_state(guild),building_type INTEGER NOT NULL,
        level INTEGER NOT NULL,construction INTEGER NOT NULL,PRIMARY KEY(guild,building_type))''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_construction_receipts (
        guild INTEGER NOT NULL REFERENCES organizations(id),source_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL,result TEXT NOT NULL,created_ms INTEGER NOT NULL,
        PRIMARY KEY(guild,source_id))''')


def new_guild(db,guild,policy):
    if policy is None:return
    db.execute('INSERT INTO guild_building_state VALUES(?,-1,0,?,?,?)',
        (guild,policy.initial_popularity,policy.origin,policy.fingerprint))
    db.executemany('INSERT INTO guild_buildings VALUES(?,?,?,0)',
        ((guild,index,level) for index,level in enumerate(policy.initial_levels)))


def snapshot(db,guild,policy):
    row=db.execute('SELECT selected,generation,popularity,origin,recipe FROM guild_building_state WHERE guild=?',(guild,)).fetchone()
    if row is None:raise ValueError('guild_building_state_unknown')
    if policy is None:raise ValueError('guild_building_policy_unknown')
    if (row[3],row[4])!=(policy.origin,policy.fingerprint):raise ValueError('guild_building_recipe_changed')
    buildings=tuple(Building(*tuple(r)) for r in db.execute(
        'SELECT building_type,level,construction FROM guild_buildings WHERE guild=? ORDER BY building_type',(guild,)))
    if (tuple(b.building_type for b in buildings)!=(0,1,2)
            or type(row[0]) is not int or row[0] not in (-1,0,1,2)
            or type(row[1]) is not int or not 0<=row[1]<2**63 or (row[0]!=-1 and row[1]==0)
            or type(row[2]) is not int or not 0<=row[2]<2**31
            or any(type(b.level) is not int or not 0<=b.level<=policy.caps[-1]
                or type(b.construction) is not int or not 0<=b.construction<2**31 for b in buildings)):
        raise ValueError('guild_building_state_invalid')
    for b in buildings:
        needed=requirements(b).construction
        if (needed and b.construction>=needed) or (not needed and b.construction):
            raise ValueError('guild_building_state_invalid')
    if row[0]!=-1 and not requirements(buildings[row[0]]).construction:
        raise ValueError('guild_building_state_invalid')
    return BuildingSnapshot(guild,row[0],row[1],row[2],buildings,row[3])


def normal_cost(state,policy):
    hourly=policy.maintenance_base+sum(b.level*rate for b,rate in zip(state.buildings,policy.maintenance_per_level))
    return (hourly*3+1)//2 if state.popularity<1000 else hourly


def choose(db,org,actor,target,policy):
    from guild_training import authorize
    authorize(db,org,actor,5)
    if type(target) is not int or target not in (0,1,2):raise ValueError('invalid_building_choice')
    current=snapshot(db,org['id'],policy)
    if current.selected==target:raise ValueError('construction_unchanged')
    if not 1<=org['level']<=len(policy.caps):raise ValueError('guild_building_cap_unknown')
    building=current.buildings[target]
    if building.level>=policy.caps[org['level']-1]:raise ValueError('guild_building_cap_reached')
    cost=requirements(building)
    if current.popularity<cost.popularity:raise ValueError('insufficient_guild_popularity')
    popularity=current.popularity-cost.popularity
    # Local explicit design: reserve12 hours at projected post-upgrade levels
    # and post-charge popularity. This does not perform hourly maintenance.
    from dataclasses import replace
    projected=replace(current,popularity=popularity,
        buildings=tuple(replace(b,level=b.level+(b.building_type==target)) for b in current.buildings))
    hourly=normal_cost(projected,policy)
    funds=db.execute('SELECT funds FROM guild_assets WHERE guild=?',(org['id'],)).fetchone()
    if funds is None:raise ValueError('guild_assets_unknown')
    if funds[0]<cost.funds+12*hourly:raise ValueError('insufficient_building_reserve')
    if current.generation==2**63-1:raise ValueError('guild_building_generation_exhausted')
    db.execute('UPDATE guild_building_state SET selected=?,generation=generation+1,popularity=? WHERE guild=?',
        (target,popularity,org['id']))
    return cost.funds


def validate_work(command,now):
    if (not isinstance(command,ConstructionWork)
            or any(type(v) is not int or not 0<v<2**63 for v in (command.guild,command.generation))
            or type(command.request_id) is not str or not 1<=len(command.request_id)<=160 or '\0' in command.request_id
            or type(command.deadline_ms) is not int or not 0<=command.deadline_ms<2**63
            or type(now) is not int or not 0<=now<2**63):
        raise ValueError('invalid_guild_construction_work')
    if now>command.deadline_ms:raise ValueError('guild_construction_deadline')


def apply_work(db,org,command,now,policy):
    """Trusted task-source consumer; source eligibility is the caller's duty.

    A task producer must prove its durable event and use outbox/inbox across
    owners. This method grants no client/NPC permission to submit task points.
    """
    validate_work(command,now)
    if not db.in_transaction:raise ValueError('guild_construction_transaction_required')
    if org['id']!=command.guild or org['kind']!='guild':raise ValueError('guild_construction_owner_mismatch')
    digest=hashlib.sha256(json.dumps((command.guild,command.generation),separators=(',',':')).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result FROM guild_construction_receipts WHERE guild=? AND source_id=?',
        (command.guild,command.request_id)).fetchone()
    if old:
        if old[0]!=digest:raise ValueError('guild_construction_intent_conflict')
        result=ConstructionResult(**json.loads(old[1]))
        if (any(type(v) is not int for v in (result.guild,result.generation))
                or (result.guild,result.generation)!=(command.guild,command.generation)
                or type(result.building_type) is not int or result.building_type not in (0,1,2)
                or type(result.level) is not int or not 0<=result.level<=20
                or type(result.construction) is not int or not 0<=result.construction<2**31
                or type(result.upgraded) is not bool or type(result.revision) is not int or result.revision<1
                or (result.upgraded and (result.construction!=0 or result.level<1))
                or (not result.upgraded and (result.level==20 or not 0<result.construction<requirements(
                    Building(result.building_type,result.level,0)).construction))):
            raise ValueError('guild_construction_receipt_invalid')
        return result
    from guild_dissolution import require_active
    require_active(db,command.guild)
    current=snapshot(db,command.guild,policy)
    if current.selected==-1 or current.generation!=command.generation:raise ValueError('construction_generation_stale')
    if not 1<=org['level']<=len(policy.caps):raise ValueError('guild_building_cap_unknown')
    b=current.buildings[current.selected]
    if b.level>=policy.caps[org['level']-1]:raise ValueError('guild_building_cap_reached')
    construction=b.construction+1;upgraded=construction==requirements(b).construction
    level=b.level
    if upgraded:
        if current.generation==2**63-1:raise ValueError('guild_building_generation_exhausted')
        level+=1;construction=0
        db.execute('UPDATE guild_building_state SET selected=-1,generation=generation+1 WHERE guild=?',(command.guild,))
    db.execute('UPDATE guild_buildings SET level=?,construction=? WHERE guild=? AND building_type=?',
        (level,construction,command.guild,b.building_type))
    db.execute('UPDATE organizations SET revision=revision+1 WHERE id=?',(command.guild,))
    result=ConstructionResult(command.guild,command.generation,b.building_type,level,construction,upgraded,org['revision']+1)
    db.execute('INSERT INTO guild_construction_receipts VALUES(?,?,?,?,?)',
        (command.guild,command.request_id,digest,json.dumps(asdict(result),separators=(',',':')),now))
    return result
