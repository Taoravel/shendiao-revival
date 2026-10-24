"""Durable CommonGroup authority. All calls run on bounded persistence workers.

Group membership belongs to its group. Cross-group role quotas are derived in
the same serializable transaction, rather than copied into several role caches.
SQLite is the local Adapter; it is not a multi-writer deployment claim.
"""
from contextlib import closing
import hashlib
import json
import datetime
import sqlite3
import struct
import time
import uuid
from types import MappingProxyType
from accounts import FencedConnection
import group_protocol as p


class GroupStore:
    def __init__(self,path,policy):self.path,self.policy=path,MappingProxyType(dict(policy))

    def connect(self):
        db=sqlite3.connect(self.path,timeout=2)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def initialize(self):
        with closing(self.connect()) as db,db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS common_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT, owner INTEGER NOT NULL REFERENCES roles(id),
                name TEXT NOT NULL UNIQUE COLLATE NOCASE, notice TEXT NOT NULL DEFAULT '',
                allow_join INTEGER NOT NULL DEFAULT 1, flash INTEGER NOT NULL DEFAULT 1,
                version INTEGER NOT NULL DEFAULT 1, active_ms INTEGER NOT NULL);
              CREATE TABLE IF NOT EXISTS common_group_members (
                group_id INTEGER NOT NULL REFERENCES common_groups(id) ON DELETE CASCADE,
                role_id INTEGER NOT NULL REFERENCES roles(id), manager INTEGER NOT NULL DEFAULT 0,
                generation TEXT NOT NULL, last_chat_ms INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(group_id,role_id));
              CREATE INDEX IF NOT EXISTS common_member_role ON common_group_members(role_id,group_id);
              CREATE TABLE IF NOT EXISTS common_group_requests (
                group_id INTEGER NOT NULL REFERENCES common_groups(id) ON DELETE CASCADE,
                role_id INTEGER NOT NULL REFERENCES roles(id), created_ms INTEGER NOT NULL,
                PRIMARY KEY(group_id,role_id));
              CREATE TABLE IF NOT EXISTS common_group_creation (
                role_id INTEGER PRIMARY KEY REFERENCES roles(id), expires_ms INTEGER NOT NULL);
              CREATE TABLE IF NOT EXISTS common_group_commands (
                role_id INTEGER NOT NULL REFERENCES roles(id), request_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL, result TEXT NOT NULL, created_ms INTEGER NOT NULL,
                PRIMARY KEY(role_id,request_id));
              CREATE INDEX IF NOT EXISTS common_command_age ON common_group_commands(role_id,created_ms);
              CREATE TABLE IF NOT EXISTS common_group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL REFERENCES common_groups(id) ON DELETE CASCADE,
                sender INTEGER NOT NULL REFERENCES roles(id), plain TEXT NOT NULL,
                formatted TEXT NOT NULL, created_ms INTEGER NOT NULL);
              CREATE INDEX IF NOT EXISTS common_message_group ON common_group_messages(group_id,id);
              CREATE TABLE IF NOT EXISTS common_group_invitations (
                group_id INTEGER NOT NULL REFERENCES common_groups(id) ON DELETE CASCADE,
                role_id INTEGER NOT NULL REFERENCES roles(id), sender INTEGER NOT NULL REFERENCES roles(id),
                sender_generation TEXT NOT NULL, token TEXT NOT NULL, created_ms INTEGER NOT NULL,
                PRIMARY KEY(group_id,role_id));
              CREATE INDEX IF NOT EXISTS common_invitation_role ON common_group_invitations(role_id,created_ms);
            ''')
            # Additive migration of stores created by the previous group batch.
            if 'flash' not in {r['name'] for r in db.execute('PRAGMA table_info(common_group_members)')}:
                db.execute('ALTER TABLE common_group_members ADD COLUMN flash INTEGER NOT NULL DEFAULT 1')
            if 'notice_extra' not in {r['name'] for r in db.execute('PRAGMA table_info(common_groups)')}:
                db.execute("ALTER TABLE common_groups ADD COLUMN notice_extra TEXT NOT NULL DEFAULT ''")

    def timestamp(self,now):
        zone=datetime.timezone(datetime.timedelta(minutes=self.policy['timestamp_utc_offset_minutes']))
        return datetime.datetime.fromtimestamp(now/1000,zone).strftime(self.policy['timestamp_format'])

    def _quota(self,db,role_id,creating=False):
        row=db.execute('SELECT level FROM roles WHERE id=?',(role_id,)).fetchone()
        if not row: raise ValueError('group_role_missing')
        if creating and row[0]<self.policy['create_min_level']: raise ValueError('group_create_level')
        limit=min(self.policy['max_groups'],row[0]//self.policy['quota_level_step']+1)
        count=db.execute('SELECT COUNT(*) FROM common_group_members WHERE role_id=?',(role_id,)).fetchone()[0]
        if count>=limit: raise ValueError('group_role_quota')

    def _info(self,db,gid):
        row=db.execute('SELECT g.*,r.name AS owner_name FROM common_groups g JOIN roles r ON r.id=g.owner WHERE g.id=?',(gid,)).fetchone()
        if not row: raise ValueError('group_missing')
        group=dict(row)
        group['members']=[dict(r) for r in db.execute('''SELECT r.id,r.name,r.level,m.manager,m.generation,m.flash
          FROM common_group_members m JOIN roles r ON r.id=m.role_id WHERE m.group_id=? ORDER BY r.id''',(gid,))]
        group['managers']=[r['id'] for r in group['members'] if r['manager']]
        return group

    def _member(self,db,gid,role):
        row=db.execute('SELECT * FROM common_group_members WHERE group_id=? AND role_id=?',(gid,role)).fetchone()
        if not row: raise ValueError('group_not_member')
        return row

    def _manager(self,group,membership):
        if group['owner']!=membership['role_id'] and not membership['manager']:raise ValueError('group_permission')

    def _invitation(self,db,gid,role,now):
        return db.execute('''SELECT q.*,r.name AS sender_name,g.name AS group_name,g.version
          FROM common_group_invitations q JOIN common_groups g ON g.id=q.group_id
          JOIN common_group_members m ON m.group_id=q.group_id AND m.role_id=q.sender
          JOIN roles r ON r.id=q.sender WHERE q.group_id=? AND q.role_id=? AND q.created_ms>=?
          AND m.generation=q.sender_generation AND (m.manager=1 OR g.owner=q.sender)''',
          (gid,role,now-self.policy['request_ttl_ms'])).fetchone()

    def _add(self,db,group,role,now):
        self._quota(db,role)
        if len(group['members'])>=self.policy['max_members']: raise ValueError('group_full')
        db.execute('INSERT INTO common_group_members(group_id,role_id,generation) VALUES(?,?,?)',(group['id'],role,uuid.uuid4().hex))
        db.execute('DELETE FROM common_group_requests WHERE group_id=? AND role_id=?',(group['id'],role))
        db.execute('DELETE FROM common_group_invitations WHERE group_id=? AND role_id=?',(group['id'],role))
        db.execute('UPDATE common_groups SET version=version+1,active_ms=? WHERE id=?',(now,group['id']))

    def initial(self,role_id):
        with closing(self.connect()) as db,db:
            # A read transaction gives the roster and outstanding applications
            # a consistent snapshot while independent group owners commit.
            db.execute('BEGIN')
            ids=[r[0] for r in db.execute('SELECT group_id FROM common_group_members WHERE role_id=? ORDER BY group_id',(role_id,))]
            groups=[self._info(db,gid) for gid in ids]
            pending=[dict(r) for r in db.execute('''SELECT q.group_id,q.role_id,r.name FROM common_group_requests q
              JOIN common_group_members m ON m.group_id=q.group_id JOIN common_groups g ON g.id=q.group_id
              JOIN roles r ON r.id=q.role_id WHERE m.role_id=? AND (m.manager=1 OR g.owner=?)
              AND q.created_ms>=? ORDER BY q.created_ms LIMIT ?''',
              (role_id,role_id,int(time.time()*1000)-self.policy['request_ttl_ms'],self.policy['max_pending']*self.policy['max_groups']))]
            invitations=[dict(r) for r in db.execute('''SELECT q.group_id,q.token,q.sender,r.name AS sender_name,g.name AS group_name,g.version
              FROM common_group_invitations q JOIN common_groups g ON g.id=q.group_id
              JOIN common_group_members m ON m.group_id=q.group_id AND m.role_id=q.sender
              JOIN roles r ON r.id=q.sender WHERE q.role_id=? AND q.created_ms>=?
              AND m.generation=q.sender_generation AND (m.manager=1 OR g.owner=q.sender)
              AND NOT EXISTS(SELECT 1 FROM social_blocks b WHERE b.owner=q.role_id AND b.target=q.sender)
              ORDER BY q.created_ms LIMIT ?''',(role_id,int(time.time()*1000)-self.policy['request_ttl_ms'],self.policy['max_pending']))]
            return dict(groups=groups,pending=pending,invitations=invitations)

    def allowed(self,role,gid,generation,version,sender=0):
        with closing(self.connect()) as db:
            row=db.execute('''SELECT g.version,m.generation FROM common_groups g JOIN common_group_members m ON m.group_id=g.id
              WHERE g.id=? AND m.role_id=?''',(gid,role)).fetchone()
            if not row or row['generation']!=generation: return False
            if sender:
                if not db.execute('SELECT 1 FROM common_group_members WHERE group_id=? AND role_id=?',(gid,sender)).fetchone():return False
                if db.execute('SELECT 1 FROM social_blocks WHERE owner=? AND target=?',(role,sender)).fetchone():return False
            elif version is not None and row['version']!=version:return False
            return True

    def invitation_allowed(self,role,gid,token):
        with closing(self.connect()) as db,db:
            db.execute('BEGIN')
            invitation=self._invitation(db,gid,role,int(time.time()*1000))
            return bool(invitation and invitation['token']==token
              and not db.execute('SELECT 1 FROM social_blocks WHERE owner=? AND target=?',(role,invitation['sender'])).fetchone()
              and not db.execute('SELECT 1 FROM common_group_members WHERE group_id=? AND role_id=?',(gid,role)).fetchone())

    def filter_history(self,role,records):
        with closing(self.connect()) as db:
            blocked={r[0] for r in db.execute('SELECT target FROM social_blocks WHERE owner=?',(role,))}
        return [r for r in records if r['sender'] not in blocked]

    def execute(self,snapshot,command,now):
        if (snapshot.role_id,snapshot.login_epoch)!=(command.role_id,command.login_epoch):raise ValueError('group_stale_epoch')
        if not command.request_id or now>command.deadline_ms:raise ValueError('group_command_deadline')
        digest=hashlib.sha256(struct.pack('>I',command.kind)+command.body).hexdigest()
        with closing(FencedConnection(self.connect(),snapshot.role_id,snapshot.login_epoch)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            if int(time.time()*1000)>command.deadline_ms:raise ValueError('group_command_deadline')
            old=db.execute('SELECT fingerprint,result FROM common_group_commands WHERE role_id=? AND request_id=?',
                           (snapshot.role_id,command.request_id)).fetchone()
            if old:
                if old[0]!=digest:raise ValueError('group_request_conflict')
                return dict(json.loads(old[1]),replayed=True)
            result=self._execute(db,snapshot,command,now)
            db.execute('INSERT INTO common_group_commands VALUES(?,?,?,?,?)',
                       (snapshot.role_id,command.request_id,digest,json.dumps(result,ensure_ascii=False),now))
            db.execute('''DELETE FROM common_group_commands WHERE role_id=? AND request_id IN
              (SELECT request_id FROM common_group_commands WHERE role_id=? ORDER BY created_ms DESC,rowid DESC LIMIT -1 OFFSET ?)''',
              (snapshot.role_id,snapshot.role_id,self.policy['receipt_limit']))
            return dict(result,replayed=False)

    def _execute(self,db,s,cmd,now):
        kind,body,rid=cmd.kind,cmd.body,s.role_id
        if kind==p.CREATE:
            p.end(body,0);self._quota(db,rid,True)
            db.execute('INSERT INTO common_group_creation VALUES(?,?) ON CONFLICT(role_id) DO UPDATE SET expires_ms=excluded.expires_ms',
                       (rid,now+self.policy['creation_window_ms']))
            return dict(mode='ready')
        if kind==p.NAME:
            name,pos=p.read_text(body,limit=32);p.end(body,pos)
            if not 1<=len(name)<=self.policy['name_max'] or not all(c.isalnum() for c in name):raise ValueError('group_name')
            ready=db.execute('SELECT expires_ms FROM common_group_creation WHERE role_id=?',(rid,)).fetchone()
            if not ready or now>ready[0]:raise ValueError('group_creation_not_ready')
            self._quota(db,rid,True)
            if db.execute('SELECT 1 FROM common_groups WHERE name=? COLLATE NOCASE',(name,)).fetchone():raise ValueError('group_duplicate_name')
            gid=db.execute('INSERT INTO common_groups(owner,name,active_ms) VALUES(?,?,?)',(rid,name,now)).lastrowid
            db.execute('INSERT INTO common_group_members(group_id,role_id,generation) VALUES(?,?,?)',(gid,rid,uuid.uuid4().hex))
            db.execute('DELETE FROM common_group_creation WHERE role_id=?',(rid,))
            return dict(mode='created',group=self._info(db,gid))
        if kind==p.SEARCH:
            name,gid,mode=p.search_request(body)
            # Native search dialogs select mode; both IDs and exact names are
            # unambiguous. No enumeration or wildcard expansion is exposed.
            row=db.execute('SELECT id FROM common_groups WHERE id=?' if gid else 'SELECT id FROM common_groups WHERE name=? COLLATE NOCASE',
                           (gid or name,)).fetchone()
            if not row:raise ValueError('group_missing')
            return dict(mode='searched',group=self._info(db,row[0]))
        if kind==p.RESPOND:
            decision,applicant,gid=p.response_request(body)
        elif kind==p.SEND:gid,plain,formatted=p.message_request(body)
        elif kind in (p.INVITE,p.EXPEL):target,gid=p.member_request(body)
        elif kind==p.INVITE_REPLY:agree,gid=p.invite_reply(body)
        elif kind==p.MANAGER:appoint,gid,target=p.manager_request(body)
        elif kind==p.CONFIG:gid,scope,flash,notice,extra,allow=p.config_request(body)
        elif kind==p.HISTORY:gid,page=p.history_request(body)
        else:gid=p.identity(body)
        group=self._info(db,gid)
        if kind==p.INVITE_REPLY:
            invitation=self._invitation(db,gid,rid,now)
            if not invitation:raise ValueError('group_invitation_missing')
            if not agree:
                db.execute('DELETE FROM common_group_invitations WHERE group_id=? AND role_id=?',(gid,rid))
                return dict(mode='silent',group=group)
            if not group['allow_join'] and not self.policy['invitations_bypass_public_join_disabled']:raise ValueError('group_join_disabled')
            if db.execute('SELECT 1 FROM social_blocks WHERE owner=? AND target=?',(rid,invitation['sender'])).fetchone():raise ValueError('group_inviter_blocked')
            if db.execute('SELECT 1 FROM common_group_members WHERE group_id=? AND role_id=?',(gid,rid)).fetchone():raise ValueError('group_already_member')
            self._add(db,group,rid,now)
            db.execute('DELETE FROM common_group_invitations WHERE group_id=? AND role_id=?',(gid,rid))
            return dict(mode='updated',group=self._info(db,gid))
        if kind==p.JOIN:
            if any(m['id']==rid for m in group['members']):return dict(mode='updated',group=group)
            if not group['allow_join']:raise ValueError('group_join_disabled')
            self._quota(db,rid)
            if len(group['members'])>=self.policy['max_members']:raise ValueError('group_full')
            db.execute('DELETE FROM common_group_requests WHERE group_id=? AND created_ms<?',(gid,now-self.policy['request_ttl_ms']))
            present=db.execute('SELECT 1 FROM common_group_requests WHERE group_id=? AND role_id=?',(gid,rid)).fetchone()
            count=db.execute('SELECT COUNT(*) FROM common_group_requests WHERE group_id=?',(gid,)).fetchone()[0]
            if not present and count>=self.policy['max_pending']:raise ValueError('group_pending_full')
            # Also bound applications across different groups per applicant.
            total=db.execute('SELECT COUNT(*) FROM common_group_requests WHERE role_id=?',(rid,)).fetchone()[0]
            if not present and total>=self.policy['max_pending']:raise ValueError('group_applicant_pending_full')
            db.execute('INSERT OR IGNORE INTO common_group_requests VALUES(?,?,?)',(gid,rid,now))
            return dict(mode='requested',group=group,applicant=rid,name=s.name)
        membership=self._member(db,gid,rid)
        if kind==p.CONFIG:
            if scope:
                self._manager(group,membership)
                if len(notice)>self.policy['notice_max'] or len(extra)>self.policy['max_formatted'] or '\0' in notice:raise ValueError('group_notice')
                db.execute('UPDATE common_groups SET notice=?,notice_extra=?,allow_join=?,version=version+1,active_ms=? WHERE id=?',
                    (notice,extra,allow,now,gid))
            db.execute('UPDATE common_group_members SET flash=? WHERE group_id=? AND role_id=?',(flash,gid,rid))
            return dict(mode='configured' if scope else 'personal_config',group=self._info(db,gid))
        if kind==p.MANAGER:
            if group['owner']!=rid or target==group['owner']:raise ValueError('group_permission')
            self._member(db,gid,target)
            db.execute('UPDATE common_group_members SET manager=? WHERE group_id=? AND role_id=?',(appoint,gid,target))
            if not appoint:db.execute('DELETE FROM common_group_invitations WHERE group_id=? AND sender=?',(gid,target))
            db.execute('UPDATE common_groups SET version=version+1,active_ms=? WHERE id=?',(now,gid))
            return dict(mode='updated',group=self._info(db,gid))
        if kind==p.EXPEL:
            self._manager(group,membership)
            expelled=self._member(db,gid,target)
            if target in (group['owner'],rid) or (expelled['manager'] and group['owner']!=rid):raise ValueError('group_expel_protected')
            db.execute('DELETE FROM common_group_members WHERE group_id=? AND role_id=?',(gid,target))
            db.execute('DELETE FROM common_group_invitations WHERE group_id=? AND (role_id=? OR sender=?)',(gid,target,target))
            db.execute('UPDATE common_groups SET version=version+1,active_ms=? WHERE id=?',(now,gid))
            return dict(mode='left',group=self._info(db,gid),departed=target)
        if kind==p.INVITE:
            self._manager(group,membership)
            if not group['allow_join'] and not self.policy['invitations_bypass_public_join_disabled']:raise ValueError('group_join_disabled')
            self._quota(db,target)
            if len(group['members'])>=self.policy['max_members']:raise ValueError('group_full')
            if any(m['id']==target for m in group['members']):raise ValueError('group_already_member')
            if db.execute('SELECT 1 FROM social_blocks WHERE owner=? AND target=?',(target,rid)).fetchone():raise ValueError('group_inviter_blocked')
            db.execute('DELETE FROM common_group_invitations WHERE group_id=? AND created_ms<?',(gid,now-self.policy['request_ttl_ms']))
            previous=db.execute('SELECT created_ms FROM common_group_invitations WHERE group_id=? AND role_id=?',(gid,target)).fetchone()
            if previous and now-previous[0]<self.policy['invite_cooldown_ms']:raise ValueError('group_invite_rate')
            for query,args in [('SELECT COUNT(*) FROM common_group_invitations WHERE group_id=?',(gid,)),
                               ('SELECT COUNT(*) FROM common_group_invitations WHERE role_id=?',(target,))]:
                if not previous and db.execute(query,args).fetchone()[0]>=self.policy['max_pending']:raise ValueError('group_invitation_full')
            token=uuid.uuid4().hex
            db.execute('''INSERT INTO common_group_invitations VALUES(?,?,?,?,?,?) ON CONFLICT(group_id,role_id)
              DO UPDATE SET sender=excluded.sender,sender_generation=excluded.sender_generation,token=excluded.token,created_ms=excluded.created_ms''',
              (gid,target,rid,membership['generation'],token,now))
            return dict(mode='invited',group=group,inviter=rid,name=s.name,target=target,token=token)
        if kind==p.HISTORY:
            rows=[dict(row) for row in db.execute('''SELECT m.*,r.name FROM common_group_messages m JOIN roles r ON r.id=m.sender
              WHERE m.group_id=? AND NOT EXISTS (SELECT 1 FROM social_blocks b WHERE b.owner=? AND b.target=m.sender)
              ORDER BY m.id LIMIT ?''',(gid,rid,self.policy['history_limit']))]
            size=self.policy['history_page_size']
            pages=max(1,(len(rows)+size-1)//size)
            if page==-1:page=pages
            if not 1<=page<=pages:raise ValueError('group_history_page')
            rows=rows[(page-1)*size:page*size]
            for row in rows:row['timestamp']=self.timestamp(row['created_ms'])
            return dict(mode='history',group=group,page=page,last=page==pages,records=rows)
        if kind==p.RESPOND:
            if group['owner']!=rid and not membership['manager']:raise ValueError('group_permission')
            row=db.execute('SELECT created_ms FROM common_group_requests WHERE group_id=? AND role_id=?',(gid,applicant)).fetchone()
            if not row or row[0]<now-self.policy['request_ttl_ms']:raise ValueError('group_application_missing')
            if decision==0:self._add(db,group,applicant,now)
            else:db.execute('DELETE FROM common_group_requests WHERE group_id=? AND role_id=?',(gid,applicant))
            return dict(mode='updated',group=self._info(db,gid))
        if kind==p.LEAVE:
            if group['owner']==rid:
                # Owner dissolution is atomic; no orphaned group authority.
                # Transfer has its own native management request, still pending.
                db.execute('DELETE FROM common_groups WHERE id=?',(gid,))
                return dict(mode='dissolved',group=group)
            db.execute('DELETE FROM common_group_members WHERE group_id=? AND role_id=?',(gid,rid))
            db.execute('DELETE FROM common_group_invitations WHERE group_id=? AND sender=?',(gid,rid))
            db.execute('UPDATE common_groups SET version=version+1,active_ms=? WHERE id=?',(now,gid))
            return dict(mode='left',group=self._info(db,gid),departed=rid)
        if kind==p.SEND:
            if not plain.strip() or len(plain)>self.policy['max_text'] or len(formatted)>self.policy['max_formatted']:raise ValueError('group_message_text')
            if membership['last_chat_ms'] and now-membership['last_chat_ms']<self.policy['chat_interval_ms']:raise ValueError('group_message_rate')
            db.execute('UPDATE common_group_members SET last_chat_ms=? WHERE group_id=? AND role_id=?',(now,gid,rid))
            db.execute('UPDATE common_groups SET active_ms=? WHERE id=?',(now,gid))
            db.execute('INSERT INTO common_group_messages(group_id,sender,plain,formatted,created_ms) VALUES(?,?,?,?,?)',(gid,rid,plain,formatted,now))
            db.execute('''DELETE FROM common_group_messages WHERE group_id=? AND id NOT IN
              (SELECT id FROM common_group_messages WHERE group_id=? ORDER BY id DESC LIMIT ?)''',(gid,gid,self.policy['history_limit']))
            return dict(mode='message',group=group,sender=rid,name=s.name,plain=plain,formatted=formatted,timestamp=self.timestamp(now))
        raise ValueError('group_unsupported')
