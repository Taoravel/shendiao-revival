"""Durable guild hold -> role learning -> guild acknowledgement/compensation.

Every function joins its caller's owning transaction. No role/guild owner waits
on another owner here. The local Adapter reads the other side's durable proof;
it never writes that side's state. Production field mappings are not defaulted.
"""
from dataclasses import dataclass,asdict
import hashlib,json
import role_life_skills as life
import role_learning_costs as costs
from guild_offices import member
from guild_dissolution import require_active
from guild_maintenance import snapshot as maintenance
from guild_research import snapshot as research


@dataclass(frozen=True)
class LearningFee:
    experience: int
    money: int
    prestige_need: int
    prestige_spend: int
    resources: int
    proficiency: int
    popularity: int


@dataclass(frozen=True)
class LearningRules:
    revision: str
    origin: str
    level_cap: int
    minimum_role_level: int
    pending_limit: int
    minimum_wallet: int
    fees: tuple
    catalog: object
    research: object
    maintenance: object
    buildings: object
    digest: str


@dataclass(frozen=True)
class LearningPermit:
    guild: int
    role: int
    reservation: str
    fingerprint: str
    status: str
    epoch: str
    deadline_ms: int
    family_token: str
    member_token: str
    before_revision: int
    before: life.LifeSkill
    fee: LearningFee
    recipe: str


@dataclass(frozen=True)
class LearningResult:
    state: life.LifeSkillsSnapshot
    cost: costs.LearningCostReceipt
    balances: costs.LearningBalances


