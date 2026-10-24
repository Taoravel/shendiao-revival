"""Original family management behind the existing organization owner seam."""
import time
import asyncio
import sqlite3
import uuid
import struct
from dataclasses import dataclass
from faction_domain import OrganizationCommand
from social_owner import Delivery,SocialCommand,SocialResult
from wire import NeedMoreData
from runtime_core import Backpressure,StaleEpoch
import faction_protocol as p


@dataclass(frozen=True)
class FamilyWake(Delivery):
    family: int
    generation: str
    removed_members: tuple = ()
    cleared_applications: tuple = ()
    departed: bool = False


@dataclass(frozen=True)
class PreparedFamily:
    packets: tuple
    scope: tuple | None
    application_ids: tuple


class FamilyRuntime:
    def __init__(self,organizations):
        self.owner=organizations
        self.store,self.rt,self.social=organizations.store,organizations.rt,organizations.social
        from family_maintenance_runtime import FamilyMaintenanceRuntime
        self.maintenance=FamilyMaintenanceRuntime(self)

    async def maintenance_owned(self,key,command,stamp):
        before=await self.rt.io.run(key,self.store.family_audience,command.family)
        result=await self.rt.io.run(key,self.store.maintain_family,command,stamp)
        after=await self.rt.io.run(key,self.store.family_audience,command.family)
        await self.notify(before,after)
        if result.state!='active':
            self.rt.log(event='family_dissolution_pending',family=command.family,due_ms=command.due_ms)
            guild=await self.rt.io.run(key,self.store.family_guild,command.family)
            if guild:self.owner.guild.nudge(guild)
        return result

    async def donation_owned(self,key,command,stamp):
        before=await self.rt.io.run(key,self.store.family_audience,command.family)
        results=await self.rt.io.run(key,self.store.sweep_family_donations,command,stamp)
        if results:
            after=await self.rt.io.run(key,self.store.family_audience,command.family)
            await self.notify(before,after)
        return results

    async def guild_history_owned(self,key,command,stamp):
        result=await self.rt.io.run(key,self.store.consume_family_guild_history,command,stamp)
        try:
            current=await self.rt.io.run(key,self.store.family_audience,command.event.family)
            await self.notify(current,current)
        except (ValueError,Backpressure,StaleEpoch,TimeoutError,sqlite3.Error) as error:
            self.rt.log(event='family_guild_history_projection_deferred',family=command.event.family,reason=str(error))
        return result

    async def close(self):
        await self.maintenance.close()

    async def request(self,snapshot,request,now):
        try:
            if (snapshot.role_id,snapshot.login_epoch)!=(request.role_id,request.login_epoch):raise ValueError('stale_epoch')
            args=p.decode(request.kind,request.body)
            if request.kind==p.JOIN_FAMILY:
                ids,mode=args
                if mode!=0:raise ValueError('family_application_mode_unbound')
                if len(ids)>self.owner.policy['family_apply_batch_limit']:raise ValueError('family_application_batch_full')
                for identity in ids:
                    c=OrganizationCommand(snapshot.role_id,snapshot.login_epoch,request.request_id+':'+str(identity),
                        request.deadline_ms,identity,'apply')
                    await self.owner.command(c,now)
                return SocialResult()
            identity=await self.rt.io.run(('role',snapshot.role_id),self.store.membership,
                                         snapshot.role_id,snapshot.login_epoch,'family')
            if request.kind==p.FAMILY_POSITION:
                target,flag=args
                position={v:k for k,v in p.FAMILY_POSITIONS.items()}.get(flag)
                if position is None:raise ValueError('invalid_family_position')
                op,values='appoint',(target,position)
            elif request.kind==p.FAMILY_REVIEW:
                target,flag=args
                if flag not in (0,1):raise ValueError('invalid_family_decision')
                op,values='review',(target,bool(flag))
            elif request.kind==p.LEAVE_FAMILY:op,values='leave',()
            elif request.kind==p.EXPEL_MEMBER:op,values='expel',args
            else:raise ValueError('family_request_unbound')
            c=OrganizationCommand(snapshot.role_id,snapshot.login_epoch,request.request_id,request.deadline_ms,identity,op,values)
            await self.owner.command(c,now)
            return SocialResult()
        except (ValueError,NeedMoreData,struct.error) as error:
            return SocialResult(rejection=str(error) or 'invalid_family_packet')

    async def execute(self,key,command,stamp):
        before=await self.rt.io.run(key,self.store.family_audience,command.organization)
        result=await self.rt.io.run(key,self.store.execute,command,stamp)
        identity=result['organization'] if result.get('kind')=='family' else command.organization
        after=await self.rt.io.run(key,self.store.family_audience,identity)
        await self.notify(before,after)
        if after and (command.operation=='appoint' or (before and before.members!=after.members)):
            guild=await self.rt.io.run(key,self.store.family_guild,identity)
            if guild:self.owner.guild.nudge(guild)
        return result

    async def notify(self,before,after):
        if after is None:return
        old=dict(before.members) if before else {}
        current=dict(after.members)
        departed=tuple(sorted(set(old)-set(current)))
        cleared=tuple(sorted(set(before.applications if before else ())|set(after.applications)))
        online=self.rt.online_snapshot()
        for index,(rid,generation) in enumerate(after.members):
            target=online.get(rid)
            if target and generation:
                self.social.offer(FamilyWake(rid,target.login_epoch,0,b'',after.identity,generation,departed,cleared))
            if index%32==31:
                await asyncio.sleep(0)
        for rid in departed:
            target=online.get(rid)
            if target:self.social.offer(FamilyWake(rid,target.login_epoch,0,b'',after.identity,old[rid] or '',departed=True))

    async def presence(self,snapshot,is_online):
        try:
            identity=await self.rt.io.run(('role',snapshot.role_id),self.store.membership,
                snapshot.role_id,snapshot.login_epoch,'family')
            now=int(time.time()*1000)
            command=SocialCommand(snapshot.role_id,snapshot.login_epoch,uuid.uuid4().hex,now+5000,0,b'')
            await self.owner._call(('organization',identity),'family-presence',(snapshot,is_online),command,now)
        except ValueError as error:
            if str(error)!='not_in_family':self.rt.log(event='family_presence_deferred',role_id=snapshot.role_id,reason=str(error))
        except (Backpressure,StaleEpoch,TimeoutError) as error:
            # Presence is best effort. A local organization failure must not
            # prevent the role disconnect path from releasing its login lease.
            self.rt.log(event='family_presence_deferred',role_id=snapshot.role_id,reason=type(error).__name__)

    async def presence_owned(self,key,data,stamp):
        snapshot,is_online=data
        await self.rt.io.run(key,self.store.family_presence,key[1],snapshot.role_id,snapshot.login_epoch,is_online,stamp)
        current=await self.rt.io.run(key,self.store.family_audience,key[1])
        await self.notify(current,current)

    def packets(self,wake,online,known_scope=None,known_applications=()):
        if wake.departed:
            try:self.store.membership(wake.role_id,wake.login_epoch,'family')
            except ValueError as error:
                if str(error)=='not_in_family':return PreparedFamily(((p.LEFT_FAMILY,b''),),None,())
            return PreparedFamily((),known_scope,known_applications)
        snapshot=self.store.family_projection(wake.role_id,wake.login_epoch,wake.family,wake.generation,online)
        scope=(wake.family,wake.generation)
        known=known_applications if known_scope==scope else ()
        ids={m.role_id for m in snapshot.members}
        packets=[(p.REMOVE_FAMILY_MEMBER,p.removed_family_member(rid)) for rid in wake.removed_members if rid not in ids]
        # Even removal IDs are private application data. A demoted manager may
        # clear IDs already shown to this endpoint; an ordinary member must not
        # learn new applicant IDs via cleanup packets or an old queued wake.
        clear=tuple(sorted(set(known)|set(wake.cleared_applications))) if snapshot.manager else known
        if clear:packets.append((p.REMOVE_FAMILY_APPLICATIONS,p.removed_family_applications(clear)))
        packets.extend(((p.UPDATE_FAMILY,p.family_update(snapshot.view)),(p.ADD_FAMILY_MEMBERS,p.family_members(snapshot.members))))
        if snapshot.applications:packets.append((p.ADD_FAMILY_APPLICATIONS,p.family_applications(snapshot.applications)))
        return PreparedFamily(tuple(packets),scope,tuple(r.role_id for r in snapshot.applications))
