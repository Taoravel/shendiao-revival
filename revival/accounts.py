"""Local accounts and owned role storage. Game state is kept in SQLite."""
from contextlib import closing
from dataclasses import asdict
import hashlib
import json
import sqlite3
from types import MappingProxyType
import uuid
import time
from inspect_client import OUT
import task_newbie_chapter
import role_lifecycle


class AccountStore:
    def __init__(self, path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        choices = json.loads((OUT / 'catalogs/knight.gsp.role.createroleconfig.json').read_text(encoding='utf-8'))
        self.choices = MappingProxyType({int(row['attributes'][color]): frozenset(int(s) for s in row['lists']['schools'])
                        for row in choices for color in ('color1', 'color2', 'color3')})
        with closing(self.connect()) as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY, name BLOB UNIQUE NOT NULL, login_secret BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL REFERENCES accounts(id),
                    name TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    school INTEGER NOT NULL, shape INTEGER NOT NULL, level INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS role_positions (
                    role_id INTEGER PRIMARY KEY REFERENCES roles(id),
                    map_id INTEGER NOT NULL, x INTEGER NOT NULL, y INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS role_leases (
                    role_id INTEGER PRIMARY KEY REFERENCES roles(id), epoch TEXT NOT NULL,
                    active INTEGER NOT NULL CHECK(active IN (0,1)));
                CREATE TABLE IF NOT EXISTS position_versions (
                    role_id INTEGER PRIMARY KEY REFERENCES roles(id), version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS role_progress (
                    role_id INTEGER PRIMARY KEY REFERENCES roles(id), experience INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS role_settlements (
                    role_id INTEGER NOT NULL REFERENCES roles(id), settlement_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, receipt TEXT NOT NULL,
                    PRIMARY KEY(role_id,settlement_id));
            ''')
            db.execute('INSERT OR IGNORE INTO accounts(id,name,login_secret) VALUES(?,?,?)',
                       (1111, b'1111', hashlib.md5(b'11111111').digest()))
            role_lifecycle.prepare(db)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=2)
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def account(self, identity):
        with closing(self.connect()) as db:
            return db.execute('SELECT id,login_secret FROM accounts WHERE name=?', (identity,)).fetchone()

    def roles(self, account_id):
        with closing(self.connect()) as db:
            return [dict(zip(('id', 'name', 'school', 'shape', 'level'), row)) for row in db.execute(
                'SELECT id,name,school,shape,level FROM roles r WHERE account_id=? '
                'AND NOT EXISTS(SELECT 1 FROM role_deletions d WHERE d.role_id=r.id) ORDER BY id', (account_id,))]

    def create_role(self, account_id, name, school, shape):
        # Native UI documents 2-8 letters/Chinese, rejecting illegal or all-numeric names.
        # The three-slot cap remains local restoration policy.
        if not 2 <= len(name) <= 8 or not all(c.isalnum() for c in name) or name.isdecimal():
            raise ValueError('invalid_name')
        if school not in self.choices.get(shape, set()):
            raise ValueError('invalid_choice')
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT COUNT(*) FROM roles r WHERE account_id=? '
                          'AND NOT EXISTS(SELECT 1 FROM role_deletions d WHERE d.role_id=r.id)', (account_id,)).fetchone()[0] >= 3:
                raise ValueError('role_limit')
            try:
                cursor = db.execute('INSERT INTO roles(account_id,name,school,shape) VALUES(?,?,?,?)', (account_id, name, school, shape))
            except sqlite3.IntegrityError:
                raise ValueError('duplicate_name') from None
            rules=getattr(self,'currency_rules',None)
            if rules is not None:
                growth=getattr(self,'growth_rules',None)
                attributes=getattr(self,'attribute_rules',None)
                if growth is None or attributes is None or attributes.initial_profile is None:
                    raise ValueError('Prepared creation growth and attribute policy required')
                if attributes.growth_policy!=growth.revision or attributes.initial_profile.level!=1:
                    raise ValueError('Creation profile policy or initial level mismatch')
                creation=json.dumps(dict(format=1,source='design/role-attributes-v1.json#new_role_designed_baseline',
                    provenance='designed',growth_policy=growth.revision,attribute_policy=attributes.revision,
                    profile=asdict(attributes.initial_profile)),sort_keys=True,separators=(',',':'))
                db.execute('INSERT INTO role_restoration_origins '
                           '(role_id,origin,wallet_policy,creation_profile) VALUES(?,?,?,?)',
                           (cursor.lastrowid,'new_restoration_role',rules.revision,creation))
            newbie=getattr(self,'newbie_rules',None)
            if newbie is not None:
                origin=task_newbie_chapter.record_newbie_creation(db,account_id,cursor.lastrowid,
                    uuid.uuid4().hex,self.task_resources,newbie)
                skills=getattr(self,'other_skill_rules',None)
                if skills is not None:
                    from role_skills import authorize_new_role_other_skills
                    authorize_new_role_other_skills(db,account_id,cursor.lastrowid,origin.creation_id,skills)
                db.execute('INSERT INTO role_positions VALUES(?,?,?,?)',(cursor.lastrowid,*origin.spawn))
                db.execute('INSERT INTO position_versions VALUES(?,1)',(cursor.lastrowid,))
            return {'id': cursor.lastrowid, 'name': name, 'school': school, 'shape': shape, 'level': 1}

    def owned_role(self, account_id, role_id):
        with closing(self.connect()) as db:
            row = db.execute('SELECT id,name,school,shape,level FROM roles WHERE id=? AND account_id=?',
                             (role_id, account_id)).fetchone()
            if db.execute('SELECT 1 FROM role_deletions WHERE role_id=?',(role_id,)).fetchone():return None
            return dict(zip(('id', 'name', 'school', 'shape', 'level'), row)) if row else None

    def deletion_candidate(self,account_id,role_id):
        with closing(self.connect()) as db:
            return role_lifecycle.candidate(db,account_id,role_id)

    def delete_role(self,candidate):
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            return role_lifecycle.retire(db,candidate,int(time.time()*1000))

    def acquire_lease(self, account_id, role_id):
        epoch = uuid.uuid4().int >> 65
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM roles WHERE id=? AND account_id=?', (role_id, account_id)).fetchone():
                raise ValueError('Role ownership mismatch')
            if db.execute('SELECT 1 FROM role_deletions WHERE role_id=?',(role_id,)).fetchone():
                raise ValueError('Deleted role cannot acquire a login lease')
            db.execute('INSERT INTO role_leases VALUES(?,?,1) ON CONFLICT(role_id) '
                       'DO UPDATE SET epoch=excluded.epoch,active=1', (role_id, epoch))
        return epoch

    def release_lease(self, role_id, epoch):
        with closing(self.connect()) as db, db:
            db.execute('UPDATE role_leases SET active=0 WHERE role_id=? AND epoch=?', (role_id, epoch))

    def leased(self, account_id, role_id, epoch):
        return LeasedAccounts(self, account_id, role_id, epoch)

    def position(self, account_id, role_id):
        if not self.owned_role(account_id, role_id):
            raise ValueError('Role ownership mismatch')
        with closing(self.connect()) as db:
            row = db.execute('SELECT map_id,x,y FROM role_positions WHERE role_id=?', (role_id,)).fetchone()
        return row or (1007, 8480, 6976)

    def save_position(self, account_id, role_id, position):
        if not self.owned_role(account_id, role_id):
            raise ValueError('Role ownership mismatch')
        with closing(self.connect()) as db, db:
            db.execute('INSERT INTO role_positions(role_id,map_id,x,y) VALUES(?,?,?,?) '
                       'ON CONFLICT(role_id) DO UPDATE SET map_id=excluded.map_id,x=excluded.x,y=excluded.y',
                       (role_id, *position))

    def save_checkpoint(self, account_id, role_id, epoch, position, version):
        leased = self.leased(account_id, role_id, epoch)
        with closing(leased.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT version FROM position_versions WHERE role_id=?', (role_id,)).fetchone()
            if old and old[0] >= version:
                return False
            db.execute('INSERT INTO role_positions VALUES(?,?,?,?) ON CONFLICT(role_id) '
                       'DO UPDATE SET map_id=excluded.map_id,x=excluded.x,y=excluded.y', (role_id, *position))
            db.execute('INSERT INTO position_versions VALUES(?,?) ON CONFLICT(role_id) '
                       'DO UPDATE SET version=excluded.version', (role_id, version))
        return True

    def position_version(self, role_id):
        with closing(self.connect()) as db:
            row = db.execute('SELECT version FROM position_versions WHERE role_id=?', (role_id,)).fetchone()
        return row[0] if row else 0


class FencedConnection:
    """Trusted local SQL Adapter: verify the lease inside every write transaction.

    SQLite serializes a lease change with the transaction. An old transaction
    may finish before replacement; no old write can start after a new lease.
    SQL is authored by modules, never supplied by the client. No DDL is allowed.
    """
    def __init__(self, db, role_id, epoch):
        self.db, self.role_id, self.epoch = db, role_id, epoch

    def _fence(self):
        row = self.db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?', (self.role_id,)).fetchone()
        if not row or str(row[0]) != str(self.epoch) or not row[1]:
            from runtime_core import StaleEpoch
            raise StaleEpoch('Expired role persistence lease')

    def execute(self, sql, args=()):
        verb = sql.lstrip().split(None, 1)[0].upper()
        if verb in ('CREATE', 'ALTER', 'DROP'):
            raise RuntimeError('Schema changes belong to startup')
        if verb == 'BEGIN':
            result = self.db.execute(sql, args)
            self._fence()
            return result
        if verb not in ('SELECT', 'PRAGMA', 'EXPLAIN'):
            if not self.db.in_transaction:
                self.db.execute('BEGIN IMMEDIATE')
            self._fence()
        return self.db.execute(sql, args)

    @property
    def row_factory(self): return self.db.row_factory
    @row_factory.setter
    def row_factory(self, value): self.db.row_factory = value
    @property
    def in_transaction(self): return self.db.in_transaction
    def close(self): self.db.close()
    def commit(self): self.db.commit()
    def rollback(self): self.db.rollback()
    def __enter__(self): return self
    def __exit__(self, *exc): return self.db.__exit__(*exc)


class LeasedAccounts(AccountStore):
    """No constructor I/O; a role storage capability, not a Session reference."""
    def __init__(self, source, account_id, role_id, epoch):
        self.path, self.choices = source.path, source.choices
        self.account_id, self.role_id, self.epoch = account_id, role_id, epoch
        self.inventory_config = source.inventory_config
        self.currency_rules = getattr(source,'currency_rules',None)
        self.growth_rules = getattr(source,'growth_rules',None)
        self.attribute_rules = getattr(source,'attribute_rules',None)
        self.task_pet_experience_rules = getattr(source,'task_pet_experience_rules',None)
        self.task_resources = getattr(source,'task_resources',None)
        self.newbie_rules = getattr(source,'newbie_rules',None)

    def connect(self):
        return FencedConnection(super().connect(), self.role_id, self.epoch)
