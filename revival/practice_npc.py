"""Trusted NPC practice Adapter joining existing role/guild owner Seams.

NpcServiceCommand must come from NpcServices.plan using a fresh map proof.
No registry binding, DB connection, owner wait, commit, Session or network send.
"""
from dataclasses import dataclass
from npc_services import NpcServiceCommand
from world_owner import Location
from guild_projection import scope
from guild_training import snapshot as training_snapshot
from faction_domain import OrganizationCommand
import role_practice as role
import practice_protocol as wire


@dataclass(frozen=True)
class PreparedPractice:
    source: NpcServiceCommand
    command: OrganizationCommand
    body: bytes


@dataclass(frozen=True)
class PracticeAction:
    receipt: object
    messages: tuple


def authorize(db,account,command,current,now):
    if (not isinstance(command,NpcServiceCommand) or not isinstance(current,Location)
        or command.service_id!=1023 or command.handler!='guild_practice'
        or current.state!='active' or type(now) is not int or now<0
        or type(command.deadline_ms) is not int or now>=command.deadline_ms
        or type(command.request_id) is not str or not 1<=len(command.request_id)<=96
        or (command.role_id,command.login_epoch,command.address,command.position_version)
        !=(current.role_id,current.login_epoch,current.address,current.version)):
        raise ValueError('invalid_practice_npc_scope')
    role.owner(db,account,current.role_id,current.login_epoch)
    return scope(db,current.role_id,current.login_epoch)


def open_panel(db,account,command,current,now,rules):
    """Known skill/open-state packets; complete price/cap responses are separate."""
    guild,_,_=authorize(db,account,command,current,now)
    states=role.read(db,account,current.role_id,current.login_epoch,rules)
    settings=training_snapshot(db,guild)
    return tuple((wire.UPDATE_ASSIST_SKILL,wire.update(s)) for s in states)+(
        (wire.FACTION_PRACTICE,wire.open_types(settings.open_practices)),)


def prepare_purchase(db,account,command,current,body,now,rules):
    guild,_,_=authorize(db,account,command,current,now)
    npc,skill,mode=wire.request(body)
    if npc!=command.entity_key or skill not in rules.skills or mode not in (0,1):
        raise ValueError('unsupported_or_foreign_practice_request')
    states=role.read(db,account,current.role_id,current.login_epoch,rules)
    before=next(s for s in states if s.skill==skill)
    reservation=OrganizationCommand(current.role_id,current.login_epoch,command.request_id,command.deadline_ms,guild,
        'reserve_practice' if mode==0 else 'reserve_pill_practice',(skill,before.revision))
    return PreparedPractice(command,reservation,body)


def finish_purchase(db,account,prepared,command,current,now,rules,*,currency_rules=None,inventory=None,precommit=None):
    """Revalidate a fresh map service proof after the guild-owner await.

    Caller supplies an inventory/source projection for pill purchases and sends
    returned logical messages only after commit. It then resolves the durable
    guild permit on its owner; this function never waits on that owner.
    """
    from guild_practice import permit
    from currency_protocol import encode_currency_balance
    from npc_transactions import precommit_messages
    guild,_,_=authorize(db,account,command,current,now)
    if not isinstance(prepared,PreparedPractice) or prepared.source!=command:
        raise ValueError('practice_prepared_scope_changed')
    npc,skill,mode=wire.request(prepared.body)
    c=prepared.command
    if (npc!=command.entity_key or skill not in rules.skills or mode not in (0,1)
        or (c.actor,c.epoch,c.organization,c.request_id,c.deadline_ms)
        !=(current.role_id,current.login_epoch,guild,command.request_id,command.deadline_ms)
        or c.operation!=('reserve_practice' if mode==0 else 'reserve_pill_practice')
        or len(c.args)!=2 or c.args[0]!=skill):raise ValueError('practice_prepared_intent_changed')
    grant=permit(db,guild,current.role_id,c.request_id)
    if grant.mode!=mode or grant.before.skill!=skill or grant.before.revision!=c.args[1]:
        raise ValueError('practice_prepared_intent_changed')
    if mode==1:
        if not callable(precommit):raise ValueError('practice_inventory_projection_required')
        receipt=role.settle_pill(db,account,current.role_id,current.login_epoch,guild,c.request_id,now,rules,inventory,precommit=precommit)
        messages=((wire.UPDATE_ASSIST_SKILL,wire.update(receipt.state)),)+receipt.messages
    else:
        if currency_rules is None:raise ValueError('practice_currency_rules_required')
        replayed=bool(db.execute('SELECT 1 FROM role_practice_receipts WHERE role_id=? AND guild=? AND reservation=?',
            (current.role_id,guild,c.request_id)).fetchone())
        receipt=role.settle(db,account,current.role_id,current.login_epoch,guild,c.request_id,now,rules,currency_rules)
        cash=next(b.balance for b in receipt.balances if b.currency=='cash')
        messages=((wire.UPDATE_ASSIST_SKILL,wire.update(receipt.state)),encode_currency_balance('cash',cash))
        if precommit is not None:
            if inventory is None:raise ValueError('practice_inventory_projection_required')
            messages+=precommit_messages(precommit,db,inventory,replayed=replayed)
    return PracticeAction(receipt,messages)
