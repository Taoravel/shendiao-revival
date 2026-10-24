"""Map-partition state owner. Schedule each instance serially on its own runtime.

No Session, storage, network, thread pool or global gameplay queue is held here.
The role router supplies authoritative login leases and routes immutable messages.
"""
from dataclasses import dataclass, replace
from queue import Queue, Full, Empty
from threading import Lock
from uuid import uuid4
from world_catalog import valid_position
from world_movement import plan_movement


@dataclass(frozen=True)
class MapAddress:
    map_id: int
    instance_id: int
    partition_id: int


@dataclass(frozen=True)
class Location:
    role_id: int
    login_epoch: int | str
    address: MapAddress
    version: int
    x: int
    y: int
    state: str = 'active'

    @property
    def position(self):
        return self.address.map_id, self.x, self.y


@dataclass(frozen=True)
class MoveCommand:
    expected: Location
    request_id: str
    deadline_ms: int
    kind: int
    body: bytes
    # Trusted role-owner snapshot of native +0x218; never read from wire body.
    movement_state: int | None = None
    # Explicit trusted producer contract; legacy callers retain all-node checks.
    collision_points: str = 'reported_nodes'


@dataclass(frozen=True)
class TransferOffer:
    transfer_id: str
    source: Location
    target_position: tuple
    deadline_ms: int


@dataclass(frozen=True)
class Reservation:
    offer: TransferOffer
    target: MapAddress


@dataclass(frozen=True)
class FrozenTransfer:
    reservation: Reservation
    source: Location


@dataclass(frozen=True)
class TransferCommit:
    frozen: FrozenTransfer
    location: Location


@dataclass(frozen=True)
class TransferCancelled:
    reservation: Reservation


@dataclass(frozen=True)
class TransferResumed:
    cancellation: TransferCancelled
    location: Location


@dataclass(frozen=True)
class RelocationPrepared:
    owner_generation: str
    preparation_id: str
    offer: TransferOffer
    frozen: Location
    target: Location
    movement_state: int


@dataclass(frozen=True)
class RelocationCommit:
    prepared: RelocationPrepared
    location: Location


@dataclass(frozen=True)
class RelocationCancelled:
    prepared: RelocationPrepared
    location: Location


@dataclass(frozen=True)
class _DetachedRelocation:
    receipt: RelocationCommit | RelocationCancelled


@dataclass(frozen=True)
class MapRelocationSnapshot:
    address: MapAddress
    owner_generation: str
    role_id: int
    request_id: str
    location: Location | None
    membership_id: str | None
    prepared: RelocationPrepared | None
    result: RelocationCommit | RelocationCancelled | None
    detached: bool
    offer: TransferOffer | None
    projection_generation: str | None
    presence: object


@dataclass(frozen=True)
class RelocationRecoveryDecision:
    prepared: RelocationPrepared
    authority: Location
    committed: bool


@dataclass(frozen=True)
class MapRelocationRetired:
    address: MapAddress
    owner_generation: str
    prepared: RelocationPrepared
    authority: Location
    removed: Location | None
    record_removed: bool


@dataclass(frozen=True)
class MoveResult:
    location: Location | None = None
    checkpoint: Location | None = None
    offer: TransferOffer | None = None
    rejection: str = ''


@dataclass(frozen=True)
class TransferRecoveryDecision:
    transfer_id: str
    source: Location
    target_position: tuple
    new_epoch: int | str
    authority_position: tuple
    authority_version: int
    committed: bool
    offer: TransferOffer | None = None
    receipt: TransferCommit | None = None


@dataclass(frozen=True)
class MapTransferSnapshot:
    address: MapAddress
    owner_generation: str
    role_id: int
    transfer_id: str
    location: Location | None
    offer: TransferOffer | None
    incoming: object
    departure: object


@dataclass(frozen=True)
class MapTransferRetired:
    address: MapAddress
    role_id: int
    old_epoch: int | str
    transfer_id: str
    target_address: MapAddress | None
    removed: Location | None


@dataclass(frozen=True)
class MapIdleSnapshot:
    address: MapAddress
    owner_generation: str
    revision: int
    enabled: bool
    retired: bool
    actors_pristine: bool
    members: int
    incoming: int
    departures: int
    offers: int
    queued_movements: int
    pending_scene_deliveries: int
    idle_since_ms: int | None
    relocations: int = 0

    @property
    def idle(self):
        return (self.enabled and not self.retired and self.actors_pristine
            and not any((self.members,self.incoming,self.departures,self.offers,
                         self.queued_movements,self.pending_scene_deliveries,self.relocations)))


@dataclass(frozen=True)
class MapRetired:
    address: MapAddress
    owner_generation: str
    revision: int
    idle_since_ms: int
    retired_at_ms: int


@dataclass(frozen=True)
class SceneDeliveryTicket:
    address: MapAddress
    owner_generation: str
    location: Location
    connection_generation: int
    request_id: str
    delivery_id: str


