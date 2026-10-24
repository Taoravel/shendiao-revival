"""Bounded per-process story projection metadata; gameplay stays map-owned.

Call synchronously on its metadata executor, then await loaders/map owners
outside it. It stores immutable identities/tickets, never live map objects,
connections, database handles or mutable role state. Directory records must
already be authorized by their current role caller transaction.
"""
from dataclasses import dataclass,field
from uuid import uuid4
from world_story_instances import StoryInstance,StoryInstanceIntent
from world_owner import MapAddress,MapIdleSnapshot,MapRetired


@dataclass(frozen=True)
class ProjectionLoad:
    record: StoryInstance
    generation: str
    request_id: str
    deadline_ms: int


@dataclass(frozen=True)
class ProjectionHandle:
    record: StoryInstance
    generation: str
    map_generation: str


@dataclass(frozen=True)
class ProjectionLoadCancellation:
    load: ProjectionLoad
    cancellation_id: str


@dataclass(frozen=True)
class ProjectionUse:
    handle: ProjectionHandle
    request_id: str
    use_id: str


@dataclass(frozen=True)
class ProjectionUnload:
    handle: ProjectionHandle
    request_id: str
    unload_id: str


@dataclass
class _Entry:
    record: StoryInstance
    loading: ProjectionLoad | None = None
    handle: ProjectionHandle | None = None
    uses: dict = field(default_factory=dict)
    unloading: ProjectionUnload | None = None
    cancelling: ProjectionLoadCancellation | None = None
    clock_ms: int = 0
    idle_since_ms: int | None = None
    unload_started_ms: int | None = None


