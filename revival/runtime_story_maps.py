"""Story projection scheduling; metadata never waits on map gameplay or I/O."""
import asyncio
import time
import uuid
from dataclasses import dataclass,replace
from world_story_projection_pool import StoryProjectionPool,ProjectionLoad
from runtime_core import Backpressure


@dataclass(frozen=True)
class TrackedSceneDelivery:
    ticket: object
    pin: object


@dataclass(frozen=True)
class PendingRetirement:
    ticket: object
    receipt: object = None
    forgotten: bool = False


class PinnedMapMailbox:
    """Every accepted map call retains its pin until the actual reply is terminal."""
    def __init__(self,manager,record,raw):
        self.manager,self.record,self.raw=manager,record,raw
        self.pending=set()
        self.accepting=True

    def __getattr__(self,name):return getattr(self.raw,name)

    async def call(self,operation,*args,**kwargs):
        if not self.accepting:raise ValueError('Story map mailbox closed')
        now=self.manager.now()
        duration=max(1,int(((kwargs.get('deadline') or time.monotonic()+10)-time.monotonic())*1000))
        pin=self.manager.pool.acquire(self.record,request_id=uuid.uuid4().hex,
            deadline_ms=now+duration,now_ms=now,actor_state='static_original')
        if isinstance(pin,ProjectionLoad):raise ValueError('Story map operation arrived before loading finished')
        task=asyncio.create_task(self.raw.call(operation,*args,**kwargs))
        self.pending.add(task)
        def terminal(done):
            self.pending.discard(done)
            if not done.cancelled():done.exception()
            self.manager.pool.release(pin,now_ms=self.manager.now())
        task.add_done_callback(terminal)
        # Cancelling an awaiter must not cancel SerialOwner.call's observer and
        # release a pin while its already accepted command is still running.
        return await asyncio.shield(task)

    async def close(self):
        self.accepting=False
        if self.pending:await asyncio.gather(*tuple(self.pending),return_exceptions=True)
        await self.raw.close()