def _json(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def _hash(v):return hashlib.sha256(_json(v).encode()).hexdigest()


def rules(raw,catalog,research_rules,maintenance_rules,building_rules):
    if raw is None:return None
    if type(raw) is not dict or any(r is None for r in (catalog,research_rules,maintenance_rules,building_rules)):
        raise ValueError('explicit_member_learning_dependencies_required')
    if (any(type(raw.get(k)) is not str or not 1<=len(raw[k])<=160 or '\0' in raw[k] for k in ('revision','origin'))
            or type(raw.get('level_cap')) is not int or not 1<=raw['level_cap']<=160
            or type(raw.get('minimum_role_level')) is not int or raw['minimum_role_level']!=30
            or type(raw.get('pending_limit')) is not int or not 1<=raw['pending_limit']<=256
            or type(raw.get('minimum_wallet')) is not int or raw['minimum_wallet']!=10000):
        raise ValueError('invalid_member_learning_policy')
    # These unbound server meanings require an explicit adoption, not a guess
    # derived from the English abbreviations. The fixture adopts these fields.
    fields=('prestige_need_field','prestige_spend_field','resources_field','proficiency_field')
    if any(raw.get(k) not in dict(catalog.cost_rows[0][1]) for k in fields):
        raise ValueError('explicit_member_learning_field_mapping_required')
    fees=[]
    for _,pairs in catalog.cost_rows[:raw['level_cap']]:
        row=dict(pairs)
        fees.append(LearningFee(row['inExpCost'],row['inMoneyCost'],*(row[raw[k]] for k in fields),row['outMoneyRP']))
    digest=_hash([raw,catalog.fingerprint,research_rules.digest,maintenance_rules.digest,building_rules.fingerprint])
    return LearningRules(raw['revision'],raw['origin'],raw['level_cap'],raw['minimum_role_level'],raw['pending_limit'],raw['minimum_wallet'],
        tuple(fees),catalog,research_rules,maintenance_rules,building_rules,digest)


def prepare(db):
    life.prepare(db);costs.prepare(db)
    db.execute('''CREATE TABLE IF NOT EXISTS guild_member_learning_permits (
        guild INTEGER NOT NULL REFERENCES organizations(id),role_id INTEGER NOT NULL REFERENCES roles(id),
        reservation TEXT NOT NULL,fingerprint TEXT NOT NULL,body TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('reserved','committed','cancelled')),
        PRIMARY KEY(guild,role_id,reservation))''')
    db.execute('''CREATE INDEX IF NOT EXISTS member_learning_pending_role
        ON guild_member_learning_permits(role_id,status,guild,reservation)''')
    db.execute('''CREATE TABLE IF NOT EXISTS role_member_learning_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id),guild INTEGER NOT NULL,reservation TEXT NOT NULL,
        fingerprint TEXT NOT NULL,skill INTEGER NOT NULL,target_level INTEGER NOT NULL,cost_source TEXT NOT NULL,
        PRIMARY KEY(role_id,guild,reservation))''')


def permit(db,guild,role,reservation):
    row=db.execute('SELECT fingerprint,body,status FROM guild_member_learning_permits WHERE guild=? AND role_id=? AND reservation=?',
        (guild,role,reservation)).fetchone()
    if row is None:raise ValueError('member_learning_permit_missing')
    raw=json.loads(row[1])
    if _hash([guild,role,reservation,raw])!=row[0]:raise ValueError('member_learning_permit_invalid')
    raw['before']=life.LifeSkill(**raw['before']);raw['fee']=LearningFee(**raw['fee'])
    result=LearningPermit(guild,role,reservation,row[0],row[2],**raw)
    if (result.status not in ('reserved','committed','cancelled')
            or any(type(v) is not int or not 0<=v<2**31 for v in asdict(result.fee).values())
            or type(result.before_revision) is not int or not 0<=result.before_revision<2**63
            or type(result.before.level) is not int or not 0<=result.before.level<160):
        raise ValueError('member_learning_permit_invalid')
    return result


def _source(grant):return f'member-learning:{grant.guild}:{grant.role}:{grant.reservation}'


def _resources(db,guild):
    row=db.execute('SELECT amount,revision FROM guild_resources WHERE guild=?',(guild,)).fetchone()
    if row is None or any(type(v) is not int for v in row) or not 0<=row[0]<2**31 or not 0<row[1]<2**63-1:
        raise ValueError('member_learning_resources_unknown')
    return tuple(row)


def _prestige(db,guild,role,family_token,member_token):
    row=db.execute('''SELECT prestige FROM guild_member_state WHERE guild=? AND role_id=?
        AND family_token=? AND member_token=?''',(guild,role,family_token,member_token)).fetchone()
    if row is None or type(row[0]) is not int or not 0<=row[0]<2**31:raise ValueError('member_learning_prestige_unknown')
    return row[0]


def _hold(db,grant,direction):
    resources,revision=_resources(db,grant.guild)
    prestige=_prestige(db,grant.guild,grant.role,grant.family_token,grant.member_token)
    resources+=direction*grant.fee.resources;prestige+=direction*grant.fee.prestige_spend
    if not 0<=resources<2**31 or not 0<=prestige<2**31:raise ValueError('member_learning_hold_overflow')
    if grant.fee.resources:
        db.execute('UPDATE guild_resources SET amount=?,revision=revision+1 WHERE guild=?',(resources,grant.guild))
    if grant.fee.prestige_spend:
        db.execute('''UPDATE guild_member_state SET prestige=? WHERE guild=? AND role_id=?
            AND family_token=? AND member_token=?''',(prestige,grant.guild,grant.role,grant.family_token,grant.member_token))


def reserve(db,org,c,now,policy):
    if policy is None:raise ValueError('member_learning_policy_unknown')
    if (len(c.args)!=2 or any(type(n) is not int for n in c.args) or c.args[0] not in policy.catalog.skills
            or not 0<=c.args[1]<2**63-1 or len(c.request_id)>96):raise ValueError('invalid_member_learning_intent')
    require_active(db,org['id']);m=member(db,org['id'],c.actor)
    account,level=tuple(db.execute('SELECT account_id,level FROM roles WHERE id=?',(c.actor,)).fetchone())
    state=life.read(db,account,c.actor,c.epoch,policy.catalog)
    if state.revision!=c.args[1]:raise ValueError('life_skill_revision_conflict')
    before=next(s for s in state.skills if s.skill==c.args[0]);target=before.level+1
    if target>policy.level_cap:raise ValueError('member_learning_level_cap')
    if level<policy.minimum_role_level:raise ValueError('member_learning_role_level')
    research_state=research(db,org['id'],policy.research)
    if next(s.level for s in research_state.skills if s.skill_id==before.skill)<target:raise ValueError('member_learning_research_level')
    maintenance(db,org['id'],policy.maintenance,policy.buildings)
    fee=policy.fees[target-1]
    if before.skill in policy.catalog.skilled and before.proficiency<fee.proficiency:raise ValueError('member_learning_proficiency')
    prestige=_prestige(db,org['id'],c.actor,m['family_token'],m['member_token'])
    if prestige<max(fee.prestige_need,fee.prestige_spend):raise ValueError('member_learning_prestige_insufficient')
    if _resources(db,org['id'])[0]<fee.resources:raise ValueError('member_learning_resources_insufficient')
    if db.execute("SELECT COUNT(*) FROM guild_member_learning_permits WHERE role_id=? AND status='reserved'",(c.actor,)).fetchone()[0]>=policy.pending_limit:
        raise ValueError('member_learning_pending_full')
    raw=dict(epoch=str(c.epoch),deadline_ms=c.deadline_ms,family_token=m['family_token'],member_token=m['member_token'],
        before_revision=state.revision,before=asdict(before),fee=asdict(fee),recipe=policy.digest)
    fingerprint=_hash([org['id'],c.actor,c.request_id,raw])
    db.execute('INSERT INTO guild_member_learning_permits VALUES(?,?,?,?,?,?)',
        (org['id'],c.actor,c.request_id,fingerprint,_json(raw),'reserved'))
    _hold(db,permit(db,org['id'],c.actor,c.request_id),-1)
    return True


def pending(db,role,limit=256):
    if type(limit) is not int or not 1<=limit<=256:raise ValueError('invalid_member_learning_recovery_limit')
    from faction_types import GuildRecoveryProblem
    result=[]
    for guild,role,reservation in db.execute('''SELECT guild,role_id,reservation FROM guild_member_learning_permits
            WHERE role_id=? AND status='reserved' ORDER BY guild,reservation LIMIT ?''',(role,limit)):
        try:result.append(permit(db,guild,role,reservation))
        except (ValueError,TypeError,KeyError) as error:
            result.append(GuildRecoveryProblem(guild,role,reservation,str(error) or type(error).__name__))
    return tuple(result)


def resolve(db,guild,role,reservation):
    grant=permit(db,guild,role,reservation)
    if grant.status!='reserved':return False
    proof=db.execute('SELECT fingerprint,cost_source FROM role_member_learning_receipts WHERE role_id=? AND guild=? AND reservation=?',
        (role,guild,reservation)).fetchone()
    cost=costs.receipt(db,role,_source(grant))
    if proof:
        if tuple(proof)!=(grant.fingerprint,_source(grant)) or cost is None or cost.fingerprint!=grant.fingerprint:
            raise ValueError('member_learning_outcome_unknown')
        status='committed'
    else:
        if cost is not None or db.execute('SELECT 1 FROM role_wallet_receipts WHERE role_id=? AND settlement_id=?',
                (role,costs.identity(_source(grant)))).fetchone():raise ValueError('member_learning_outcome_unknown')
        _hold(db,grant,1);status='cancelled'
    db.execute('UPDATE guild_member_learning_permits SET status=? WHERE guild=? AND role_id=? AND reservation=?',
        (status,guild,role,reservation))
    return True


def settle(db,inventory,guild,reservation,now,life_rules,policy,currency_rules,*,popularity):
    account,role,epoch=inventory.account_id,inventory.role_id,inventory.epoch
    life.owner(db,account,role,epoch)
    grant=permit(db,guild,role,reservation);source=_source(grant)
    current=life.read(db,account,role,epoch,life_rules)
    old=db.execute('SELECT fingerprint,skill,target_level,cost_source FROM role_member_learning_receipts WHERE role_id=? AND guild=? AND reservation=?',
        (role,guild,reservation)).fetchone()
    if old:
        if (tuple(old)!=(grant.fingerprint,grant.before.skill,grant.before.level+1,source) or grant.status=='cancelled'):
            raise ValueError('member_learning_outcome_unknown')
        paid=costs.receipt(db,role,source)
        if paid is None or paid.fingerprint!=grant.fingerprint:raise ValueError('member_learning_outcome_unknown')
        return LearningResult(current,paid,costs.current(db,inventory,currency_rules))
    if costs.receipt(db,role,source) is not None:raise ValueError('member_learning_outcome_unknown')
    if type(now) is not int or now<0 or grant.status!='reserved' or grant.epoch!=str(epoch) or now>=grant.deadline_ms:
        raise ValueError('member_learning_permit_expired_or_inactive')
    if policy is None or policy.digest!=grant.recipe or life_rules.fingerprint!=policy.catalog.fingerprint:
        raise ValueError('member_learning_recipe_changed')
    if type(popularity) is not int or not 0<=popularity<2**31:raise ValueError('member_learning_popularity_unknown')
    if popularity<grant.fee.popularity:raise ValueError('member_learning_popularity_insufficient')
    if current.revision!=grant.before_revision or next(s for s in current.skills if s.skill==grant.before.skill)!=grant.before:
        raise ValueError('life_skill_revision_conflict')
    require_active(db,guild);m=member(db,guild,role)
    if (m['family_token'],m['member_token'])!=(grant.family_token,grant.member_token):raise ValueError('member_learning_membership_changed')
    if db.execute('SELECT level FROM roles WHERE id=?',(role,)).fetchone()[0]<policy.minimum_role_level:
        raise ValueError('member_learning_role_level')
    if next(s.level for s in research(db,guild,policy.research).skills if s.skill_id==grant.before.skill)<grant.before.level+1:
        raise ValueError('member_learning_research_level')
    balances=costs.current(db,inventory,currency_rules)
    carried=sum(b.balance for b in balances.wallet if b.currency in ('cash','bound_silver'))
    if carried<grant.fee.money:
        if balances.depot is None:raise ValueError('learning_depot_unknown')
        if carried+balances.depot<grant.fee.money:raise ValueError('learning_money_insufficient')
    if carried<policy.minimum_wallet:raise ValueError('member_learning_minimum_wallet')
    paid=costs.pay(db,inventory,source,grant.fingerprint,grant.fee.money,grant.fee.experience,currency_rules)
    after=life.learn_one(db,account,role,epoch,grant.before.skill,grant.before_revision,life_rules)
    db.execute('INSERT INTO role_member_learning_receipts VALUES(?,?,?,?,?,?,?)',
        (role,guild,reservation,grant.fingerprint,grant.before.skill,grant.before.level+1,source))
    return LearningResult(after,paid,costs.current(db,inventory,currency_rules))
