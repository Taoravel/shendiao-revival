"""Partition-ready social commands. No Session, cipher, writer or global queue.

Integration owns role-key scheduling and runs SQLite Adapter calls on bounded
persistence resources, outside the network loop. Channel owners consume Publish;
only connection owners encode Delivery after checking the target login epoch.
"""
from contextlib import closing
from dataclasses import dataclass,field
from queue import Queue, Full
import sqlite3
import struct
import uuid
from wire import compact, NeedMoreData
import social_protocol as p


@dataclass(frozen=True)
class RoleSnapshot:
    role_id: int
    login_epoch: int
    name: str
    level: int
    school: int
    shape: int
    scene_id: int
    scene_scope: tuple[int,int,int] | None = None

    def __post_init__(self):
        scope=self.scene_scope
        if scope is None:return
        if (type(scope) is not tuple or len(scope)!=3
                or any(type(value) is not int or not 0<=value<2**63 for value in scope)
                or scope[0]<=0 or scope[1]<=0
                or type(self.scene_id) is not int or scope[0]!=self.scene_id):
            raise ValueError('Invalid social scene scope')

    @property
    def scene_key(self) -> int | tuple[int,int,int]:
        """Opaque channel identity; scene_id keeps its original template meaning."""
        scope=self.scene_scope
        if scope is None or scope==(self.scene_id,self.scene_id,0):
            return self.scene_id
        return scope

    def profile(self):
        return dict(id=self.role_id, name=self.name, level=self.level,
                    school=self.school, shape=self.shape)


@dataclass(frozen=True)
class SocialCommand:
    role_id: int
    login_epoch: int
    request_id: str
    deadline_ms: int
    kind: int
    body: bytes


@dataclass(frozen=True)
class Delivery:
    role_id: int
    login_epoch: int
    kind: int
    body: bytes
    scene_key: int | tuple[int,int,int] | None = field(default=None,kw_only=True)

    def __post_init__(self):
        key=self.scene_key
        if key is None:return
        if type(key) is int and 0<key<2**63:return
        if (type(key) is not tuple or len(key)!=3
                or any(type(value) is not int or not 0<=value<2**63 for value in key)
                or key[0]<=0 or key[1]<=0):
            raise ValueError('Invalid delivery scene key')
        if key==(key[0],key[0],0):object.__setattr__(self,'scene_key',key[0])


@dataclass(frozen=True)
class Publish:
    # scope and partition_key route to independent channel owners. They fan out
    # in bounded batches from membership snapshots; never query target Sessions.
    scope: str
    partition_key: int | tuple[int,int,int]
    sender_role_id: int
    kind: int
    body: bytes


@dataclass(frozen=True)
class RelationWake:
    role_id: int
    # Wake an independent recipient owner; durable events remain in SQLite.
    # This does not authorize accessing another role's mutable state.
    event_id: str


@dataclass(frozen=True)
class SocialResult:
    effects: tuple = ()
    rejection: str = ''


class RoleMailbox:
    """One bounded inbox per role/epoch. Full means reject/retry, never drop."""
    def __init__(self, role_id, login_epoch, capacity):
        if capacity < 1:
            raise ValueError('Mailbox capacity must be positive')
        self.role_id, self.login_epoch = role_id, login_epoch
        self.queue = Queue(maxsize=capacity)

    def submit(self, command):
        if (command.role_id, command.login_epoch) != (self.role_id, self.login_epoch):
            return 'stale_epoch'
        try:
            self.queue.put_nowait(command)
        except Full:
            return 'backpressure'
        return 'accepted'


