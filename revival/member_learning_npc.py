"""Fresh service121 Adapter; guild residence comes from main's directory.

No registry guess, scene derivation, connection, commit or owner wait. The
caller must renew both residence and NPC proof after the guild reservation.
"""
from dataclasses import dataclass
from npc_services import NpcServiceCommand
from world_owner import Location,MapAddress
from guild_projection import scope
from guild_research import snapshot as research
from faction_domain import OrganizationCommand
from role_practice import owner
from npc_transactions import precommit_messages
from currency_protocol import encode_currency_balance
from task_dialog_protocol import S_REFRESH_USER_EXP,encode_user_experience
import role_life_skills as life
import guild_member_learning as learning
import life_skill_protocol as wire


@dataclass(frozen=True)
class LearningResidence:
    """Trusted current directory result, never constructed from a wire Q."""
    guild: int
    address: MapAddress
    generation: str
    evidence: str


@dataclass(frozen=True)
class PreparedLearning:
    source: NpcServiceCommand
    residence: LearningResidence
    command: OrganizationCommand
    body: bytes


@dataclass(frozen=True)
class LearningAction:
    result: learning.LearningResult
    messages: tuple


def authorize(db,account,command,current,residence,now,policy):
    if (type(command) is not NpcServiceCommand or type(current) is not Location or type(residence) is not LearningResidence
            or type(residence.address) is not MapAddress or type(residence.guild) is not int or residence.guild<=0
            or type(residence.generation) is not str or not 1<=len(residence.generation)<=160
            or type(residence.evidence) is not str or not residence.evidence
            or command.service_id!=121 or command.handler!='guild_member_learning' or current.state!='active'
            or type(now) is not int or now<0 or now>=command.deadline_ms
            or (command.role_id,command.login_epoch,command.address,command.position_version)
                !=(current.role_id,current.login_epoch,current.address,current.version)
            or residence.address!=current.address or type(command.request_id) is not str or not 1<=len(command.request_id)<=96):
        raise ValueError('invalid_member_learning_npc_scope')
    if policy is None:raise ValueError('member_learning_policy_unknown')
    owner(db,account,current.role_id,current.login_epoch)
    membership=scope(db,current.role_id,current.login_epoch)
    if membership[0]!=residence.guild:raise ValueError('foreign_member_learning_residence')
    if db.execute('SELECT level FROM roles WHERE id=?',(current.role_id,)).fetchone()[0]<policy.minimum_role_level:
        raise ValueError('member_learning_role_level')
    return membership


def open_panel(db,account,command,current,residence,now,policy):
    guild,_,_=authorize(db,account,command,current,residence,now,policy)
    state=life.read(db,account,current.role_id,current.login_epoch,policy.catalog)
    studied=research(db,guild,policy.research)
    maximums=tuple((s.skill_id,min(s.level,policy.level_cap)) for s in studied.skills)
    return tuple((wire.UPDATE_ASSIST_SKILL,wire.update(s)) for s in state.skills)+(
        (wire.ASSIST_SKILL_MAX_LEVELS,wire.study_panel(command.entity_key,maximums)),)


def prepare_purchase(db,account,command,current,residence,body,now,policy,*,popularity):
    guild,_,_=authorize(db,account,command,current,residence,now,policy)
    npc,skill,mode=wire.request(body)
    if npc!=command.entity_key or skill not in policy.catalog.skills or mode!=0:
        raise ValueError('unsupported_or_foreign_member_learning_request')
    state=life.read(db,account,current.role_id,current.login_epoch,policy.catalog)
    before=next(s for s in state.skills if s.skill==skill)
    if before.level>=policy.level_cap:raise ValueError('member_learning_level_cap')
    if type(popularity) is not int or not 0<=popularity<2**31:raise ValueError('member_learning_popularity_unknown')
    if popularity<policy.fees[before.level].popularity:raise ValueError('member_learning_popularity_insufficient')
    reserve=OrganizationCommand(current.role_id,current.login_epoch,command.request_id,command.deadline_ms,guild,
        'reserve_member_learning',(skill,state.revision))
    return PreparedLearning(command,residence,reserve,body)


def finish_purchase(db,account,prepared,command,current,residence,now,policy,inventory,currency_rules,*,popularity,precommit=None):
    guild,_,_=authorize(db,account,command,current,residence,now,policy)
    if type(prepared) is not PreparedLearning or prepared.source!=command or prepared.residence!=residence:
        raise ValueError('member_learning_prepared_scope_changed')
    npc,skill,mode=wire.request(prepared.body);c=prepared.command
    if (npc!=command.entity_key or mode!=0 or c.operation!='reserve_member_learning'
            or (c.actor,c.epoch,c.organization,c.request_id,c.deadline_ms)!=(current.role_id,current.login_epoch,guild,command.request_id,command.deadline_ms)
            or len(c.args)!=2 or c.args[0]!=skill
            or (inventory.account_id,inventory.role_id,str(inventory.epoch))!=(account,current.role_id,str(current.login_epoch))):
        raise ValueError('member_learning_prepared_intent_changed')
    grant=learning.permit(db,guild,current.role_id,c.request_id)
    if grant.before.skill!=skill or grant.before_revision!=c.args[1]:raise ValueError('member_learning_prepared_intent_changed')
    replayed=db.execute('SELECT 1 FROM role_member_learning_receipts WHERE role_id=? AND guild=? AND reservation=?',
        (current.role_id,guild,c.request_id)).fetchone() is not None
    result=learning.settle(db,inventory,guild,c.request_id,now,policy.catalog,policy,currency_rules,popularity=popularity)
    messages=tuple((wire.UPDATE_ASSIST_SKILL,wire.update(s)) for s in result.state.skills)
    messages+=tuple(encode_currency_balance(b.currency,b.balance) for b in result.balances.wallet if b.currency in ('cash','bound_silver'))
    messages+=((S_REFRESH_USER_EXP,encode_user_experience(result.balances.experience)),)
    if any(name=='depot_cash' for name,_ in result.cost.spent) and precommit is None:
        raise ValueError('member_learning_depot_projection_required')
    messages+=precommit_messages(precommit,db,inventory,replayed=replayed)
    return LearningAction(result,messages)
