"""Target-connection-owned player view inbox, before RC4/MPPC encoding.

Only the target executor calls these methods. Trusted role/map joins install
bindings; an incoming delivery never establishes or resets a binding. This
module owns logical queue admission, never a Session, writer, or send ACK.
"""
from collections import deque
from dataclasses import dataclass
from world_owner import MapAddress,Location
from world_roles import RolePresence,RoleDelivery
from world_role_protocol import S_ADD_USER_SCREEN,S_REMOVE_USER_SCREEN,S_ROLE_MOVE


@dataclass(frozen=True)
class RoleViewBinding:
    address: MapAddress
    owner_generation: str
    role_id: int
    login_epoch: int | str
    membership_revision: int
    connection_generation: int

    def __post_init__(self):
        if (type(self.address) is not MapAddress
                or any(type(v) is not int or v<1 for v in (self.address.map_id,self.address.instance_id))
                or type(self.address.partition_id) is not int or self.address.partition_id<0
                or type(self.owner_generation) is not str or not 1<=len(self.owner_generation)<=128
                or any(type(v) is not int or not 0<v<2**63 for v in (self.role_id,self.connection_generation))
                or type(self.membership_revision) is not int or self.membership_revision<1
                or not ((type(self.login_epoch) is str and 1<=len(self.login_epoch)<=128)
                    or (type(self.login_epoch) is int and self.login_epoch>0))):
            raise ValueError('Explicit immutable player membership and connection generation required')


def bind_role_view(presence,connection_generation):
    """Called for a trusted current join, never from received packet metadata."""
    if (type(presence) is not RolePresence or type(presence.location) is not Location
            or presence.location.state!='active'):
        raise ValueError('Trusted player presence required')
    loc=presence.location
    return RoleViewBinding(loc.address,presence.owner_generation,loc.role_id,
                           loc.login_epoch,presence.membership_revision,connection_generation)


def _matches(delivery,binding):
    return (type(delivery) is RoleDelivery and delivery.address==binding.address
            and delivery.owner_generation==binding.owner_generation
            and delivery.recipient_role_id==binding.role_id
            and delivery.recipient_epoch==binding.login_epoch
            and delivery.recipient_membership_revision==binding.membership_revision)


@dataclass(frozen=True)
class RoleViewRoute:
    binding: RoleViewBinding
    delivery: RoleDelivery

    def __post_init__(self):
        if type(self.binding) is not RoleViewBinding or not _matches(self.delivery,self.binding):
            raise ValueError('Player delivery and captured target binding disagree')


def route_role_delivery(delivery,binding):
    """Capture the trusted target generation before posting to its executor."""
    return RoleViewRoute(binding,delivery)


class RoleViewInbox:
    def __init__(self,binding,*,message_capacity,byte_capacity):
        if (type(binding) is not RoleViewBinding
                or any(type(v) is not int or v<1 for v in (message_capacity,byte_capacity))):
            raise ValueError('Explicit target binding and logical queue limits required')
        self.binding=binding
        self.message_capacity,self.byte_capacity=message_capacity,byte_capacity
        self._queue=deque()
        self._failure=''
        self._last_sequence=0
        self._messages,self._bytes=0,0

    @property
    def failure(self):
        return self._failure

    @property
    def pending(self):
        """Logical packet count and sum(len(body)+10), not resident/wire bytes."""
        return self._messages,self._bytes

    def _fail(self,reason):
        self._failure=self._failure or reason
        self._queue.clear()
        self._messages,self._bytes=0,0

    def close(self):
        """Also call if the downstream connection queue cannot take a pop batch."""
        self._fail('closed')

    def _current(self,current):
        if self._failure:
            return False
        if type(current) is not RoleViewBinding or current!=self.binding:
            self._fail('binding_changed')
            return False
        return True

    def offer(self,route,*,current):
        if not self._current(current):
            return 'resync_required'
        if type(route) is not RoleViewRoute:
            self._fail('malformed_route')
            return 'resync_required'
        if route.binding!=self.binding:
            return 'stale'
        packets=route.delivery.packets
        if (type(packets) is not tuple or not packets
                or any(type(p) is not tuple or len(p)!=2 or type(p[0]) is not int
                       or p[0] not in (S_ADD_USER_SCREEN,S_REMOVE_USER_SCREEN,S_ROLE_MOVE)
                       or type(p[1]) is not bytes for p in packets)):
            self._fail('malformed_packets')
            return 'resync_required'
        sequence=route.delivery.sequence
        if type(sequence) is not int or sequence<1:
            self._fail('invalid_sequence')
            return 'resync_required'
        if sequence<=self._last_sequence:
            return 'duplicate'
        if sequence!=self._last_sequence+1:
            self._fail('sequence_gap')
            return 'resync_required'
        count,size=len(packets),sum(len(body)+10 for kind,body in packets)
        if self._messages+count>self.message_capacity or self._bytes+size>self.byte_capacity:
            self._fail('backpressure')
            return 'resync_required'
        self._queue.append((route.delivery,count,size))
        self._messages+=count
        self._bytes+=size
        self._last_sequence=sequence
        return 'accepted'

    def pop(self,*,current):
        if not self._current(current):
            return None
        if not self._queue:
            return None
        delivery,count,size=self._queue.popleft()
        self._messages-=count
        self._bytes-=size
        return delivery
