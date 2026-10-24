"""Legacy single-loop compatibility Adapter; NOT the partition-ready runtime.

Migration target: social_owner.py. This Adapter remains only until the shared
gateway integrator switches routing to immutable effects and connection queues.

Local policy: adding a friend saves a contact on the caller's list. It does
not edit the other player's contacts. Offline private delivery is unsupported.
"""
from contextlib import closing
import struct
import sqlite3
import json
from inspect_client import OUT
from wire import compact, NeedMoreData
import social_protocol as p


class SocialHub:
    def __init__(self, accounts):
        self.accounts = accounts
        self.policy = json.loads((OUT/'design/recovery-baseline.json').read_text(encoding='utf-8'))['social']
        self.online = {}
        with closing(accounts.connect()) as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS social_friends (
                    owner INTEGER NOT NULL REFERENCES roles(id),
                    target INTEGER NOT NULL REFERENCES roles(id),
                    PRIMARY KEY(owner,target), CHECK(owner != target));
            ''')

    def find(self, role_id=0, name=''):
        with closing(self.accounts.connect()) as db:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT id,name,school,shape,level FROM roles WHERE id=?' if role_id
                             else 'SELECT id,name,school,shape,level FROM roles WHERE name=? COLLATE NOCASE',
                             (role_id or name,)).fetchone()
            return dict(row) if row else None

    def friends(self, owner):
        with closing(self.accounts.connect()) as db:
            ids = [r[0] for r in db.execute('SELECT target FROM social_friends WHERE owner=? ORDER BY target', (owner,))]
        return [self.find(i) for i in ids]

    def join(self, session):
        rid = session.role['id']
        if rid in self.online and self.online[rid] is not session:
            raise ValueError('Role already online')
        if self.online.get(rid) is session:
            return []
        self.online[rid] = session
        self.presence(rid, True)
        friends = self.friends(rid)
        return [(p.FRIENDS_INIT, compact(len(friends)) + b''.join(
            p.friend_info(r, r['id'] in self.online) for r in friends) + bytes(4))]

    def presence(self, rid, online):
        with closing(self.accounts.connect()) as db:
            watchers = [r[0] for r in db.execute('SELECT owner FROM social_friends WHERE target=?', (rid,))]
        for watcher in watchers:
            if watcher in self.online:
                self.online[watcher].push(p.ONLINE, struct.pack('>Qi', rid, int(online)))

    def leave(self, session):
        if session.role and self.online.get(session.role['id']) is session:
            del self.online[session.role['id']]
            self.presence(session.role['id'], False)

    def handle(self, session, kind, body):
        if kind not in (p.SEARCH_ID_SEND, p.SEARCH_NAME_SEND, p.ADD_SEND,
                        p.DELETE_SEND, p.PRIVATE_SEND, p.CHAT_SEND):
            return None
        rid = session.role['id']
        try:
            if kind == p.SEARCH_ID_SEND:
                target, _ = p.target_request(body)
                return [(p.SEARCH_ID_RECEIVE, p.profile(self.find(target)))]
            if kind == p.SEARCH_NAME_SEND:
                name, pos = p.read_text(body, limit=32)
                if len(body)-pos != 12:
                    raise ValueError('Invalid friend name search')
                target, mode = struct.unpack_from('>Qi', body, pos)
                return [(p.SEARCH_NAME_RECEIVE, p.profile(self.find(target, name), True))]
            if kind in (p.ADD_SEND, p.DELETE_SEND):
                target, name = p.target_request(body, True)
                role = self.find(target, name)
                if not role or role['id'] == rid:
                    raise ValueError('Invalid friend target')
                with closing(self.accounts.connect()) as db, db:
                    if kind == p.ADD_SEND:
                        count = db.execute('SELECT COUNT(*) FROM social_friends WHERE owner=?', (rid,)).fetchone()[0]
                        if count >= self.policy['max_contacts_per_role'] and role['id'] not in [r['id'] for r in self.friends(rid)]:
                            raise ValueError('Local contact limit reached')
                        db.execute('INSERT OR IGNORE INTO social_friends VALUES(?,?)', (rid, role['id']))
                    else:
                        db.execute('DELETE FROM social_friends WHERE owner=? AND target=?', (rid, role['id']))
                return [(p.ADD_RECEIVE, p.friend_added(role, role['id'] in self.online))] if kind == p.ADD_SEND else [
                    (p.DELETE_RECEIVE, struct.pack('>Q', role['id']))]
            if kind == p.PRIVATE_SEND:
                target, content, extra, mode = p.private_request(body)
                self.valid_content(content, extra)
                peer = self.online.get(target)
                if not peer:
                    raise ValueError('Private recipient offline')
                if peer is session:
                    return [(p.PRIVATE_RECEIVE, p.private_message(session.role, content, extra))]
                peer.push(p.PRIVATE_RECEIVE, p.private_message(session.role, content, extra))
                return []
            channel, content, extra = p.chat_request(body)
            self.valid_content(content, extra)
            # Native table 0x22be000 maps button 2->2, button 5->3, button 6->5.
            # Team/family/faction require membership modules and are refused.
            if channel not in (p.CURRENT_CHANNEL, p.SCHOOL_CHANNEL, p.WORLD_CHANNEL):
                raise ValueError('Channel not restored')
            message = p.chat_message(session.role, channel, content)
            for peer in tuple(self.online.values()):
                if peer is session:
                    continue
                if channel == p.CURRENT_CHANNEL and self.scene(peer) != self.scene(session):
                    continue
                if channel == p.SCHOOL_CHANNEL and peer.role['school'] != session.role['school']:
                    continue
                peer.push(p.CHAT_RECEIVE, message)
            return [(p.CHAT_RECEIVE, message)]
        except (ValueError, UnicodeError, NeedMoreData, struct.error) as error:
            # Contents never enter gateway logs; rejection isn't a fake success.
            session.events.append({'event': 'social_rejected', 'type': kind,
                                   'reason': str(error) if type(error) is ValueError else type(error).__name__})
            return []

    @staticmethod
    def scene(session):
        return session.world.position[0] if session.world else session.scene_id

    def valid_content(self, content, extra):
        if not content.strip() or len(content) > self.policy['max_text_characters'] or '\0' in content or extra:
            raise ValueError('Unsupported social content')
