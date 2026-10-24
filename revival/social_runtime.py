"""Bounded per-role social scheduling and recipient-owned filtering.

Cross-role effects enqueue without awaiting another actor. A recipient alone
filters its packets and offers logical bytes to its connection's send mailbox.
No worker receives a Session, connection, cipher or network writer.
"""
import asyncio
from collections import Counter
from dataclasses import dataclass,replace
from runtime_core import Backpressure,StaleEpoch
from social_owner import RoleSocialOwner,SocialCommand,Delivery,Publish,RelationWake
from group_runtime import GroupRuntime,GroupDelivery
from group_protocol import GROUP_TYPES
from faction_runtime import OrganizationRuntime,OrganizationDelivery,FamilyWake,GuildWake


@dataclass(frozen=True)
class Work:
    operation: str
    value: object
    reply: object = None


@dataclass(frozen=True)
class SnapshotUpdate:
    snapshot: object
    revision: int


class SocialEndpoint:
    def __init__(self, router, snapshot, capacity):
        self.router,self.snapshot=router,snapshot
        self.domain=RoleSocialOwner(snapshot,router.rt.social_store,**router.rt.social_limits)
        self.queue=asyncio.Queue(maxsize=capacity)
        self.accepting=True
        self.poisoned=False
        self.metrics=Counter()
        self.snapshot_revision=0
        self.family_scope=None
        self.family_applications=()
        self.guild_scope=None
        self.guild_members=()
        self.task=asyncio.create_task(self.run(),name=f'social:{snapshot.role_id}:{snapshot.login_epoch}')

    def current(self):
        s=self.snapshot
        return self.accepting and not self.poisoned and self.router.endpoints.get(s.role_id) is self

    def offer(self,operation,value,reply=None):
        if not self.current(): raise StaleEpoch('Social endpoint closed or replaced')
        try: self.queue.put_nowait(Work(operation,value,reply))
        except asyncio.QueueFull:
            self.metrics['rejected']+=1
            raise Backpressure('Social mailbox full') from None
        self.metrics['high_water']=max(self.metrics['high_water'],self.queue.qsize())

    async def call(self,operation,value=None):
        reply=asyncio.get_running_loop().create_future()
        reply.add_done_callback(lambda f:f.exception() if not f.cancelled() else None)
        self.offer(operation,value,reply)
        return await asyncio.shield(reply)

    async def io(self,operation,*args):
        try: result=await self.router.rt.io.run(('role',self.snapshot.role_id),operation,*args)
        except TimeoutError:
            self.poisoned=True
            self.router.disconnect_slow(self.snapshot.role_id,self.snapshot.login_epoch)
            raise
        if not self.current(): raise StaleEpoch('Social endpoint expired during I/O')
        return result

    async def effects(self,effects):
        for effect in effects:
            if isinstance(effect,Delivery) and effect.role_id==self.snapshot.role_id:
                await self.deliver(effect)
            else: await self.router.rt.effects((effect,))

    async def deliver(self,delivery):
        if delivery.login_epoch!=self.snapshot.login_epoch:
            self.metrics['stale_delivery']+=1;return
        scene_key=delivery.scene_key
        if scene_key is not None and scene_key!=self.snapshot.scene_key:
            self.metrics['scene_delivery_stale']+=1;return
        if isinstance(delivery,GuildWake):
            online=tuple((rid,s.login_epoch) for rid,s in self.router.rt.online_snapshot().items())
            try:prepared=await self.io(self.router.organizations.guild.packets,delivery,online,self.guild_scope,self.guild_members)
            except ValueError as error:
                self.metrics['guild_filtered']+=1
                self.router.rt.log(event='guild_projection_deferred',role_id=self.snapshot.role_id,reason=str(error))
                return
            for kind,body in prepared.packets:await self.deliver(Delivery(delivery.role_id,delivery.login_epoch,kind,body,scene_key=scene_key))
            self.guild_scope,self.guild_members=prepared.scope,prepared.members
            return
        if isinstance(delivery,FamilyWake):
            online=tuple((rid,s.login_epoch) for rid,s in self.router.rt.online_snapshot().items())
            try:prepared=await self.io(self.router.organizations.family.packets,delivery,online,self.family_scope,self.family_applications)
            except ValueError as error:
                self.metrics['family_filtered']+=1
                self.router.rt.log(event='family_projection_deferred',role_id=self.snapshot.role_id,reason=str(error))
                return
            for kind,body in prepared.packets:await self.deliver(Delivery(delivery.role_id,delivery.login_epoch,kind,body,scene_key=scene_key))
            self.family_scope,self.family_applications=prepared.scope,prepared.application_ids
            return
        if isinstance(delivery,GroupDelivery):
            delivery=await self.io(self.router.groups.prepare_delivery,delivery)
            if delivery is None:self.metrics['group_filtered']+=1;return
        if isinstance(delivery,OrganizationDelivery):
            delivery=await self.io(self.router.organizations.prepare_delivery,delivery)
            if delivery is None:self.metrics['organization_filtered']+=1;return
        if not await self.io(self.domain.filter_delivery,delivery):
            self.metrics['filtered']+=1;return
        if scene_key is not None:
            hook=getattr(self.router.rt,'offer_scene_channel',None)
            if not callable(hook):
                self.metrics['scene_delivery_unavailable']+=1;return
            scoped=delivery if delivery.scene_key==scene_key else replace(delivery,scene_key=scene_key)
            if await hook(self.snapshot,scoped) is False:self.metrics['scene_delivery_rejected']+=1
            return
        target=self.router.rt.connections.get(delivery.role_id)
        if target and self.current(): target.offer(delivery.kind,delivery.body,delivery.login_epoch)

    async def recover(self,notify=True):
        wakes=await self.io(self.domain.store.relation_events,self.snapshot.role_id,64)
        recovered=[]
        for wake in wakes:
            result=await self.io(self.domain.apply_relation,wake,self.router.rt.online_snapshot())
            if result.rejection:
                self.router.rt.log(event='social_relation_deferred',role_id=self.snapshot.role_id,reason=result.rejection)
            if notify:await self.effects(result.effects)
            else:recovered.extend(result.effects)
        return tuple(recovered)

    async def handle(self,work):
        if not self.current(): raise StaleEpoch('Social endpoint expired')
        if work.operation=='snapshot': return self.update_snapshot(work.value)
        if work.operation=='delivery': return await self.deliver(work.value)
        if work.operation=='join':
            # Initial list reflects committed state even if a notification was
            # lost on the previous connection. Pending requests replay afterward.
            recovered=await self.recover(False)
            result=await self.io(self.domain.initial,self.router.rt.online_snapshot())
            await self.effects(result.effects)
            await self.effects(recovered)
            pending=await self.io(self.domain.pending_notices)
            await self.effects(pending.effects)
            await self.router.groups.initial(self)
            await self.router.organizations.family.presence(self.snapshot,True)
            await self.router.organizations.guild.presence(self.snapshot)
            await self.router.organizations.guild.initial(self)
            return
        if work.operation=='recover': return await self.recover()
        if work.operation=='relation':
            result=await self.io(self.domain.apply_relation,work.value,self.router.rt.online_snapshot())
        elif work.operation=='request':
            update,command,now=work.value
            self.update_snapshot(update)
            snapshot=self.snapshot
            if command.kind in GROUP_TYPES:
                result=await self.router.groups.request(snapshot,command,now)
            elif self.router.organizations.handles(command):
                result=await self.router.organizations.request(snapshot,command,now)
            else:result=await self.io(self.domain.execute,command,self.router.rt.online_snapshot(),now)
        else: raise ValueError('Unknown social operation')
        if result.rejection:
            self.router.rt.log(event='social_rejected',role_id=self.snapshot.role_id,reason=result.rejection)
        await self.effects(result.effects)
        return result

    def update_snapshot(self,update):
        """Only this endpoint's sequential handler mutates its domain snapshot."""
        if not isinstance(update,SnapshotUpdate): raise ValueError('Versioned social snapshot required')
        snapshot,revision=update.snapshot,update.revision
        if (snapshot.role_id,snapshot.login_epoch)!=(self.snapshot.role_id,self.snapshot.login_epoch):
            raise StaleEpoch('Social snapshot epoch mismatch')
        if type(revision) is not int or revision<0: raise ValueError('Invalid social snapshot revision')
        if revision<self.snapshot_revision or (revision==self.snapshot_revision and snapshot!=self.snapshot):
            raise StaleEpoch('Stale or conflicting social snapshot revision')
        self.snapshot=snapshot
        self.domain.snapshot=snapshot
        self.snapshot_revision=revision
        return snapshot

    async def run(self):
        while True:
            work=await self.queue.get()
            try:
                if work is None:return
                result=await self.handle(work)
                if work.reply is not None and not work.reply.done():work.reply.set_result(result)
            except Exception as error:
                self.metrics['errors']+=1
                if work.reply is not None and not work.reply.done():work.reply.set_exception(error)
                else:self.router.rt.log(event='social_delivery_failed',role_id=self.snapshot.role_id,reason=type(error).__name__)
            finally:self.queue.task_done()

    async def close(self):
        self.accepting=False
        await self.queue.join()
        self.queue.put_nowait(None)
        await self.task