class RuntimeStoryMaps:
    """A bounded metadata Adapter; each map retains its independent mailbox."""
    def __init__(self,rules,create_map,forget_map,*,clock=None):
        self.rules=rules
        self.pool=StoryProjectionPool(rules,pins_per_projection=rules.pins_per_projection)
        self.create_map,self.forget_map=create_map,forget_map
        self.clock=clock or (lambda:int(time.monotonic()*1000))
        self.loaded={};self.loading={};self.maintenance={};self.retirements={};self.work=set();self.closed=False
        self.scene_finishes={};self.scene_finish_tasks={}
        self.gc=asyncio.create_task(self._collect_loop(),name='story-projection-maintenance')

    def now(self):
        value=self.clock()
        if type(value) is not int or not 0<=value<2**63:raise ValueError('Trusted monotonic story clock required')
        return value

    async def get_map(self,record,*,request_id,deadline_ms):
        if self.closed:raise ValueError('Story projection runtime closed')
        ticket=self.pool.acquire(record,request_id=request_id,deadline_ms=deadline_ms,
            now_ms=self.now(),actor_state='static_original')
        if not isinstance(ticket,ProjectionLoad):
            owner,handle=self.loaded[record.address]
            if handle!=ticket.handle:raise ValueError('Story projection generation mismatch')
            self.pool.release(ticket,now_ms=self.now())
            return owner
        task=self.loading.get(record.address)
        if task is None:
            task=asyncio.create_task(self._load(ticket),name='story-load:'+str(record.address.instance_id))
            self.loading[record.address]=task
            def terminal(done):
                if self.loading.get(record.address) is done:self.loading.pop(record.address,None)
                if not done.cancelled():done.exception()
            task.add_done_callback(terminal)
        return await asyncio.shield(task)

    async def _load(self,ticket):
        owner=None
        try:
            owner=self.create_map(ticket.record)
            owner.control_mailbox=owner.mailbox
            snapshot=await owner.control_mailbox.call('inspect_lifecycle',self.now())
            pin=self.pool.finish_load(ticket,snapshot,now_ms=self.now())
            owner.mailbox=PinnedMapMailbox(self,ticket.record,owner.control_mailbox)
            owner.story_record=ticket.record
            owner.story_handle=pin.handle
            self.loaded[ticket.record.address]=(owner,pin.handle)
            self.pool.release(pin,now_ms=self.now())
            return owner
        except BaseException:
            cancellation=self.pool.cancel_load(ticket)
            if owner is not None:
                await getattr(owner,'control_mailbox',owner.mailbox).close()
                self.forget_map(ticket.record.address,owner)
            # This runs on the actual loader's terminal cleanup path, never an
            # outer observer timeout. Unknown cleanup leaves the slot fenced.
            self.pool.finish_load_cancel(cancellation)
            raise

    def _schedule_collection(self):
        if self.closed:return ()
        jobs=[]
        for address,(owner,handle) in tuple(self.loaded.items()):
            task=self.maintenance.get(address)
            if task is None:
                task=asyncio.create_task(self._collect_one(address,owner,handle))
                self.maintenance[address]=task
                def terminal(done,key=address):
                    if self.maintenance.get(key) is done:self.maintenance.pop(key,None)
                    if not done.cancelled():done.exception()
                task.add_done_callback(terminal)
            jobs.append(task)
        return tuple(jobs)

    async def collect(self):
        results=await asyncio.gather(*(asyncio.shield(task) for task in self._schedule_collection()))
        return tuple(address for address in results if address is not None)

    async def _collect_one(self,address,owner,handle):
        finishes=tuple(delivery for delivery in self.scene_finishes.values()
            if delivery.pin.handle==handle)
        if finishes:
            await asyncio.gather(*(self.finish_delivery(delivery) for delivery in finishes))
        pending=self.retirements.get(address)
        if pending is None or pending.receipt is None:
            now=self.now()
            snapshot=await owner.control_mailbox.call('inspect_lifecycle',now)
            if pending is None:
                if not snapshot.idle:return None
                try:ticket=self.pool.begin_unload(handle,request_id=uuid.uuid4().hex,now_ms=now)
                except ValueError:return None
                pending=PendingRetirement(ticket)
                self.retirements[address]=pending
            elif not snapshot.idle:
                # A retired generation without its acknowledgement stays
                # fenced. A confirmed live refusal may resume admission.
                self.pool.cancel_unload(pending.ticket,snapshot)
                self.retirements.pop(address)
                return None
            try:
                receipt=await owner.control_mailbox.call('retire_idle',snapshot,self.now(),self.rules.idle_unload_after_ms)
            except (ValueError,TimeoutError,Backpressure):
                live=await owner.control_mailbox.call('inspect_lifecycle',self.now())
                self.pool.cancel_unload(pending.ticket,live)
                self.retirements.pop(address)
                return None
            pending=replace(pending,receipt=receipt)
            self.retirements[address]=pending
        # Remove the sealed generation and drain its Adapter before a new
        # load may reuse the persistent address or its process slot.
        if not pending.forgotten:
            self.forget_map(address,owner)
            pending=replace(pending,forgotten=True)
            self.retirements[address]=pending
        if not owner.mailbox.task.done():await owner.mailbox.close()
        self.pool.finish_unload(pending.ticket,pending.receipt)
        self.loaded.pop(address,None)
        self.retirements.pop(address)
        return address

    async def _collect_loop(self):
        while True:
            await asyncio.sleep(1)
            # Only per-map tasks are scheduled. A held map's cleanup cannot
            # prevent a later tick from inspecting another loaded address.
            # Each terminal callback observes failures; the original map's
            # ticket/receipt remains fenced for a later retry.
            self._schedule_collection()

    def _track(self,task):
        self.work.add(task)
        def terminal(done):
            self.work.discard(done)
            if not done.cancelled():done.exception()
        task.add_done_callback(terminal)
        return task

    async def begin_delivery(self,owner,location,generation):
        if self.closed:raise ValueError('Story scene admission closed')
        now=self.now();identity=uuid.uuid4().hex
        pin=self.pool.acquire(owner.story_record,request_id='scene:'+identity,
            deadline_ms=now+10000,now_ms=now,actor_state='static_original')
        if isinstance(pin,ProjectionLoad):raise ValueError('Scene delivery requires a loaded projection')
        async def register():
            try:
                ticket=await owner.control_mailbox.call('begin_scene_delivery',location,generation,identity)
            except Exception:
                self.pool.release(pin,now_ms=self.now())
                raise
            return TrackedSceneDelivery(ticket,pin)
        task=self._track(asyncio.create_task(register()))
        try:return await asyncio.shield(task)
        except asyncio.CancelledError:
            async def cancel_late():
                delivery=await task
                await self.finish_delivery(delivery)
            self._track(asyncio.create_task(cancel_late()))
            raise

    async def finish_delivery(self,delivery):
        if type(delivery) is not TrackedSceneDelivery:raise ValueError('Exact tracked scene delivery required')
        address=delivery.pin.handle.record.address
        if delivery.ticket.address!=address:raise ValueError('Scene delivery address mismatch')
        current=self.loaded.get(address)
        if (current is None or current[1]!=delivery.pin.handle
                or delivery.ticket.owner_generation!=current[1].map_generation):
            raise ValueError('Scene delivery map generation expired')
        key=delivery.pin.use_id
        previous=self.scene_finishes.get(key)
        if previous is not None and previous!=delivery:raise ValueError('Scene finish identity conflict')
        existing=self.scene_finish_tasks.get(key)
        if existing is not None:return await asyncio.shield(existing)
        self.scene_finishes[key]=delivery
        async def finish():
            address=delivery.pin.handle.record.address
            if delivery.ticket.address!=address:raise ValueError('Scene delivery address mismatch')
            owner,handle=self.loaded[address]
            if handle!=delivery.pin.handle or delivery.ticket.owner_generation!=handle.map_generation:
                raise ValueError('Scene delivery map generation expired')
            result=await owner.control_mailbox.call('finish_scene_delivery',delivery.ticket)
            self.pool.release(delivery.pin,now_ms=self.now())
            self.scene_finishes.pop(key)
            return result
        task=self._track(asyncio.create_task(finish()))
        self.scene_finish_tasks[key]=task
        def terminal(done):
            if self.scene_finish_tasks.get(key) is done:self.scene_finish_tasks.pop(key)
        task.add_done_callback(terminal)
        return await asyncio.shield(task)

    async def stop(self):
        self.closed=True
        self.gc.cancel()
        await asyncio.gather(self.gc,return_exceptions=True)
        if self.maintenance:await asyncio.gather(*tuple(self.maintenance.values()),return_exceptions=True)
        if self.loading:await asyncio.gather(*tuple(self.loading.values()),return_exceptions=True)

    async def close(self):
        await self.stop()
        while self.work:await asyncio.gather(*tuple(self.work),return_exceptions=True)
