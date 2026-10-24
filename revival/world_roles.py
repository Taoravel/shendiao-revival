"""Instance-owned player interest projection using the original role codec.

Run only on the owning map executor after authoritative location validation.
This is a visibility projection, never a position/lease writer. Circle radius,
capacities and batching are explicit caller policy; no production defaults.
Outputs are immutable logical deliveries for the target connection owner.
"""
from dataclasses import dataclass,replace
import struct
from uuid import uuid4
from world_catalog import valid_position
from world_owner import MapAddress,Location
from world_role_protocol import (RoleBasic,S_ADD_USER_SCREEN,S_REMOVE_USER_SCREEN,S_ROLE_MOVE,
                                 role_screen,remove_role_screen,role_move)


@dataclass(frozen=True)
class RolePresence:
    owner_generation: str
    revision: int
    location: Location
    appearance: RoleBasic | None
    membership_revision: int


@dataclass(frozen=True)
class RoleDelivery:
    address: MapAddress
    owner_generation: str
    recipient_role_id: int
    recipient_epoch: int | str
    recipient_membership_revision: int
    sequence: int
    packets: tuple


@dataclass(frozen=True)
class RoleSceneChange:
    presence: RolePresence | None
    deliveries: tuple


class RoleScene:
    def __init__(self,address,catalog,*,radius,role_capacity,pair_capacity,batch_size):
        self._initialize(address,catalog,role_capacity)
        if (type(radius) is not int or not 1 <= radius < 32768
                or type(pair_capacity) is not int or pair_capacity < 0
                or type(batch_size) is not int or not 1 <= batch_size <= 4096):
            raise ValueError('Explicit visibility radius, bounded capacities and batch size required')
        self.radius,self.pair_capacity,self.batch_size=radius,pair_capacity,batch_size

    @classmethod
    def membership_only(cls,address,catalog,*,role_capacity,owner_generation=None):
        """Track trusted map membership without appearance, AOI or wire output."""
        scene=cls.__new__(cls)
        scene._initialize(address,catalog,role_capacity)
        if owner_generation is not None:
            if type(owner_generation) is not str or not 1<=len(owner_generation)<=128:
                raise ValueError('Explicit owner generation required')
            scene._generation=owner_generation
        scene._membership_only=True
        return scene

    @property
    def metadata_only(self):
        return self._membership_only

    @property
    def owner_generation(self):
        """Immutable projection lifetime identity, including an empty scene."""
        return self._generation

    def _initialize(self,address,catalog,role_capacity):
        if (type(address) is not MapAddress
                or any(type(v) is not int or v < 1 for v in (address.map_id,address.instance_id))
                or type(address.partition_id) is not int or address.partition_id < 0
                or not catalog.get(address.map_id,{}).get('available')):
            raise ValueError('Available map instance required')
        if type(role_capacity) is not int or role_capacity < 1:
            raise ValueError('Explicit bounded role capacity required')
        self.address,self.catalog=address,catalog
        self.role_capacity=role_capacity
        self.radius=self.pair_capacity=self.batch_size=None
        self._membership_only=False
        self._roles,self._cells,self._links,self._sequences={},{},{},{}
        self._pairs,self._revision=0,0
        self._generation=uuid4().hex

    def snapshot(self,role_id):
        return self._roles.get(role_id)

    def visible_ids(self,role_id):
        return tuple(sorted(self._links.get(role_id,())))

    def _location(self,location):
        if (type(location) is not Location or location.address != self.address
                or type(location.address) is not MapAddress
                or any(type(v) is not int for v in (location.address.map_id,
                    location.address.instance_id,location.address.partition_id))
                or location.state != 'active'
                or any(type(v) is not int or not 0 < v < 2**63 for v in (location.role_id,location.version))
                or not ((type(location.login_epoch) is str and 1 <= len(location.login_epoch) <= 128)
                        or (type(location.login_epoch) is int and location.login_epoch > 0))
                or any(type(v) is not int for v in (location.x,location.y))
                or not valid_position(location.position,self.catalog)):
            raise ValueError('Invalid active role visibility location')

    def _appearance(self,location,appearance):
        if self._membership_only:
            if appearance is not None:
                raise ValueError('Membership-only projection has no appearance')
            return
        if (type(appearance) is not RoleBasic
                or (appearance.role_id,appearance.x,appearance.y)!=(location.role_id,location.x,location.y)
                or type(appearance.name) is not str
                or any(type(v) is not int for v in (appearance.role_id,appearance.x,appearance.y,
                    appearance.shape,appearance.packed_2c,appearance.field_4c,appearance.screen_flag))
                or appearance.shape < 1
                or any(type(v) is not tuple for v in (appearance.properties,appearance.octets_properties,appearance.path))):
            raise ValueError('Frozen original player appearance matching location required')
        for entries,value_type in ((appearance.properties,int),(appearance.octets_properties,bytes)):
            if any(type(p) is not tuple or len(p)!=2 or type(p[0]) is not int
                   or type(p[1]) is not value_type for p in entries):
                raise ValueError('Mutable or malformed player metadata')
        if any(type(p) is not tuple or len(p)!=2 or any(type(v) is not int for v in p) for p in appearance.path):
            raise ValueError('Frozen native role path required')
        try:
            role_screen((appearance,))
        except (TypeError,struct.error) as error:
            raise ValueError('Player appearance exceeds the original wire layout') from error

    def _cell(self,location):
        return location.x//self.radius,location.y//self.radius

    def _near(self,location):
        cx,cy=self._cell(location)
        candidates=set()
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                candidates.update(self._cells.get((cx+dx,cy+dy),()))
        candidates.discard(location.role_id)
        return {key for key in candidates if (self._roles[key].location.x-location.x)**2
                +(self._roles[key].location.y-location.y)**2 <= self.radius**2}

    def _add_packets(self,appearances):
        appearances=tuple(appearances)
        return tuple((S_ADD_USER_SCREEN,role_screen(appearances[i:i+self.batch_size]))
                     for i in range(0,len(appearances),self.batch_size))

    def _deliveries(self,packets,new_presence=None):
        results=[]
        for key,messages in sorted(packets.items()):
            if not messages:
                continue
            target=new_presence if new_presence is not None and key==new_presence.location.role_id else self._roles[key]
            results.append(RoleDelivery(self.address,self._generation,key,target.location.login_epoch,
                                        target.membership_revision,self._sequences.get(key,0)+1,tuple(messages)))
        return tuple(results)

    def _record_sequences(self,deliveries):
        for delivery in deliveries:
            self._sequences[delivery.recipient_role_id]=delivery.sequence

    def delivery_is_current(self,delivery):
        """Recipient scope only; target sender must also preserve sequence order.

        It must recheck current map membership/connection generation before
        enqueueing. Already emitted packets have no native scene epoch. This
        predicate is not a durable outbox, delivery ACK or duplicate filter.
        """
        if self._membership_only or type(delivery) is not RoleDelivery:
            return False
        current=self.snapshot(delivery.recipient_role_id)
        return bool(current and delivery.address==self.address
                    and delivery.owner_generation==self._generation
                    and delivery.recipient_epoch==current.location.login_epoch
                    and delivery.recipient_membership_revision==current.membership_revision)

    def join(self,location,appearance):
        """Project a trusted active role; retry is idempotent, replacement is explicit."""
        self._location(location)
        self._appearance(location,appearance)
        old=self.snapshot(location.role_id)
        if old is not None:
            if old.location==location and old.appearance==appearance:
                return RoleSceneChange(old,())
            raise ValueError('Role already present; old membership must leave first')
        if len(self._roles)>=self.role_capacity:
            raise ValueError('Player visibility role capacity')
        presence=RolePresence(self._generation,self._revision+1,location,appearance,self._revision+1)
        if self._membership_only:
            self._roles[location.role_id]=presence
            self._revision=presence.revision
            return RoleSceneChange(presence,())
        neighbors=self._near(location)
        if self._pairs+len(neighbors)>self.pair_capacity:
            raise ValueError('Player visibility pair capacity')
        one=((S_ADD_USER_SCREEN,role_screen((appearance,))),)
        packets={key:one for key in neighbors}
        packets[location.role_id]=self._add_packets(self._roles[k].appearance for k in sorted(neighbors))
        deliveries=self._deliveries(packets,presence)  # Complete encoding before mutation.
        self._roles[location.role_id]=presence
        self._cells.setdefault(self._cell(location),set()).add(location.role_id)
        self._links[location.role_id]=set(neighbors)
        for key in neighbors:
            self._links[key].add(location.role_id)
        self._pairs+=len(neighbors)
        self._revision=presence.revision
        self._sequences[location.role_id]=0
        self._record_sequences(deliveries)
        return RoleSceneChange(presence,deliveries)

    def _current(self,expected):
        if (type(expected) is not RolePresence or expected.owner_generation!=self._generation
                or type(expected.owner_generation) is not str
                or type(expected.revision) is not int or type(expected.membership_revision) is not int
                or type(expected.location) is not Location
                or expected.location.address!=self.address
                or self.snapshot(expected.location.role_id)!=expected):
            raise ValueError('Stale player visibility snapshot')
        self._location(expected.location)

    def fence_binding(self,expected):
        """Permanently supersede this metadata member's previous binding.

        Called by the paired map command after authoritative active-member
        validation. It creates no AOI sequence, packet or position update.
        """
        if not self._membership_only:
            raise ValueError('Binding fence requires membership-only projection')
        self._current(expected)
        presence=replace(expected,revision=self._revision+1,membership_revision=self._revision+1)
        self._roles[expected.location.role_id]=presence
        self._revision=presence.revision
        return presence

    def _remove_packets(self,role_ids):
        role_ids=tuple(role_ids)
        return tuple((S_REMOVE_USER_SCREEN,remove_role_screen(role_ids[i:i+self.batch_size]))
                     for i in range(0,len(role_ids),self.batch_size))

    def move(self,expected,location):
        """Project an accepted position; never consume raw client movement here.

        Caller preflights this on the map executor before publishing authority,
        then applies both in-memory changes without an intervening await. A
        capacity/encoding failure leaves this projection completely unchanged.
        The ordinary remote target notification is not exact-stop confirmation;
        this original client's SRoleStop handler is empty, so it is not emitted.
        """
        self._current(expected)
        self._location(location)
        old=expected.location
        if (location.role_id!=old.role_id or location.login_epoch!=old.login_epoch
                or location.version<=old.version):
            raise ValueError('Player movement requires the same lease and a newer position')
        if self._membership_only:
            presence=RolePresence(self._generation,self._revision+1,location,None,expected.membership_revision)
            self._roles[location.role_id]=presence
            self._revision=presence.revision
            return RoleSceneChange(presence,())
        neighbors=self._near(location)
        previous=self._links[old.role_id]
        entered,left=neighbors-previous,previous-neighbors
        remaining=neighbors & previous
        pair_count=self._pairs+len(entered)-len(left)
        if pair_count>self.pair_capacity:
            raise ValueError('Player visibility pair capacity')
        appearance=replace(expected.appearance,x=location.x,y=location.y,path=())
        presence=RolePresence(self._generation,self._revision+1,location,appearance,expected.membership_revision)
        added=((S_ADD_USER_SCREEN,role_screen((appearance,))),)
        removed=((S_REMOVE_USER_SCREEN,remove_role_screen((old.role_id,))),)
        moved=((S_ROLE_MOVE,role_move(old.role_id,location.x,location.y)),)
        packets={key:added for key in entered}
        packets.update({key:removed for key in left})
        packets.update({key:moved for key in remaining})
        packets[old.role_id]=(self._remove_packets(sorted(left))
            +self._add_packets(self._roles[key].appearance for key in sorted(entered)))
        deliveries=self._deliveries(packets,presence)
        # Complete all checks/encoding before changing links, buckets or presence.
        old_cell=self._cell(old)
        self._cells[old_cell].remove(old.role_id)
        if not self._cells[old_cell]:
            del self._cells[old_cell]
        self._cells.setdefault(self._cell(location),set()).add(old.role_id)
        for key in left:
            self._links[key].remove(old.role_id)
        for key in entered:
            self._links[key].add(old.role_id)
        self._links[old.role_id]=set(neighbors)
        self._roles[old.role_id]=presence
        self._pairs,self._revision=pair_count,presence.revision
        self._record_sequences(deliveries)
        return RoleSceneChange(presence,deliveries)

    def leave(self,expected):
        """After map handoff/logout, remove the old projection without aliasing reuse."""
        if (type(expected) is not RolePresence or expected.owner_generation!=self._generation
                or expected.location.address!=self.address):
            raise ValueError('Foreign player visibility departure')
        key=expected.location.role_id
        if self.snapshot(key) is None:
            return RoleSceneChange(None,())
        self._current(expected)
        if self._membership_only:
            del self._roles[key]
            self._revision+=1
            return RoleSceneChange(None,())
        neighbors=self._links[key]
        removed=((S_REMOVE_USER_SCREEN,remove_role_screen((key,))),)
        deliveries=self._deliveries({peer:removed for peer in neighbors})
        cell=self._cell(expected.location)
        self._cells[cell].remove(key)
        if not self._cells[cell]:
            del self._cells[cell]
        for peer in neighbors:
            self._links[peer].remove(key)
        self._pairs-=len(neighbors)
        del self._links[key]
        del self._roles[key]
        del self._sequences[key]
        self._revision+=1
        self._record_sequences(deliveries)
        return RoleSceneChange(None,deliveries)