class StoryProjectionPool:
    def __init__(self,rules,*,pins_per_projection):
        if type(pins_per_projection) is not int or not 1<=pins_per_projection<=rules.pins_per_projection:
            raise ValueError('Explicit per-projection pending-operation budget within published cap required')
        self.rules=rules
        self.pins_per_projection=pins_per_projection
        self._entries={}
        self._identities={}

    @property
    def loaded_count(self):
        """Reserved process slots, including loading and retiring projections."""
        return len(self._entries)

    def _record(self,record):
        if (type(record) is not StoryInstance or type(record.intent) is not StoryInstanceIntent
                or type(record.address) is not MapAddress
                or record.kind!=self.rules.kind or record.directory_policy!=self.rules.revision
                or any(type(v) is not int or not 0<v<2**63 for v in (record.role_id,record.account_id))
                or any(type(v) is not int for v in
                    (record.address.map_id,record.address.instance_id,record.address.partition_id))
                or record.address.map_id!=self.rules.map_id or record.address.partition_id!=self.rules.partition_id
                or not self.rules.minimum_id<=record.address.instance_id<self.rules.maximum_id
                or type(record.intent.source_task_id) is not int
                or record.intent.source_task_id not in self.rules.source_tasks.values()
                or any(type(v) is not str or not 1<=len(v)<=128 for v in
                    (record.intent.chapter_id,record.intent.creation_id,record.intent.origin_policy,record.intent.route_fingerprint))):
            raise ValueError('Validated frozen story directory record required')

    @staticmethod
    def _request(request_id):
        if type(request_id) is not str or not 1<=len(request_id)<=128:
            raise ValueError('Stable bounded internal operation identity required')

    @staticmethod
    def _identity(record):
        return record.kind,record.role_id,record.intent.chapter_id

    @staticmethod
    def _clock(entry,now_ms):
        if type(now_ms) is not int or now_ms<entry.clock_ms:
            raise ValueError('Monotonic trusted projection clock required')

    def acquire(self,record,*,request_id,deadline_ms,now_ms,actor_state):
        """Return a load ticket or a use pin on an already loaded projection.

        A pin fences every queued/in-flight cross-owner call. Same pending ID
        retries are idempotent; release/reacquire gets a fresh use_id. Unknown
        or dynamic actors refuse cold loading until durable recovery exists.
        """
        self._record(record);self._request(request_id)
        if (type(now_ms) is not int or type(deadline_ms) is not int or not 0<=now_ms<deadline_ms<2**63
                or actor_state not in ('static_original','dynamic_uncheckpointed','unknown')):
            raise ValueError('Trusted deadline and explicit actor state required')
        key=self._identity(record)
        if key in self._identities and self._identities[key]!=record.address:
            raise ValueError('Story identity already has a different loaded address')
        entry=self._entries.get(record.address)
        if entry is not None:
            self._clock(entry,now_ms)
            if entry.record!=record:raise ValueError('Loaded story directory identity conflict')
            if entry.unloading is not None:raise ValueError('Story projection is retiring')
            if entry.loading is not None:
                if entry.cancelling is not None:raise ValueError('Story load cancellation awaits loader cleanup')
                if actor_state!='static_original':raise ValueError('Unrecoverable cold actor state')
                if entry.loading.request_id!=request_id or entry.loading.deadline_ms!=deadline_ms:
                    raise ValueError('Story projection still loading')
                entry.clock_ms=now_ms
                return entry.loading
            previous=entry.uses.get(request_id)
            if previous is not None:
                entry.clock_ms=now_ms
                return previous
            if len(entry.uses)>=self.pins_per_projection:raise ValueError('Story pending operation capacity')
            use=ProjectionUse(entry.handle,request_id,uuid4().hex)
            entry.uses[request_id]=use
            entry.clock_ms=now_ms;entry.idle_since_ms=None
            return use
        if actor_state!='static_original':raise ValueError('Unrecoverable cold actor state')
        if len(self._entries)>=self.rules.loaded_capacity:
            raise ValueError('Story loaded projection capacity')
        load=ProjectionLoad(record,uuid4().hex,request_id,deadline_ms)
        self._entries[record.address]=_Entry(record,loading=load,clock_ms=now_ms)
        self._identities[key]=record.address
        return load

    def _loading(self,ticket):
        if type(ticket) is not ProjectionLoad or type(ticket.deadline_ms) is not int:
            raise ValueError('Exact projection load ticket required')
        self._record(ticket.record)
        entry=self._entries.get(ticket.record.address)
        if entry is None or entry.loading!=ticket:
            raise ValueError('Stale projection load ticket')
        return entry

    def finish_load(self,ticket,snapshot,*,now_ms):
        """After external construction, bind its exact empty map generation."""
        entry=self._loading(ticket)
        self._clock(entry,now_ms)
        if (entry.cancelling is not None or type(now_ms) is not int or not 0<=now_ms<ticket.deadline_ms
                or type(snapshot) is not MapIdleSnapshot or not snapshot.idle
                or snapshot.address!=ticket.record.address
                or type(snapshot.owner_generation) is not str or not snapshot.owner_generation):
            raise ValueError('Live empty lifecycle-enabled map generation required')
        handle=ProjectionHandle(entry.record,ticket.generation,snapshot.owner_generation)
        use=ProjectionUse(handle,ticket.request_id,uuid4().hex)
        entry.loading=None;entry.handle=handle;entry.uses[ticket.request_id]=use;entry.clock_ms=now_ms
        return use

    def _remove(self,entry):
        del self._entries[entry.record.address]
        del self._identities[self._identity(entry.record)]

    def cancel_load(self,ticket):
        """Request cancellation; keep its process slot until the loader stops.

        Observation timeout never proves the loader or resources are gone.
        Repeated requests return the same immutable cancellation operation.
        """
        entry=self._loading(ticket)
        if entry.cancelling is None:
            entry.cancelling=ProjectionLoadCancellation(ticket,uuid4().hex)
        return entry.cancelling

    def finish_load_cancel(self,cancellation):
        """Loader terminal/cleanup acknowledgement, never an awaiter timeout.

        Invoke only after the exact loading executor confirms no running work
        or owned resources remain. Unknown outcomes keep the slot fenced.
        """
        if type(cancellation) is not ProjectionLoadCancellation:
            raise ValueError('Exact loader cancellation confirmation required')
        entry=self._loading(cancellation.load)
        if entry.cancelling!=cancellation:raise ValueError('Stale loader cancellation confirmation')
        self._remove(entry)
        return entry.record

    def _loaded(self,handle):
        if type(handle) is not ProjectionHandle:raise ValueError('Exact loaded projection handle required')
        self._record(handle.record)
        entry=self._entries.get(handle.record.address)
        if entry is None or entry.handle!=handle:raise ValueError('Stale loaded projection handle')
        return entry

    def release(self,use,*,now_ms):
        if type(use) is not ProjectionUse:raise ValueError('Exact projection operation pin required')
        entry=self._loaded(use.handle)
        self._clock(entry,now_ms)
        previous=entry.uses.get(use.request_id)
        if previous is None:return False
        if previous!=use:raise ValueError('Stale operation pin cannot release its replacement')
        del entry.uses[use.request_id]
        entry.clock_ms=now_ms
        if not entry.uses:entry.idle_since_ms=now_ms
        return True

    def begin_unload(self,handle,*,request_id,now_ms):
        """Fence new acquire before asking the map executor to retire idle state."""
        self._request(request_id);entry=self._loaded(handle)
        self._clock(entry,now_ms)
        if entry.uses:raise ValueError('Story projection still has queued/in-flight operations')
        if entry.idle_since_ms is None or now_ms-entry.idle_since_ms<self.rules.idle_unload_after_ms:
            raise ValueError('Story pending-operation idle period is too short')
        if entry.unloading is not None:
            if entry.unloading.request_id!=request_id:raise ValueError('Another story unload is pending')
            return entry.unloading
        ticket=ProjectionUnload(handle,request_id,uuid4().hex)
        entry.unloading=ticket
        entry.clock_ms=now_ms;entry.unload_started_ms=now_ms
        return ticket

    def _unloading(self,ticket):
        if type(ticket) is not ProjectionUnload:raise ValueError('Exact projection unload ticket required')
        entry=self._loaded(ticket.handle)
        if entry.unloading!=ticket:raise ValueError('Stale projection unload ticket')
        return entry

    def cancel_unload(self,ticket,live_snapshot):
        """Only after confirmed refusal and a fresh live-owner snapshot.

        An observation timeout leaves the projection fenced. A retired owner
        cannot be made available again; finish its exact retirement instead.
        """
        entry=self._unloading(ticket)
        if (type(live_snapshot) is not MapIdleSnapshot or live_snapshot.retired
                or live_snapshot.address!=entry.record.address
                or live_snapshot.owner_generation!=entry.handle.map_generation):
            raise ValueError('Confirmed live map generation required to cancel unloading')
        entry.unloading=None
        entry.unload_started_ms=None

    def finish_unload(self,ticket,receipt):
        """Release a process slot only after the exact owner confirms retirement."""
        entry=self._unloading(ticket)
        if (type(receipt) is not MapRetired or receipt.address!=entry.record.address
                or receipt.owner_generation!=entry.handle.map_generation
                or any(type(v) is not int or v<0 for v in
                    (receipt.idle_since_ms,receipt.retired_at_ms,receipt.revision))
                or receipt.retired_at_ms-receipt.idle_since_ms<self.rules.idle_unload_after_ms
                or receipt.retired_at_ms<entry.unload_started_ms
                or receipt.retired_at_ms-entry.idle_since_ms<self.rules.idle_unload_after_ms):
            raise ValueError('Exact map retirement receipt and published idle duration required')
        self._remove(entry)
        return entry.record
