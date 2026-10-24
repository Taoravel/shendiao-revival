"""Map-owned native NPC presence, authoritative visits and scoped replay.

No scheduler, file/database I/O, Session or sends. The map owner is the sole
writer and supplies trusted commands. Scene scenery remains client-owned.
"""
from collections import OrderedDict
from dataclasses import dataclass,asdict,replace
import hashlib
import json
import struct
from types import MappingProxyType
from pathlib import Path
from inspect_client import OUT
from world_catalog import valid_position
from world_collision import maze_clear,maze_segment_result
from world_npcs import NpcPlacement,NpcInteraction
from npc_interaction import NpcInteractionRules,resolve_interaction_radius
from world_entity_protocol import (NpcBasic,npc_screen,remove_npc_screen,
    ADD_USER_SCREEN,REMOVE_USER_SCREEN,read_visit_npc)

NPC_MOVE_TO = 0xc0fd2


@dataclass(frozen=True)
class NpcLifecycleRules:
    revision: str
    binding_capacity: int
    receipt_capacity: int
    snapshot_batch_size: int
    interaction_rules: NpcInteractionRules
    initial_control_source: str
    movement_enabled: bool

    def __post_init__(self):
        budgets=(self.binding_capacity,self.receipt_capacity,self.snapshot_batch_size)
        if (self.revision!='2026-10-23.npc-lifecycle.1'
                or any(type(value) is not int for value in budgets) or budgets!=(512,4096,64)
                or type(self.interaction_rules) is not NpcInteractionRules
                or self.interaction_rules.revision!='2026-10-23.npc-interaction.2'
                or self.initial_control_source!='root-lifecycle-control:2026-10-23.npc-lifecycle.1'
                or self.movement_enabled is not False):
            raise ValueError('Explicit supported frozen NPC lifecycle startup policy required')

    @property
    def interaction_policy(self):return self.interaction_rules.revision


def load_npc_lifecycle_rules(interaction_rules,*,path=None):
    """Startup only. The source label grants no authority to submit commands.

    The trusted owning-map registration, generation and logical delivery fences
    remain the shared runtime's responsibility. No movement is activated here.
    """
    policy=json.loads((Path(path) if path is not None else OUT/'design/npc-lifecycle-v1.json')
        .read_text(encoding='utf-8'))
    if (type(policy) is not dict or 'interaction_radius' in policy
            or policy.get('interaction_policy')!='2026-10-23.npc-interaction.2'):
        raise ValueError('NPC lifecycle requires the shared cell interaction policy')
    return NpcLifecycleRules(policy.get('revision'),policy.get('binding_capacity'),
        policy.get('receipt_capacity'),policy.get('snapshot_batch_size'),interaction_rules,
        policy.get('initial_control_source'),policy.get('movement_enabled'))


def prepare(accounts,*,path=None):
    """Freeze after npc_interaction.prepare and before creating map owners."""
    rules=load_npc_lifecycle_rules(getattr(accounts,'npc_interaction_rules',None),path=path)
    accounts.npc_lifecycle_rules=rules
    return rules


def npc_move_to(entity_key,duration_ms,origin,target):
    """Original SNPCMoveTo fields; scheduling/authoritative travel is separate.

    The original handler ignores nonpositive duration and origin(0,0). The
    current server emits only representable nonnegative logical-pixel points.
    """
    if (type(entity_key) is not int or not 0<=entity_key<2**63
            or type(duration_ms) is not int or not 1<=duration_ms<2**31
            or any(type(p) is not tuple or len(p)!=2 for p in (origin,target))
            or any(type(v) is not int or not 0<=v<32768 for p in (origin,target) for v in p)
            or origin==(0,0)):
        raise ValueError('Invalid or ignored native NPC movement fields')
    return NPC_MOVE_TO,struct.pack('>qi4h',entity_key,duration_ms,*origin,*target)


@dataclass(frozen=True)
class NpcSpawn:
    entity_key: int
    npc_id: int
    x: int
    y: int


@dataclass(frozen=True)
class NpcMove:
    entity_key: int
    target: tuple
    duration_ms: int
    collision_mask: int


