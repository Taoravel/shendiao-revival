"""Partitioned live runtime. Session.feed and SocialHub are offline Adapters only."""
import asyncio
from collections import Counter
from dataclasses import dataclass, replace
import struct
import time
from types import MappingProxyType
import uuid
from connection_codec import ConnectionCodec
from runtime_core import SerialOwner, BlockingIO, AsyncLog, Backpressure, StaleEpoch
from runtime_story_maps import RuntimeStoryMaps
from runtime_movement import (MapMovement, MovementDeclaration, load_movement_policy,
    SET_ROLE_LOCATION, UNSUPPORTED_JUMPS, SupersededMovementDelivery)
import runtime_storage
import world_transfer_storage
from role_protocol import (role_list,role_info,parse_create,parse_enter,parse_delete,load_exit_ui_message,
    ROLE_OFFLINE_REQUEST,ROLE_OFFLINE,DELETE_ROLE_REQUEST,DELETE_ROLE,
    RETURN_ROLE_LIST_REQUEST,RETURN_ROLE_LIST,RETURN_LOGIN_REQUEST,RETURN_LOGIN)
from world_protocol import world_snapshot, scene_entry, ENTER_WORLD, ENTER_SCENE, AFTER_ENTER_WORLD
from world_movement import plan_movement, MOVEMENT_TYPES,decode_movement
from inventory import INVENTORY_TYPES, InventoryNotReady, USE_ITEM
from task_protocol import (C_REQUEST_QUEST_CAN_ACCEPT,S_REQUEST_QUEST_CAN_ACCEPT,C_TRACK_QUEST,
                           S_TRACK_QUEST,decode_empty_request,decode_track_quest,
                           encode_quest_can_accept,encode_track_quest)
from task_session import TASK_TYPES
from task_domain import TaskDomain
from social_owner import RoleSnapshot, SocialCommand, Delivery, Publish, RelationWake
from social_runtime import SocialRuntime
from social_protocol import SOCIAL_TYPES, ONLINE
from training_battle import TrainingBattle
from training_battle import DEFAULT_RULES
from battle_owner import BattleOwner, Participant, BattleCommand
from world_owner import MapOwner as WorldDomain,MapAddress,Location,MoveCommand
from battle_protocol import BATTLE_TYPES
from world_npcs import NpcScene
from world_entity_protocol import VISIT_NPC,NPC_SERVICE,read_npc_service,visit_npc_reply,VISIT_NPC_REPLY
from task_conversation import TaskConversation
from task_session import TASK_INTENT_TYPES,decode_task_intent
from task_workflow import completion_messages
from task_dialog_protocol import S_REFRESH_USER_EXP,encode_user_experience
from task_protocol import C_COMMIT_SCENARIO_QUEST
from currency_protocol import encode_currency_balance,encode_yuanbao_balances
from role_growth_protocol import (C_REQ_LEVEL_UP,C_ADD_POINT_TO_ATTR,GROWTH_TYPES,
                                  decode_level_request,decode_allocation_request)
from world_newbie import END_PLAY_CG
from world_card_protocol import C_GET_CARD_ITEM
from task_newbie_chapter import resume_newbie_messages
from task_protocol import S_ACCEPT_SCENARIO_QUEST,decode_accept_scenario_quest
import npc_gameplay
import npc_depot
import npc_repairs
import npc_shop_sales
import npc_recovery
import npc_role_healing
import role_vigor
import random
from wild_encounters import WildEncounters
from wild_battle import WildBattle
import wild_runtime_storage
from task_pve import TaskPveBattle
import task_pve_runtime_storage
from task_battle_protocol import C_ACTIVE_SCENARIO_QUEST_AI_BATTLE,decode_task_battle_request
from visible_notice import visible_notice
from inventory import QUERY_BAG,MOVE_ITEM,EQUIP_ITEM,UNEQUIP_ITEM


@dataclass(frozen=True)
class Position:
    role_id: int
    epoch: str
    value: tuple
    version: int
    arrival: tuple


@dataclass(frozen=True)
class SceneSendBarrier:
    role_id: int
    epoch: object
    generation: int
    transfer_id: str
    target_version: int
    body: bytes
    movement: MovementDeclaration | None = None


@dataclass(frozen=True)
class SceneMessage:
    kind: int
    body: bytes
    barrier: SceneSendBarrier

    def __iter__(self):
        return iter((self.kind,self.body))


@dataclass(frozen=True)
class SceneFence:
    address: MapAddress
    map_generation: str | None
    role_id: int
    epoch: object
    connection_generation: int
    scene_token: str


@dataclass(frozen=True)
class ScopedSceneMessage:
    kind: int
    body: bytes
    barrier: object
    delivery: object
    fence: SceneFence

    def __iter__(self):return iter((self.kind,self.body))


def runtime_map_address(value):
    """Trusted full server identity; integer callers select their public map."""
    address=MapAddress(value,value,0) if type(value) is int else value
    if (type(address) is not MapAddress
            or type(address.map_id) is not int or not 0<address.map_id<2**63
            or type(address.instance_id) is not int or not 0<address.instance_id<2**63
            or type(address.partition_id) is not int or not 0<=address.partition_id<2**63):
        raise ValueError('Explicit valid full runtime map address required')
    return address


