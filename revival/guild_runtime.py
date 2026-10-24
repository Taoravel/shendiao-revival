"""Recipient-owned native guild projection behind the organization owner."""
import asyncio
import sqlite3
from dataclasses import dataclass
import time
import uuid
import struct
from wire import NeedMoreData
from faction_domain import OrganizationCommand
from social_owner import Delivery,SocialCommand,SocialResult
from runtime_core import Backpressure,StaleEpoch
import faction_protocol as p
import guild_protocol as g
import practice_protocol as practice
import guild_research_protocol as research
import guild_building_protocol as buildings


@dataclass(frozen=True)
class GuildWake(Delivery):
    guild: int
    family_token: str
    member_token: str
    departed: bool = False


@dataclass(frozen=True)
class PreparedGuild:
    packets: tuple
    scope: tuple | None
    members: tuple


class GuildRuntime:
    def __init__(self,owner):
        self.owner=owner
        self.rt,self.social,self.store=owner.rt,owner.social,owner.store
        self.background={}
        self.recovery={}
        self.dirty=set()
        self.closing=False
        from guild_maintenance_runtime import GuildMaintenanceRuntime
        self.maintenance=GuildMaintenanceRuntime(self) if self.store.guild_maintenance_rules else None

    async def initial(self,endpoint):
        """Called by the recipient owner, with no target retained afterward."""
        self.nudge_recovery(endpoint.snapshot.role_id,endpoint.snapshot.login_epoch)
        if self.store.life_rules is not None:
            try:
                from life_skill_protocol import UPDATE_ASSIST_SKILL,update
                state=await endpoint.io(self.store.life_skill_states,endpoint.snapshot.role_id,endpoint.snapshot.login_epoch)
                for skill in state.skills:
                    await endpoint.deliver(Delivery(endpoint.snapshot.role_id,endpoint.snapshot.login_epoch,UPDATE_ASSIST_SKILL,update(skill)))
            except (ValueError,sqlite3.Error) as error:
                if str(error)!='life_skill_profile_unknown':
                    self.rt.log(event='member_learning_projection_deferred',role_id=endpoint.snapshot.role_id,reason=str(error))
        try:states=await endpoint.io(self.store.practice_states,endpoint.snapshot.role_id,endpoint.snapshot.login_epoch)
        except ValueError as error:
            if str(error)!='practice_profile_unknown':
                self.rt.log(event='practice_projection_deferred',role_id=endpoint.snapshot.role_id,reason=str(error))
            return
        packets=tuple((practice.UPDATE_ASSIST_SKILL,practice.update(s)) for s in states)
        for kind,body in packets:
            await endpoint.deliver(Delivery(endpoint.snapshot.role_id,endpoint.snapshot.login_epoch,kind,body))

    def nudge_recovery(self,role,epoch):
        """A bounded independent task resolves old/expired durable purchases.

        It retains IDs only, holds no role/guild owner while awaiting another,
        and never cancels a live purchase from the same epoch before deadline.
        """
        key=(role,epoch)
        if self.closing or self.owner.closing:return False
        if key in self.recovery:return True
        if len(self.recovery)>=self.owner.policy['owner_limit']:
            self.rt.log(event='practice_recovery_deferred',role_id=role,reason='capacity');return False
        async def run():
            try:
                from faction_types import GuildRecoveryProblem
                for loader,operation in ((self.store.pending_practices,'resolve_practice'),
                        (self.store.pending_member_learning,'resolve_member_learning')):
                    try:grants=await self.rt.io.run(('role',role),loader,role,epoch)
                    except (ValueError,TypeError,KeyError,Backpressure,StaleEpoch,TimeoutError,sqlite3.Error) as error:
                        self.rt.log(event='guild_recovery_domain_deferred',role_id=role,operation=operation,reason=str(error))
                        continue
                    for index,grant in enumerate(grants):
                        if self.closing or self.owner.closing:break
                        if isinstance(grant,GuildRecoveryProblem):
                            self.rt.log(event='guild_recovery_source_deferred',role_id=role,organization=grant.guild,
                                reservation=grant.reservation,reason=grant.reason)
                            continue
                        now=int(time.time()*1000)
                        if str(grant.epoch)==str(epoch) and grant.deadline_ms>now:continue
                        command=OrganizationCommand(role,epoch,uuid.uuid4().hex,now+5000,grant.guild,operation,(grant.reservation,))
                        try:await self.owner.command(command,now)
                        except (ValueError,Backpressure,StaleEpoch,TimeoutError,sqlite3.Error) as error:
                            self.rt.log(event='practice_recovery_deferred',role_id=role,organization=grant.guild,reason=str(error))
                        if index%32==31:await asyncio.sleep(0)
            except (ValueError,Backpressure,StaleEpoch,TimeoutError,sqlite3.Error) as error:
                self.rt.log(event='practice_recovery_deferred',role_id=role,reason=str(error))
            finally:self.recovery.pop(key,None)
        task=asyncio.create_task(run(),name=f'practice-recovery:{role}:{epoch}')
        self.recovery[key]=task
        task.add_done_callback(lambda t:t.exception() if not t.cancelled() else None)
        return True

    def nudge(self,identity):
        """Coalesce bounded guild work without waiting from a family owner.

        The durable current-join record/cursor is authoritative. A rejected or
        lost nudge is repaired by the next guild query, presence or mutation.
        """
        if self.closing or self.owner.closing:return False
        if identity in self.background:
            self.dirty.add(identity);return True
        if len(self.background)>=self.owner.policy['owner_limit']:
            self.rt.log(event='guild_refresh_deferred',organization=identity,reason='capacity')
            return False
        async def run():
            try:
                while not self.closing:
                    self.dirty.discard(identity)
                    now=int(time.time()*1000)
                    request=SocialCommand(0,'internal',uuid.uuid4().hex,now+5000,0,b'')
                    await self.owner._call(('organization',identity),'guild-refresh',(),request,now)
                    if identity not in self.dirty:break
                    await asyncio.sleep(0)
            except (ValueError,Backpressure,StaleEpoch,TimeoutError) as error:
                self.rt.log(event='guild_refresh_deferred',organization=identity,reason=str(error))
            finally:
                self.background.pop(identity,None);self.dirty.discard(identity)
        task=asyncio.create_task(run())
        self.background[identity]=task
        task.add_done_callback(lambda t:t.exception() if not t.cancelled() else None)
        return True

    async def idle(self):
        if self.maintenance:await self.maintenance.idle()
        while self.background or self.recovery:
            await asyncio.gather(*tuple(self.background.values()),*tuple(self.recovery.values()),return_exceptions=True)

    async def close(self):
        self.closing=True
        if self.maintenance:await self.maintenance.close()
        await self.idle()

    async def request(self,snapshot,request,now):
        try:
            if (snapshot.role_id,snapshot.login_epoch)!=(request.role_id,request.login_epoch):raise ValueError('stale_epoch')
            args=buildings.decode_query(request.body) if request.kind==buildings.QUERY_BUILDINGS else p.decode(request.kind,request.body)
            scope=await self.rt.io.run(('role',snapshot.role_id),self.store.guild_scope,snapshot.role_id,snapshot.login_epoch)
            if request.kind==buildings.QUERY_BUILDINGS:
                await self.owner._call(('organization',scope[0]),'guild-buildings-query',
                    (snapshot.role_id,snapshot.login_epoch,*scope[1:]),request,now)
                return SocialResult()
            if request.kind==p.REQUEST_FACTION:
                await self.owner._call(('organization',scope[0]),'guild-refresh',
                    (snapshot.role_id,snapshot.login_epoch),request,now)
                return SocialResult()
            if request.kind==p.FACTION_POSITION:
                target,flag=args
                rank={v:k for k,v in p.GUILD_POSITIONS.items() if k!='family_leader'}.get(flag)
                if rank is None:raise ValueError('invalid_guild_position')
                operation,values='appoint',(target,rank)
            elif request.kind==p.RESIGN_FACTION_OFFICE:operation,values='resign',()
            else:raise ValueError('guild_request_unbound')
            command=OrganizationCommand(snapshot.role_id,snapshot.login_epoch,request.request_id,request.deadline_ms,
                scope[0],operation,values)
            await self.owner.command(command,now)
            return SocialResult()
        except (ValueError,NeedMoreData,struct.error) as error:
            return SocialResult(rejection=str(error) or 'invalid_guild_packet')

    async def execute(self,key,command,stamp):
        if command.operation=='choose_building':
            result=await self.rt.io.run(key,self.store.execute,command,stamp)
            await self.building_notify(command.organization)
            return result
        if command.operation in ('reserve_practice','reserve_pill_practice','resolve_practice','reserve_member_learning','resolve_member_learning'):
            return await self.owner.family.execute(key,command,stamp)
        before=await self.rt.io.run(key,self.store.guild_audience,command.organization)
        result=await self.owner.family.execute(key,command,stamp)
        identity=result['organization'] if result.get('kind')=='guild' else command.organization
        after=await self.rt.io.run(key,self.store.guild_audience,identity)
        if after is not None:
            try:
                if result.get('kind')!='guild':
                    change=await self.rt.io.run(key,self.store.refresh_guild,identity)
                    after=change.after
                await self.notify(before,after)
            except ValueError as error:
                # The command receipt is already committed. Unknown legacy or
                # damaged presentation state cannot turn it into a fake failure.
                self.rt.log(event='guild_projection_deferred',organization=identity,reason=str(error))
        return result

    async def presence(self,snapshot):
        try:
            scope=await self.rt.io.run(('role',snapshot.role_id),self.store.guild_scope,snapshot.role_id,snapshot.login_epoch)
            now=int(time.time()*1000)
            c=SocialCommand(snapshot.role_id,snapshot.login_epoch,uuid.uuid4().hex,now+5000,0,b'')
            await self.owner._call(('organization',scope[0]),'guild-refresh',(snapshot.role_id,snapshot.login_epoch),c,now)
        except ValueError as error:
            if str(error)!='not_in_guild':self.rt.log(event='guild_presence_deferred',role_id=snapshot.role_id,reason=str(error))
        except (Backpressure,StaleEpoch,TimeoutError) as error:
            self.rt.log(event='guild_presence_deferred',role_id=snapshot.role_id,reason=type(error).__name__)

    async def refresh_owned(self,key,requester):
        change=await self.rt.io.run(key,self.store.refresh_guild,key[1],requester)
        await self.notify(change.before,change.after)

    async def research_awarded_owned(self,key,command,stamp):
        result=await self.rt.io.run(key,self.store.award_guild_research,command,stamp)
        try:
            current=await self.rt.io.run(key,self.store.guild_audience,command.guild)
            await self.notify(current,current)
        except (ValueError,Backpressure,StaleEpoch,TimeoutError,sqlite3.Error) as error:
            # The receipt is committed. A query/login can recover the current
            # display; a presentation failure cannot revoke the reward.
            self.rt.log(event='guild_research_projection_deferred',organization=command.guild,reason=str(error))
        return result

    async def buildings_query_owned(self,key,data):
        role,epoch,family_token,member_token=data
        await self.rt.io.run(key,self.store.guild_building_panel,role,epoch,key[1],family_token,member_token)
        self.social.offer(GuildWake(role,epoch,0,b'',key[1],family_token,member_token))

    async def construction_owned(self,key,command,stamp):
        result=await self.rt.io.run(key,self.store.apply_guild_construction,command,stamp)
        await self.building_notify(command.guild)
        return result

    async def maintenance_owned(self,key,command,stamp):
        result=await self.rt.io.run(key,self.store.maintain_guild,command,stamp)
        try:
            current=await self.rt.io.run(key,self.store.guild_audience,command.guild)
            before=current
            if result.status=='retired':
                from guild_projection import GuildAudience
                event=await self.rt.io.run(key,self.store.guild_maintenance_terminal,command.guild,command.due_ms)
                before=GuildAudience(command.guild,event.members)
            await self.notify(before,current)
        except (ValueError,Backpressure,StaleEpoch,TimeoutError,sqlite3.Error) as error:
            self.rt.log(event='guild_maintenance_projection_deferred',organization=command.guild,reason=str(error))
        return result

    async def building_notify(self,guild):
        try:
            current=await self.rt.io.run(('organization',guild),self.store.guild_audience,guild)
            await self.notify(current,current)
        except (ValueError,Backpressure,StaleEpoch,TimeoutError,sqlite3.Error) as error:
            self.rt.log(event='guild_building_projection_deferred',organization=guild,reason=str(error))

    async def dissolve_family_owned(self,key,command,stamp):
        from guild_projection import GuildAudience
        event=command.event
        before=await self.rt.io.run(key,self.store.guild_audience,event.guild)
        result=await self.rt.io.run(key,self.store.apply_guild_family_dissolution,
            event,command.request_id,command.deadline_ms,stamp)
        after=await self.rt.io.run(key,self.store.guild_audience,event.guild)
        # Durable source members also wake after a crash between commit and
        # notify. The recipient rechecks tokens/current membership at dequeue.
        old={rid:(family,member) for rid,family,member in before.members} if before else {}
        for rid,token in event.members:old.setdefault(rid,(event.guild_token,token))
        before=GuildAudience(event.guild,tuple((rid,*tokens) for rid,tokens in sorted(old.items())))
        await self.notify(before,after)
        return result

    async def notify(self,before,after):
        if after is None:return
        old={rid:(family,member) for rid,family,member in before.members} if before else {}
        current={rid:(family,member) for rid,family,member in after.members}
        online=self.rt.online_snapshot()
        for index,(rid,tokens) in enumerate(current.items()):
            target=online.get(rid)
            if target:self.social.offer(GuildWake(rid,target.login_epoch,0,b'',after.identity,*tokens))
            if index%32==31:await asyncio.sleep(0)
        for rid in old.keys()-current.keys():
            target=online.get(rid)
            if target:self.social.offer(GuildWake(rid,target.login_epoch,0,b'',after.identity,*old[rid],departed=True))

    def packets(self,wake,online,known_scope=None,known_members=()):
        if wake.departed:
            try:self.store.guild_scope(wake.role_id,wake.login_epoch)
            except ValueError as error:
                if str(error)=='not_in_guild':return PreparedGuild(((p.LEFT_FACTION,b''),),None,())
                raise
            return PreparedGuild((),known_scope,known_members)
        snapshot=self.store.guild_projection(wake.role_id,wake.login_epoch,wake.guild,wake.family_token,wake.member_token,online)
        members=tuple(m.role_id for m in snapshot.members)
        packets=[(g.REMOVE_GUILD_MEMBER,g.removed_guild_member(rid)) for rid in sorted(set(known_members)-set(members))]
        # Populate the own-member cache before basic-data/UI notifications.
        packets.append((g.ADD_GUILD_MEMBERS,g.guild_members(snapshot.members)))
        packets.append((research.REFRESH_RESEARCH,research.refresh(snapshot.research)
            if snapshot.research is not None else research.clear_cache()))
        if snapshot.buildings is not None:packets.append((buildings.BUILDING_DATA,buildings.building_data(snapshot.buildings)))
        packets.extend(((g.UPDATE_GUILD,g.guild_data(snapshot.view)),(p.DEPUTY_AUTHORITY,p.deputy_authority(snapshot.authority))))
        return PreparedGuild(tuple(packets),(wake.guild,wake.family_token,wake.member_token),members)