@dataclass(frozen=True)
class NpcMotionRules:
    revision: str
    interpolation: str
    collision: str
    max_move_batch: int
    max_path_pixels: int

    def __post_init__(self):
        if (type(self.revision) is not str or not self.revision
                or self.interpolation!='linear_rational_nearest_half_up'
                or self.collision!='native_dda_with_explicit_trusted_source_mask'
                or type(self.max_move_batch) is not int or not 1<=self.max_move_batch<=4096
                or type(self.max_path_pixels) is not int or not 1<=self.max_path_pixels<=1048576):
            raise ValueError('Explicit supported NPC motion reconstruction policy required')


def load_npc_motion_rules(path=None):
    """Startup only; loading this proposal does not enable a map by itself."""
    p=json.loads((Path(path) if path is not None else OUT/'design/npc-motion-v1.json').read_text(encoding='utf-8'))
    return NpcMotionRules(*(p[k] for k in ('revision','interpolation','collision','max_move_batch','max_path_pixels')))


@dataclass(frozen=True)
class _Motion:
    request_id: str
    origin: tuple
    target: tuple
    started_ms: int
    duration_ms: int

    @property
    def ends_ms(self):return self.started_ms+self.duration_ms

    def position(self,now_ms):
        elapsed=max(0,min(now_ms-self.started_ms,self.duration_ms))
        return tuple((2*(a*self.duration_ms+(b-a)*elapsed)+self.duration_ms)//(2*self.duration_ms)
            for a,b in zip(self.origin,self.target))


@dataclass(frozen=True)
class NpcArrival:
    event_id: str
    generation: str
    entity_key: int
    position: tuple
    arrived_at_ms: int


@dataclass(frozen=True)
class NpcLifecycleCommand:
    address: object
    generation: str
    request_id: str
    expected_revision: int
    deadline_ms: int
    operation: str
    entities: tuple
    source_ref: str


@dataclass(frozen=True)
class NpcPresence:
    entity_key: int
    placement: NpcPlacement
    source_ref: str


@dataclass(frozen=True)
class NpcControlSnapshot:
    address: object
    generation: str
    revision: int
    next_entity_key: int
    presence: tuple


@dataclass(frozen=True)
class NpcChange:
    revision: int
    replayed: bool
    entity_keys: tuple
    messages: tuple
    before: tuple = ()
    after: tuple = ()