class SQLiteSocialStore:
    """Local persistence Adapter only. No online state; no schema work in requests.

    initialize() is a startup migration. All methods must execute on the bounded
    persistence/role worker, not on the network event loop. SQLite is not claimed
    to provide horizontally scalable writes.
    """
    def __init__(self, path):
        self.path = path

    def connect(self):
        db = sqlite3.connect(self.path, timeout=2)
        db.execute('PRAGMA foreign_keys=ON')
        db.row_factory = sqlite3.Row
        return db

    def leased(self, role_id, epoch):
        return LeasedSocialStore(self.path, role_id, epoch)

    def initialize(self):
        with closing(self.connect()) as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS social_friends (
                owner INTEGER NOT NULL REFERENCES roles(id),
                target INTEGER NOT NULL REFERENCES roles(id),
                PRIMARY KEY(owner,target), CHECK(owner != target))''')
            db.execute('CREATE INDEX IF NOT EXISTS social_friend_target ON social_friends(target,owner)')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS social_groups (
                    owner INTEGER NOT NULL, target INTEGER NOT NULL, name TEXT NOT NULL,
                    PRIMARY KEY(owner,target),
                    FOREIGN KEY(owner,target) REFERENCES social_friends(owner,target) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS social_blocks (
                    owner INTEGER NOT NULL REFERENCES roles(id), target INTEGER NOT NULL REFERENCES roles(id),
                    PRIMARY KEY(owner,target), CHECK(owner!=target));
                CREATE TABLE IF NOT EXISTS social_requests (
                    id TEXT PRIMARY KEY, sender INTEGER NOT NULL REFERENCES roles(id),
                    recipient INTEGER NOT NULL REFERENCES roles(id), greeting TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    UNIQUE(sender,recipient));
                CREATE INDEX IF NOT EXISTS social_request_recipient ON social_requests(recipient,status);
                CREATE TABLE IF NOT EXISTS social_request_commands (
                    owner INTEGER NOT NULL REFERENCES roles(id), request_id TEXT NOT NULL,
                    target INTEGER NOT NULL REFERENCES roles(id), greeting TEXT NOT NULL, token TEXT NOT NULL,
                    PRIMARY KEY(owner,request_id));
                CREATE TABLE IF NOT EXISTS social_relation_outbox (
                    id TEXT PRIMARY KEY, source INTEGER NOT NULL REFERENCES roles(id),
                    recipient INTEGER NOT NULL REFERENCES roles(id), action TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0);
                CREATE INDEX IF NOT EXISTS social_outbox_recipient ON social_relation_outbox(recipient,done);
            ''')

        # Startup-only migration/configuration for player-created chat groups.
        import json
        from inspect_client import OUT
        from group_store import GroupStore
        baseline=json.loads((OUT/'design/recovery-baseline.json').read_text(encoding='utf-8'))
        self.group_policy=baseline['social']['common_groups']
        GroupStore(self.path,self.group_policy).initialize()
        # Organization schemas are prepared with the other social schemas.
        # Runtime role owners still explicitly authorize any wallet operation.
        from types import MappingProxyType
        from faction_domain import OrganizationStore
        from faction_payments import prepare_payment_storage
        self.organization_policy=MappingProxyType({k:tuple(v) if isinstance(v,list) else v
            for k,v in baseline['organizations'].items()})
        OrganizationStore(self.path,self.organization_policy).initialize()
        with closing(self.connect()) as db,db:prepare_payment_storage(db)

    def find(self, role_id=0, name=''):
        with closing(self.connect()) as db:
            row = db.execute('SELECT id,name,school,shape,level FROM roles WHERE id=?' if role_id
                             else 'SELECT id,name,school,shape,level FROM roles WHERE name=? COLLATE NOCASE',
                             (role_id or name,)).fetchone()
            return dict(row) if row else None

    def friends(self, owner):
        with closing(self.connect()) as db:
            return [dict(r) for r in db.execute('''SELECT r.id,r.name,r.school,r.shape,r.level,
                COALESCE(g.name,?) AS group_name
                FROM social_friends f JOIN roles r ON r.id=f.target
                LEFT JOIN social_groups g ON g.owner=f.owner AND g.target=f.target
                WHERE f.owner=? ORDER BY f.target''', (p.GROUP_FRIEND,owner))]

    def contact(self, owner, target, add, limit):
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if add:
                present = db.execute('SELECT 1 FROM social_friends WHERE owner=? AND target=?', (owner,target)).fetchone()
                count = db.execute('SELECT COUNT(*) FROM social_friends WHERE owner=?', (owner,)).fetchone()[0]
                if not present and count >= limit:
                    raise ValueError('contact_limit')
                db.execute('INSERT OR IGNORE INTO social_friends VALUES(?,?)', (owner,target))
            else:
                db.execute('DELETE FROM social_friends WHERE owner=? AND target=?', (owner,target))
                db.execute('DELETE FROM social_blocks WHERE owner=? AND target=?',(owner,target))

    def watchers(self, target, after=0, limit=128):
        if not 1 <= limit <= 128: raise ValueError('Presence batch limit')
        with closing(self.connect()) as db:
            return tuple(r[0] for r in db.execute('''SELECT f.owner FROM social_friends f
                WHERE f.target=? AND f.owner>? AND NOT EXISTS
                (SELECT 1 FROM social_blocks b WHERE b.owner=f.owner AND b.target=f.target)
                ORDER BY f.owner LIMIT ?''', (target,after,limit)))

    def blocked(self, owner, target):
        with closing(self.connect()) as db:
            return bool(db.execute('SELECT 1 FROM social_blocks WHERE owner=? AND target=?', (owner,target)).fetchone())

    def move_group(self, owner, target, group):
        if group not in (p.GROUP_FRIEND,p.GROUP_BLACK): raise ValueError('unsupported_group')
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM social_friends WHERE owner=? AND target=?',(owner,target)).fetchone():
                raise ValueError('contact_missing')
            db.execute('INSERT INTO social_groups VALUES(?,?,?) ON CONFLICT(owner,target) DO UPDATE SET name=excluded.name',
                       (owner,target,group))
            if group==p.GROUP_BLACK:
                db.execute('INSERT OR IGNORE INTO social_blocks VALUES(?,?)',(owner,target))
                db.execute("UPDATE social_requests SET status='blocked' WHERE sender=? AND recipient=? AND status='pending'",(target,owner))
            else: db.execute('DELETE FROM social_blocks WHERE owner=? AND target=?',(owner,target))

    def request(self, sender, target, greeting, limit, request_id):
        # Submission to a durable recipient inbox; only recipient resolves it.
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            seen=db.execute('SELECT target,greeting,token FROM social_request_commands WHERE owner=? AND request_id=?',
                            (sender,request_id)).fetchone()
            if seen:
                if (seen['target'],seen['greeting'])!=(target,greeting): raise ValueError('request_id_conflict')
                return seen['token'],False
            if db.execute('SELECT 1 FROM social_blocks WHERE owner=? AND target=?',(target,sender)).fetchone():
                raise ValueError('recipient_blocked')
            prior=db.execute('SELECT id,status FROM social_requests WHERE sender=? AND recipient=?',(sender,target)).fetchone()
            if prior and prior['status']=='pending':
                db.execute('INSERT INTO social_request_commands VALUES(?,?,?,?,?)',(sender,request_id,target,greeting,prior['id']))
                return prior['id'],False
            count=db.execute("SELECT COUNT(*) FROM social_requests WHERE recipient=? AND status='pending'",(target,)).fetchone()[0]
            if count>=limit: raise ValueError('request_inbox_full')
            key=uuid.uuid4().hex
            db.execute('''INSERT INTO social_requests(id,sender,recipient,greeting,status) VALUES(?,?,?,?,'pending')
                ON CONFLICT(sender,recipient) DO UPDATE SET id=excluded.id,greeting=excluded.greeting,status='pending' ''',
                (key,sender,target,greeting))
            db.execute('INSERT INTO social_request_commands VALUES(?,?,?,?,?)',(sender,request_id,target,greeting,key))
            return key,True

    def pending_requests(self, owner, limit):
        with closing(self.connect()) as db:
            return [dict(r) for r in db.execute("SELECT * FROM social_requests WHERE recipient=? AND status='pending' ORDER BY id LIMIT ?",(owner,limit))]

    def resolve_request(self, owner, sender, agree, limit):
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT id,status FROM social_requests WHERE sender=? AND recipient=?',(sender,owner)).fetchone()
            action='accepted' if agree else 'refused'
            if row and row['status']==action: return row['id']+':'+action
            if not row or row['status']!='pending': raise ValueError('request_not_pending')
            queued=db.execute('SELECT COUNT(*) FROM social_relation_outbox WHERE recipient=? AND done=0',(sender,)).fetchone()[0]
            if queued>=limit: raise ValueError('relation_inbox_full')
            blocked=db.execute('SELECT 1 FROM social_blocks WHERE owner=? AND target=?',(owner,sender)).fetchone()
            if blocked: raise ValueError('sender_blocked')
            action='accepted' if agree else 'refused'
            db.execute('UPDATE social_requests SET status=? WHERE id=?',(action,row['id']))
            event=row['id']+':'+action
            db.execute('INSERT INTO social_relation_outbox(id,source,recipient,action) VALUES(?,?,?,?)',
                       (event,owner,sender,action))
            return event

    def relation_events(self, owner, limit=64):
        if not 1<=limit<=128: raise ValueError('Outbox batch limit')
        with closing(self.connect()) as db:
            return tuple(RelationWake(owner,r[0]) for r in db.execute(
                'SELECT id FROM social_relation_outbox WHERE recipient=? AND done=0 ORDER BY id LIMIT ?',(owner,limit)))

    def apply_relation_event(self, owner, event_id, limit):
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM social_relation_outbox WHERE id=? AND recipient=?',(event_id,owner)).fetchone()
            if not row or row['done']: return None
            peer=row['source']
            if row['action']=='accepted':
                if db.execute('SELECT 1 FROM social_blocks WHERE owner=? AND target=?',(owner,peer)).fetchone():
                    raise ValueError('peer_blocked')
                present=db.execute('SELECT 1 FROM social_friends WHERE owner=? AND target=?',(owner,peer)).fetchone()
                count=db.execute('SELECT COUNT(*) FROM social_friends WHERE owner=?',(owner,)).fetchone()[0]
                if not present and count>=limit: raise ValueError('contact_limit')
                db.execute('INSERT OR IGNORE INTO social_friends VALUES(?,?)',(owner,peer))
            db.execute('UPDATE social_relation_outbox SET done=1 WHERE id=?',(event_id,))
            return row['action'],peer