class MapOwner:
    def __init__(self, address, catalog, *, capacity, transfer_capacity, mailbox_capacity, maze=None):
        if min(capacity, transfer_capacity, mailbox_capacity) < 1:
            raise ValueError('Explicit positive owner capacities required')
        if address.map_id not in catalog or not catalog[address.map_id]['available']:
            raise ValueError('Unavailable map')
        self.address, self.catalog = address, catalog
        self.maze = maze
        self.capacity, self.transfer_capacity = capacity, transfer_capacity
        self._roles = {}
        self._memberships = {}  # actual relation identity, no second position writer
        self._offers = {}  # at most one per member
        self._incoming = {}  # reservation or committed receipt, bounded together
        self._departures = {}  # frozen handoff or finalized receipt, bounded together
        self._relocations = {}  # same-instance decisions, each bounded by transfer_capacity
        self._mailbox = Queue(maxsize=mailbox_capacity)
        self._generation=uuid4().hex
        self._member_projection=None
        # Only producer enqueue vs owner retirement share this per-map gate.
        # Gameplay, I/O and other maps never execute under it.
        self._submission_gate=Lock()
        self._retired=False
        self._lifecycle_enabled=False
        self._lifecycle_revision=0
        self._idle_since_ms=None
        self._lifecycle_clock=-1
        self._actors_pristine=False
        self._scene_deliveries={}
        self._scene_delivery_capacity=0

    def configure_lifecycle(self,*,scene_delivery_capacity,actor_state):
        """Startup opt-in, after the Adapter installs all delivery hooks.

        Only static original actors are currently cold-recoverable. Existing
        Adapters remain non-retirable until explicitly wired to this contract.
        """
        if (self._lifecycle_enabled or self._retired
                or type(scene_delivery_capacity) is not int or scene_delivery_capacity<1
                or actor_state!='static_original'
                or self._roles or self._incoming or self._departures or self._offers or self._relocations
                or not self._mailbox.empty()):
            raise ValueError('Lifecycle requires a fresh static owner and explicit delivery budget')
        self._scene_delivery_capacity=scene_delivery_capacity
        self._actors_pristine=True
        self._lifecycle_enabled=True
        self._invalidate_idle()

    def _invalidate_idle(self):
        self._lifecycle_revision+=1
        self._idle_since_ms=None

    @staticmethod
    def _delivery_location(location):
        return (type(location) is Location and type(location.address) is MapAddress
            and all(type(v) is int for v in (location.role_id,location.version,location.x,location.y,
                location.address.map_id,location.address.instance_id,location.address.partition_id))
            and 0<location.role_id<2**63 and 0<location.version<2**63
            and ((type(location.login_epoch) is int and 0<location.login_epoch<2**63)
                 or (type(location.login_epoch) is str and 1<=len(location.login_epoch)<=128)))

    def begin_scene_delivery(self,expected,*,connection_generation,request_id):
        """Track a trusted pending server send fence, not a client-ready ACK.

        Register on this map executor before publishing the asynchronous send;
        finish on acknowledged send/cancellation even if the role has left.
        """
        if (not self._lifecycle_enabled or self._retired or not self._delivery_location(expected)
                or type(connection_generation) is not int or not 0<connection_generation<2**63
                or type(request_id) is not str or not 1<=len(request_id)<=128
                or self.location(expected.role_id)!=expected):
            raise ValueError('Current map member and connection generation required for scene delivery')
        previous=self._scene_deliveries.get(request_id)
        if previous is not None:
            if previous.location!=expected or previous.connection_generation!=connection_generation:
                raise ValueError('Scene delivery identity conflict')
            return previous
        if len(self._scene_deliveries)>=self._scene_delivery_capacity:
            raise ValueError('Scene delivery capacity')
        ticket=SceneDeliveryTicket(self.address,self._generation,expected,connection_generation,request_id,uuid4().hex)
        self._scene_deliveries[request_id]=ticket
        self._invalidate_idle()
        return ticket

    def finish_scene_delivery(self,ticket):
        """Release exactly this owner generation's pending send/cancel token."""
        if (type(ticket) is not SceneDeliveryTicket or ticket.address!=self.address
                or ticket.owner_generation!=self._generation or not self._delivery_location(ticket.location)
                or type(ticket.connection_generation) is not int or not 0<ticket.connection_generation<2**63
                or type(ticket.delivery_id) is not str or not 1<=len(ticket.delivery_id)<=128
                or type(ticket.request_id) is not str or not 1<=len(ticket.request_id)<=128):
            raise ValueError('Foreign or malformed scene delivery confirmation')
        previous=self._scene_deliveries.get(ticket.request_id)
        if previous is None:return False
        if previous!=ticket:raise ValueError('Stale scene delivery confirmation')
        del self._scene_deliveries[ticket.request_id]
        self._invalidate_idle()
        return True

    def mark_actor_mutation(self):
        """Fence unload after dynamic actor changes; durable cold restore is pending.

        Adapter must durably record dynamic state before permitting any cold
        reconstruction. There is deliberately no in-memory 'pristine' reset.
        """
        if not self._lifecycle_enabled or self._retired:
            raise ValueError('Actor mutation requires a live lifecycle-enabled map')
        self._actors_pristine=False
        self._invalidate_idle()

    def _lifecycle_snapshot(self,now_ms):
        if type(now_ms) is not int or now_ms<self._lifecycle_clock or now_ms<0:
            raise ValueError('Monotonic trusted lifecycle clock required')
        self._lifecycle_clock=now_ms
        counts=(len(self._roles),len(self._incoming),len(self._departures),len(self._offers),
            self._mailbox.qsize(),len(self._scene_deliveries))
        if not self._lifecycle_enabled or not self._actors_pristine or any(counts) or self._relocations:
            self._idle_since_ms=None
        elif self._idle_since_ms is None:
            self._idle_since_ms=now_ms
        return MapIdleSnapshot(self.address,self._generation,self._lifecycle_revision,
            self._lifecycle_enabled,self._retired,self._actors_pristine,*counts,self._idle_since_ms,
            len(self._relocations))

    def inspect_lifecycle(self,now_ms):
        """Owner-executor snapshot; first empty observation starts a safe timer."""
        with self._submission_gate:return self._lifecycle_snapshot(now_ms)

    def retire_idle(self,expected,now_ms,*,minimum_idle_ms):
        """Seal empty state on this executor against concurrent producer enqueue.

        Caller first fences new cross-owner operations in its projection pool;
        remove the projection only after this immutable receipt. No storage,
        transport or gameplay runs under the narrow per-map enqueue gate.
        """
        if type(minimum_idle_ms) is not int or minimum_idle_ms<1:
            raise ValueError('Explicit positive idle budget required')
        with self._submission_gate:
            current=self._lifecycle_snapshot(now_ms)
            if (type(expected) is not MapIdleSnapshot or current!=expected or not current.idle
                    or now_ms-current.idle_since_ms<minimum_idle_ms):
                raise ValueError('Map is busy, stale, retired or not idle long enough')
            self._retired=True
            self._lifecycle_revision+=1
            return MapRetired(self.address,self._generation,self._lifecycle_revision,current.idle_since_ms,now_ms)

    def location(self, role_id):
        return self._roles.get(role_id)

    def inspect_transfer(self,role_id,transfer_id):
        """Owner-executor snapshot, including a prepared target's exact instance."""
        if (type(role_id) is not int or role_id<1 or type(transfer_id) is not str
                or not 1<=len(transfer_id)<=128):
            raise ValueError('Explicit recovery role/transfer identity required')
        return MapTransferSnapshot(self.address,self._generation,role_id,transfer_id,
            self.location(role_id),self._offers.get(role_id),self._incoming.get(transfer_id),
            self._departures.get(transfer_id))

    def retire_recovered_transfer(self,expected,decision):
        """Retire only a fenced old lease after the NEW lease's DB decision.

        Caller must commit that decision first, execute on each exact map key,
        clear old-epoch adapter caches and finish all retirements before join.
        This never activates or writes a position; new join uses durable state.
        """
        return self._retire_recovered_transfer(expected,decision,None)[0]

    def retire_recovered_transfer_with_view(self,expected,decision,view):
        """Retire the same old lease from authority and its subordinate view."""
        self._view(view)
        return self._retire_recovered_transfer(expected,decision,view)

    def _retire_recovered_transfer(self,expected,decision,view):
        self._paired_members(view)
        if (type(expected) is not MapTransferSnapshot or type(decision) is not TransferRecoveryDecision
                or type(decision.source) is not Location or type(decision.source.address) is not MapAddress
                or expected.address!=self.address or expected.owner_generation!=self._generation
                or expected.role_id!=decision.source.role_id or expected.transfer_id!=decision.transfer_id
                or not ((type(decision.new_epoch) is int and decision.new_epoch>0)
                    or (type(decision.new_epoch) is str and 1<=len(decision.new_epoch)<=128))
                or str(decision.new_epoch)==str(decision.source.login_epoch)
                or type(decision.committed) is not bool
                or type(decision.authority_version) is not int or decision.authority_version<1
                or any(type(p) is not tuple or len(p)!=3 or any(type(v) is not int for v in p)
                       for p in (decision.target_position,decision.authority_position))):
            raise ValueError('Fenced new-lease recovery decision required')
        source=decision.source
        def match(offer):
            return (type(offer) is TransferOffer and offer.transfer_id==decision.transfer_id
                and offer.source==source and offer.target_position==decision.target_position
                and (decision.offer is None or decision.offer==offer))
        target_address=None
        def record(value):
            if value is None:return
            nonlocal target_address
            if type(value) is Reservation:reservation=value
            elif type(value) is FrozenTransfer:reservation=value.reservation
            elif type(value) is TransferCommit:reservation=value.frozen.reservation
            elif type(value) is TransferCancelled:reservation=value.reservation
            elif type(value) is TransferResumed:reservation=value.cancellation.reservation
            else:raise ValueError('Unknown transfer recovery record')
            if not match(reservation.offer) or (target_address is not None and target_address!=reservation.target):
                raise ValueError('Foreign transfer recovery record')
            target_address=reservation.target
        if decision.committed:
            if type(decision.receipt) is not TransferCommit:
                raise ValueError('Committed recovery requires durable target receipt')
            record(decision.receipt)
        elif decision.receipt is not None:
            raise ValueError('Uncommitted recovery must preserve durable source')
        record(expected.incoming)
        record(expected.departure)
        if expected.offer is not None and not match(expected.offer):
            raise ValueError('Another source transfer is pending')
        if self.address!=source.address and self.address!=target_address:
            raise ValueError('Recovery is for another map instance')
        if (expected.location is not None and (expected.location.role_id!=source.role_id
                or str(expected.location.login_epoch)!=str(source.login_epoch))):
            raise ValueError('Recovery cannot retire a replacement login')
        current=self.inspect_transfer(expected.role_id,expected.transfer_id)
        empty=all(v is None for v in (current.location,current.offer,current.incoming,current.departure))
        if current!=expected and not empty:
            raise ValueError('Stale map recovery snapshot')
        presence=view.snapshot(expected.role_id) if view is not None else None
        if presence is not None and str(presence.location.login_epoch)!=str(source.login_epoch):
            raise ValueError('Recovery cannot retire a replacement player projection')
        change=None
        if view is not None:
            from world_roles import RoleSceneChange
            change=view.leave(presence) if presence is not None else RoleSceneChange(None,())
        removed=self._roles.pop(expected.role_id,None)
        if removed is not None:self._detach_relocations(removed)
        self._memberships.pop(expected.role_id,None)
        self._offers.pop(expected.role_id,None)
        self._incoming.pop(expected.transfer_id,None)
        self._departures.pop(expected.transfer_id,None)
        return MapTransferRetired(self.address,expected.role_id,source.login_epoch,
            expected.transfer_id,target_address,removed),change

    def join(self, location):
        return self._join(location,None,None)[0]

    def join_with_view(self,location,appearance,view):
        """Validate both memberships before publishing either on this executor."""
        self._view(view)
        return self._join(location,view,appearance)

    def _join(self, location, view, appearance):
        self._paired_members(view)
        # The role owner validates the login lease before issuing join. This map
        # does not authenticate client-supplied role IDs or replace other leases.
        if (self._retired or location.address != self.address or location.state != 'active'
                or min(location.role_id, location.version) < 1
                or not ((type(location.login_epoch) is int and location.login_epoch > 0)
                        or (type(location.login_epoch) is str and 1 <= len(location.login_epoch) <= 128))
                or not valid_position(location.position, self.catalog)):
            raise ValueError('Invalid map membership')
        existing = self.location(location.role_id)
        if existing == location:
            change=view.join(location,appearance) if view is not None else None
            return existing,change
        if existing is not None:
            raise ValueError('Role already in map')
        if any(isinstance(r, Reservation) and r.offer.source.role_id == location.role_id
               for r in self._incoming.values()):
            raise ValueError('Role reserved for transfer')
        if any(type(r) is RelocationPrepared and r.offer.source.role_id==location.role_id
               for r in self._relocations.values()):
            raise ValueError('Role awaits relocation recovery')
        if len(self._roles) + self._reserved_slots() >= self.capacity:
            raise ValueError('Map capacity')
        change=view.join(location,appearance) if view is not None else None
        self._invalidate_idle()
        self._roles[location.role_id] = location
        self._memberships[location.role_id]=uuid4().hex
        return location,change

    def _reserved_slots(self):
        return sum(isinstance(value, Reservation) for value in self._incoming.values())

    def leave(self, expected):
        """Role-owner release after its required checkpoint has committed.

        Frozen/loading handoffs must resolve before ordinary disconnect cleanup.
        A stale disconnect cannot release the replacement login's membership.
        """
        return self._leave(expected,None)[0]

    def leave_with_view(self,expected,view):
        """Release both memberships after the required role checkpoint commit."""
        self._view(view)
        return self._leave(expected,view)

    def _leave(self,expected,view):
        self._paired_members(view)
        current = self.location(expected.role_id)
        presence=view.snapshot(expected.role_id) if view is not None else None
        if current is None:
            if presence is not None:
                raise ValueError('Player projection remains without map membership')
            if view is None:
                return None,None
            from world_roles import RoleSceneChange
            return None,RoleSceneChange(None,())
        if current != expected or current.state != 'active':
            raise ValueError('Stale or unresolved map departure')
        if view is not None and (presence is None or presence.location!=current):
            raise ValueError('Player projection location mismatch')
        change=view.leave(presence) if view is not None else None
        self._detach_relocations(current)
        del self._roles[expected.role_id]
        self._memberships.pop(expected.role_id,None)
        self._offers.pop(expected.role_id, None)
        return current,change

    def _guard(self, command, now_ms):
        if self._retired:return 'owner_retired'
        if not command.request_id or len(command.request_id) > 128 or not isinstance(command.body, bytes):
            return 'invalid_envelope'
        if now_ms >= command.deadline_ms:
            return 'deadline'
        expected = command.expected
        if expected.address != self.address:
            return 'wrong_map_owner'
        current = self.location(expected.role_id)
        if current is None:
            return 'not_in_map'
        if current.login_epoch != expected.login_epoch:
            return 'stale_epoch'
        if current.version != expected.version or current != expected:
            return 'stale_position'
        if current.state != 'active':
            return 'movement_frozen'
        return ''

    def submit(self, command, now_ms):
        # Producers touch only this bounded inbox and immutable routing data.
        # Authoritative state is checked again by the owner's serial executor.
        if (not command.request_id or len(command.request_id) > 128
                or not isinstance(command.body, bytes)):
            return 'invalid_envelope'
        if now_ms >= command.deadline_ms:
            return 'deadline'
        if command.expected.address != self.address:
            return 'wrong_map_owner'
        with self._submission_gate:
            if self._retired:return 'owner_retired'
            try:
                self._mailbox.put_nowait(command)
            except Full:
                return 'backpressure'
            self._invalidate_idle()
            return 'accepted'

    def process_one(self, now_ms):
        """Called only by this partition's serial executor; never waits."""
        self._paired_members(None)
        try:
            command = self._mailbox.get_nowait()
        except Empty:
            return None
        return self.move(command, now_ms)

    def process_one_with_view(self,now_ms,view):
        """Dequeue on this map executor, then validate and publish both states.

        Empty inbox returns None; a dequeued command returns the same tuple as
        move_with_view, including a rejection if its version/deadline expired
        while queued. A foreign view is refused before consuming any command.
        """
        self._view(view)
        try:
            command=self._mailbox.get_nowait()
        except Empty:
            return None
        return self.move_with_view(command,now_ms,view)

    def move(self, command, now_ms):
        return self._move(command,now_ms,None)[0]

    def member_projection(self,*,role_capacity):
        """Install one metadata projection on this actual domain lifetime.

        Construct before active membership/handoffs. Repeating the same startup
        configuration is idempotent; replacing the projection is not supported.
        """
        if self._retired or type(role_capacity) is not int or role_capacity<1:
            raise ValueError('Live owner and explicit member capacity required')
        if self._member_projection is not None:
            if self._member_projection.role_capacity!=role_capacity:
                raise ValueError('Member projection capacity already fixed')
            return self._member_projection
        if self._roles or self._offers or self._incoming or self._departures or self._scene_deliveries or self._relocations:
            raise ValueError('Member projection requires an empty owner')
        from world_roles import RoleScene
        projection=RoleScene.membership_only(self.address,self.catalog,role_capacity=role_capacity,
            owner_generation=self._generation)
        self._member_projection=projection
        return projection

    def _paired_members(self,view):
        if self._member_projection is not None and view is not self._member_projection:
            raise ValueError('Use this owner\'s paired member projection')

    def _view(self,view):
        # The projection is a subordinate of THIS map executor. Never pass a
        # mutable projection belonging to a separate owner or worker thread.
        from world_roles import RoleScene
        if type(view) is not RoleScene or view.address!=self.address:
            raise ValueError('Player projection must belong to the same map instance')
        self._paired_members(view)
        if view.metadata_only and view is not self._member_projection:
            raise ValueError('Member projection belongs to a different owner lifetime')

    def _role_presence(self,expected,view):
        self._view(view)
        if view is not self._member_projection:
            raise ValueError('Domain-owned member projection required')
        from world_roles import RolePresence
        if type(expected) is not RolePresence or type(expected.location) is not Location:
            raise ValueError('Captured player presence required')
        location=expected.location
        if (type(location.address) is not MapAddress
                or any(type(v) is not int for v in (location.address.map_id,location.address.instance_id,
                    location.address.partition_id,location.role_id,location.version,location.x,location.y))
                or type(expected.owner_generation) is not str
                or type(expected.revision) is not int or type(expected.membership_revision) is not int):
            raise ValueError('Exact typed player membership required')
        current=self.location(location.role_id)
        if (location.address!=self.address or location.state!='active' or current!=location
                or type(location.login_epoch) is not type(current.login_epoch)
                or view.snapshot(location.role_id)!=expected):
            raise ValueError('Stale or inactive player membership')
        return expected

    def role_binding(self,expected,view,connection_generation):
        """Issue identity only from a captured, still-current active presence.

        Run on this map executor; the role router authenticates the supplied
        connection generation. This is not NPC permission or a send ACK.
        """
        from world_role_delivery import bind_role_view
        return bind_role_view(self._role_presence(expected,view),connection_generation)

    def fence_role_binding(self,expected,view):
        """Revoke a captured member identity without changing its location.

        Only the explicit membership-only projection supports this operation;
        full AOI requires its own ordered delivery/rebuild lifecycle.
        """
        return view.fence_binding(self._role_presence(expected,view))

    def move_with_view(self,command,now_ms,view):
        """Return (MoveResult, RoleSceneChange|None) from one map command.

        Both checks and original encoding finish before authority is published.
        A rejected view leaves position, pending offer, links and sequences
        unchanged. Caller sends/persists only after this synchronous return.
        This is in-memory command atomicity, not a storage/network transaction.
        """
        self._view(view)
        return self._move(command,now_ms,view)

    def _move(self, command, now_ms, view):
        self._paired_members(view)
        rejection = self._guard(command, now_ms)
        if rejection:
            return MoveResult(rejection=rejection),None
        current = command.expected
        presence=view.snapshot(current.role_id) if view is not None else None
        if view is not None and (presence is None or presence.location!=current):
            return MoveResult(rejection='Player projection location mismatch'),None
        try:
            plan = plan_movement(current.position, (current.x//16, current.y//16),
                                 command.kind, command.body, self.catalog,
                                 maze=self.maze, movement_state=command.movement_state,
                                 collision_points=command.collision_points)
        except ValueError as error:
            return MoveResult(rejection=str(error)),None
        if not plan.checkpoint:
            return MoveResult(location=current),None
        # A destination in plan.position is still a proposal. Source movement
        # confirms only the reported source point until a transfer is committed.
        location = replace(current, version=current.version+1,
                           x=plan.reported[1], y=plan.reported[2])
        offer = None
        if plan.transfer_target:
            offer = TransferOffer(command.request_id, location, plan.transfer_target, command.deadline_ms)
        result=MoveResult(location=location, checkpoint=location, offer=offer)
        try:
            change=view.move(presence,location) if view is not None else None
        except ValueError as error:
            return MoveResult(rejection=str(error)),None
        # No await/callback/I/O between the accepted projection and authority.
        self._roles[location.role_id] = location
        self._offers.pop(location.role_id, None)
        if offer is not None:
            self._offers[location.role_id] = offer
        return result,change

    def inspect_relocation(self,role_id,request_id,*,view=None):
        """Capture this role's actual relation, operation and paired projection.

        Read only on the map executor. Empty projections retain a lifecycle
        identity, so an asynchronous recovery cannot silently drop its view.
        """
        self._paired_members(view)
        if view is not None:self._view(view)
        if (type(role_id) is not int or not 0<role_id<2**63
                or type(request_id) is not str or not 1<=len(request_id)<=128):
            raise ValueError('Explicit relocation role/request identity required')
        location=self.location(role_id)
        membership=self._memberships.get(role_id)
        if ((location is None)!=(membership is None)
                or (membership is not None and (type(membership) is not str or not membership))):
            raise ValueError('Map relation identity and membership disagree')
        value=self._relocations.get(request_id)
        detached=type(value) is _DetachedRelocation
        if detached:value=value.receipt
        if type(value) is RelocationPrepared:
            prepared,result=value,None
        elif type(value) in (RelocationCommit,RelocationCancelled):
            prepared,result=value.prepared,value
        elif value is None:
            prepared=result=None
        else:
            raise ValueError('Unknown relocation state')
        if prepared is not None:
            self._relocation_proof(prepared,allow_retired=True)
            if prepared.offer.source.role_id!=role_id:
                raise ValueError('Relocation belongs to another role')
        return MapRelocationSnapshot(self.address,self._generation,role_id,request_id,
            location,membership,prepared,result,detached,self._offers.get(role_id),
            view.owner_generation if view is not None else None,
            view.snapshot(role_id) if view is not None else None)

    def inspect_relocations(self,role_id,*,view=None):
        """Bounded enumeration for freeze-before-journal recovery discovery."""
        self._paired_members(view)
        if view is not None:self._view(view)
        if type(role_id) is not int or not 0<role_id<2**63:
            raise ValueError('Explicit relocation role identity required')
        keys=[]
        for key,value in self._relocations.items():
            if type(value) is _DetachedRelocation:value=value.receipt
            prepared=value if type(value) is RelocationPrepared else value.prepared
            if prepared.offer.source.role_id==role_id:keys.append(key)
        return tuple(self.inspect_relocation(role_id,key,view=view) for key in sorted(keys))

    def retire_recovered_relocation(self,expected,decision,*,view=None):
        """Retire ONLY captured old-lease state after the new SQL decision commits.

        This never joins or publishes the immutable current authority. Caller
        fences old writers first, commits SQL recovery, and rechecks its own
        connection/flow before joining the current checkpoint. Other transfers
        must resolve separately. Already empty exact-owner retries are inert.
        """
        self._paired_members(view)
        if view is not None:self._view(view)
        if type(decision) is not RelocationRecoveryDecision or type(decision.committed) is not bool:
            raise ValueError('Committed new-lease relocation decision required')
        offer=self._relocation_proof(decision.prepared,allow_retired=True)
        authority=decision.authority
        if (not self._delivery_location(authority) or authority.role_id!=offer.source.role_id
                or authority.state!='active' or not valid_position(authority.position,self.catalog)
                or str(authority.login_epoch)==str(offer.source.login_epoch)
                or authority.version<decision.prepared.target.version):
            raise ValueError('Fenced new lease and current durable authority required')
        endpoint=decision.prepared.target if decision.committed else offer.source
        if (authority.version==decision.prepared.target.version
                and (authority.position!=endpoint.position or authority.address!=endpoint.address)):
            raise ValueError('Relocation outcome and current authority disagree')
        if (type(expected) is not MapRelocationSnapshot or type(expected.role_id) is not int
                or expected.role_id!=offer.source.role_id or expected.address!=self.address
                or type(expected.address) is not MapAddress
                or any(type(v) is not int for v in (expected.address.map_id,
                    expected.address.instance_id,expected.address.partition_id))
                or type(expected.owner_generation) is not str or expected.owner_generation!=self._generation
                or type(expected.request_id) is not str or expected.request_id!=offer.transfer_id
                or type(expected.detached) is not bool
                or (expected.membership_id is not None and (type(expected.membership_id) is not str
                    or not 1<=len(expected.membership_id)<=128))
                or (expected.projection_generation is not None and (type(expected.projection_generation) is not str
                    or not 1<=len(expected.projection_generation)<=128))):
            raise ValueError('Exact old-owner relocation snapshot required')
        if expected.location is not None:
            if (not self._delivery_location(expected.location)
                    or expected.location.address!=self.address or expected.location.role_id!=expected.role_id
                    or type(expected.location.login_epoch) is not type(offer.source.login_epoch)
                    or expected.location.login_epoch!=offer.source.login_epoch):
                raise ValueError('Recovery cannot retire a replacement login')
        if expected.prepared is not None:
            self._relocation_proof(expected.prepared,allow_retired=True)
            if expected.prepared!=decision.prepared:
                raise ValueError('Recovery cannot retire another preparation')
        if expected.result is not None:
            if (type(expected.result) not in (RelocationCommit,RelocationCancelled)
                    or not self._delivery_location(expected.result.location)
                    or expected.result.prepared!=decision.prepared):
                raise ValueError('Recovery terminal snapshot conflict')
            self._relocation_proof(expected.result.prepared,allow_retired=True)
        if expected.offer is not None:
            self._relocation_proof(replace(decision.prepared,offer=expected.offer),allow_retired=True)
        if expected.presence is not None:
            from world_roles import RolePresence
            presence=expected.presence
            if (type(presence) is not RolePresence or not self._delivery_location(presence.location)
                    or presence.location.role_id!=expected.role_id or presence.location.address!=self.address
                    or type(presence.location.login_epoch) is not type(offer.source.login_epoch)
                    or presence.location.login_epoch!=offer.source.login_epoch
                    or type(presence.revision) is not int or type(presence.membership_revision) is not int
                    or presence.revision<1 or presence.membership_revision<1
                    or type(presence.owner_generation) is not str
                    or presence.owner_generation!=expected.projection_generation):
                raise ValueError('Recovery cannot retire a replacement projection')
        current=self.inspect_relocation(expected.role_id,expected.request_id,view=view)
        if current.projection_generation!=expected.projection_generation:
            raise ValueError('Relocation recovery projection lifetime changed')
        empty=(current.location is None and current.membership_id is None
            and current.prepared is None and current.result is None and current.offer is None
            and current.presence is None)
        if current!=expected and not empty:
            raise ValueError('Stale relocation recovery snapshot')
        if empty:
            change=None
            if view is not None:
                from world_roles import RoleSceneChange
                change=RoleSceneChange(None,())
            return MapRelocationRetired(self.address,self._generation,decision.prepared,
                authority,None,False),change
        if current.offer is not None and current.offer!=offer:
            raise ValueError('Another source operation needs recovery first')
        if (any(type(r) is RelocationPrepared and key!=expected.request_id
                and r.offer.source.role_id==expected.role_id for key,r in self._relocations.items())
                or any(type(r) is Reservation and r.offer.source.role_id==expected.role_id
                    for r in self._incoming.values())
                or any(type(r) is FrozenTransfer and r.source.role_id==expected.role_id
                    for r in self._departures.values())):
            raise ValueError('Another pending transfer needs its own recovery')
        change=view.leave(current.presence) if view is not None and current.presence is not None else None
        if view is not None and change is None:
            from world_roles import RoleSceneChange
            change=RoleSceneChange(None,())
        removed=self._roles.pop(expected.role_id,None)
        self._memberships.pop(expected.role_id,None)
        if removed is not None:self._detach_relocations(removed)
        if self._offers.get(expected.role_id)==offer:self._offers.pop(expected.role_id)
        record_removed=self._relocations.pop(expected.request_id,None) is not None
        self._invalidate_idle()
        return MapRelocationRetired(self.address,self._generation,decision.prepared,
            authority,removed,record_removed),change

    def _detach_relocations(self,departed):
        # A later equal Location is a different membership. Keep terminal
        # receipts bounded/retirable, but never executable for that member.
        for key,record in self._relocations.items():
            if type(record) in (RelocationCommit,RelocationCancelled):
                source=record.prepared.offer.source
                if (source.role_id==departed.role_id
                        and type(source.login_epoch) is type(departed.login_epoch)
                        and source.login_epoch==departed.login_epoch):
                    self._relocations[key]=_DetachedRelocation(record)

    def freeze_relocation(self,offer,now_ms,*,movement_state,view=None):
        """Freeze a registered, separately authorized same-instance offer.

        Role-owner policy authorizes this operation; ordinary move never calls
        it automatically. Coordinates keep their original offer meaning. No
        housing interpretation, durable commit, loading ACK or packet is made.
        Run on this map executor; commit/cancel must follow the role's durable
        decision. A pending relocation retains the sole frozen source member.
        """
        self._paired_members(view)
        if view is not None:self._view(view)
        if (self._retired or self.maze is None or type(offer) is not TransferOffer
                or not self._delivery_location(offer.source) or offer.source.state!='active'
                or offer.source.address!=self.address or offer.source.version>=2**63-3
                or type(offer.transfer_id) is not str or not 1<=len(offer.transfer_id)<=128
                or type(offer.deadline_ms) is not int or offer.deadline_ms<0
                or type(now_ms) is not int or now_ms<0
                or type(offer.target_position) is not tuple or len(offer.target_position)!=3
                or any(type(v) is not int for v in offer.target_position)
                or offer.target_position[0]!=self.address.map_id
                or not valid_position(offer.source.position,self.catalog)
                or not valid_position(offer.target_position,self.catalog)):
            raise ValueError('Exact original same-instance offer and maze required')
        from world_collision import character_movement_mask,maze_clear
        mask=character_movement_mask(movement_state)
        previous=self._relocations.get(offer.transfer_id)
        if previous is not None:
            if (type(previous) is RelocationPrepared and previous.offer==offer
                    and previous.movement_state==movement_state
                    and self.location(offer.source.role_id)==previous.frozen):
                return previous
            raise ValueError('Relocation identity already used')
        if (now_ms>=offer.deadline_ms or self.location(offer.source.role_id)!=offer.source
                or self._offers.get(offer.source.role_id)!=offer):
            raise ValueError('Stale or expired relocation offer')
        if len(self._relocations)>=self.transfer_capacity:
            raise ValueError('Relocation receipt capacity')
        if not all(maze_clear(self.maze,*point,mask=mask)
                   for point in ((offer.source.x,offer.source.y),offer.target_position[1:])):
            raise ValueError('Relocation source or target is blocked')
        presence=view.snapshot(offer.source.role_id) if view is not None else None
        if view is not None and (presence is None or presence.location!=offer.source):
            raise ValueError('Relocation member projection mismatch')
        frozen=replace(offer.source,version=offer.source.version+1,state='frozen')
        target=replace(frozen,version=frozen.version+1,x=offer.target_position[1],
            y=offer.target_position[2],state='loading')
        prepared=RelocationPrepared(self._generation,uuid4().hex,offer,frozen,target,movement_state)
        # Complete all fallible validation before superseding a member permit.
        if view is not None and view.metadata_only:view.fence_binding(presence)
        self._roles[offer.source.role_id]=frozen
        self._relocations[offer.transfer_id]=prepared
        self._invalidate_idle()
        return prepared

    def _relocation_proof(self,prepared,*,allow_retired=False):
        if (type(prepared) is not RelocationPrepared or (self._retired and not allow_retired)
                or type(prepared.owner_generation) is not str
                or prepared.owner_generation!=self._generation
                or type(prepared.preparation_id) is not str or not 1<=len(prepared.preparation_id)<=128
                or type(prepared.offer) is not TransferOffer
                or type(prepared.movement_state) is not int or not 0<=prepared.movement_state<=255
                or not all(self._delivery_location(p) for p in
                    (prepared.offer.source,prepared.frozen,prepared.target))):
            raise ValueError('Current owner relocation proof required')
        offer=prepared.offer
        if (offer.source.address!=self.address or offer.source.state!='active'
                or offer.source.version>=2**63-3
                or not valid_position(offer.source.position,self.catalog)
                or type(offer.transfer_id) is not str or not 1<=len(offer.transfer_id)<=128
                or type(offer.deadline_ms) is not int or offer.deadline_ms<0
                or type(offer.target_position) is not tuple or len(offer.target_position)!=3
                or any(type(v) is not int for v in offer.target_position)
                or offer.target_position[0]!=self.address.map_id
                or prepared.frozen!=replace(offer.source,version=offer.source.version+1,state='frozen')
                or prepared.target!=replace(prepared.frozen,version=offer.source.version+2,
                    x=offer.target_position[1],y=offer.target_position[2],state='loading')
                or not valid_position(prepared.target.position,self.catalog)):
            raise ValueError('Relocation proof topology mismatch')
        return offer

    def commit_relocation(self,prepared,*,view=None):
        """Publish loading target only AFTER the caller durably commits it.

        The caller's role transaction owns the durable decision; this is not a
        storage ACK. Expiry cannot roll back a committed target. A new exact
        scene delivery and existing ready/ready_with_view release loading.
        """
        self._paired_members(view)
        if view is not None:self._view(view)
        offer=self._relocation_proof(prepared)
        previous=self._relocations.get(offer.transfer_id)
        current=self.location(offer.source.role_id)
        if type(previous) is RelocationCommit and previous.prepared==prepared:
            ready=replace(previous.location,version=previous.location.version+1,state='active')
            if current not in (previous.location,ready):
                raise ValueError('Relocation retry cannot rewind a later membership')
            presence=view.snapshot(offer.source.role_id) if view is not None else None
            if view is not None and ((current.state=='loading' and presence is not None)
                    or (current.state=='active' and (presence is None or presence.location!=current))):
                raise ValueError('Relocation retry projection mismatch')
            if view is None:return previous,None
            from world_roles import RoleSceneChange
            return previous,RoleSceneChange(presence,())
        if previous!=prepared or current!=prepared.frozen:
            raise ValueError('Relocation no longer pending at its frozen source')
        presence=view.snapshot(offer.source.role_id) if view is not None else None
        if view is not None and (presence is None or presence.location!=offer.source):
            raise ValueError('Relocation source projection mismatch')
        receipt=RelocationCommit(prepared,prepared.target)
        change=view.leave(presence) if view is not None else None
        self._detach_relocations(offer.source)
        self._roles[offer.source.role_id]=receipt.location
        self._memberships[offer.source.role_id]=uuid4().hex
        self._offers.pop(offer.source.role_id,None)
        self._relocations[offer.transfer_id]=receipt
        self._invalidate_idle()
        return receipt,change

    def cancel_relocation(self,prepared,*,view=None):
        """Restore the source after the caller confirms NO durable target.

        A timeout alone is not that confirmation. A committed in-memory target
        cannot cancel. The caller checkpoints the returned source version and
        rebuilds its exact movement declaration before admitting new inputs.
        """
        self._paired_members(view)
        if view is not None:self._view(view)
        offer=self._relocation_proof(prepared)
        previous=self._relocations.get(offer.transfer_id)
        current=self.location(offer.source.role_id)
        presence=view.snapshot(offer.source.role_id) if view is not None else None
        if type(previous) is RelocationCancelled and previous.prepared==prepared:
            if (current!=previous.location or (view is not None
                    and (presence is None or presence.location!=current))):
                raise ValueError('Relocation cancel retry cannot rewind a later membership')
            if view is None:return previous,None
            from world_roles import RoleSceneChange
            return previous,RoleSceneChange(presence,())
        if previous!=prepared or current!=prepared.frozen:
            raise ValueError('Relocation absent or already committed')
        if view is not None and (presence is None or presence.location!=offer.source):
            raise ValueError('Relocation source projection mismatch')
        restored=replace(prepared.frozen,state='active',version=prepared.frozen.version+1)
        cancelled=RelocationCancelled(prepared,restored)
        change=view.move(presence,restored) if view is not None else None
        self._roles[offer.source.role_id]=restored
        self._offers.pop(offer.source.role_id,None)
        self._relocations[offer.transfer_id]=cancelled
        self._invalidate_idle()
        return cancelled,change

    def retire_relocation(self,receipt):
        """Release only a terminal decision after durable replay is retained.

        Caller retains its durable decision/outbox before release. Pending
        freezes cannot disappear through this operation; ordinary membership
        and loading activation are unchanged. Exact repeated release is inert.
        """
        if type(receipt) not in (RelocationCommit,RelocationCancelled):
            raise ValueError('Completed relocation receipt required')
        offer=self._relocation_proof(receipt.prepared,allow_retired=True)
        expected=(receipt.prepared.target if type(receipt) is RelocationCommit else
            replace(receipt.prepared.frozen,version=receipt.prepared.frozen.version+1,state='active'))
        if not self._delivery_location(receipt.location) or receipt.location!=expected:
            raise ValueError('Relocation terminal receipt mismatch')
        previous=self._relocations.get(offer.transfer_id)
        if previous is None:return False
        if type(previous) is _DetachedRelocation:previous=previous.receipt
        if previous!=receipt:
            raise ValueError('Relocation decision is pending or different')
        del self._relocations[offer.transfer_id]
        self._invalidate_idle()
        return True

    def prepare_transfer(self, expected, target_position, *, request_id, deadline_ms, now_ms):
        """Register a trusted cross-map quest/service offer on the source owner.

        Call only on this owner's executor after the role owner authorizes the
        destination from a durable task/service continuation. Never route client
        destination fields here. The runtime journals/replays the same request
        ID and uses reserve/freeze/activate/finalize/ready unchanged; this method
        does not commit tasks, move/freeze a role, or acknowledge client loading.
        Same-map warps need a separate explicit policy and are rejected here.
        """
        if (type(request_id) is not str or not 1 <= len(request_id) <= 128
                or now_ms >= deadline_ms):
            raise ValueError('Invalid or expired scripted transfer')
        if (not isinstance(expected, Location) or expected.address != self.address
                or expected.state != 'active' or self.location(expected.role_id) != expected):
            raise ValueError('Stale scripted transfer source')
        if (type(target_position) is not tuple or len(target_position) != 3
                or any(type(v) is not int for v in target_position)
                or target_position[0] == self.address.map_id
                or not valid_position(target_position,self.catalog)):
            raise ValueError('Invalid scripted transfer target')
        offer = TransferOffer(request_id,expected,target_position,deadline_ms)
        existing = self._offers.get(expected.role_id)
        if existing is not None and existing != offer:
            raise ValueError('Another transfer offer is pending')
        self._offers[expected.role_id] = offer
        return offer

    def reserve(self, offer, now_ms):
        """Target-only reservation, consuming bounded capacity, not membership."""
        if self._retired:raise ValueError('Map owner retired')
        if now_ms >= offer.deadline_ms:
            raise ValueError('Transfer deadline')
        if (offer.target_position[0] != self.address.map_id or offer.source.address == self.address
                or not valid_position(offer.target_position, self.catalog)):
            raise ValueError('Invalid transfer target')
        existing = self._incoming.get(offer.transfer_id)
        expected = Reservation(offer, self.address)
        if isinstance(existing, TransferCancelled):
            raise ValueError('Transfer cancelled')
        if existing is not None:
            previous = existing.frozen.reservation if isinstance(existing, TransferCommit) else existing
            if previous != expected:
                raise ValueError('Transfer ID conflict')
            return previous
        if (offer.source.role_id in self._roles or any(
                isinstance(r, Reservation) and r.offer.source.role_id == offer.source.role_id
                for r in self._incoming.values())):
            raise ValueError('Target role already present or reserved')
        if len(self._incoming) >= self.transfer_capacity:
            raise ValueError('Transfer receipt capacity')
        if len(self._roles) + self._reserved_slots() >= self.capacity:
            raise ValueError('Map capacity')
        self._invalidate_idle()
        self._incoming[offer.transfer_id] = expected
        return expected

    def freeze(self, reservation, now_ms):
        """Source freezes only its still-current offer after target reservation."""
        offer = reservation.offer
        if now_ms >= offer.deadline_ms:
            raise ValueError('Transfer deadline')
        existing = self._departures.get(offer.transfer_id)
        if isinstance(existing, FrozenTransfer) and existing.reservation == reservation:
            return existing
        if existing is not None:
            raise ValueError('Transfer ID conflict')
        if (reservation.target.map_id != offer.target_position[0]
                or offer.source.address != self.address
                or self.location(offer.source.role_id) != offer.source
                or self._offers.get(offer.source.role_id) != offer):
            raise ValueError('Stale transfer offer')
        if len(self._departures) >= self.transfer_capacity:
            raise ValueError('Transfer receipt capacity')
        location = replace(offer.source, version=offer.source.version+1, state='frozen')
        frozen = FrozenTransfer(reservation, location)
        self._roles[location.role_id] = location
        self._departures[offer.transfer_id] = frozen
        return frozen

    def activate(self, frozen, now_ms):
        """Target switches to loading membership on the exact frozen proof.

        Runtime must durably journal this decision and fence the role router
        before acknowledging it or emitting a scene message. No I/O occurs here.
        """
        reservation = frozen.reservation
        offer = reservation.offer
        existing = self._incoming.get(offer.transfer_id)
        if isinstance(existing, TransferCommit):
            if existing.frozen != frozen:
                raise ValueError('Transfer ID conflict')
            return existing
        if now_ms >= offer.deadline_ms:
            raise ValueError('Transfer deadline')
        if (reservation.target != self.address or existing != reservation
                or frozen.source != replace(offer.source, version=offer.source.version+1, state='frozen')):
            raise ValueError('Invalid frozen transfer')
        if offer.source.role_id in self._roles:
            raise ValueError('Target role already present')
        _, x, y = offer.target_position
        location = replace(frozen.source, address=self.address, version=frozen.source.version+1,
                           x=x, y=y, state='loading')
        receipt = TransferCommit(frozen, location)
        self._roles[location.role_id] = location
        self._incoming[offer.transfer_id] = receipt
        self._memberships[location.role_id]=uuid4().hex
        return receipt

    def finalize(self, receipt):
        """Source cleanup after a durable target/role-router commit receipt."""
        return self._finalize(receipt,None)[0]

    def finalize_with_view(self,receipt,view):
        """After durable commit, remove the frozen source and its player view."""
        self._view(view)
        return self._finalize(receipt,view)

    def _finalize(self,receipt,view):
        self._paired_members(view)
        frozen = receipt.frozen
        offer = frozen.reservation.offer
        existing = self._departures.get(offer.transfer_id)
        if existing == receipt:
            if view is None:
                return receipt,None
            if self.location(offer.source.role_id) is not None or view.snapshot(offer.source.role_id) is not None:
                raise ValueError('Finalized source has a different current membership')
            from world_roles import RoleSceneChange
            return receipt,RoleSceneChange(None,())
        _, x, y = offer.target_position
        expected_target = replace(frozen.source, address=frozen.reservation.target,
                                  version=frozen.source.version+1, x=x, y=y, state='loading')
        if (existing != frozen or self.location(frozen.source.role_id) != frozen.source
                or receipt.location != expected_target):
            raise ValueError('Stale transfer commit')
        presence=view.snapshot(offer.source.role_id) if view is not None else None
        if view is not None and (presence is None or presence.location!=offer.source):
            raise ValueError('Player projection transfer source mismatch')
        change=view.leave(presence) if view is not None else None
        self._detach_relocations(frozen.source)
        del self._roles[frozen.source.role_id]
        self._memberships.pop(frozen.source.role_id,None)
        self._offers.pop(frozen.source.role_id, None)
        self._departures[offer.transfer_id] = receipt
        return receipt,change

    def ready(self, expected):
        """Server-validated scene-load fence; not a raw client movement signal."""
        return self._ready(expected,None,None)[0]

    def ready_with_view(self,expected,appearance,view):
        """Publish active target only when its original player entry is ready."""
        self._view(view)
        return self._ready(expected,view,appearance)

    def _ready(self,expected,view,appearance):
        self._paired_members(view)
        if self.location(expected.role_id) != expected or expected.state != 'loading':
            raise ValueError('Stale scene-ready confirmation')
        location = replace(expected, state='active', version=expected.version+1)
        change=view.join(location,appearance) if view is not None else None
        self._roles[location.role_id] = location
        return location,change

    def cancel(self, reservation):
        """Target cancels only before activation. Journal before telling source.

        Expiry alone never thaws a source: obtain this target decision first.
        """
        offer = reservation.offer
        existing = self._incoming.get(offer.transfer_id)
        cancelled = TransferCancelled(reservation)
        if existing == cancelled:
            return existing
        if reservation.target != self.address or existing != reservation:
            raise ValueError('Reservation absent or already committed')
        self._incoming[offer.transfer_id] = cancelled
        return cancelled

    def resume(self, cancellation):
        return self._resume(cancellation,None)[0]

    def resume_with_view(self,cancellation,view):
        """Keep the source view's accepted version aligned after cancellation."""
        self._view(view)
        return self._resume(cancellation,view)

    def _resume(self,cancellation,view):
        self._paired_members(view)
        reservation = cancellation.reservation
        offer = reservation.offer
        existing = self._departures.get(offer.transfer_id)
        if isinstance(existing, TransferResumed) and existing.cancellation == cancellation:
            if view is None:
                return existing.location,None
            presence=view.snapshot(offer.source.role_id)
            if (self.location(offer.source.role_id)!=existing.location
                    or presence is None or presence.location!=existing.location):
                raise ValueError('Resumed source has a different current membership')
            from world_roles import RoleSceneChange
            return existing.location,RoleSceneChange(presence,())
        if (not isinstance(existing, FrozenTransfer) or existing.reservation != reservation
                or self.location(offer.source.role_id) != existing.source):
            raise ValueError('No matching frozen transfer')
        location = replace(existing.source, state='active', version=existing.source.version+1)
        presence=view.snapshot(offer.source.role_id) if view is not None else None
        if view is not None and (presence is None or presence.location!=offer.source):
            raise ValueError('Player projection frozen source mismatch')
        change=view.move(presence,location) if view is not None else None
        self._roles[location.role_id] = location
        self._offers.pop(location.role_id, None)
        self._departures[offer.transfer_id] = TransferResumed(cancellation, location)
        return location,change

    def retire_receipt(self, receipt):
        """Release memory only after the runtime journals replay results.

        External durable inbox/outbox must answer retries after retirement.
        This module is in-memory and does not claim crash recovery.
        """
        if isinstance(receipt, TransferCommit):
            key = receipt.frozen.reservation.offer.transfer_id
            records = self._incoming if receipt.location.address == self.address else self._departures
        elif isinstance(receipt, TransferCancelled):
            key, records = receipt.reservation.offer.transfer_id, self._incoming
        elif isinstance(receipt, TransferResumed):
            key, records = receipt.cancellation.reservation.offer.transfer_id, self._departures
        else:
            raise ValueError('Only completed receipts can be retired')
        if records.get(key) != receipt:
            raise ValueError('Receipt mismatch')
        del records[key]