class SocialRuntime:
    def __init__(self,runtime,capacity=64):
        if type(capacity) is not int or capacity<1:raise ValueError('Positive bounded social mailbox capacity required')
        self.rt,self.capacity=runtime,capacity
        self.endpoints={}
        self.groups=GroupRuntime(self,runtime.social_store.group_policy)
        self.organizations=OrganizationRuntime(self,runtime.social_store.organization_policy)

    def disconnect_slow(self,role_id,epoch):
        c=self.rt.connections.get(role_id)
        if c and c.epoch==epoch:
            c.closed=True;c.writer.close()

    def open(self,snapshot):
        if snapshot.role_id in self.endpoints:raise ValueError('Social role already registered')
        endpoint=SocialEndpoint(self,snapshot,self.capacity)
        self.endpoints[snapshot.role_id]=endpoint
        return endpoint

    async def join(self,snapshot,snapshot_revision=0):
        endpoint=self.endpoints.get(snapshot.role_id)
        if endpoint is None:endpoint=self.open(snapshot)
        if endpoint.snapshot.login_epoch!=snapshot.login_epoch:raise StaleEpoch('Social login epoch mismatch')
        await endpoint.call('snapshot',SnapshotUpdate(snapshot,snapshot_revision))
        await endpoint.call('join')

    async def publish(self,snapshot,snapshot_revision):
        endpoint=self.endpoints.get(snapshot.role_id)
        if not endpoint or endpoint.snapshot.login_epoch!=snapshot.login_epoch:raise StaleEpoch('Social role not online')
        return await endpoint.call('snapshot',SnapshotUpdate(snapshot,snapshot_revision))

    async def request(self,snapshot,command,now,snapshot_revision=0):
        endpoint=self.endpoints.get(snapshot.role_id)
        if not endpoint or endpoint.snapshot.login_epoch!=snapshot.login_epoch:raise StaleEpoch('Social role not online')
        return await endpoint.call('request',(SnapshotUpdate(snapshot,snapshot_revision),command,now))

    def offer(self,effect):
        endpoint=self.endpoints.get(effect.role_id)
        # Offline approval effects remain in the durable outbox; join replays them.
        if endpoint is None:return False
        try:endpoint.offer('relation' if isinstance(effect,RelationWake) else 'delivery',effect)
        except (Backpressure,StaleEpoch):
            if isinstance(effect,Delivery):self.disconnect_slow(effect.role_id,effect.login_epoch)
            self.rt.log(event='social_mailbox_rejected',role_id=effect.role_id,durable=isinstance(effect,RelationWake))
            return False
        return True

    async def recover(self,snapshot):
        endpoint=self.endpoints.get(snapshot.role_id)
        if endpoint and endpoint.snapshot.login_epoch==snapshot.login_epoch:
            await endpoint.call('recover')

    async def leave(self,role_id,epoch):
        endpoint=self.endpoints.get(role_id)
        if endpoint and endpoint.snapshot.login_epoch==epoch:
            # Retire before waiting: no old completion can offer to a replacement.
            del self.endpoints[role_id]
            await endpoint.close()
            await self.organizations.family.presence(endpoint.snapshot,False)
            await self.organizations.guild.presence(endpoint.snapshot)

    async def idle(self):
        # Verification/shutdown helper: nested relation effects may enqueue again.
        for _ in range(8):
            current=tuple(self.endpoints.values())
            await asyncio.gather(*(e.queue.join() for e in current))
            if all(e.queue.empty() for e in current):return
        raise TimeoutError('Social mailboxes did not quiesce')

    async def close(self):
        for endpoint in tuple(self.endpoints.values()):
            await self.leave(endpoint.snapshot.role_id,endpoint.snapshot.login_epoch)
        await self.groups.close()
        await self.organizations.close()