class LeasedSocialStore(SQLiteSocialStore):
    """Per-role storage capability; lease is checked inside every write txn."""
    def __init__(self, path, role_id, epoch):
        super().__init__(path)
        self.role_id,self.epoch=role_id,epoch

    def connect(self):
        from accounts import FencedConnection
        return FencedConnection(super().connect(),self.role_id,self.epoch)


class RoleSocialOwner:
    """Commands are scheduled serially by role_id, separately from other roles.

    online is an immutable role_id->RoleSnapshot mapping supplied per command.
    Results contain logical immutable effects only. Sender identity is the owner
    snapshot; wire input never supplies an authoritative sender.
    """
    def __init__(self, snapshot, store, max_contacts, max_text):
        self.snapshot = snapshot
        self.store = store.leased(snapshot.role_id,snapshot.login_epoch) if isinstance(store,SQLiteSocialStore) else store
        self.max_contacts, self.max_text = max_contacts, max_text

    def own_reply(self, kind, body):
        s = self.snapshot
        return SocialResult((Delivery(s.role_id,s.login_epoch,kind,body),))

    def initial(self, online):
        rows = self.store.friends(self.snapshot.role_id)
        return self.own_reply(p.FRIENDS_INIT,compact(len(rows))+b''.join(
            p.friend_info(r,r['id'] in online,r['group_name']) for r in rows)+bytes(4))

    def pending_notices(self):
        effects=[]
        for row in self.store.pending_requests(self.snapshot.role_id,self.max_contacts):
            sender=self.store.find(row['sender'])
            if sender and not self.store.blocked(self.snapshot.role_id,row['sender']):
                effects.extend(self.own_reply(p.REQUEST_RECEIVE,p.request_notice(sender,row['greeting'])).effects)
        return SocialResult(tuple(effects))

    def apply_relation(self, wake, online):
        if wake.role_id!=self.snapshot.role_id: return SocialResult(rejection='wrong_owner')
        try:
            result=self.store.apply_relation_event(wake.role_id,wake.event_id,self.max_contacts)
            if not result: return SocialResult()
            action,peer_id=result
            peer=self.store.find(peer_id)
            if action=='accepted':
                return self.own_reply(p.ADD_RECEIVE,p.friend_added(peer,peer_id in online,p.GROUP_FRIEND))
            return self.own_reply(p.REFUSE_RECEIVE,p.refusal_notice(peer,''))
        except ValueError as error:
            return SocialResult(rejection=str(error))

    def filter_delivery(self, delivery):
        # Run at the recipient role owner before the connection mailbox.
        # The connection owner still performs its own epoch check on dequeue.
        s=self.snapshot
        if (delivery.role_id,delivery.login_epoch)!=(s.role_id,s.login_epoch): return False
        if delivery.kind==p.REQUEST_RECEIVE:
            try:
                _,pos=p.read_text(delivery.body,limit=512)
                sender=struct.unpack_from('>Q',delivery.body,pos)[0]
            except (ValueError,NeedMoreData,struct.error): return False
            return not self.store.blocked(s.role_id,sender)
        if delivery.kind in (p.PRIVATE_RECEIVE,p.CHAT_RECEIVE):
            if len(delivery.body)<8: return False
            sender=struct.unpack_from('>Q',delivery.body)[0]
            return not self.store.blocked(s.role_id,sender)
        return True

    def execute(self, command, online, now_ms):
        s = self.snapshot
        if (command.role_id,command.login_epoch) != (s.role_id,s.login_epoch):
            return SocialResult(rejection='stale_epoch')
        if now_ms > command.deadline_ms:
            return SocialResult(rejection='deadline')
        if not command.request_id:
            return SocialResult(rejection='missing_request_id')
        kind, body = command.kind, command.body
        try:
            if kind==p.TRY_ADD_SEND:
                target,name=p.target_request(body,True)
                peer=self.store.find(target,name)
                if not peer or peer['id']==s.role_id: raise ValueError('invalid_contact')
                return self.own_reply(p.TRY_ADD_RECEIVE,p.try_add_info(peer))
            if kind==p.REQUEST_SEND:
                target,greeting=p.request_with_text(body)
                if len(greeting)>self.max_text or '\0' in greeting: raise ValueError('invalid_greeting')
                peer=self.store.find(target)
                if not peer or target==s.role_id: raise ValueError('invalid_contact')
                if self.store.blocked(s.role_id,target): raise ValueError('peer_blocked')
                _,created=self.store.request(s.role_id,target,greeting,self.max_contacts,command.request_id)
                # Pending inbox survives offline recipients and reconnects.
                remote=online.get(target)
                if not remote or not created: return SocialResult()
                return SocialResult((Delivery(target,remote.login_epoch,p.REQUEST_RECEIVE,
                                              p.request_notice(s.profile(),greeting)),))
            if kind in (p.AGREE_SEND,p.REFUSE_SEND):
                target,_=(p.target_request(body) if kind==p.AGREE_SEND else p.request_with_text(body))
                event=self.store.resolve_request(s.role_id,target,kind==p.AGREE_SEND,self.max_contacts)
                return SocialResult((RelationWake(target,event),))
            if kind==p.MOVE_GROUP_SEND:
                group,target,name=p.group_request(body)
                peer=self.store.find(target,name)
                if not peer or peer['id']==s.role_id: raise ValueError('invalid_contact')
                self.store.move_group(s.role_id,peer['id'],group)
                return self.own_reply(p.MOVE_GROUP_RECEIVE,p.moved_group(peer['id'],group))
            if kind==p.UNBLOCK_SEND:
                target,_=p.target_request(body)
                if not self.store.blocked(s.role_id,target): raise ValueError('not_blocked')
                self.store.contact(s.role_id,target,False,self.max_contacts)
                return self.own_reply(p.UNBLOCK_RECEIVE,struct.pack('>Q',target))
            if kind == p.SEARCH_ID_SEND:
                target, _ = p.target_request(body)
                return self.own_reply(p.SEARCH_ID_RECEIVE,p.profile(self.store.find(target)))
            if kind == p.SEARCH_NAME_SEND:
                name, pos = p.read_text(body,limit=32)
                if len(body)-pos != 12: raise ValueError('name_search_size')
                target, _ = struct.unpack_from('>Qi',body,pos)
                return self.own_reply(p.SEARCH_NAME_RECEIVE,p.profile(self.store.find(target,name),True))
            if kind in (p.ADD_SEND,p.DELETE_SEND):
                target, name = p.target_request(body,True)
                role = self.store.find(target,name)
                if not role or role['id'] == s.role_id: raise ValueError('invalid_contact')
                if self.store.blocked(s.role_id,role['id']): raise ValueError('peer_blocked')
                self.store.contact(s.role_id,role['id'],kind==p.ADD_SEND,self.max_contacts)
                return (self.own_reply(p.ADD_RECEIVE,p.friend_added(role,role['id'] in online,p.GROUP_FRIEND))
                        if kind == p.ADD_SEND else self.own_reply(p.DELETE_RECEIVE,struct.pack('>Q',role['id'])))
            if kind == p.PRIVATE_SEND:
                target, content, extra, mode = p.private_request(body)
                self.validate_text(content,extra)
                if self.store.blocked(s.role_id,target) or self.store.blocked(target,s.role_id):
                    raise ValueError('peer_blocked')
                peer = online.get(target)
                if not peer: raise ValueError('recipient_offline')
                return SocialResult((Delivery(target,peer.login_epoch,p.PRIVATE_RECEIVE,
                                              p.private_message(s.profile(),content)),))
            if kind == p.CHAT_SEND:
                channel, content, extra = p.chat_request(body)
                self.validate_text(content,extra)
                route = {p.CURRENT_CHANNEL:('scene',s.scene_key),p.SCHOOL_CHANNEL:('school',s.school),
                         p.WORLD_CHANNEL:('world',0)}.get(channel)
                if not route: raise ValueError('channel_not_restored')
                return SocialResult((Publish(*route,s.role_id,p.CHAT_RECEIVE,
                                             p.chat_message(s.profile(),channel,content)),))
            return SocialResult(rejection='unimplemented')
        except (ValueError,NeedMoreData,struct.error) as error:
            return SocialResult(rejection=str(error) if type(error) is ValueError else type(error).__name__)

    def validate_text(self, content, extra):
        if not content.strip() or len(content)>self.max_text or '\0' in content or extra:
            raise ValueError('unsupported_content')
