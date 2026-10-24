"""Bounded organization owners and recipient-owned native chat delivery.

Paid commands arrive only after role-owned funding/consent. This module has no
wallet access, role-owner calls, Session, cipher or writer. Every operation and
funding revocation for one organization shares the same sequential owner.
"""
import asyncio
from dataclasses import dataclass
import time
from types import MappingProxyType
from faction_domain import OrganizationStore,OrganizationCommand,OrganizationBroadcast
from faction_protocol import FAMILY_CHANNEL,GUILD_CHANNEL,organization_chat
from runtime_core import SerialOwner,Backpressure
from social_owner import Delivery,SocialResult
import social_protocol as p
from family_runtime import FamilyRuntime,FamilyWake
from faction_types import FAMILY_NATIVE_TYPES,GUILD_NATIVE_TYPES
from guild_runtime import GuildRuntime,GuildWake


@dataclass(frozen=True)
class OrganizationDelivery(Delivery):
    event: OrganizationBroadcast


@dataclass(frozen=True)
class OrganizationOutcome:
    organization: int
    revision: int
    kind: str = ''


class OrganizationRuntime:
    def __init__(self,social,policy,*,research_policy=None,building_policy=None,guild_maintenance_policy=None,member_learning_policy=None):
        self.social,self.rt=social,social.rt
        self.policy=MappingProxyType(dict(policy))
        if any(type(self.policy.get(k)) is not int or self.policy[k]<1 for k in ('owner_limit','mailbox_capacity','chat_receipt_limit')):
            raise ValueError('Positive bounded organization capacities required')
        self.store=OrganizationStore(self.rt.social_store.path,self.policy,research_policy=research_policy,
            building_policy=building_policy,guild_maintenance_policy=guild_maintenance_policy,member_learning_policy=member_learning_policy)
        self.family=FamilyRuntime(self)
        self.guild=GuildRuntime(self)
        self.owners={}
        self.inflight=set()
        self.closing=False

    @staticmethod
    def handles(command):
        if command.kind in FAMILY_NATIVE_TYPES or command.kind in GUILD_NATIVE_TYPES:return True
        # Do not consume ordinary chat or malformed packets on another route.
        if command.kind!=p.CHAT_SEND or len(command.body)<4:return False
        return int.from_bytes(command.body[:4],'big',signed=True) in (FAMILY_CHANNEL,GUILD_CHANNEL)

    async def request(self,snapshot,command,now):
        if command.kind in FAMILY_NATIVE_TYPES:return await self.family.request(snapshot,command,now)
        if command.kind in GUILD_NATIVE_TYPES:return await self.guild.request(snapshot,command,now)
        try:
            if command.kind!=p.CHAT_SEND or type(command.request_id) is not str or not 1<=len(command.request_id)<=160:
                raise ValueError('invalid_organization_chat')
            if (command.role_id,command.login_epoch)!=(snapshot.role_id,snapshot.login_epoch):
                raise ValueError('stale_epoch')
            channel,content,extra=p.chat_request(command.body)
            if extra:raise ValueError('rich_chat_not_restored')
            kind={FAMILY_CHANNEL:'family',GUILD_CHANNEL:'guild'}.get(channel)
            if not kind:raise ValueError('invalid_organization_channel')
            identity=await self.rt.io.run(('role',snapshot.role_id),self.store.membership,
                                         snapshot.role_id,snapshot.login_epoch,kind)
            await self._call(('organization',identity),'chat',(snapshot,command,content,kind),command,now)
            return SocialResult()
        except (ValueError,p.NeedMoreData) as error:
            return SocialResult(rejection=str(error) or 'invalid_organization_chat')

    async def command(self,command,now,*,revoke=False):
        """Trusted integration seam: organization commit or terminal revoke.

        Caller owns role eligibility/consent and cash funding. Cancellation only
        cancels waiting; an accepted commit remains ordered ahead of revocation.
        Returned values are frozen, and never contain a wallet or mutable rows.
        """
        if not isinstance(command,OrganizationCommand):raise ValueError('OrganizationCommand required')
        def immutable(value):
            return all(immutable(x) for x in value) if type(value) is tuple else type(value) in (str,int,bool)
        if (type(command.args) is not tuple or not immutable(command.args)
            or type(command.organization) is not int or command.organization<0
            or type(command.actor) is not int or command.actor<=0
            or type(command.request_id) is not str or not 1<=len(command.request_id)<=160):
            raise ValueError('Frozen organization command required')
        return await self._call(self.store.owner_key(command),'revoke' if revoke else 'command',command,command,now)

    async def maintain_family(self,command,now):
        """Trusted system observation, ordered with this family's management."""
        from family_maintenance import validate
        validate(command,now,self.store.maintenance_rules)
        return await self._call(('organization',command.family),'family-maintenance',command,command,now)

    async def award_guild_research(self,command,now):
        """Trusted proved source event; shares the guild's management owner.

        Does not authorize maintenance or NPC input. The source producer must
        supply its stable committed event, never a client-provided XP amount.
        """
        from guild_research import validate
        validate(command,now)
        return await self._call(('organization',command.guild),'guild-research-award',command,command,now)

    async def apply_guild_construction(self,command,now):
        """Trusted durable task source only; no wire route grants points."""
        from guild_buildings import validate_work
        validate_work(command,now)
        return await self._call(('organization',command.guild),'guild-construction-work',command,command,now)

    async def maintain_guild(self,command,now):
        from guild_maintenance import validate
        validate(command,now,self.store.guild_maintenance_rules)
        return await self._call(('organization',command.guild),'guild-maintenance',command,command,now)

    async def resume_guild_maintenance(self,command,now):
        from guild_maintenance import validate
        validate(command,now,self.store.guild_maintenance_rules,resume=True)
        return await self._call(('organization',command.guild),'guild-maintenance-resume',command,command,now)

    async def resume_family_maintenance(self,command,now):
        from family_maintenance import validate_resume
        validate_resume(command,now,self.store.maintenance_rules)
        return await self._call(('organization',command.family),'family-maintenance-resume',command,command,now)

    async def consume_family_guild_dissolution(self,command,now):
        from family_maintenance import validate_closure_command
        validate_closure_command(command,now,self.store.guild_closure_rules)
        if command.event.guild is None:raise ValueError('guild_dissolution_guild_required')
        return await self._call(('organization',command.event.guild),'guild-family-dissolution',command,command,now)

    async def ack_family_guild_dissolution(self,command,now):
        from family_maintenance import validate_closure_command
        validate_closure_command(command,now,self.store.guild_closure_rules)
        return await self._call(('organization',command.event.family),'family-guild-dissolution-ack',command,command,now)

    async def sweep_family_donations(self,command,now):
        from family_donation import validate_sweep
        validate_sweep(command,now)
        return await self._call(('organization',command.family),'family-donation-sweep',command,command,now)

    async def consume_family_guild_history(self,command,now):
        from family_guild_history import validate
        validate(command,now)
        return await self._call(('organization',command.event.family),'family-guild-history',command,command,now)

    async def ack_family_guild_history(self,command,now):
        from family_guild_history import validate
        validate(command,now)
        return await self._call(('organization',command.event.guild),'guild-family-history-ack',command,command,now)

    async def _call(self,key,operation,value,command,now):
        if self.closing:raise Backpressure('Organization runtime closing')
        entry=self.owners.get(key)
        if entry is None:
            if len(self.owners)>=self.policy['owner_limit']:raise Backpressure('Organization owners full')
            entry=dict(refs=0,poisoned=False)
            async def handle(work):
                if entry['poisoned']:raise TimeoutError('Organization outcome pending; reload required')
                op,data,stamp=work.args
                stamp=max(stamp,int(time.time()*1000))
                try:
                    if op=='chat':
                        snapshot,request,content,kind=data
                        event=await self.rt.io.run(key,self.store.chat,key[1],snapshot.role_id,snapshot.login_epoch,
                                                  content,stamp,request.request_id,request.deadline_ms)
                        if event:
                            body=organization_chat(kind,snapshot.profile(),event.content)
                            online=self.rt.online_snapshot()
                            for index,rid in enumerate(event.recipients):
                                target=online.get(rid)
                                if target:self.social.offer(OrganizationDelivery(rid,target.login_epoch,p.CHAT_RECEIVE,body,event))
                                if index%32==31:await asyncio.sleep(0)
                        return None
                    if op=='revoke':return await self.rt.io.run(key,self.store.revoke_funding,data,stamp)
                    if op=='family-presence':return await self.family.presence_owned(key,data,stamp)
                    if op=='family-maintenance':return await self.family.maintenance_owned(key,data,stamp)
                    if op=='guild-research-award':return await self.guild.research_awarded_owned(key,data,stamp)
                    if op=='guild-construction-work':return await self.guild.construction_owned(key,data,stamp)
                    if op=='guild-maintenance':return await self.guild.maintenance_owned(key,data,stamp)
                    if op=='guild-maintenance-resume':return await self.rt.io.run(key,self.store.resume_guild_maintenance,data,stamp)
                    if op=='guild-buildings-query':return await self.guild.buildings_query_owned(key,data)
                    if op=='family-donation-sweep':return await self.family.donation_owned(key,data,stamp)
                    if op=='family-guild-history':return await self.family.guild_history_owned(key,data,stamp)
                    if op=='guild-family-history-ack':return await self.rt.io.run(key,self.store.ack_family_guild_history,data,stamp)
                    if op=='family-maintenance-resume':return await self.rt.io.run(key,self.store.resume_family_maintenance,data,stamp)
                    if op=='guild-refresh':return await self.guild.refresh_owned(key,data)
                    if op=='guild-family-dissolution':return await self.guild.dissolve_family_owned(key,data,stamp)
                    if op=='family-guild-dissolution-ack':return await self.rt.io.run(key,self.store.ack_family_guild_dissolution,data,stamp)
                    result=await self.guild.execute(key,data,stamp)
                    return OrganizationOutcome(result['organization'],result['revision'],result.get('kind',''))
                except TimeoutError:
                    # A timed-out DB call may still finish. Keep this owner
                    # poisoned until runtime restart rather than overtaking it.
                    entry['poisoned']=True
                    raise
            entry['owner']=SerialOwner(key,handle,capacity=self.policy['mailbox_capacity'])
            self.owners[key]=entry
        entry['refs']+=1
        async def invoke():
            try:
                return await entry['owner'].call('organization',operation,value,now,request_id=command.request_id,
                    deadline=time.monotonic()+max(0,(command.deadline_ms-int(time.time()*1000))/1000))
            finally:
                entry['refs']-=1
                if not entry['refs'] and not entry['poisoned']:
                    del self.owners[key]
                    await entry['owner'].close()
        pending=asyncio.create_task(invoke())
        self.inflight.add(pending)
        def completed(task):
            self.inflight.discard(task)
            if not task.cancelled():task.exception()
        pending.add_done_callback(completed)
        return await asyncio.shield(pending)

    def prepare_delivery(self,delivery):
        return delivery if self.store.authorize_delivery(delivery.event,delivery.role_id) else None

    async def close(self):
        self.closing=True
        await self.family.close()
        await self.guild.close()
        if self.inflight:await asyncio.gather(*tuple(self.inflight),return_exceptions=True)
        for entry in tuple(self.owners.values()):await entry['owner'].close()
        self.owners.clear()