class NpcLifecycle:
    def __init__(self,address,placements,catalog,*,generation,interaction_radius=None,
                 binding_capacity,receipt_capacity,motion_rules=None,maze=None,interaction_rules=None):
        interaction_radius=resolve_interaction_radius(interaction_rules,interaction_radius)
        if (type(generation) is not str or not 1<=len(generation)<=128
                or (interaction_radius is None and interaction_rules is None)
                or (interaction_radius is not None and (type(interaction_radius) is not int or interaction_radius<=0))
                or type(binding_capacity) is not int or not 1<=binding_capacity<=4096
                or type(receipt_capacity) is not int or not 1<=receipt_capacity<=65536):
            raise ValueError('Explicit bounded map NPC lifecycle policy required')
        if motion_rules is not None and (type(motion_rules) is not NpcMotionRules or maze is None):
            raise ValueError('NPC movement requires explicit startup rules and a preloaded maze')
        templates=tuple(p for p in placements if p.map_id==address.map_id)
        if len({p.placement_id for p in templates})!=len(templates):
            raise ValueError('Duplicate static NPC placement identity')
        self.address,self.catalog,self.generation=address,catalog,generation
        self.radius,self.capacity,self.receipt_capacity=interaction_radius,binding_capacity,receipt_capacity
        self.interaction_rules=interaction_rules
        self.templates=MappingProxyType({p.placement_id:p for p in templates})
        self._definitions=MappingProxyType({});self._entities={};self._receipts=OrderedDict()
        self._revision=0;self._max_key=-1
        self._last_placement=max(self.templates,default=0);self._bootstrapped=False
        self._motion_rules,self._maze=motion_rules,maze
        self._motions={};self._last_ms=0

    @property
    def revision(self):return self._revision

    @property
    def next_entity_key(self):
        """Read inside the map control snapshot; expected_revision reserves it."""
        if self._max_key>=2**63-1:raise ValueError('NPC key namespace exhausted')
        return self._max_key+1

    def _time(self,now_ms):
        if now_ms is None:
            if self._motions:raise ValueError('Explicit server time required for moving NPC snapshots')
            return self._last_ms
        if type(now_ms) is not int or now_ms<self._last_ms:
            raise ValueError('NPC motion clock cannot go backwards')
        return now_ms

    def _at(self,entity,now_ms):
        motion=self._motions.get(entity.entity_key)
        if motion is None:return entity
        x,y=motion.position(now_ms)
        return replace(entity,placement=replace(entity.placement,x=x,y=y))

    def view(self,*,now_ms=None):
        """Immutable current authority. Removed entities do not remain eligible."""
        now=self._time(now_ms)
        return tuple(self._at(self._entities[k],now) for k in sorted(self._entities))

    def control_snapshot(self,*,now_ms):
        """Read once inside the map mailbox; no mutable owner crosses the seam."""
        return NpcControlSnapshot(self.address,self.generation,self.revision,
            self.next_entity_key,self.view(now_ms=now_ms))

    def _valid(self,key,placement,definitions):
        if (type(key) is not int or not 0<=key<2**63
                or type(placement.npc_id) is not int or not 1<=placement.npc_id<2**31
                or placement.npc_id not in definitions
                or not valid_position((placement.map_id,placement.x,placement.y),self.catalog)
                or any(type(v) is not int or not 0<=v<32768 for v in (placement.x,placement.y))):
            raise ValueError('Unknown or non-encodable NPC presence')

    @staticmethod
    def _spawn_messages(entities,definitions,batch_size):
        if type(batch_size) is not int or not 1<=batch_size<=4096:
            raise ValueError('Bounded NPC native batch size required')
        records=tuple(NpcBasic(e.entity_key,e.placement.npc_id,
            definitions[e.placement.npc_id].get('name',''),e.placement.x,e.placement.y,
            field_48=e.placement.direction) for e in entities)
        return tuple((ADD_USER_SCREEN,npc_screen(records[i:i+batch_size]))
            for i in range(0,len(records),batch_size))

    def spawn(self,bindings,definitions,*,batch_size):
        """Bootstrap once with original static bindings; same shape as NpcScene.

        Later appearance uses apply with generation/revision and fresh keys.
        Every packet encodes before any authority changes.
        """
        if self._bootstrapped:raise ValueError('NPC lifecycle already bootstrapped')
        bindings=tuple(bindings)
        if (len(bindings)>self.capacity or any(type(row) is not tuple or len(row)!=2 for row in bindings)
                or len({key for key,pid in bindings})!=len(bindings)):
            raise ValueError('Invalid NPC bootstrap bindings')
        entities={}
        for key,pid in bindings:
            if pid not in self.templates:raise ValueError('Unknown NPC bootstrap placement')
            p=self.templates[pid];self._valid(key,p,definitions)
            entities[key]=NpcPresence(key,p,'original-map-placement')
        messages=self._spawn_messages(tuple(entities.values()),definitions,batch_size)
        self._definitions=MappingProxyType(dict(definitions));self._entities=entities
        self._max_key=max(entities,default=-1);self._bootstrapped=True
        return messages

    def _remaining_moves(self,entities,now_ms):
        messages=[]
        for entity in entities:
            motion=self._motions.get(entity.entity_key)
            if motion is None or now_ms>=motion.ends_ms:continue
            origin=(entity.placement.x,entity.placement.y)
            # Quantization can reach the exact target before the animation's
            # last fraction of a pixel. A spawn there needs no ignored0,0 move.
            if origin!=motion.target:
                messages.append(npc_move_to(entity.entity_key,motion.ends_ms-now_ms,origin,motion.target))
        return tuple(messages)

    def snapshot(self,*,batch_size,now_ms=None,entity_keys=None):
        """Fresh join/reconnect view; never cache the bootstrap packets forever."""
        now=self._time(now_ms)
        if entity_keys is None:
            entities=self.view(now_ms=now)
        else:
            if (type(entity_keys) is not tuple or len(entity_keys)>self.capacity
                    or any(type(k) is not int or k not in self._entities for k in entity_keys)
                    or len(set(entity_keys))!=len(entity_keys)):
                raise ValueError('Trusted current NPC visibility subset required')
            entities=tuple(self._at(self._entities[k],now) for k in sorted(entity_keys))
        return self._spawn_messages(entities,self._definitions,batch_size)+self._remaining_moves(entities,now)

    def _current_messages(self,keys,now_ms):
        missing=tuple(k for k in keys if k not in self._entities)
        active=tuple(self._at(self._entities[k],now_ms) for k in keys if k in self._entities)
        return (((REMOVE_USER_SCREEN,remove_npc_screen(missing)),) if missing else ())+self._spawn_messages(
            active,self._definitions,min(self.capacity,64))+self._remaining_moves(active,now_ms)

    def apply(self,command,*,now_ms):
        """Apply one trusted map command, not a client packet or a role DB call.

        New keys must increase monotonically within this map generation, so an
        old menu can never address a different replacement NPC. Bounded receipt
        eviction is safe against old effects because expected_revision is also
        mandatory. Replay returns CURRENT touched entities/removals, preventing
        an old spawn packet from resurrecting a later removed client entity.
        """
        if (type(command) is not NpcLifecycleCommand or not self._bootstrapped
                or command.address!=self.address or command.generation!=self.generation
                or type(command.request_id) is not str or not 1<=len(command.request_id)<=128
                or type(command.source_ref) is not str or not 1<=len(command.source_ref)<=160
                or type(command.expected_revision) is not int or not 0<=command.expected_revision<2**63-1
                or type(command.deadline_ms) is not int or type(now_ms) is not int
                or not 0<=now_ms<command.deadline_ms
                or type(command.entities) is not tuple or not 1<=len(command.entities)<=self.capacity
                or command.operation not in ('spawn','remove','move')):
            raise ValueError('Invalid/expired map NPC lifecycle command')
        self._time(now_ms)
        if command.operation=='spawn':
            if any(type(e) is not NpcSpawn for e in command.entities):raise ValueError('Frozen NPC spawn records required')
            keys=tuple(e.entity_key for e in command.entities)
        elif command.operation=='move':
            if (self._motion_rules is None or len(command.entities)>self._motion_rules.max_move_batch
                    or any(type(e) is not NpcMove for e in command.entities)):
                raise ValueError('Explicit bounded frozen NPC motion commands required')
            keys=tuple(e.entity_key for e in command.entities)
        else:
            keys=command.entities
        if any(type(k) is not int or not 0<=k<2**63 for k in keys) or len(set(keys))!=len(keys):
            raise ValueError('Unique native NPC keys required')
        fingerprint=hashlib.sha256(json.dumps(asdict(command),sort_keys=True,separators=(',',':')).encode()).hexdigest()
        old=self._receipts.get(command.request_id)
        if old:
            if old[0]!=fingerprint:raise ValueError('NPC lifecycle retry intent conflict')
            active=tuple(self._at(self._entities[k],now_ms) for k in keys if k in self._entities)
            return NpcChange(self.revision,True,keys,self._current_messages(keys,now_ms),old[2],active)
        if command.expected_revision!=self.revision:raise ValueError('Stale NPC lifecycle revision')
        before=tuple(self._at(self._entities[k],now_ms) for k in keys if k in self._entities)
        updated=dict(self._entities);placement_id=self._last_placement;max_key=self._max_key
        motions=dict(self._motions)
        if command.operation=='spawn':
            if len(updated)+len(keys)>self.capacity:raise ValueError('NPC lifecycle capacity')
            for e in command.entities:
                if e.entity_key<=max_key:raise ValueError('NPC keys cannot be reused or issued out of order')
                placement_id+=1
                p=NpcPlacement(placement_id,e.npc_id,self.address.map_id,e.x,e.y,0)
                self._valid(e.entity_key,p,self._definitions)
                updated[e.entity_key]=NpcPresence(e.entity_key,p,command.source_ref);max_key=e.entity_key
            messages=self._spawn_messages(tuple(updated[k] for k in keys),self._definitions,min(self.capacity,64))
        elif command.operation=='move':
            messages=[];pixels=0
            for e in command.entities:
                if e.entity_key not in updated:raise ValueError('NPC motion entity is not present')
                entity=self._at(updated[e.entity_key],now_ms);p=entity.placement
                origin=(p.x,p.y)
                # Validate exact native fields before spending path-query work.
                message=npc_move_to(e.entity_key,e.duration_ms,origin,e.target)
                if type(e.collision_mask) is not int or not 0<=e.collision_mask<=255:
                    raise ValueError('Trusted explicit native NPC collision mask required')
                self._valid(e.entity_key,replace(p,x=e.target[0],y=e.target[1]),self._definitions)
                if origin==e.target:raise ValueError('NPC already at requested destination')
                pixels+=max(abs(a-b) for a,b in zip(origin,e.target))+1
                if pixels>self._motion_rules.max_path_pixels:raise ValueError('NPC path query budget exceeded')
                if (not maze_clear(self._maze,*origin,mask=e.collision_mask)
                        or not maze_clear(self._maze,*e.target,mask=e.collision_mask)
                        or maze_segment_result(self._maze,origin,e.target,mask=e.collision_mask)==1):
                    raise ValueError('NPC path enters blocked maze cell')
                updated[e.entity_key]=entity
                motions[e.entity_key]=_Motion(command.request_id,origin,e.target,now_ms,e.duration_ms)
                messages.append(message)
            messages=tuple(messages)
        else:
            if any(k not in updated for k in keys):raise ValueError('Cannot remove an unknown or already removed NPC')
            messages=((REMOVE_USER_SCREEN,remove_npc_screen(keys)),)
            for key in keys:
                del updated[key];motions.pop(key,None)
        self._entities=updated;self._motions=motions
        self._last_placement=placement_id;self._max_key=max_key;self._revision+=1;self._last_ms=now_ms
        after=tuple(self._at(updated[k],now_ms) for k in keys if k in updated)
        self._receipts[command.request_id]=(fingerprint,keys,before or after)
        if len(self._receipts)>self.receipt_capacity:self._receipts.popitem(last=False)
        return NpcChange(self.revision,False,keys,messages,before,after)

    def advance(self,*,now_ms):
        """Map tick: commit completed targets and return stable arrival events.

        The client already has the positive-duration native movement. Arrival
        emits no duration0 packet and never grants role assets. Script consumers
        own persistence/delivery of returned events, separately from this map.
        """
        now=self._time(now_ms)
        completed=tuple((k,m) for k,m in sorted(self._motions.items()) if now>=m.ends_ms)
        if completed and self.revision>=2**63-2:raise ValueError('NPC lifecycle revision exhausted')
        events=[];updated=dict(self._entities);motions=dict(self._motions)
        for key,motion in completed:
            entity=updated[key]
            updated[key]=replace(entity,placement=replace(entity.placement,x=motion.target[0],y=motion.target[1]))
            del motions[key]
            source=json.dumps((self.generation,motion.request_id,key),separators=(',',':'))
            events.append(NpcArrival('na:'+hashlib.sha256(source.encode()).hexdigest(),
                self.generation,key,motion.target,motion.ends_ms))
        self._entities=updated;self._motions=motions;self._last_ms=now
        if events:self._revision+=1
        return tuple(events)

    def interact(self,body,expected,current,*,request_id,deadline_ms,now_ms):
        if (type(body) is not bytes or type(request_id) is not str or not 1<=len(request_id)<=128
                or type(now_ms) is not int or type(deadline_ms) is not int or not 0<=now_ms<deadline_ms
                or current!=expected or current.address!=self.address or current.state!='active'
                or not valid_position(current.position,self.catalog)):
            raise ValueError('Invalid or stale map NPC visit')
        key=read_visit_npc(body);entity=self._entities.get(key)
        if entity is None:raise ValueError('NPC entity is not currently present')
        npc=self._at(entity,self._time(now_ms)).placement
        nearby=((current.x-npc.x)**2+(current.y-npc.y)**2<=self.radius**2 if self.interaction_rules is None
            else self.interaction_rules.allows(npc,current.position))
        if not nearby:
            raise ValueError('NPC is out of interaction range')
        return NpcInteraction(request_id,current.role_id,current.login_epoch,self.address,
            current.version,key,npc.npc_id,npc.placement_id)