class MapOwner:
    def __init__(self, instance, catalog, npc_resources=None,*,interaction_rules=None,story_rules=None,
                 maze=None,movement_policy=None):
        address=runtime_map_address(instance)
        template=address.map_id
        self.instance, self.catalog, self.positions = address.instance_id, catalog, {}
        self.domain=WorldDomain(address,catalog,capacity=story_rules.member_capacity if story_rules is not None else 2048,
                                transfer_capacity=128,mailbox_capacity=64,maze=maze)
        self.movement=MapMovement(movement_policy or load_movement_policy())
        self.npcs=None
        self.spawn_packets=()
        if npc_resources is not None:
            placements,definitions=npc_resources
            self.npcs=NpcScene(self.domain.address,placements.get(template,()),catalog,
                               interaction_radius=32,binding_capacity=4096,interaction_rules=interaction_rules)
            bindings=tuple(((template<<32)|p.placement_id,p.placement_id)
                for p in placements.get(template,()) if p.npc_id in definitions
                and 0<=p.x<min(catalog[template]['width'],32768)
                and 0<=p.y<min(catalog[template]['height'],32768))
            self.spawn_packets=self.npcs.spawn(bindings,definitions,batch_size=64)
        if story_rules is not None:
            self.domain.configure_lifecycle(scene_delivery_capacity=story_rules.scene_delivery_capacity,
                actor_state='static_original')
        self.mailbox = SerialOwner(('map',template,address.instance_id,address.partition_id), self.handle)

    async def handle(self, cmd):
        if cmd.operation=='inspect_lifecycle':return self.domain.inspect_lifecycle(*cmd.args)
        if cmd.operation=='retire_idle':
            snapshot,now_ms,minimum_idle_ms=cmd.args
            return self.domain.retire_idle(snapshot,now_ms,minimum_idle_ms=minimum_idle_ms)
        if cmd.operation=='begin_scene_delivery':
            location,generation,request_id=cmd.args
            return self.domain.begin_scene_delivery(location,connection_generation=generation,request_id=request_id)
        if cmd.operation=='finish_scene_delivery':return self.domain.finish_scene_delivery(*cmd.args)
        # Recovery has no online member in the new lease yet. Execute through
        # the exact map owner before the ordinary membership guard below.
        if cmd.operation=='inspect_transfer':
            return self.domain.inspect_transfer(*cmd.args)
        if cmd.operation=='retire_recovered_transfer':
            retired=self.domain.retire_recovered_transfer(*cmd.args)
            cached=self.positions.get(retired.role_id)
            if cached is not None and str(cached.epoch)==str(retired.old_epoch):
                # The durable recovery decision fenced this old member already.
                self.movement.leave(Location(cached.role_id,cached.epoch,self.domain.address,
                    cached.version,cached.value[1],cached.value[2]))
                self.positions.pop(retired.role_id,None)
            return retired
        if cmd.operation in ('reserve','freeze','activate','finalize','ready','cancel','resume','retire_receipt'):
            method=getattr(self.domain,cmd.operation)
            if cmd.operation in ('reserve','freeze','activate'):
                result=method(*cmd.args,now_ms=int(time.monotonic()*1000))
            else: result=method(*cmd.args)
            location=getattr(result,'location',None)
            if cmd.operation=='freeze': location=result.source
            if cmd.operation in ('resume','ready'): location=result
            # An idempotent historical receipt is not current map authority.
            # In particular finalize returns the *target* location on source.
            # Replays must not overwrite a new lease or revoke its declaration.
            if (location and location.address==self.domain.address
                    and self.domain.location(location.role_id)==location):
                projected=Position(location.role_id,location.login_epoch,location.position,
                    location.version,(location.x//16,location.y//16))
                if self.positions.get(location.role_id)!=projected:
                    if cmd.operation!='ready':self.movement.invalidate(location)
                    self.positions[location.role_id]=projected
            if cmd.operation=='finalize':
                departed=result.frozen.source
                cached=self.positions.get(departed.role_id)
                if (cached is not None and cached.epoch==departed.login_epoch
                        and cached.value==departed.position and cached.version==departed.version
                        and self.domain.location(departed.role_id) is None):
                    self.positions.pop(departed.role_id)
                    self.movement.leave(departed)
            return result
        if cmd.operation=='join':
            position, = cmd.args
            previous=self.positions.get(position.role_id)
            before=self.domain.location(position.role_id)
            joined=self.domain.join(Location(position.role_id,position.epoch,self.domain.address,
                                      max(1,position.version),position.value[1],position.value[2]))
            # Domain admission can reject or return an idempotent member.
            # Only a successful *new* admission supersedes old derived state.
            if before is None:
                old=(Location(previous.role_id,previous.epoch,self.domain.address,
                    previous.version,previous.value[1],previous.value[2]) if previous is not None else joined)
                self.movement.leave(old)
            elif previous is not None:
                return previous
            position=replace(position,version=max(1,position.version))
            self.positions[position.role_id] = position
            return position
        role_id, epoch = cmd.args[:2]
        old = self.positions.get(role_id)
        if not old or old.epoch!=epoch: raise StaleEpoch('Map membership expired')
        if cmd.operation=='spawn': return self.spawn_packets
        if cmd.operation=='location': return self.domain.location(role_id)
        if cmd.operation=='invalidate_movement':
            self.movement.invalidate(self.domain.location(role_id))
            return
        if cmd.operation=='suspend_movement':
            current=self.domain.location(role_id)
            try:self.movement.current(current)
            except ValueError:supported=False
            else:supported=True
            self.movement.invalidate(current)
            return supported
        if cmd.operation=='movement_will_send':
            declaration,=cmd.args[2:]
            if not self.movement.pending_current(declaration,self.domain.location(role_id)):
                raise StaleEpoch('Movement declaration no longer current before send')
            return
        if cmd.operation=='declare_movement':
            expected,generation,token,kind,body,source=cmd.args[2:]
            current=self.domain.location(role_id)
            if expected!=current:raise StaleEpoch('Movement declaration member changed')
            return self.movement.declare(current,generation,token,kind,body,source)
        if cmd.operation=='movement_sent':
            declaration,transferred=cmd.args[2:]
            return self.movement.confirm(declaration,self.domain.location(role_id),transferred=transferred)
        if cmd.operation=='scripted_transfer':
            version,target=cmd.args[2:]
            current=self.domain.location(role_id)
            if version!=old.version: raise ValueError('Stale NPC transport source')
            return self.domain.prepare_transfer(current,target,request_id=cmd.request_id,
                deadline_ms=int(cmd.deadline*1000),now_ms=int(time.monotonic()*1000))
        if cmd.operation=='authorized_transfer':
            expected,target,deadline_ms=cmd.args[2:]
            if expected!=self.domain.location(role_id) or expected.version!=old.version:
                raise ValueError('Stale authorized transfer source')
            return self.domain.prepare_transfer(expected,target,request_id=cmd.request_id,
                deadline_ms=deadline_ms,now_ms=int(time.monotonic()*1000))
        if cmd.operation in ('npc','quest_npc'):
            version,body=cmd.args[2:]
            if version!=old.version or not self.npcs: raise ValueError('Stale/unavailable NPC scope')
            current=self.domain.location(role_id)
            proof=self.npcs.interact(body,current,current,request_id=cmd.request_id,
                deadline_ms=int(cmd.deadline*1000),now_ms=int(time.monotonic()*1000))
            if cmd.operation=='quest_npc':
                context=self.movement.current(current)
                lifecycle=self.domain.inspect_lifecycle(int(time.monotonic()*1000))
                return proof,current,lifecycle.owner_generation,context.state
            return proof,current
        if cmd.operation=='leave':
            self.movement.leave(self.domain.location(role_id))
            self.domain.leave(self.domain.location(role_id))
            del self.positions[role_id]
            return
        version, kind, body = cmd.args[2:]
        if version!=old.version: raise StaleEpoch('Position version mismatch')
        current=self.domain.location(role_id)
        context=self.movement.current(current)
        result=self.domain.move(MoveCommand(current,cmd.request_id,int(time.monotonic()*1000)+5000,kind,body,
                                movement_state=context.state,collision_points='native_current'),
                                int(time.monotonic()*1000))
        if result.rejection: raise ValueError(result.rejection)
        # Cross-map reservations/loading acknowledgements are not yet migrated.
        # Keep the source authoritative; never immediately persist a proposal.
        location=result.location
        self.movement.advance(current,location)
        new = replace(old,value=location.position,arrival=(location.x//16,location.y//16),version=location.version)
        self.positions[role_id] = new
        return (new,result) if cmd.operation=='move_for_encounter' else (new,result.offer)


class ScheduledBattle:
    """Async scheduling Adapter around the system window's battle owner."""
    def __init__(self,role,epoch,generation,version,*,participant=None,ticket=None,
                 task_ticket=None,task_definition=None,task_rules=None):
        r=role
        self.wild_ticket=ticket
        self.task_ticket=task_ticket
        if task_ticket is not None and (ticket is not None or participant is None
                or task_definition is None or task_rules is None):
            raise ValueError('One actual dedicated Task battle identity and recipe required')
        factory=({'engine_factory':lambda actor,rules,clock:
                    TaskPveBattle(actor,rules,task_definition,clock=clock)} if task_ticket is not None else
                 {'engine_factory':lambda actor,rules,clock:WildBattle(actor,ticket,rules,clock=clock)} if ticket else {})
        self.domain=BattleOwner(participant or Participant(r['id'],epoch,generation,max(1,version),r['name'],r['shape'],r['level']),
            task_rules if task_ticket is not None else DEFAULT_RULES,
            mailbox_capacity=64,receipt_capacity=1024 if task_ticket is not None else 512,
            playback_timeout_ms=task_rules.playback_timeout_ms if task_ticket is not None else 30000,
            now_ms=int(time.monotonic()*1000),**factory)
        self.key=self.domain.id
        self.sequence=0
        self.mailbox=SerialOwner(('battle',self.key),self.handle)

    async def handle(self,command):
        if command.operation=='snapshot':return self.domain.snapshot()
        now=int(time.monotonic()*1000)
        if command.operation=='opening': outcome=self.domain.initial()
        elif command.operation=='tick': outcome=self.domain.advance(now)
        elif command.operation=='close': outcome=self.domain.close('disconnected',now)
        else:
            self.sequence+=1
            s=self.domain.snapshot();p=self.domain.participant
            envelope=BattleCommand(self.key,p.role_id,p.login_epoch,p.connection_generation,command.request_id,
                self.sequence,s.state_version,s.round_number,now+5000,*command.args)
            admission=self.domain.submit(envelope,now)
            if admission!='accepted': raise Backpressure(admission)
            outcome=self.domain.process_one(now)
        packets=list(outcome.delivery.packets) if outcome and outcome.delivery else []
        if command.operation=='opening': return packets
        return packets,(outcome.finished or outcome.aborted) if outcome else None

    async def call(self,*args,**kwargs): return await self.mailbox.call(*args,**kwargs)
    async def close(self): await self.mailbox.close()


class RoleOwner:
    def __init__(self, runtime, role, account_id, epoch):
        self.rt, self.role, self.account_id, self.epoch = runtime, dict(role), account_id, epoch
        self.id = role['id']
        self.inventory = self.tasks = self.position = self.battle = None
        self.map_address=None
        self.scene_token=uuid.uuid4().hex
        self.wild=None
        self.pending_battle_delivery=None
        self.battle_normal_resume=False
        self.snapshot_revision=0
        self.joined = False
        self.dirty = False
        self.last_checkpoint = time.monotonic()
        self.poisoned = False
        self.social_recovery_at = 0
        self.conversation=None
        self.transfer=None
        self.require_move_start=False
        self.newbie_chapter=None
        self.intro_ticket=None
        self.master_dialogue_ticket=None
        self.cart_dialogue_ticket=None
        self.touch_dialogue_ticket=None
        self.task_battle_ticket=None
        self.first_skill_ticket=None
        self.npc_depot_ticket=None
        self.vigor_enabled=False
        self.vigor_sync_at=time.monotonic()
        self.mailbox = SerialOwner(('role',self.id,epoch),self.handle)

    def valid(self):
        if self.poisoned or self.rt.roles.get(self.id) is not self: raise StaleEpoch('Role owner replaced or I/O outcome unknown')

    async def io(self, fn, *args):
        try:
            result = await self.rt.io.run(('role',self.id),fn,*args)
        except TimeoutError:
            self.poisoned = True
            raise
        self.valid()
        return result

    async def handle(self, cmd):
        self.valid()
        if self.newbie_pending and cmd.operation not in ('load','close','tick','receive','movement_sent','movement_will_send'):
            raise ValueError('Role writes wait for authorized intro completion')
        if cmd.operation=='load':
            # Recover a durable original Task terminal before any unrelated
            # load-time reconciliation or role gameplay can change its source.
            await self.io(task_pve_runtime_storage.recover,self.rt.accounts,
                self.account_id,self.id,self.epoch)
            recovered=await self.io(runtime_storage.prepare_login_map_recovery,
                self.rt.accounts,self.account_id,self.id,self.epoch)
            if recovered.decision is not None:
                await self.retire_old_transfer(recovered.decision)
            self.inventory,self.tasks,pos,version = await self.io(runtime_storage.load_role,
                self.rt.accounts,self.account_id,self.id,self.epoch,self.rt.task_resources)
            await self.io(wild_runtime_storage.recover,self.rt.accounts,self.account_id,self.id,self.epoch)
            self.position = Position(self.id,self.epoch,pos,version,(pos[1]//16,pos[2]//16))
            checkpoint=recovered.checkpoint
            if checkpoint is not None and (checkpoint.position,checkpoint.version)!=(pos,version):
                raise ValueError('Role load changed the recovered exact map checkpoint')
            if recovered.story_instance is not None:
                target=await self.rt.story_maps.get_map(recovered.story_instance,request_id=cmd.request_id,
                    deadline_ms=self.rt.story_maps.now()+10000)
            else:target=self.rt.map(checkpoint.address if checkpoint is not None else pos[0])
            self.map_address=target.domain.address
            self.position=await target.mailbox.call('join',self.position)
            self.conversation=TaskConversation(self.rt.task_resources,self.id,self.epoch)
            profile=await self.io(runtime_storage.role_load_profile,
                self.rt.accounts,self.account_id,self.id,self.epoch)
            self.adopt_load_profile(profile)
            self.newbie_chapter=await self.io(runtime_storage.newbie_state,
                self.rt.accounts,self.account_id,self.id,self.epoch)
            intro=1 if self.newbie_chapter is None else self.newbie_chapter.intro_discriminator
            body=scene_entry(pos)
            entry=await self.entry_movement_messages(body)
            return [(ENTER_WORLD,world_snapshot(self.role,profile.attributes,intro_discriminator=intro,
                                               growth_snapshot=profile.growth)),
                    (0xc0007,struct.pack('>Q',int(time.time()*1000)))]+entry
        if cmd.operation=='settle':
            return await self.io(runtime_storage.settle,self.rt.accounts,self.account_id,self.id,self.epoch,cmd.args[0])
        if cmd.operation=='initialize_wallet':
            baseline,origin=cmd.args
            return await self.io(runtime_storage.initialize_role_wallet,self.rt.accounts,self.account_id,self.id,
                                 self.epoch,baseline,origin)
        if cmd.operation=='initialize_vigor':
            value,maximum,origin=cmd.args
            state=await self.io(role_vigor.initialize_profile,self.rt.accounts,self.inventory,value,maximum,origin,
                                int(time.monotonic()*1000))
            self.vigor_enabled=True
            self.vigor_sync_at=time.monotonic()
            return state
        if cmd.operation=='scene_sent':
            barrier,=cmd.args
            receipt=self.transfer
            connection=self.rt.connections.get(self.id)
            if (not isinstance(barrier,SceneSendBarrier) or not receipt or not connection or connection.closed
                    or (barrier.role_id,barrier.epoch,barrier.generation)!=(self.id,self.epoch,connection.generation)
                    or barrier.transfer_id!=receipt.frozen.reservation.offer.transfer_id
                    or barrier.target_version!=receipt.location.version
                    or barrier.body!=scene_entry(receipt.location.position,reason=0)):
                raise StaleEpoch('Foreign or stale scene send barrier')
            return await self.scene_ready(barrier.movement)
        if cmd.operation=='movement_sent':
            declaration,=cmd.args
            self.validate_movement_delivery(declaration)
            await self.rt.map(self.map_address).mailbox.call('movement_sent',self.id,self.epoch,declaration,False)
            return []
        if cmd.operation=='movement_will_send':
            declaration,=cmd.args
            self.validate_movement_delivery(declaration)
            await self.rt.map(self.map_address).mailbox.call('movement_will_send',self.id,self.epoch,declaration)
            return []
        if cmd.operation=='offer_task':
            # Trusted server activation only; no wire route accepts arbitrary offers.
            actor,state=await self.io(runtime_storage.task_state,self.rt.accounts,self.account_id,self.id,self.epoch)
            plan=TaskDomain(self.rt.task_resources).plan(actor,state,'offer',cmd.args[0])
            return await self.io(runtime_storage.commit_task,self.rt.accounts,self.account_id,self.id,self.epoch,
                                 actor,plan,cmd.request_id)
        if cmd.operation=='tick':
            if self.touch_dialogue_ticket is not None and int(time.monotonic()*1000)>=self.touch_dialogue_ticket.intent.deadline_ms:
                self.touch_dialogue_ticket=None
            if self.newbie_pending:
                if self.intro_ticket is not None and int(time.time()*1000)>=self.intro_ticket.deadline_ms:
                    self.intro_ticket=None  # Durable root remains pending until a new connection/resume.
                return []
            vigor_replies=[]
            if self.joined and self.vigor_enabled and time.monotonic()-self.vigor_sync_at>=60:
                vigor_replies=await self.io(role_vigor.checkpoint,self.rt.accounts,self.inventory,int(time.monotonic()*1000))
                self.vigor_sync_at=time.monotonic()
            if self.joined and time.monotonic()-self.social_recovery_at>=1:
                await self.rt.social_runtime.recover(self.snapshot())
                self.social_recovery_at=time.monotonic()
            if self.dirty and time.monotonic()-self.last_checkpoint>=1:
                await self.checkpoint()
            if self.battle:
                return vigor_replies+await self.battle_step('tick')
            return vigor_replies
        if cmd.operation=='close':
            try:
                if self.position:
                    await self.rt.map(self.map_address).mailbox.call('invalidate_movement',self.id,self.epoch)
                self.intro_ticket=None
                self.master_dialogue_ticket=None
                self.cart_dialogue_ticket=None
                self.touch_dialogue_ticket=None
                self.task_battle_ticket=None
                self.first_skill_ticket=None
                if self.joined and self.vigor_enabled:
                    await self.io(role_vigor.checkpoint,self.rt.accounts,self.inventory,int(time.monotonic()*1000),True)
                    self.vigor_enabled=False
                if self.transfer:
                    receipt=self.transfer
                    # Socket gone: release the committed loading member without
                    # admitting any movement. A new login loads its durable target.
                    location=await self.rt.map(receipt.location.address).mailbox.call('ready',receipt.location)
                    self.position=Position(self.id,self.epoch,location.position,location.version,
                                           (location.x//16,location.y//16))
                    self.map_address=location.address
                    await self.rt.map(location.address).mailbox.call('retire_receipt',receipt)
                    self.transfer=None
                if self.dirty: await self.checkpoint()
                if self.battle:
                    await self.battle_step('close')
                return []
            finally:
                # Even unavailable persistence must not retain a disconnected
                # BattleOwner. A new lease recovers its last durable copy/outbox.
                try:
                    if self.battle:
                        owner=self.battle
                        self.battle=None
                        self.rt.battles.pop(owner.key,None)
                        await owner.close()
                finally:
                    self.pending_battle_delivery=None
                    if self.position:
                        await self.rt.map(self.map_address).mailbox.call('leave',self.id,self.epoch)
        kind,body = cmd.args
        if kind==npc_depot.CLOSE_DEPOT:
            npc_depot.decode_close(body)
            self.npc_depot_ticket=None
            return []
        if kind==AFTER_ENTER_WORLD and not body:
            if self.transfer:
                raise ValueError('First-world acknowledgement cannot finish a general scene handoff')
            if self.joined: return []
            # Do not replay the earlier login profile if authoritative wounds or
            # growth changed before initialization delivery.
            profile=await self.io(runtime_storage.role_load_profile,
                self.rt.accounts,self.account_id,self.id,self.epoch)
            self.adopt_load_profile(profile)
            self.joined = True
            vigor=await self.io(role_vigor.login,self.rt.accounts,self.inventory,int(time.monotonic()*1000))
            self.vigor_enabled=vigor is not None
            self.vigor_sync_at=time.monotonic()
            self.rt.online[self.id] = self.snapshot()
            self.rt.index(self.snapshot(),True)
            await self.rt.social_runtime.join(self.snapshot(),self.snapshot_revision)
            await self.rt.presence(self.id,True)
            # The original world reset disables both X and the system exit
            # menu until this signed-mode notification initializes them.
            spawn=[self.rt.exit_ui_message]
            spawn.extend(await self.rt.map(self.map_address).mailbox.call('spawn',self.id,self.epoch))
            if vigor is not None:spawn.append(role_vigor.refresh(vigor))
            spawn.append((S_REFRESH_USER_EXP,encode_user_experience(self.role['experience'])))
            if profile.refresh is not None:
                spawn.append(profile.refresh)
            # Re-read at initialization delivery, after any earlier committed
            # owner commands; do not send a cached login or reward receipt value.
            wallet=await self.io(runtime_storage.wallet_snapshot,
                self.rt.accounts,self.account_id,self.id,self.epoch)
            if wallet is not None:
                spawn.extend(encode_currency_balance(row.currency,row.balance)
                             for row in wallet if row.currency in ('cash','bound_silver'))
                balances={row.currency:row.balance for row in wallet}
                if 'yuanbao' not in balances or 'bound_yuanbao' not in balances:
                    raise ValueError('Current wallet is missing a yuanbao balance pair')
                try:
                    pair=encode_yuanbao_balances(balances['yuanbao'],balances['bound_yuanbao'])
                except ValueError:
                    # Reject this display operation without truncating the
                    # ledger or preventing unrelated scene/task initialization.
                    self.rt.log(event='wallet_display_rejected',role_id=self.id,
                                reason='yuanbao_pair_outside_native_signed32_range')
                else:
                    spawn.append(pair)
            touch_messages=await self.io(runtime_storage.prologue_resume,self.rt.accounts,self.account_id,self.id,
                self.epoch) if self.rt.prologue_touch else ()
            spawn.extend(await self.io(runtime_storage.other_skill_login_messages,self.rt.accounts,
                                       self.account_id,self.id,self.epoch))
            actor,state=await self.io(runtime_storage.task_state,self.rt.accounts,self.account_id,self.id,self.epoch)
            resumed=self.conversation.resume_messages(actor,state)
            spawn.extend(resumed)
            projected={decode_accept_scenario_quest(body).quest_id for kind,body in resumed
                       if kind==S_ACCEPT_SCENARIO_QUEST}
            for message in profile.task_messages+touch_messages:
                kind_,body_=message
                ident=decode_accept_scenario_quest(body_).quest_id if kind_==S_ACCEPT_SCENARIO_QUEST else None
                if ident is None or ident not in projected:
                    spawn.append(message)
                    if ident is not None:projected.add(ident)
            spawn.extend(resume_newbie_messages(self.newbie_chapter,state,already_projected=projected))
            if self.newbie_pending:
                connection=self.rt.connections[self.id]
                location=await self.rt.map(self.map_address).mailbox.call('location',self.id,self.epoch)
                try:
                    playback=await self.io(runtime_storage.newbie_playback,self.rt.accounts,self.account_id,self.id,
                        self.epoch,location,connection.generation,cmd.request_id,int(time.time()*1000),self.intro_ticket)
                except ValueError as error:
                    # Initial ACK has already registered presence. Reconnect
                    # recovers durable pending state instead of leaving a
                    # joined connection with no authorized playback ticket.
                    raise ConnectionError('Intro authorization requires reconnect') from error
                self.newbie_chapter,self.intro_ticket=playback.chapter,playback.ticket
                await self.rt.map(self.map_address).mailbox.call('invalidate_movement',self.id,self.epoch)
                return spawn+list(playback.messages)
            if self.rt.training:
                self.battle_normal_resume=await self.rt.map(self.map_address).mailbox.call(
                    'suspend_movement',self.id,self.epoch)
                self.battle = ScheduledBattle(self.role,self.epoch,self.rt.connections[self.id].generation,self.position.version)
                self.rt.battles[self.battle.key] = self.battle
                return spawn+await self.battle.call('opening')
            return spawn
        if kind==END_PLAY_CG:
            if (not self.joined or self.transfer or self.battle or type(body) is not bytes
                    or len(body)!=4 or struct.unpack('>i',body)[0]<=0):
                raise ValueError('Invalid or unavailable intro completion')
            connection=self.rt.connections[self.id]
            location=await self.rt.map(self.map_address).mailbox.call('location',self.id,self.epoch)
            committed=await self.io(runtime_storage.newbie_finish,self.rt.accounts,self.account_id,self.id,
                self.epoch,body,location,connection.generation,int(time.time()*1000),self.intro_ticket,self.inventory)
            self.newbie_chapter=committed.action.chapter
            self.intro_ticket=None
            await self.publish_committed_role(committed.role)
            messages=list(committed.action.messages)
            if committed.action.evidence is not None:
                messages.append(await self.normal_location_message('authorized_intro_completed'))
            return messages
        if kind in UNSUPPORTED_JUMPS:
            await self.rt.map(self.map_address).mailbox.call('invalidate_movement',self.id,self.epoch)
            raise ConnectionError('Unsupported movement state requires a new scene lease')
        if self.newbie_pending:
            raise ValueError('Gameplay waits for authorized intro completion')
        if kind in BATTLE_TYPES:
            if not self.battle: return []
            return await self.battle_step('receive',kind,body)
        if self.battle and (kind in MOVEMENT_TYPES or kind in INVENTORY_TYPES or kind in TASK_TYPES
                            or kind in TASK_INTENT_TYPES or kind in GROWTH_TYPES or kind in npc_gameplay.NPC_GAMEPLAY_TYPES
                            or kind in (VISIT_NPC,NPC_SERVICE,C_GET_CARD_ITEM,C_ACTIVE_SCENARIO_QUEST_AI_BATTLE)):
            self.rt.log(event='world_request_rejected',role_id=self.id,reason='in_battle')
            return []
        if self.transfer:
            raise ValueError('Gameplay waits for matching committed scene send barrier')
        if kind==C_ACTIVE_SCENARIO_QUEST_AI_BATTLE:
            return await self.start_task_battle(cmd,body)
        if kind==C_GET_CARD_ITEM:
            if not self.joined:raise ValueError('Card choice waits for world initialization')
            current=await self.rt.map(self.map_address).mailbox.call('location',self.id,self.epoch)
            connection=self.rt.connections[self.id]
            committed=await self.io(runtime_storage.master_choose,self.rt.accounts,self.account_id,self.id,
                self.epoch,body,current,connection.generation,int(time.monotonic()*1000),self.inventory)
            self.master_dialogue_ticket=None
            await self.publish_committed_role(committed.role)
            return list(committed.action.messages)
        if kind in GROWTH_TYPES:
            if not self.joined: raise ValueError('Role growth waits for world initialization')
            if kind==C_REQ_LEVEL_UP:
                operation=runtime_storage.manual_level
                intent=decode_level_request(body)
            elif kind==C_ADD_POINT_TO_ATTR:
                operation=runtime_storage.allocate_potential
                intent=decode_allocation_request(body)
            else:
                raise ValueError('Role growth request requires its own operation decoder')
            committed=await self.io(operation,self.rt.accounts,self.account_id,self.id,
                self.epoch,intent,cmd.request_id)
            await self.publish_committed_role(committed.role)
            return list(committed.action.messages)
        if kind in MOVEMENT_TYPES:
            if not self.joined:raise ValueError('Movement waits for world initialization')
            self.conversation.cancel()
            self.master_dialogue_ticket=None
            self.cart_dialogue_ticket=None
            self.touch_dialogue_ticket=None
            self.task_battle_ticket=None
            self.first_skill_ticket=None
            self.npc_depot_ticket=None
            if self.transfer: raise ValueError('Scene still loading')
            if self.require_move_start:
                start,_,_=decode_movement(kind,body)
                if start!=self.position.value[1:]: raise ValueError('Movement does not start at committed target')
                if kind==0xc0fa1: self.require_move_start=False
            previous=Location(self.id,self.epoch,self.rt.map(self.map_address).domain.address,
                self.position.version,self.position.value[1],self.position.value[2])
            self.position, movement = await self.rt.map(self.map_address).mailbox.call(
                'move_for_encounter',self.id,self.epoch,self.position.version,kind,body,request_id=cmd.request_id,deadline=cmd.deadline)
            offer=movement.offer
            self.valid()
            self.dirty = True  # Source checkpoint survives an early handoff refusal.
            if offer:
                return await self.handoff(offer)
            # CHECK updates are coalesced; STOP or tick checkpoints the latest version.
            if kind==0xc0faa and self.dirty: await self.checkpoint()
            return await self.wild_move(previous,movement)
        if kind in npc_gameplay.NPC_GAMEPLAY_TYPES:
            if not self.joined: raise ValueError('NPC gameplay waits for world initialization')
            if kind in npc_gameplay.NPC_DEPOT_TYPES:
                return await self.depot_request(cmd,kind,body)
            sale=kind in (npc_shop_sales.SELL_ITEMS,npc_shop_sales.REPURCHASE)
            recovery=kind==npc_recovery.RECOVERY
            if recovery:key,_=npc_recovery.decode_request(body)
            elif sale:key,_=npc_shop_sales.decode_request(kind,body)
            else:key,_,_=(npc_repairs.decode_repair(body) if kind==npc_repairs.REPAIR_EQUIPMENT
                          else npc_gameplay.decode_purchase(body))
            proof,current=await self.rt.map(self.map_address).mailbox.call('npc',
                self.id,self.epoch,self.position.version,struct.pack('>q',key),
                request_id=cmd.request_id,deadline=cmd.deadline)
            if recovery:
                intent=npc_recovery.plan(self.rt.accounts.npc_gameplay,body,proof,current,
                    request_id=cmd.request_id,now_ms=int(time.monotonic()*1000),deadline_ms=int(cmd.deadline*1000))
                handler=runtime_storage.npc_recover_resources
            elif sale:
                intent=npc_shop_sales.plan(self.rt.accounts.npc_gameplay,kind,body,proof,current,
                    request_id=cmd.request_id,now_ms=int(time.monotonic()*1000),deadline_ms=int(cmd.deadline*1000))
                handler=npc_shop_sales.settle
            else:
                planner=npc_repairs.plan if kind==npc_repairs.REPAIR_EQUIPMENT else npc_gameplay.plan_purchase
                intent=planner(self.rt.accounts.npc_gameplay,body,proof,current,
                    request_id=cmd.request_id,now_ms=int(time.monotonic()*1000),deadline_ms=int(cmd.deadline*1000))
                handler=runtime_storage.repair_role_equipment if kind==npc_repairs.REPAIR_EQUIPMENT else npc_gameplay.purchase
            if handler in (npc_shop_sales.settle,npc_gameplay.purchase):
                return await self.io(runtime_storage.npc_asset_operation,self.rt.accounts,self.inventory,intent,handler)
            return await self.io(handler,self.rt.accounts,self.inventory,intent)
        if kind in (VISIT_NPC,NPC_SERVICE):
            if not self.joined: raise ValueError('NPC interaction waits for world initialization')
            self.master_dialogue_ticket=None
            self.cart_dialogue_ticket=None
            self.touch_dialogue_ticket=None
            self.task_battle_ticket=None
            self.first_skill_ticket=None
            if kind==VISIT_NPC: self.npc_depot_ticket=None
            if kind==NPC_SERVICE:
                key,service=read_npc_service(body)
                visit=struct.pack('>q',key)
            else:
                visit=body
                service=None
            proof,current=await self.rt.map(self.map_address).mailbox.call('npc',
                self.id,self.epoch,self.position.version,visit,request_id=cmd.request_id,deadline=cmd.deadline)
            # Native task entries use vector 2 and CCommit, not generic service IDs.
            if service is not None:
                command=self.rt.accounts.npc_gameplay.services.plan(body,proof,current,
                    request_id=cmd.request_id,now_ms=int(time.monotonic()*1000),deadline_ms=int(cmd.deadline*1000))
                if command.handler=='warehouse.open':
                    return await self.depot_request(cmd,npc_depot.OPEN_DEPOT,visit)
                if command.handler=='transport.depart':
                    target=npc_gameplay.transport_destination(self.rt.accounts.npc_gameplay,command,self.role['school'])
                    offer=await self.rt.map(self.map_address).mailbox.call('scripted_transfer',
                        self.id,self.epoch,self.position.version,target,request_id=cmd.request_id,deadline=cmd.deadline)
                    self.npc_depot_ticket=None
                    return await self.handoff(offer)
                if command.handler=='items.sell':
                    return await self.io(npc_shop_sales.cache_messages,self.rt.accounts,self.inventory,proof.npc_id)
                if command.handler=='role.heal':
                    return await self.io(npc_role_healing.settle,self.rt.accounts,self.inventory,command)
                if command.handler.startswith('recovery.'):
                    return await self.io(runtime_storage.npc_recover_resources,self.rt.accounts,self.inventory,
                        npc_recovery.RecoveryIntent(command,{3:1,10:2,11:3,12:4}[service]))
                if command.handler not in ('shop.open','equipment.repair'): raise ValueError('NPC service handler unavailable')
                # Original service2 opens its shop locally and sends CBuyItemFromNpc.
                return []
            connection=self.rt.connections[self.id]
            if (proof.address.map_id,proof.npc_id)==(1501,10908):
                proof,current,map_generation,movement_state=await self.rt.map(self.map_address).mailbox.call(
                    'quest_npc',self.id,self.epoch,self.position.version,body,
                    request_id=cmd.request_id,deadline=cmd.deadline)
                await self.checkpoint()
                now_ms=int(time.monotonic()*1000)
                opening=await self.io(task_pve_runtime_storage.dialogue,self.rt.accounts,
                    self.account_id,self.id,self.epoch,proof,current,connection.generation,
                    map_generation,now_ms,now_ms+60000,movement_state)
                if opening is not None:
                    self.conversation.cancel()
                    self.task_battle_ticket=opening.ticket
                    return list(opening.messages)
                teaching=await self.io(task_pve_runtime_storage.skill_dialogue,self.rt.accounts,
                    self.account_id,self.id,self.epoch,proof,current,connection.generation,
                    map_generation,now_ms,movement_state)
                if teaching is not None:
                    self.conversation.cancel()
                    self.first_skill_ticket=teaching.ticket
                    return list(teaching.messages)
            master=await self.io(runtime_storage.master_dialogue,self.rt.accounts,self.account_id,self.id,
                self.epoch,proof,current,connection.generation,int(time.monotonic()*1000))
            if master is not None:
                self.conversation.cancel()
                self.master_dialogue_ticket=master.ticket
                return list(master.messages)
            now_ms=int(time.monotonic()*1000)
            cart=await self.io(runtime_storage.cart_dialogue,self.rt.accounts,self.account_id,self.id,
                self.epoch,proof,current,connection.generation,now_ms,now_ms+60000)
            if cart is not None:
                self.conversation.cancel()
                self.cart_dialogue_ticket=cart.ticket
                return list(cart.messages)
            if self.rt.prologue_touch and (proof.address.map_id,proof.npc_id)==(1006,10498):
                await self.checkpoint()
                touch=await self.io(runtime_storage.prologue_dialogue,self.rt.accounts,self.account_id,self.id,
                    self.epoch,proof,current,connection.generation,int(time.monotonic()*1000))
                if touch is not None:
                    self.conversation.cancel()
                    self.touch_dialogue_ticket=touch
                    return list(touch.messages)
            actor,snapshot=await self.io(runtime_storage.task_state,self.rt.accounts,self.account_id,self.id,self.epoch)
            messages=self.conversation.menu_messages(actor,snapshot,proof,current,
                now_ms=int(time.monotonic()*1000),deadline_ms=int(time.monotonic()*1000)+60000)
            cache=await self.io(npc_shop_sales.cache_messages,self.rt.accounts,self.inventory,proof.npc_id)
            return cache+npc_gameplay.merge_menu(self.rt.accounts.npc_gameplay,messages,proof,current)
        if kind in TASK_INTENT_TYPES:
            intent=decode_task_intent(kind,body)
            current=await self.rt.map(self.map_address).mailbox.call('location',self.id,self.epoch)
            if self.first_skill_ticket is not None and intent.task_id==self.first_skill_ticket.task_id:
                if kind!=C_COMMIT_SCENARIO_QUEST:
                    raise ValueError('Teaching requires its original commit request')
                connection=self.rt.connections[self.id]
                proof,current,map_generation,movement_state=await self.rt.map(self.map_address).mailbox.call(
                    'quest_npc',self.id,self.epoch,self.position.version,struct.pack('>q',intent.npc_key),
                    request_id=cmd.request_id,deadline=cmd.deadline)
                await self.checkpoint()
                committed=await self.io(task_pve_runtime_storage.skill_complete,self.rt.accounts,
                    self.account_id,self.id,self.epoch,self.first_skill_ticket,intent,proof,current,
                    connection.generation,map_generation,int(time.monotonic()*1000),movement_state)
                await self.publish_committed_role(committed.role)
                return list(committed.packets)
            if self.touch_dialogue_ticket is not None and intent.task_id==self.touch_dialogue_ticket.intent.task_id:
                pending=self.touch_dialogue_ticket
                connection=self.rt.connections[self.id]
                proof,current=await self.rt.map(self.map_address).mailbox.call('npc',self.id,self.epoch,
                    self.position.version,struct.pack('>q',intent.npc_key),request_id=cmd.request_id,deadline=cmd.deadline)
                accepted=await self.io(runtime_storage.prologue_authorize,self.rt.accounts,self.account_id,self.id,
                    self.epoch,pending.intent,intent,current,proof,connection.generation,int(time.monotonic()*1000))
                await self.checkpoint()
                offer=await self.rt.map(self.map_address).mailbox.call('authorized_transfer',self.id,self.epoch,
                    accepted.source,accepted.target_position,accepted.deadline_ms,request_id=accepted.request_id)
                return await self.handoff(offer,touch_intent=accepted,touch_record=pending.directory)
            if self.cart_dialogue_ticket is not None and intent.task_id==self.cart_dialogue_ticket.task_id:
                connection=self.rt.connections[self.id]
                resolved=await self.io(runtime_storage.cart_authorize,self.rt.accounts,self.account_id,self.id,
                    self.epoch,self.cart_dialogue_ticket,intent,current,connection.generation,int(time.monotonic()*1000))
                # The new task/world transaction requires an exact durable
                # source, including its position version; no legacy lag option.
                await self.checkpoint()
                accepted=resolved.intent
                offer=await self.rt.map(self.map_address).mailbox.call('authorized_transfer',
                    self.id,self.epoch,accepted.source,resolved.target_position,accepted.deadline_ms,
                    request_id=accepted.request_id)
                return await self.handoff(offer,cart_intent=accepted)
            if self.master_dialogue_ticket is not None and intent.task_id==self.master_dialogue_ticket.task_id:
                connection=self.rt.connections[self.id]
                return list(await self.io(runtime_storage.master_authorize,self.rt.accounts,self.account_id,self.id,
                    self.epoch,self.master_dialogue_ticket,intent,current,connection.generation,int(time.monotonic()*1000)))
            actor,snapshot=await self.io(runtime_storage.task_state,self.rt.accounts,self.account_id,self.id,self.epoch)
            if kind==C_COMMIT_SCENARIO_QUEST and intent.task_id not in snapshot.active:
                proof,current=await self.rt.map(self.map_address).mailbox.call('npc',self.id,self.epoch,
                    self.position.version,struct.pack('>q',intent.npc_key),request_id=cmd.request_id,deadline=cmd.deadline)
                acceptance=self.conversation.plan_accept(actor,snapshot,intent,proof,current,
                    now_ms=int(time.monotonic()*1000),deadline_ms=int(time.monotonic()*1000)+60000)
                await self.io(runtime_storage.commit_task,self.rt.accounts,self.account_id,self.id,self.epoch,
                              actor,acceptance,cmd.request_id)
                self.conversation.open(actor,acceptance.after,intent.task_id,proof,current,
                    now_ms=int(time.monotonic()*1000),deadline_ms=int(time.monotonic()*1000)+60000)
                return list(self.conversation.acceptance_messages(acceptance,proof.entity_key)+
                            self.conversation.opening_messages())
            plan=self.conversation.plan_finish(actor,snapshot,intent,current,now_ms=int(time.monotonic()*1000))
            committed=await self.io(runtime_storage.complete_conversation,self.rt.accounts,self.account_id,self.id,
                self.epoch,actor,plan,cmd.request_id,self.rt.task_resources,self.inventory,self.rt.prologue_touch)
            completion=committed.completion
            self.conversation.acknowledge(plan)
            await self.publish_committed_role(committed.role)
            self.rt.log(event='task_committed',role_id=self.id,task_id=plan.task_id,
                        request_id=cmd.request_id,pending_channels=len(completion.rewards.pending))
            return list(completion_messages(completion))+list(committed.extra_messages)
        if kind in TASK_TYPES:
            actor,snapshot=await self.io(runtime_storage.task_state,self.rt.accounts,self.account_id,self.id,self.epoch)
            domain=TaskDomain(self.rt.task_resources)
            if kind==C_REQUEST_QUEST_CAN_ACCEPT:
                decode_empty_request(body)
                ids = domain.available(actor,snapshot)
                return [(S_REQUEST_QUEST_CAN_ACCEPT,encode_quest_can_accept(ids))]
            ident,tracked = decode_track_quest(body)
            plan=domain.plan(actor,snapshot,'track',ident,tracked=tracked)
            await self.io(runtime_storage.commit_task,self.rt.accounts,self.account_id,self.id,self.epoch,
                          actor,plan,cmd.request_id)
            return [(S_TRACK_QUEST,encode_track_quest(ident,tracked))]
        if kind in INVENTORY_TYPES:
            if kind in (EQUIP_ITEM,UNEQUIP_ITEM):
                if not self.joined:raise ValueError('Equipment waits for world initialization')
                committed=await self.io(runtime_storage.equip_role,self.rt.accounts,self.account_id,self.id,
                    self.epoch,self.inventory,kind,body,cmd.request_id)
                await self.publish_committed_role(committed.role)
                return list(committed.action.messages)
            if (kind==QUERY_BAG and len(body)==12 and struct.unpack_from('>i',body)[0]==2
                    or kind==MOVE_ITEM and len(body)==32 and
                    (struct.unpack_from('>i',body)[0]==2 or struct.unpack_from('>i',body,12)[0]==2)):
                return await self.depot_request(cmd,kind,body)
            if kind==USE_ITEM:
                if len(body)!=16:
                    raise ValueError('Invalid use-item request layout')
                key,target_kind,target_id=struct.unpack('>iiQ',body)
                if key<=0:
                    raise ValueError('Invalid use-item key')
                if target_kind==0:
                    if target_id!=self.id:
                        raise ValueError('Role medicine target ownership mismatch')
                    return await self.io(self.inventory.receive_role_consumable,
                                         body,self.epoch,cmd.request_id)
            return await self.io(runtime_storage.receive_inventory,self.rt.accounts,self.inventory,kind,body,
                cmd.request_id,int(time.monotonic()*1000))
        if kind in SOCIAL_TYPES and self.joined:
            command = SocialCommand(self.id,self.epoch,cmd.request_id,int(time.time()*1000)+5000,kind,body)
            await self.rt.social_runtime.request(self.snapshot(),command,int(time.time()*1000),self.snapshot_revision)
            return []
        self.rt.log(event='unimplemented_message',role_id=self.id,type=kind,size=len(body))
        return []

    async def depot_request(self,cmd,kind,body):
        if not self.joined: raise ValueError('Warehouse waits for world initialization')
        opening=kind==npc_depot.OPEN_DEPOT
        ticket=self.npc_depot_ticket
        if opening:
            self.npc_depot_ticket=None
            if len(body)!=8: raise ValueError('Invalid warehouse open request')
            key=struct.unpack('>q',body)[0]
        else:
            if ticket is None or int(time.monotonic()*1000)>=ticket.deadline_ms:
                self.npc_depot_ticket=None
                raise ValueError('Warehouse access expired or was not opened')
            key=ticket.entity_key
            if kind in npc_depot.MONEY_TYPES and npc_depot.decode_money(kind,body)[0]!=key:
                raise ValueError('Warehouse transfer NPC differs from current access')
        proof,current=await self.rt.map(self.map_address).mailbox.call('npc',
            self.id,self.epoch,self.position.version,struct.pack('>q',key),
            request_id=cmd.request_id,deadline=cmd.deadline)
        if not opening and (ticket.address,ticket.position_version,ticket.npc_id)!=(
                current.address,current.version,proof.npc_id):
            self.npc_depot_ticket=None
            raise ValueError('Warehouse access is from an old map position')
        command=self.rt.accounts.npc_gameplay.services.plan(struct.pack('>qi',key,6),proof,current,
            request_id=cmd.request_id,now_ms=int(time.monotonic()*1000),deadline_ms=int(cmd.deadline*1000))
        result=await self.io(runtime_storage.depot_operation,self.rt.accounts,self.inventory,command,kind,body)
        if opening:
            self.npc_depot_ticket=replace(command,deadline_ms=int(time.monotonic()*1000)+60000)
        return result

    def snapshot(self):
        r=self.role
        address=self.map_address
        if address is None or address.map_id!=self.position.value[0]:
            raise ValueError('Social snapshot requires the current full map identity')
        return RoleSnapshot(self.id,self.epoch,r['name'],r['level'],r['school'],r['shape'],address.map_id,
            (address.map_id,address.instance_id,address.partition_id))

    @property
    def newbie_pending(self):
        return self.newbie_chapter is not None and self.newbie_chapter.phase!='completed'

    def adopt_load_profile(self,profile):
        state=profile.role
        if (state.role_id,state.epoch)!=(self.id,self.epoch): raise StaleEpoch('Loaded role profile scope mismatch')
        if (self.role['level'],self.role.get('experience'))!=(state.level,state.experience):
            self.snapshot_revision+=1
        self.role['level'],self.role['experience']=state.level,state.experience

    async def publish_committed_role(self,state):
        self.valid()
        if (state.role_id,state.epoch)!=(self.id,self.epoch): raise StaleEpoch('Committed role scope mismatch')
        self.role['level'],self.role['experience']=state.level,state.experience
        self.snapshot_revision+=1
        if self.id in self.rt.online:
            old=self.rt.online[self.id]
            snapshot=self.snapshot()
            self.rt.index(old,False)
            self.rt.online[self.id]=snapshot
            self.rt.index(snapshot,True)
            await self.rt.social_runtime.publish(snapshot,self.snapshot_revision)

    async def handoff(self,offer,*,cart_intent=None,touch_intent=None,touch_record=None):
        if cart_intent is not None and touch_intent is not None:raise ValueError('One task owns a scene transfer')
        self.touch_dialogue_ticket=None
        self.task_battle_ticket=None
        self.first_skill_ticket=None
        if (self.map_address,self.position.value,self.position.version)!=(
                offer.source.address,offer.source.position,offer.source.version):
            raise StaleEpoch('Transfer offer differs from the current complete source')
        source=self.rt.map(offer.source.address)
        if touch_intent is not None:
            if touch_record is None or touch_record.address!=touch_intent.target_address or touch_record.role_id!=self.id:
                raise ValueError('Touch transfer requires its exact committed directory identity')
            target=await self.rt.story_maps.get_map(touch_record,request_id=touch_intent.request_id,
                deadline_ms=self.rt.story_maps.now()+max(1,touch_intent.deadline_ms-int(time.monotonic()*1000)))
        else:target=self.rt.map(offer.target_position[0])
        reservation=frozen=receipt=None
        await source.mailbox.call('invalidate_movement',self.id,self.epoch)
        await self.io(world_transfer_storage.begin,self.rt.accounts,self.account_id,self.id,self.epoch,offer)
        try:
            reservation=await target.mailbox.call('reserve',offer)
            frozen=await source.mailbox.call('freeze',reservation)
            receipt=await target.mailbox.call('activate',frozen)
        except (ValueError,Backpressure) as error:
            if reservation:
                cancellation=await target.mailbox.call('cancel',reservation)
                await self.io(world_transfer_storage.cancel,self.rt.accounts,self.account_id,self.id,self.epoch,offer.transfer_id)
                if frozen:
                    location=await source.mailbox.call('resume',cancellation)
                    self.position=Position(self.id,self.epoch,location.position,location.version,
                                           (location.x//16,location.y//16))
                    self.map_address=location.address
                await target.mailbox.call('retire_receipt',cancellation)
            else:
                await self.io(world_transfer_storage.cancel,self.rt.accounts,self.account_id,self.id,self.epoch,offer.transfer_id)
            self.dirty=True
            raise ConnectionError('Cancelled scene transfer requires a new movement declaration') from error
        committed_cart=None
        try:
            if cart_intent is None and touch_intent is None:
                await self.io(world_transfer_storage.commit,self.rt.accounts,self.account_id,self.id,self.epoch,receipt)
            else:
                connection=self.rt.connections[self.id]
                operation=runtime_storage.complete_prologue_transfer if touch_intent is not None else runtime_storage.complete_cart_transfer
                committed_cart=await self.io(operation,self.rt.accounts,
                    self.account_id,self.id,self.epoch,touch_intent if touch_intent is not None else cart_intent,receipt,self.inventory,
                    connection.generation,int(time.monotonic()*1000))
        except Exception:
            self.poisoned=True
            self.rt.log(event='transfer_outcome_requires_recovery',role_id=self.id,transfer_id=offer.transfer_id)
            raise
        try:
            await source.mailbox.call('finalize',receipt)
            await source.mailbox.call('retire_receipt',receipt)
        except Exception:
            self.poisoned=True
            self.rt.log(event='transfer_finalize_requires_recovery',role_id=self.id,transfer_id=offer.transfer_id)
            raise
        old=self.rt.online.get(self.id)
        if old: self.rt.index(old,False)
        location=receipt.location
        self.position=Position(self.id,self.epoch,location.position,location.version,(location.x//16,location.y//16))
        self.map_address=location.address
        self.transfer=receipt
        self.scene_token=uuid.uuid4().hex
        self.dirty=False
        self.conversation.cancel()
        self.master_dialogue_ticket=None
        self.cart_dialogue_ticket=None
        self.rt.online.pop(self.id,None)  # Join channel indexes after loading ack.
        if committed_cart is not None:
            await self.publish_committed_role(committed_cart.role)
        body=(committed_cart.scene_body if committed_cart is not None else scene_entry(location.position,reason=0))
        connection=self.rt.connections[self.id]
        declaration=None
        if location.address.map_id not in self.rt.movement_policy['skip_maps']:
            declaration=(await self.movement_message(ENTER_SCENE,body,'normal_scene')).barrier
        elif not self.rt.movement_policy['special_normalization']:
            raise ValueError('Special scene movement normalization is unavailable')
        barrier=SceneSendBarrier(self.id,self.epoch,connection.generation,offer.transfer_id,location.version,body,
                                 declaration)
        messages=list(committed_cart.action.messages) if committed_cart is not None else []
        return messages+[SceneMessage(ENTER_SCENE,body,barrier)]

    async def retire_old_transfer(self,decision):
        """Retire fenced memberships via public map Interfaces, before new join.

        Storage has committed its final decision under this new lease. No map
        is invented for recovery and no private world dictionary is inspected.
        """
        connection=self.rt.connections.get(self.id)
        if connection is None:raise StaleEpoch('Recovery connection has left')
        generation=connection.generation
        def valid():
            self.valid()
            if (self.rt.connections.get(self.id) is not connection or connection.closed
                    or connection.epoch!=self.epoch or connection.generation!=generation):
                raise StaleEpoch('Recovery connection generation changed')
        async def inspect(owner):
            valid()
            snapshot=await owner.mailbox.call('inspect_transfer',self.id,decision.transfer_id)
            valid()
            return snapshot
        async def retire(owner,snapshot):
            valid()
            result=await owner.mailbox.call('retire_recovered_transfer',snapshot,decision)
            valid()
            return result
        source=self.rt.registered_map(decision.source.address)
        target_address=(decision.receipt.location.address if decision.receipt is not None else None)
        if source is not None:
            result=await retire(source,await inspect(source))
            target_address=result.target_address or target_address
        if target_address is not None:
            target=self.rt.registered_map(target_address)
            if target is not None and target is not source:
                await retire(target,await inspect(target))
        else:
            # A prepared target may exist before source.freeze records its
            # address. Inspect only registered instances of that target map;
            # strict retirement validates the exact matching transfer record.
            candidates=tuple(owner for owner in self.rt.maps.values()
                if owner is not source and owner.domain.address.map_id==decision.target_position[0])
            for target in candidates:
                snapshot=await inspect(target)
                if snapshot.incoming is not None or snapshot.departure is not None:
                    await retire(target,snapshot)
        valid()

    def validate_movement_delivery(self,declaration):
        connection=self.rt.connections.get(self.id)
        if (type(declaration) is not MovementDeclaration or not connection or connection.closed
                or declaration.location.role_id!=self.id or declaration.location.login_epoch!=self.epoch
                or declaration.location.address!=self.map_address
                or declaration.connection_generation!=connection.generation
                or declaration.scene_token!=self.scene_token):
            raise StaleEpoch('Foreign or stale movement send declaration')

    async def movement_message(self,kind,body,source):
        target=self.rt.map(self.map_address)
        connection=self.rt.connections[self.id]
        location=await target.mailbox.call('location',self.id,self.epoch)
        declaration=await target.mailbox.call('declare_movement',self.id,self.epoch,
            location,connection.generation,self.scene_token,kind,body,source)
        return SceneMessage(kind,body,declaration)

    async def normal_location_message(self,source):
        location=await self.rt.map(self.map_address).mailbox.call('location',self.id,self.epoch)
        body=struct.pack('>QhhB',self.id,location.x,location.y,0)
        return await self.movement_message(SET_ROLE_LOCATION,body,source)

    async def entry_movement_messages(self,body):
        if self.map_address.map_id not in self.rt.movement_policy['skip_maps']:
            return [await self.movement_message(ENTER_SCENE,body,'normal_scene')]
        # ConnectionOwner drains the preceding Scene before writing this
        # separate explicit normal-state command. The Scene itself grants none.
        return [(ENTER_SCENE,body),await self.normal_location_message('special_scene_normalization')]

    async def scene_ready(self,movement=None):
        receipt=self.transfer
        if movement is not None:self.validate_movement_delivery(movement)
        elif (self.map_address.map_id not in self.rt.movement_policy['skip_maps']
                or not self.rt.movement_policy['special_normalization']):
            raise StaleEpoch('Scene has no authorized movement declaration')
        location=await self.rt.map(self.map_address).mailbox.call('ready',receipt.location)
        if movement is not None:
            await self.rt.map(self.map_address).mailbox.call('movement_sent',self.id,self.epoch,movement,True)
        self.position=Position(self.id,self.epoch,location.position,location.version,(location.x//16,location.y//16))
        self.map_address=location.address
        await self.checkpoint()
        await self.rt.map(location.address).mailbox.call('retire_receipt',receipt)
        self.transfer=None
        self.require_move_start=True
        self.snapshot_revision+=1
        self.rt.online[self.id]=self.snapshot()
        self.rt.index(self.snapshot(),True)
        await self.rt.social_runtime.join(self.snapshot(),self.snapshot_revision)
        messages=list(await self.rt.map(location.address).mailbox.call('spawn',self.id,self.epoch))
        if movement is None:messages.append(await self.normal_location_message('special_scene_normalization'))
        return messages

    async def finish_battle(self, finished):
        if finished is not None:
            owner=self.battle
            messages=[]
            if owner.task_ticket is not None:
                committed=await self.io(task_pve_runtime_storage.settle,self.rt.accounts,
                    self.account_id,self.id,self.epoch,owner.key)
                await self.publish_committed_role(committed.role)
                messages=list(committed.packets)
            elif owner.wild_ticket:
                committed=await self.io(wild_runtime_storage.settle,self.rt.accounts,self.account_id,self.id,self.epoch,owner.key)
                await self.publish_committed_role(committed.role)
                messages=list(committed.packets)
                self.wild.finished(owner.wild_ticket,owner.key,now_ms=int(time.monotonic()*1000))
            self.battle=None
            self.rt.battles.pop(owner.key,None)
            await owner.close()
            if self.battle_normal_resume:
                self.battle_normal_resume=False
                connection=self.rt.connections.get(self.id)
                if connection is not None and not connection.closed and connection.epoch==self.epoch:
                    messages.append(await self.normal_location_message('confirmed_normal_battle_completed'))
            self.rt.log(event='task_battle_finished' if owner.task_ticket is not None else
                        'wild_battle_finished' if owner.wild_ticket else 'training_battle_finished',role_id=self.id,battle_id=finished.battle_id,
                        settlement_id=getattr(finished,'settlement_id',''),
                        reason=getattr(finished,'reason',getattr(finished,'outcome','completed')),
                        rewards='committed' if owner.wild_ticket or owner.task_ticket is not None else 'zero; training')
            return messages
        return []

    async def battle_step(self,operation,*args):
        owner=self.battle
        retrying=self.pending_battle_delivery is not None
        if self.pending_battle_delivery is None:
            packets,finished=await owner.call(operation,*args)
            if not packets and finished is None:return []
            self.pending_battle_delivery=(tuple(packets),finished)
        packets,finished=self.pending_battle_delivery
        if owner.task_ticket is not None:
            snapshot=await owner.call('snapshot')
            await self.io(task_pve_runtime_storage.checkpoint,self.rt.accounts,
                self.account_id,self.id,self.epoch,snapshot,finished)
        elif owner.wild_ticket:
            snapshot=await owner.call('snapshot')
            await self.io(wild_runtime_storage.checkpoint,self.rt.accounts,self.account_id,self.id,self.epoch,snapshot,finished)
        messages=await self.finish_battle(finished)
        self.pending_battle_delivery=None
        if operation=='close' and retrying and self.battle is not None:
            # Retrying a nonterminal playback is not the requested disconnect.
            messages+=await self.battle_step('close',*args)
        return list(packets)+messages

    async def start_task_battle(self,cmd,body):
        request=decode_task_battle_request(body)
        pending=self.task_battle_ticket
        if (not self.joined or pending is None
                or request.task_id!=pending.battle_ticket.task_id
                or request.npc_key!=pending.battle_ticket.entity_key):
            raise ValueError('Task battle requires the current original NPC dialogue')
        connection=self.rt.connections[self.id]
        proof,current,map_generation,movement_state=await self.rt.map(self.map_address).mailbox.call(
            'quest_npc',self.id,self.epoch,self.position.version,struct.pack('>q',request.npc_key),
            request_id=cmd.request_id,deadline=cmd.deadline)
        await self.checkpoint()
        try:
            participant=await self.io(task_pve_runtime_storage.participant,self.rt.accounts,
                self.account_id,self.id,self.epoch,connection.generation)
        except ValueError:
            notice=visible_notice('当前角色战斗资料或先前战斗结果尚未准备好，请重新登录后再试。')
            return [(notice.kind,notice.body)]
        owner=ScheduledBattle(self.role,self.epoch,connection.generation,participant.attribute_version,
            participant=participant,task_ticket=pending,
            task_definition=self.rt.accounts.task_battle_resources.definitions[request.task_id],
            task_rules=self.rt.accounts.task_pve_rules)
        try:
            # Pure opening bytes are preflighted while the owner is unpublished;
            # no client command, timer or delivery reaches it before admission.
            opening=await owner.call('opening')
            admission=await self.io(task_pve_runtime_storage.admit,self.rt.accounts,self.account_id,
                participant,pending,request,proof,current,owner.key,
                map_generation,int(time.monotonic()*1000),movement_state)
            if admission.replayed:
                raise ValueError('Existing task admission must recover its original battle')
        except ValueError:
            await owner.close()
            notice=visible_notice('任务对话已变化，请重新与说书人交谈后开始战斗。')
            return [(notice.kind,notice.body)]
        except BaseException:
            await owner.close()
            raise
        self.task_battle_ticket=None
        self.first_skill_ticket=None
        self.conversation.cancel()
        self.battle=owner;self.rt.battles[owner.key]=owner
        self.battle_normal_resume=await self.rt.map(self.map_address).mailbox.call(
            'suspend_movement',self.id,self.epoch)
        self.rt.log(event='task_battle_started',role_id=self.id,battle_id=owner.key,
                    task_id=request.task_id,ai_id=8001,map_id=current.address.map_id)
        return opening

    async def wild_move(self,previous,movement):
        now=int(time.monotonic()*1000)
        if self.wild is None or self.wild.location!=previous:
            self.wild=WildEncounters(previous,self.rt.accounts.wild_rules,now_ms=now,rng=random.SystemRandom())
        ticket=self.wild.accepted_move(previous,movement,now_ms=now,eligible=self.joined and not self.rt.training)
        if ticket is None:return []
        owner=None
        try:
            participant=await self.io(wild_runtime_storage.participant,self.rt.accounts,self.account_id,self.id,
                self.epoch,self.rt.connections[self.id].generation)
            owner=ScheduledBattle(self.role,self.epoch,participant.connection_generation,self.position.version,
                participant=participant,ticket=ticket)
            await self.io(wild_runtime_storage.admit,self.rt.accounts,self.account_id,participant,ticket,owner.key)
        except ValueError as error:
            if owner:await owner.close()
            self.wild.rejected(ticket,now_ms=int(time.monotonic()*1000))
            self.rt.log(event='wild_encounter_declined',role_id=self.id,reason=str(error))
            return []
        self.wild.accepted(ticket,owner.key)
        self.battle_normal_resume=await self.rt.map(self.map_address).mailbox.call(
            'suspend_movement',self.id,self.epoch)
        self.battle=owner;self.rt.battles[owner.key]=owner
        self.rt.log(event='wild_battle_started',role_id=self.id,battle_id=owner.key,
            map_id=ticket.location.address.map_id,monster_id=ticket.monster.template_id)
        return await owner.call('opening')

    async def checkpoint(self):
        p=self.position
        await self.io(self.rt.accounts.save_checkpoint,self.account_id,self.id,self.epoch,p.value,p.version)
        self.dirty=False
        self.last_checkpoint=time.monotonic()


class ConnectionOwner:
    """Single target-owned send pump, frame/byte limits and epoch validation."""
    def __init__(self, runtime, writer, capacity=128, byte_capacity=1024*1024):
        if type(capacity) is not int or capacity<1 or type(byte_capacity) is not int or byte_capacity<1:
            raise ValueError('Positive connection queue limits required')
        self.rt,self.writer,self.codec=runtime,writer,ConnectionCodec()
        self.id=uuid.uuid4().hex
        self.generation=uuid.uuid4().int >> 65
        self.queue=asyncio.Queue(maxsize=capacity)
        self.byte_capacity,self.pending_bytes=byte_capacity,0
        self.role_id=self.epoch=None
        self.closed=False
        self.cleanup_started=False
        self.cleanup_done=asyncio.Event()
        self.last_input=time.monotonic()
        self.metrics=Counter()
        self.scene_generation=0
        self.partial_generation=None
        self.pump=asyncio.create_task(self._send(),name='send:'+self.id)
        self.rt.clients.add(self)
        self.offer(None,self.codec.opening())

    def offer(self, kind, body, epoch=None, barrier=None,delivery=None,fence=None):
        if self.closed or (epoch is not None and (epoch!=self.epoch or self.rt.connections.get(self.role_id) is not self)):
            self.metrics['stale_delivery']+=1
            return False
        size=len(body)+10
        if self.queue.full() or self.pending_bytes+size>self.byte_capacity:
            self.metrics['send_rejected']+=1
            self.closed=True
            self.writer.close()  # Disconnect slow target; never block a broadcaster.
            return False
        self.queue.put_nowait((kind,bytes(body),epoch,size,barrier,delivery,fence))
        self.pending_bytes+=size
        self.metrics['send_high_water']=max(self.metrics['send_high_water'],self.queue.qsize())
        return True

    async def offer_message(self,message,epoch):
        kind,body=message
        accepted=self.offer(kind,body,epoch,getattr(message,'barrier',None),
            getattr(message,'delivery',None),getattr(message,'fence',None))
        if not accepted and isinstance(message,ScopedSceneMessage):
            await self.cleanup_delivery(message.delivery)
        return accepted

    async def _offer_batch(self,messages,*,advance_scene=False):
        # Each consumed item is owned by its queue or offer_message cleanup.
        # Only the unconsumed suffix remains the batch caller's responsibility.
        remaining=iter(messages)
        try:
            for message in remaining:
                if advance_scene and getattr(message,'barrier',None) is not None:
                    self.scene_generation+=1
                await self.offer_message(message,self.epoch)
        finally:
            cleanup=tuple(self.cleanup_delivery(getattr(message,'delivery',None))
                for message in remaining)
            if cleanup:
                await asyncio.shield(asyncio.gather(*cleanup,return_exceptions=True))

    async def cleanup_delivery(self,delivery):
        if delivery is None:return
        try:await self.rt.story_maps.finish_delivery(delivery)
        except (ValueError,KeyError,TimeoutError,Backpressure):
            self.metrics['scene_cleanup_failed']+=1
            self.rt.log(event='scene_cleanup_requires_recovery',connection=self.id)

    async def _send(self):
        try:
            while True:
                kind,body,epoch,size,barrier,delivery,fence=await self.queue.get()
                try:
                    if self.closed: continue
                    if epoch is not None and (epoch!=self.epoch or self.rt.connections.get(self.role_id) is not self):
                        self.metrics['stale_delivery']+=1
                        continue
                    if fence is not None and not self.rt.scene_fence_current(self,fence):
                        self.metrics['stale_scene_delivery']+=1
                        continue
                    if barrier is not None:
                        if type(barrier) not in (MovementDeclaration,SceneSendBarrier):
                            raise ValueError('Unsupported delivery barrier type')
                        declaration=barrier if type(barrier) is MovementDeclaration else barrier.movement
                        if declaration is not None and (kind,body)!=(declaration.kind,declaration.body):
                            raise ValueError('Movement declaration differs from queued message')
                        if type(barrier) is SceneSendBarrier and (kind,body)!=(ENTER_SCENE,barrier.body):
                            raise ValueError('Transfer declaration differs from queued scene')
                        owner=self.rt.roles.get(self.role_id)
                        if not owner or owner.epoch!=self.epoch:raise StaleEpoch('Movement sender expired')
                        if declaration is not None:await owner.mailbox.call('movement_will_send',declaration)
                    packet=body if kind is None else self.codec.send(kind,body)
                    self.writer.write(packet)
                    await asyncio.wait_for(self.writer.drain(),3)
                    if barrier is not None:
                        owner=self.rt.roles.get(self.role_id)
                        if not owner or owner.epoch!=self.epoch: raise StaleEpoch('Scene owner expired')
                        operation='movement_sent' if type(barrier) is MovementDeclaration else 'scene_sent'
                        try:replies=await owner.mailbox.call(operation,barrier)
                        except SupersededMovementDelivery:
                            # The exact bytes were sent, but a current intro or
                            # other explicit lifecycle has since revoked them.
                            # Reject state installation while allowing its new
                            # queued messages to proceed on this same stream.
                            self.metrics['superseded_movement_deliveries']+=1
                            continue
                        self.metrics['scene_send_barriers']+=1
                        await self._offer_batch(await self.rt.scene_messages(owner,replies))
                finally:
                    try:
                        await self.cleanup_delivery(delivery)
                    finally:
                        self.pending_bytes-=size
                        self.queue.task_done()
        except (ConnectionError,TimeoutError,ValueError,Backpressure):
            self.closed=True
            self.writer.close()

    async def receive(self, data):
        batch_generation=self.partial_generation if self.codec.reader.buffer else self.scene_generation
        if batch_generation is None: batch_generation=self.scene_generation
        frames=self.codec.decode(data)
        self.partial_generation=batch_generation if self.codec.reader.buffer else None
        for kind,body in frames:
            if self.closed: return
            if kind==100 and len(body)==4:
                self.offer(kind,body)
                continue
            if batch_generation!=self.scene_generation:
                self.metrics['old_scene_batch_rejected']+=1
                continue
            replies=await self.rt.dispatch(self,kind,body)
            await self._offer_batch(replies,advance_scene=True)

    async def run(self, reader):
        self.rt.log(event='connected',connection=self.id)
        try:
            while not self.closed:
                try: data=await asyncio.wait_for(reader.read(65536),1)
                except TimeoutError:
                    if time.monotonic()-self.last_input>=300: raise TimeoutError('Idle connection')
                    if self.role_id:
                        role=self.rt.roles.get(self.role_id)
                        if role and role.epoch==self.epoch:
                            replies=await role.mailbox.call('tick')
                            await self._offer_batch(await self.rt.scene_messages(role,replies))
                    continue
                if not data: break
                self.last_input=time.monotonic()
                await self.receive(data)
        except (ValueError,ConnectionError,TimeoutError,Backpressure) as exc:
            self.rt.log(event='connection_error',connection=self.id,reason=type(exc).__name__)
        finally:
            await self.close()

    async def close(self):
        if self.cleanup_started:
            await self.cleanup_done.wait()
            return
        self.cleanup_started=True
        try:
            self.closed=True
            self.writer.close()
            self.pump.cancel()
            await asyncio.gather(self.pump,return_exceptions=True)
            while not self.queue.empty():
                _,_,_,size,_,delivery,_=self.queue.get_nowait()
                try:await self.cleanup_delivery(delivery)
                finally:
                    self.pending_bytes-=size
                    self.queue.task_done()
            await self.rt.disconnect(self)
        finally:
            self.rt.clients.discard(self)
            self.rt.log(event='disconnected',connection=self.id)
            self.cleanup_done.set()


class GameRuntime:
    def __init__(self, accounts, prepared, io=None, logger=None, training=False,prologue_touch=False,story_clock=None):
        if type(prologue_touch) is not bool:raise ValueError('Explicit prologue activation required')
        self.prologue_touch=prologue_touch
        self.exit_ui_message=load_exit_ui_message()
        self.accounts=accounts
        self.movement_policy=accounts.movement_policy
        self.task_resources,self.social_store,policy,self.catalog=prepared
        self.social_limits=dict(max_contacts=policy['max_contacts_per_role'],max_text=policy['max_text_characters'])
        self.io=io or BlockingIO()
        self.logger,self.training=logger,training
        self.roles,self.connections,self.maps,self.battles,self.online={},{},{},{},{}
        self.channels={}
        self.members={}
        self.clients=set()
        self.story_maps=RuntimeStoryMaps(accounts.story_instance_rules,self._create_story_map,
            self._forget_story_map,clock=story_clock)
        self.social_runtime=SocialRuntime(self)

    def _create_story_map(self,record):
        if self.registered_map(record.address) is not None:
            raise ValueError('A private projection already exists outside its managed generation')
        owner=MapOwner(record.address,self.catalog,self.accounts.npc_resources,
            interaction_rules=self.accounts.npc_interaction_rules,story_rules=self.accounts.story_instance_rules,
            maze=self.accounts.movement_grids[record.address.map_id],movement_policy=self.movement_policy)
        self.maps[record.address]=owner
        return owner

    def _forget_story_map(self,address,owner):
        if self.registered_map(address) is not owner:raise ValueError('Private projection registry generation changed')
        del self.maps[address]

    def log(self, **event):
        if self.logger: self.logger.emit(**event)

    def online_snapshot(self): return MappingProxyType(dict(self.online))

    def index(self, snapshot, add):
        keys=(('scene',snapshot.scene_key),('school',snapshot.school),('world',0))
        for key in keys:
            # Membership is split into fixed role-key partitions, not one world mailbox.
            partition=(key,snapshot.role_id%16)
            members=self.members.setdefault(partition,{})
            if add: members[snapshot.role_id]=snapshot
            else:
                members.pop(snapshot.role_id,None)
                if not members: self.members.pop(partition,None)

    def map(self, instance):
        address=runtime_map_address(instance)
        if address not in self.maps:
            if address.instance_id>=2**62:raise ValueError('Private map load requires its validated story directory record')
            self.maps[address]=MapOwner(address,self.catalog,getattr(self.accounts,'npc_resources',None),
                interaction_rules=getattr(self.accounts,'npc_interaction_rules',None),
                story_rules=self.accounts.story_instance_rules if address.instance_id>=2**62 else None,
                maze=self.accounts.movement_grids[address.map_id],movement_policy=self.movement_policy)
        return self.maps[address]

    def registered_map(self,address):
        """Exact full-address lookup; recovery never creates a replacement map."""
        return self.maps.get(runtime_map_address(address))

    def scene_fence_current(self,connection,fence):
        owner=self.roles.get(fence.role_id)
        target=self.registered_map(fence.address)
        return (not connection.closed and self.connections.get(fence.role_id) is connection
            and (connection.epoch,connection.generation)==(fence.epoch,fence.connection_generation)
            and owner is not None and owner.epoch==fence.epoch and owner.map_address==fence.address
            and not owner.poisoned and owner.scene_token==fence.scene_token and target is not None
            and ((fence.address.instance_id<2**62 and fence.map_generation is None)
                or (getattr(target,'story_handle',None) is not None
                    and target.story_handle.map_generation==fence.map_generation)))

    async def scene_messages(self,owner,replies):
        """Track every private logical response before it reaches a send queue."""
        if not replies or owner.map_address.instance_id<2**62:return replies
        owner.valid()
        connection=self.connections.get(owner.id)
        if connection is None or connection.closed:return []
        target=self.registered_map(owner.map_address)
        if target is None or getattr(target,'story_handle',None) is None:
            raise ValueError('Private scene response has no managed map generation')
        fence=SceneFence(owner.map_address,target.story_handle.map_generation,owner.id,owner.epoch,
            connection.generation,owner.scene_token)
        messages=[]
        try:
            location=await target.mailbox.call('location',owner.id,owner.epoch)
            for reply in replies:
                kind,body=reply
                delivery=await self.story_maps.begin_delivery(target,location,connection.generation)
                message=ScopedSceneMessage(kind,body,getattr(reply,'barrier',None),delivery,fence)
                messages.append(message)
                if not self.scene_fence_current(connection,fence):raise StaleEpoch('Scene changed while preparing delivery')
            return messages
        except BaseException:
            await asyncio.gather(*(self.story_maps.finish_delivery(message.delivery) for message in messages),
                return_exceptions=True)
            raise

    async def offer_scene_channel(self,snapshot,delivery):
        """Social recipient supplied a frozen, filtered current-channel delivery."""
        if (delivery.scene_key is None or delivery.scene_key!=snapshot.scene_key
                or (delivery.role_id,delivery.login_epoch)!=(snapshot.role_id,snapshot.login_epoch)):
            return False
        owner=self.roles.get(snapshot.role_id);connection=self.connections.get(snapshot.role_id)
        if (owner is None or connection is None or connection.closed or owner.epoch!=snapshot.login_epoch
                or not owner.joined or owner.transfer is not None
                or owner.snapshot().scene_key!=snapshot.scene_key):
            return False
        if owner.map_address.instance_id>=2**62:
            messages=await self.scene_messages(owner,[(delivery.kind,delivery.body)])
            if not messages:return False
            message=messages[0]
        else:
            fence=SceneFence(owner.map_address,None,owner.id,owner.epoch,connection.generation,owner.scene_token)
            message=ScopedSceneMessage(delivery.kind,delivery.body,None,None,fence)
        return await connection.offer_message(message,snapshot.login_epoch)

    async def handle_socket(self, reader, writer):
        await ConnectionOwner(self,writer).run(reader)

    async def dispatch(self, connection, kind, body):
        c=connection.codec
        if c.state=='closing':return []
        if c.state in ('roles','world') and kind in (ROLE_OFFLINE_REQUEST,RETURN_ROLE_LIST_REQUEST,RETURN_LOGIN_REQUEST):
            if body:
                self.log(event='role_control_rejected',type=kind,reason='nonempty_body')
                return []
            previous=connection.role_id
            await self.disconnect(connection)
            connection.role_id=connection.epoch=None
            if kind==RETURN_ROLE_LIST_REQUEST:
                roles=await self.io.run(('account',c.account_id),self.accounts.roles,c.account_id)
                c.state='roles'
                last=previous if any(r['id']==previous for r in roles) else (roles[0]['id'] if roles else 0)
                return [(RETURN_ROLE_LIST,role_list(last,roles))]
            c.state='closing'
            return [(ROLE_OFFLINE if kind==ROLE_OFFLINE_REQUEST else RETURN_LOGIN,b'')]
        if c.state=='response' and kind==103:
            identity,_=c.auth_fields(body)
            account=await self.io.run(('account',identity),self.accounts.account,identity)
            if connection.closed: return []
            connection.offer(None,c.accept_auth(body,account))
            return []
        if c.state=='key_exchange' and kind==106: return [c.accept_key(body)]
        if c.state=='roles':
            if kind==DELETE_ROLE_REQUEST:
                try:
                    rid=parse_delete(body)
                    candidate=await self.io.run(('account',c.account_id),self.accounts.deletion_candidate,c.account_id,rid)
                    # Login reserves the role owner before any await. The DB
                    # compare against this candidate also closes the later race.
                    if rid in self.roles:raise ValueError('Online role cannot be deleted')
                    deleted=await self.io.run(('account',c.account_id),self.accounts.delete_role,candidate)
                    return [(DELETE_ROLE,struct.pack('>Q',deleted))]
                except ValueError:
                    self.log(event='role_delete_rejected',account_id=c.account_id)
                    return []
            if kind==0xc0001:
                if body: raise ValueError('Role list must be empty')
                roles=await self.io.run(('account',c.account_id),self.accounts.roles,c.account_id)
                return [(0xc0002,role_list(roles[0]['id'] if roles else 0,roles))]
            if kind==0xc0003:
                try:
                    role=await self.io.run(('account',c.account_id),self.accounts.create_role,c.account_id,*parse_create(body))
                    return [(0xc0004,role_info(role))]
                except ValueError as exc:
                    return [(0xc0008,struct.pack('>i',4 if str(exc)=='duplicate_name' else 3))]
            if kind in (0xc0078,0xc0005):
                if kind==0xc0078:
                    if len(body)!=8: raise ValueError('Invalid role preflight')
                    rid=struct.unpack('>Q',body)[0]
                else: rid,_,_=parse_enter(body)
                role=await self.io.run(('role',rid),self.accounts.owned_role,c.account_id,rid)
                if not role: raise ValueError('Role ownership mismatch')
                if kind==0xc0078: return [(0xc0079,b'')]
                # Account-scoped mailbox prevents simultaneous login acquisition.
                owner=self.roles.get(rid)
                if owner: raise ValueError('Role already online')
                epoch=uuid.uuid4().hex
                owner=RoleOwner(self,role,c.account_id,epoch)
                self.roles[rid]=owner  # reserve before any await
                try:
                    owner.epoch=await self.io.run(('role',rid),self.accounts.acquire_lease,c.account_id,rid)
                    connection.role_id,connection.epoch=rid,owner.epoch
                    self.connections[rid]=connection
                    replies=await owner.mailbox.call('load')
                    c.state='world'
                    return await self.scene_messages(owner,replies)
                except BaseException:
                    if connection.role_id!=rid:
                        self.roles.pop(rid,None)
                        await owner.mailbox.close()
                    raise
        if c.state=='world':
            owner=self.roles.get(connection.role_id)
            if not owner or owner.epoch!=connection.epoch: raise StaleEpoch('Connection epoch expired')
            try:
                replies=await owner.mailbox.call('receive',kind,body)
                return await self.scene_messages(owner,replies)
            except (InventoryNotReady,ValueError) as exc:
                self.log(event='gameplay_rejected',role_id=owner.id,type=kind,reason=type(exc).__name__)
                return []
        raise ValueError('Protocol stage mismatch')

    async def effects(self, effects):
        for effect in effects:
            if isinstance(effect,(Delivery,RelationWake)):
                self.social_runtime.offer(effect)
            elif isinstance(effect,Publish):
                if effect.scope not in ('scene','school','world'):
                    raise ValueError('Unknown social channel scope')
                for part in range(16):
                    key=((effect.scope,effect.partition_key),part)
                    if key not in self.members: continue
                    if key not in self.channels:
                        async def publish(cmd, membership_key=key):
                            event,=cmd.args
                            snapshots=tuple(self.members.get(membership_key,{}).values())
                            for offset in range(0,len(snapshots),64):
                                for s in snapshots[offset:offset+64]:
                                    if event.scope=='scene':
                                        packet=Delivery(s.role_id,s.login_epoch,event.kind,event.body,scene_key=event.partition_key)
                                    else:packet=Delivery(s.role_id,s.login_epoch,event.kind,event.body)
                                    await self.effects((packet,))
                                await asyncio.sleep(0)
                            return None
                        self.channels[key]=SerialOwner(('channel',key),publish)
                    await self.channels[key].call('publish',effect)

    async def presence(self, rid, online):
        after=0
        while True:
            watchers=await self.io.run(('social',rid),self.social_store.watchers,rid,after,128)
            if not watchers: return
            for watcher in watchers:
                s=self.online.get(watcher)
                if s: await self.effects((Delivery(watcher,s.login_epoch,ONLINE,struct.pack('>Qi',rid,int(online))),))
            after=watchers[-1]
            await asyncio.sleep(0)

    async def disconnect(self, connection):
        rid=connection.role_id
        owner=self.roles.get(rid)
        if not owner or owner.epoch!=connection.epoch: return
        self.connections.pop(rid,None)
        snapshot=self.online.pop(rid,None)
        if snapshot: self.index(snapshot,False)
        try:
            await owner.mailbox.call('close')
        except (ValueError,TimeoutError,Backpressure):
            self.log(event='disconnect_checkpoint_failed',role_id=rid)
        finally:
            await self.social_runtime.leave(rid,owner.epoch)
            await self.io.run(('role',rid),self.accounts.release_lease,rid,owner.epoch)
            await owner.mailbox.close()
            if self.roles.get(rid) is owner: self.roles.pop(rid,None)
        await self.presence(rid,False)

    async def close(self):
        await self.story_maps.stop()
        for connection in tuple(self.clients): await connection.close()
        await self.story_maps.close()
        await self.social_runtime.close()
        for owner in (*self.channels.values(),*(m.mailbox for m in self.maps.values())):
            await owner.close()
        await self.io.close()
