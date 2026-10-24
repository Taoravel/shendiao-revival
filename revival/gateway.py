"""Synchronous offline compatibility Adapter for native protocol regression.

Live routing is game_runtime, with connection_codec owning transport state.
Session.feed and legacy SocialHub must never run on the live network loop.
"""
import hashlib
import hmac
import secrets
import struct
import time
from crypto import ArcFour
from mppc import Encoder
from wire import FrameReader, frame, octets, read_octets
from role_protocol import role_info, role_list, parse_create, parse_enter
from world_protocol import world_snapshot, scene_entry, ENTER_WORLD, ENTER_SCENE, AFTER_ENTER_WORLD
from inventory import Inventory, InventoryNotReady, INVENTORY_TYPES
from world_movement import WorldMovement, MOVEMENT_TYPES
from task_session import TaskSession, TASK_TYPES
from social_protocol import SOCIAL_TYPES
from training_battle import TrainingBattle
from battle_protocol import BATTLE_TYPES

WORLD_MUTATIONS = frozenset(MOVEMENT_TYPES) | frozenset(TASK_TYPES) | frozenset(INVENTORY_TYPES)


class Session:
    def __init__(self, accounts, now_ms=None, social=None, deliver=None, training_battle=False):
        self.accounts = accounts
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))
        self.state = 'response'
        self.challenge = secrets.token_bytes(16)
        self.server_nonce = None
        self.identity = None
        self.account_id = None
        self.secret = None
        self.in_cipher = self.out_cipher = None
        self.encoder = Encoder()
        self.reader = FrameReader()
        self.events = []
        self.social = social
        self.deliver = deliver
        self.role = None
        self.world = None
        self.scene_id = 1007
        self.training_enabled = training_battle
        self.training = None
        self.training_started = False

    def push(self, kind, body):
        if self.deliver:
            self.deliver(self.send(kind, body))

    def close(self):
        if self.training:
            self.training.close()
        if self.social:
            self.social.leave(self)
        self.world = None

    def start_training(self):
        if self.state != 'world' or self.role is None:
            raise ValueError('Training requires an owned role in the world')
        if self.training and self.training.battle.phase != 'ended':
            raise ValueError('Battle already active')
        self.training = TrainingBattle(self.role)
        self.training_started = True
        self.events.append({'event': 'training_battle_started', 'battle_id': self.training.id,
                            'revision': self.training.revision, 'wire_bindings': 'inferred'})
        return [self.send(k, b) for k, b in self.training.opening()]

    def tick(self):
        if self.training:
            return [self.send(k, b) for k, b in self.training.tick()]
        return []

    def opening(self):
        # Real game callers 0x82c44c/0x82c6a0 explicitly pass network version 601.
        return frame(101, octets(self.challenge) + struct.pack('>II', 601, 0) + b'\0\0')

    def send(self, kind, body):
        output = frame(kind, body)
        self.events.append({'event': 'send', 'type': kind, 'size': len(body)})
        if self.out_cipher:
            output = self.out_cipher.transform(self.encoder.encode(output))
        return output

    def feed(self, data):
        if self.in_cipher:
            data = self.in_cipher.transform(data)
        outputs = []
        for kind, body in self.reader.feed(data):
            self.events.append({'event': 'receive', 'state': self.state, 'type': kind, 'size': len(body)})
            if kind == 100 and len(body) == 4:
                outputs.append(self.send(100, body))
                continue
            if self.state == 'response' and kind == 103:
                self.identity, pos = read_octets(body, limit=128)
                proof, pos = read_octets(body, pos, limit=128)
                if pos + 4 > len(body):
                    raise ValueError('Truncated response')
                pos += 4
                _, pos = read_octets(body, pos, limit=4096)
                if pos + 4 > len(body):
                    raise ValueError('Truncated response field')
                pos += 4
                _, pos = read_octets(body, pos, limit=4096)
                if pos != len(body):
                    raise ValueError('Response trailing data')
                account = self.accounts.account(self.identity)
                if not account or not hmac.compare_digest(proof, hmac.new(account[1], self.challenge, hashlib.md5).digest()):
                    raise ValueError('Authentication failed')
                self.account_id, self.secret = account
                self.server_nonce = secrets.token_bytes(16)
                outputs.append(self.send(106, octets(self.server_nonce) + struct.pack('>I', 0)))
                key = hmac.new(self.secret, self.identity + self.server_nonce, hashlib.md5).digest()
                self.in_cipher = ArcFour(key)
                self.state = 'key_exchange'
            elif self.state == 'key_exchange' and kind == 106:
                nonce, pos = read_octets(body, limit=16)
                if len(nonce) != 16 or pos + 4 != len(body):
                    raise ValueError('Invalid client key exchange')
                key = hmac.new(self.secret, self.identity + nonce, hashlib.md5).digest()
                self.out_cipher = ArcFour(key)
                self.state = 'roles'
                # Local bootstrap: authenticated account ID; other fields retain zero defaults.
                outputs.append(self.send(110, struct.pack('>6I', self.account_id, 0, 0, 0, 0, 0)))
                self.events.append({'event': 'authenticated', 'account_id': self.account_id})
            elif self.state == 'roles' and kind == 0xc0001:
                if body:
                    raise ValueError('Role list request must be empty')
                roles = self.accounts.roles(self.account_id)
                outputs.append(self.send(0xc0002, role_list(roles[0]['id'] if roles else 0, roles)))
            elif self.state == 'roles' and kind == 0xc0003:
                name, school, shape = parse_create(body)
                try:
                    role = self.accounts.create_role(self.account_id, name, school, shape)
                except ValueError as error:
                    reason = str(error)
                    code = 4 if reason == 'duplicate_name' else 3
                    outputs.append(self.send(0xc0008, struct.pack('>i', code)))
                    self.events.append({'event': 'create_role_rejected', 'reason': reason, 'school': school, 'shape': shape})
                else:
                    outputs.append(self.send(0xc0004, role_info(role)))
                    self.events.append({'event': 'role_persisted', 'role_id': role['id']})
            elif self.state == 'roles' and kind == 0xc0078:
                if len(body) != 8:
                    raise ValueError('Invalid role entry preflight')
                role_id = struct.unpack('>Q', body)[0]
                if not self.accounts.owned_role(self.account_id, role_id):
                    raise ValueError('Role ownership mismatch')
                # Native SSendIgnoreRole's empty reply continues the entry button.
                # This does not delete a role or change persistent character data.
                outputs.append(self.send(0xc0079, b''))
                self.events.append({'event': 'role_entry_preflight_accepted', 'role_id': role_id})
            elif self.state == 'roles' and kind == 0xc0005:
                role_id, extra, flag = parse_enter(body)
                role = self.accounts.owned_role(self.account_id, role_id)
                if not role:
                    raise ValueError('Role ownership mismatch')
                self.inventory = Inventory(self.accounts, self.account_id, role_id)
                if self.social and role_id in self.social.online:
                    raise ValueError('Role already online')
                self.role = role
                self.world = WorldMovement(self.accounts, self.account_id, role_id)
                self.tasks = TaskSession(self.accounts, self.account_id, role_id)
                self.scene_id = self.world.position[0]
                outputs.append(self.send(ENTER_WORLD, world_snapshot(role)))
                # Native SGameTime creates CActivityListManager before scene entry.
                outputs.append(self.send(0xc0007, struct.pack('>Q', self.now_ms())))
                outputs.append(self.send(ENTER_SCENE, scene_entry(self.world.position)))
                self.state = 'world'
                self.events.append({'event': 'world_bootstrap_sent', 'role_id': role_id, 'map': self.world.position[0]})
            elif self.state == 'world' and kind == AFTER_ENTER_WORLD and not body:
                self.events.append({'event': 'client_after_enter_world', 'map': self.scene_id})
                if self.social:
                    outputs.extend(self.send(k, b) for k, b in self.social.join(self))
                if self.training_enabled and not self.training_started:
                    outputs.extend(self.start_training())
            elif self.state == 'world' and kind in BATTLE_TYPES:
                if self.training:
                    replies = self.training.receive(kind, body)
                    outputs.extend(self.send(k, b) for k, b in replies)
                    if self.training.result is not None:
                        self.events.append({'event': 'training_battle_finished', **self.training.result})
                        self.training = None
                else:
                    self.events.append({'event': 'battle_request_rejected', 'reason': 'no_active_battle'})
            elif (self.state == 'world' and self.training
                  and self.training.battle.phase != 'ended'
                  and kind in WORLD_MUTATIONS):
                self.events.append({'event': 'world_request_rejected', 'reason': 'in_battle', 'type': kind})
            elif self.state == 'world' and kind in MOVEMENT_TYPES:
                event = self.world.receive(kind, body)
                self.events.append(event)
                if event['transferred']:
                    self.scene_id = self.world.position[0]
                    # Zero selects the general scene branch, avoiding first-login
                    # initialization (516015). Live portal presentation pending.
                    outputs.append(self.send(ENTER_SCENE, scene_entry(self.world.position, reason=0)))
            elif self.state == 'world' and kind in TASK_TYPES:
                try:
                    replies = self.tasks.receive(kind, body)
                except ValueError as error:
                    self.events.append({'event': 'task_request_rejected', 'reason': str(error)})
                else:
                    outputs.extend(self.send(k, b) for k, b in replies)
            elif (self.state == 'world' and kind in SOCIAL_TYPES and self.social
                  and self.social.online.get(self.role['id']) is self):
                replies = self.social.handle(self, kind, body)
                if replies is None:
                    self.events.append({'event': 'unimplemented_message', 'type': kind, 'size': len(body)})
                else:
                    outputs.extend(self.send(k, b) for k, b in replies)
            elif self.state == 'world' and kind in INVENTORY_TYPES:
                try:
                    replies = self.inventory.receive(kind, body)
                except InventoryNotReady as error:
                    self.events.append({'event': 'inventory_protocol_pending', 'type': kind, 'reason': str(error)})
                except (ValueError, UnicodeError) as error:
                    self.events.append({'event': 'inventory_request_rejected', 'type': kind, 'reason': str(error)})
                else:
                    outputs.extend(self.send(k, b) for k, b in replies)
            else:
                self.events.append({'event': 'unimplemented_message', 'type': kind, 'size': len(body)})
        return outputs
