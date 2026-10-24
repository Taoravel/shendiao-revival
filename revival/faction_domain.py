"""Family -> guild organizations. Per-organization ownership; SQLite local Adapter.

Call on bounded persistence workers. No Session, network writer or world lock.
Creation requires a funding receipt written by the trusted role asset owner in
the same transaction as its debit. This module never invents cash or charges it.
"""
from contextlib import closing
from dataclasses import dataclass,replace
import hashlib
import json
import sqlite3


@dataclass(frozen=True)
class OrganizationCommand:
    actor: int
    epoch: int | str
    request_id: str
    deadline_ms: int
    organization: int
    operation: str
    args: tuple = ()


@dataclass(frozen=True)
class OrganizationBroadcast:
    organization: int
    revision: int
    sender: int
    recipients: tuple
    content: str
    memberships: tuple


@dataclass(frozen=True)
class FundingDecision:
    actor: int
    request_id: str
    fingerprint: str
    status: str


@dataclass(frozen=True)
class FamilyAssets:
    organization: int
    founder_name: str
    funds: int
    popularity: int
    origin: str
    construction: int | None = None


@dataclass(frozen=True)
class GuildAssets:
    organization: int
    funds: int
    origin: str


class OrganizationStore:
    def __init__(self, path, policy, *, research_policy=None,building_policy=None,guild_maintenance_policy=None,member_learning_policy=None):
        self.path, self.policy = path, policy
        from guild_training import rules
        self.training_rules=rules(policy)
        from guild_research import rules as research_rules
        self.research_rules=research_rules(research_policy,self.training_rules.research_skills)
        from guild_buildings import rules as building_rules
        self.building_rules=building_rules(building_policy)
        from guild_maintenance import rules as guild_maintenance_rules
        self.guild_maintenance_rules=guild_maintenance_rules(guild_maintenance_policy,self.building_rules,self.research_rules)
        from guild_member_learning import rules as learning_rules
        from role_life_skills import load_rules as life_rules
        self.life_rules=life_rules()
        self.learning_rules=learning_rules(member_learning_policy,self.life_rules,self.research_rules,self.guild_maintenance_rules,self.building_rules)
        from guild_projection import rules as projection_rules
        self.guild_rules=projection_rules(policy)
        from role_practice import load_rules
        self.practice_rules=load_rules(policy)
        from family_products import rules as product_rules
        self.product_rules=product_rules(policy)
        from family_maintenance import rules as maintenance_rules
        self.maintenance_rules=maintenance_rules(policy)
        from guild_dissolution import rules as guild_closure_rules
        self.guild_closure_rules=guild_closure_rules(policy)
        from family_donation import rules as donation_rules
        self.donation_rules=donation_rules(policy)

    @staticmethod
    def owner_key(command):
        # Creation is partitioned by creator, never by a global organization=0.
        return ('organization',command.organization) if command.organization else ('organization-create',command.actor)

    @staticmethod
    def _valid_lease(row,epoch):
        # Current accounts return an integer while SQLite's TEXT affinity stores
        # its decimal representation; historical UUID epochs remain supported.
        return bool(row and str(row['epoch'])==str(epoch) and row['active']==1)

    def connect(self):
        db=sqlite3.connect(self.path,timeout=2)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def initialize(self):
        with closing(self.connect()) as db,db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS organizations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL CHECK(kind IN ('family','guild')),
              name TEXT NOT NULL UNIQUE COLLATE NOCASE,aim TEXT NOT NULL,
              leader INTEGER NOT NULL REFERENCES roles(id),level INTEGER NOT NULL DEFAULT 1,
              revision INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS family_members (
              role_id INTEGER PRIMARY KEY REFERENCES roles(id),family INTEGER NOT NULL REFERENCES organizations(id),
              position TEXT NOT NULL DEFAULT 'member',joined_ms INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS family_roster ON family_members(family,role_id);
            CREATE TABLE IF NOT EXISTS guild_families (
              family INTEGER PRIMARY KEY REFERENCES organizations(id),guild INTEGER NOT NULL REFERENCES organizations(id),joined_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS guild_offices (
              guild INTEGER NOT NULL REFERENCES organizations(id),role_id INTEGER NOT NULL REFERENCES roles(id),
              position TEXT NOT NULL,PRIMARY KEY(guild,role_id));
            CREATE INDEX IF NOT EXISTS guild_roster ON guild_families(guild,family);
            CREATE TABLE IF NOT EXISTS organization_applications (
              organization INTEGER NOT NULL REFERENCES organizations(id),applicant INTEGER NOT NULL,
              PRIMARY KEY(organization,applicant));
            CREATE TABLE IF NOT EXISTS organization_receipts (
              actor INTEGER NOT NULL,request_id TEXT NOT NULL,fingerprint TEXT NOT NULL,result TEXT NOT NULL,
              PRIMARY KEY(actor,request_id));
            CREATE TABLE IF NOT EXISTS organization_funding (
              actor INTEGER NOT NULL,request_id TEXT NOT NULL,fingerprint TEXT NOT NULL,amount INTEGER NOT NULL,
              consumed INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(actor,request_id));
            CREATE TABLE IF NOT EXISTS organization_mutes (
              organization INTEGER NOT NULL REFERENCES organizations(id),role_id INTEGER NOT NULL REFERENCES roles(id),
              until_ms INTEGER NOT NULL,PRIMARY KEY(organization,role_id));
            CREATE TABLE IF NOT EXISTS organization_chat_clock (
              organization INTEGER NOT NULL REFERENCES organizations(id),role_id INTEGER NOT NULL REFERENCES roles(id),
              last_ms INTEGER NOT NULL,PRIMARY KEY(organization,role_id));
            CREATE TABLE IF NOT EXISTS organization_chat_receipts (
              actor INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
              fingerprint TEXT NOT NULL,deadline_ms INTEGER NOT NULL,
              PRIMARY KEY(actor,request_id));
            CREATE TABLE IF NOT EXISTS family_assets (
              family INTEGER PRIMARY KEY REFERENCES organizations(id),founder_name TEXT NOT NULL,
              funds INTEGER NOT NULL CHECK(funds>=0),popularity INTEGER NOT NULL CHECK(popularity>=0),
              origin TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS guild_assets (
              guild INTEGER PRIMARY KEY REFERENCES organizations(id),funds INTEGER NOT NULL CHECK(funds>=0),origin TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS organization_fund_ledger (
              organization INTEGER NOT NULL REFERENCES organizations(id),actor INTEGER NOT NULL REFERENCES roles(id),
              request_id TEXT NOT NULL,reason TEXT NOT NULL,delta INTEGER NOT NULL,
              balance INTEGER NOT NULL CHECK(balance>=0),created_ms INTEGER NOT NULL,
              PRIMARY KEY(actor,request_id));
            ''')
            # Preserve the short-lived earlier local ledger shape if present.
            # All migrations run at startup; disagreement keeps the old data
            # intact and fails rather than silently discarding financial rows.
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='family_fund_ledger'").fetchone():
                conflict=db.execute('''SELECT 1 FROM family_fund_ledger f JOIN organization_fund_ledger o
                    ON o.actor=f.actor AND o.request_id=f.request_id WHERE o.organization!=f.family
                    OR o.reason!=f.reason OR o.delta!=f.delta OR o.balance!=f.balance OR o.created_ms!=f.created_ms LIMIT 1''').fetchone()
                if conflict:raise ValueError('organization_fund_ledger_conflict')
                db.execute('''INSERT OR IGNORE INTO organization_fund_ledger
                    SELECT family,actor,request_id,reason,delta,balance,created_ms FROM family_fund_ledger''')
            from family_projection import prepare
            prepare(db)
            from family_maintenance import prepare as prepare_family_maintenance
            prepare_family_maintenance(db)
            from guild_offices import prepare as prepare_guild_offices
            prepare_guild_offices(db)
            from guild_training import prepare as prepare_guild_training
            prepare_guild_training(db)
            from guild_projection import prepare as prepare_guild_projection
            prepare_guild_projection(db)
            from guild_dissolution import prepare as prepare_guild_dissolution
            prepare_guild_dissolution(db)
            from role_practice import prepare as prepare_role_practice
            prepare_role_practice(db)
            from guild_practice import prepare as prepare_guild_practice
            prepare_guild_practice(db)
            from family_products import prepare as prepare_family_products
            prepare_family_products(db)
            from family_donation import prepare as prepare_family_donation
            prepare_family_donation(db)
            from family_history import prepare as prepare_family_history
            prepare_family_history(db)
            from guild_research import prepare as prepare_guild_research
            prepare_guild_research(db)
            from family_guild_history import prepare as prepare_family_guild_history
            prepare_family_guild_history(db)
            from guild_buildings import prepare as prepare_buildings
            prepare_buildings(db)
            from guild_maintenance import prepare as prepare_guild_maintenance
            prepare_guild_maintenance(db)
            from guild_member_learning import prepare as prepare_member_learning
            prepare_member_learning(db)

    @staticmethod
    def fingerprint(c):
        return hashlib.sha256(json.dumps([c.organization,c.operation,c.args],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

    @staticmethod
    def record_funding(db,command,amount):
        """Trusted asset Adapter only, inside its already-open debit transaction.

        No wire handler may call this. Cross-database deployment needs an outbox
        saga and compensation before replacing this single-database Adapter.
        """
        fingerprint=OrganizationStore.fingerprint(command)
        row=db.execute('SELECT fingerprint,amount FROM organization_funding WHERE actor=? AND request_id=?',
                       (command.actor,command.request_id)).fetchone()
        if row and tuple(row)!=(fingerprint,amount): raise ValueError('funding_conflict')
        db.execute('INSERT OR IGNORE INTO organization_funding(actor,request_id,fingerprint,amount) VALUES(?,?,?,?)',
                   (command.actor,command.request_id,fingerprint,amount))

    def execute(self,c,now_ms):
        if not c.request_id or now_ms>c.deadline_ms: raise ValueError('invalid_request_or_deadline')
        fingerprint=self.fingerprint(c)
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(c.actor,)).fetchone()
            if not self._valid_lease(lease,c.epoch): raise ValueError('stale_epoch')
            receipt=db.execute('SELECT fingerprint,result FROM organization_receipts WHERE actor=? AND request_id=?',
                               (c.actor,c.request_id)).fetchone()
            if receipt:
                if receipt['fingerprint']!=fingerprint: raise ValueError('request_id_conflict')
                return json.loads(receipt['result'])
            try: result=self._execute(db,c,now_ms)
            except sqlite3.IntegrityError:
                raise ValueError('organization_constraint') from None
            db.execute('INSERT INTO organization_receipts VALUES(?,?,?,?)',
                       (c.actor,c.request_id,fingerprint,json.dumps(result,ensure_ascii=False)))
            return result

    def revoke_funding(self,c,now_ms):
        """Organization owner decides cancellation before the role may refund.

        Schedule on owner_key(c), alongside execute(c). No wallet writes occur
        here. The immutable decision is only a wake-up: the role verifies the
        persisted revoked grant and absence of a success receipt in its own tx.
        A new login may revoke a prior intent using its current epoch; the
        fingerprint intentionally identifies business intent, not login epoch.
        """
        if not c.request_id or now_ms>c.deadline_ms:raise ValueError('invalid_request_or_deadline')
        fingerprint=self.fingerprint(c)
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(c.actor,)).fetchone()
            if not self._valid_lease(lease,c.epoch):raise ValueError('stale_epoch')
            grant=db.execute('SELECT fingerprint,consumed FROM organization_funding WHERE actor=? AND request_id=?',
                             (c.actor,c.request_id)).fetchone()
            if not grant:raise ValueError('funding_missing')
            if grant['fingerprint']!=fingerprint:raise ValueError('request_id_conflict')
            receipt=db.execute('SELECT fingerprint FROM organization_receipts WHERE actor=? AND request_id=?',
                               (c.actor,c.request_id)).fetchone()
            if receipt:
                if receipt[0]!=fingerprint or grant['consumed']!=1:raise ValueError('funding_receipt_inconsistent')
                status='committed'
            else:
                if grant['consumed'] not in (0,-1):raise ValueError('funding_outcome_unknown')
                # Revoked grants never become spendable again on retry.
                db.execute('UPDATE organization_funding SET consumed=-1 WHERE actor=? AND request_id=?',
                           (c.actor,c.request_id))
                status='revoked'
            return FundingDecision(c.actor,c.request_id,fingerprint,status)

    def _org(self,db,identity,kind=None,*,allow_pending=False):
        row=db.execute('SELECT * FROM organizations WHERE id=?',(identity,)).fetchone()
        if not row or (kind and row['kind']!=kind): raise ValueError('organization_missing')
        if row['kind']=='family' and not allow_pending:
            clock=db.execute('SELECT state FROM family_maintenance WHERE family=?',(identity,)).fetchone()
            if clock and clock[0]=='dissolution_pending':raise ValueError('family_dissolution_pending')
        if row['kind']=='guild' and not allow_pending:
            from guild_dissolution import require_active
            require_active(db,identity)
        return row

    def _family(self,db,role):
        row=db.execute('''SELECT m.family FROM family_members m LEFT JOIN family_maintenance c ON c.family=m.family
            WHERE m.role_id=? AND COALESCE(c.state,'active')='active' ''',(role,)).fetchone()
        if not row: raise ValueError('not_in_family')
        return row['family']

    def _members(self,db,org):
        if org['kind']=='family':
            return tuple(r[0] for r in db.execute('SELECT role_id FROM family_members WHERE family=? ORDER BY role_id',(org['id'],)))
        return tuple(r[0] for r in db.execute('''SELECT m.role_id FROM family_members m JOIN guild_families g ON g.family=m.family
            LEFT JOIN family_maintenance c ON c.family=m.family
            WHERE g.guild=? AND COALESCE(c.state,'active')='active' ORDER BY m.role_id''',(org['id'],)))

    def _membership_stamps(self,db,org):
        if org['kind']=='family':
            return tuple(tuple(r) for r in db.execute('''SELECT role_id,family,?,joined_ms,0
                FROM family_members WHERE family=? ORDER BY role_id''',(org['revision'],org['id'])))
        return tuple(tuple(r) for r in db.execute('''SELECT m.role_id,m.family,f.revision,m.joined_ms,g.joined_ms
            FROM family_members m JOIN guild_families g ON g.family=m.family
            JOIN organizations f ON f.id=m.family LEFT JOIN family_maintenance c ON c.family=m.family
            WHERE g.guild=? AND COALESCE(c.state,'active')='active' ORDER BY m.role_id''',(org['id'],)))

    def _manager(self,db,org,actor):
        if org['kind']=='guild' and actor not in self._members(db,org):raise ValueError('not_member')
        if org['leader']==actor: return
        if org['kind']=='family' and db.execute("SELECT 1 FROM family_members WHERE family=? AND role_id=? AND position='deputy'",
                                               (org['id'],actor)).fetchone(): return
        raise ValueError('permission_denied')

    def _funding(self,db,c,amount):
        row=db.execute('SELECT * FROM organization_funding WHERE actor=? AND request_id=?',(c.actor,c.request_id)).fetchone()
        if not row or row['fingerprint']!=self.fingerprint(c) or row['amount']!=amount or row['consumed']:
            raise ValueError('funding_required')
        db.execute('UPDATE organization_funding SET consumed=1 WHERE actor=? AND request_id=?',(c.actor,c.request_id))

    def _text(self,name,aim):
        p=self.policy
        if not p['name_min']<=len(name)<=p['name_max'] or not all('\u4e00'<=x<='\u9fff' for x in name):
            raise ValueError('invalid_name')
        if not p['aim_min']<=len(aim)<=p['aim_max'] or any(x.isspace() or x=='\0' for x in aim):
            raise ValueError('invalid_aim')

    def _execute(self,db,c,now):
        p=self.policy
        if c.operation=='create_family':
            name,aim,founders=c.args
            self._text(name,aim)
            # Founders are role-owner-approved (role_id,epoch) snapshots from a
            # verified team/consent flow, never IDs accepted directly off wire.
            ids=[x[0] for x in founders]
            if c.organization or len(ids)<p['family_min_founders'] or len(ids)!=len(set(ids)) or c.actor not in ids:
                raise ValueError('invalid_founders')
            if len(ids)>p['family_capacities'][0]: raise ValueError('family_full')
            for rid,epoch in founders:
                row=db.execute('''SELECT r.level,l.epoch,l.active FROM roles r JOIN role_leases l ON l.role_id=r.id
                    WHERE r.id=?''',(rid,)).fetchone()
                if not row or row['level']<p['family_create_level'] or not self._valid_lease(row,epoch):
                    raise ValueError('founder_not_eligible')
                if db.execute('SELECT 1 FROM family_members WHERE role_id=?',(rid,)).fetchone(): raise ValueError('already_in_family')
            self._funding(db,c,p['family_create_fee'])
            identity=db.execute("INSERT INTO organizations(kind,name,aim,leader) VALUES('family',?,?,?)",(name,aim,c.actor)).lastrowid
            from family_projection import new_member
            for rid in ids:
                db.execute('INSERT INTO family_members VALUES(?,?,?,?)',(rid,identity,'leader' if rid==c.actor else 'member',now))
                new_member(db,rid,p)
            founder=db.execute('SELECT name FROM roles WHERE id=?',(c.actor,)).fetchone()[0]
            # Explicit new-family grant, independent of the application fee.
            # Startup never creates this baseline for existing organizations.
            db.execute('''INSERT INTO family_assets(family,founder_name,funds,popularity,origin,construction)
                VALUES(?,?,?,?,?,?)''',(identity,founder,p['family_initial_funds'],
                       p['family_initial_popularity'],p['family_funds_origin'],p['family_initial_construction']))
            from family_products import new_family as new_family_products
            new_family_products(db,identity,self.product_rules)
            from family_maintenance import new_family as new_family_maintenance
            new_family_maintenance(db,identity,now,self.maintenance_rules)
            db.execute('INSERT INTO organization_fund_ledger VALUES(?,?,?,?,?,?,?)',
                       (identity,c.actor,c.request_id,'new_family',p['family_initial_funds'],p['family_initial_funds'],now))
            from family_history import record
            record(db,identity,f'command:{c.actor}:{c.request_id}',1,now,None)
            return {'organization':identity,'kind':'family','revision':1}
        if c.operation=='create_guild':
            name,aim,online_founders=c.args
            self._text(name,aim)
            family=self._org(db,c.organization,'family')
            if family['leader']!=c.actor: raise ValueError('permission_denied')
            level=db.execute('SELECT level FROM roles WHERE id=?',(c.actor,)).fetchone()[0]
            if level<p['guild_create_level'] or family['level']<p['guild_family_level']: raise ValueError('guild_create_level')
            members=self._members(db,family)
            capacity=p['family_capacities'][family['level']-1]
            eligible=set()
            for rid,epoch in online_founders:
                row=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(rid,)).fetchone()
                if rid in members and self._valid_lease(row,epoch): eligible.add(rid)
            if len(eligible)*2<capacity: raise ValueError('insufficient_online')
            if db.execute('SELECT 1 FROM guild_families WHERE family=?',(family['id'],)).fetchone(): raise ValueError('already_in_guild')
            self._funding(db,c,p['guild_create_fee'])
            identity=db.execute("INSERT INTO organizations(kind,name,aim,leader) VALUES('guild',?,?,?)",(name,aim,c.actor)).lastrowid
            db.execute('INSERT INTO guild_families VALUES(?,?,?)',(family['id'],identity,now))
            from guild_offices import new_family
            new_family(db,family['id'])
            db.execute('INSERT INTO guild_assets VALUES(?,?,?)',(identity,p['guild_initial_funds'],p['guild_funds_origin']))
            from guild_training import new_guild
            new_guild(db,identity,self.training_rules)
            from guild_research import new_guild as new_guild_research
            new_guild_research(db,identity,self.research_rules)
            from guild_projection import new_guild as new_guild_view
            new_guild_view(db,identity,self.guild_rules)
            from guild_buildings import new_guild as new_guild_buildings
            new_guild_buildings(db,identity,self.building_rules)
            from guild_maintenance import new_guild as new_guild_clock
            new_guild_clock(db,identity,now,self.guild_maintenance_rules)
            from guild_dissolution import new_guild as new_guild_lifecycle
            new_guild_lifecycle(db,identity,self.guild_closure_rules)
            from guild_practice import new_guild as new_practice_materials
            new_practice_materials(db,identity,self.practice_rules)
            db.execute('INSERT INTO organization_fund_ledger VALUES(?,?,?,?,?,?,?)',
                       (identity,c.actor,c.request_id,'new_guild',p['guild_initial_funds'],p['guild_initial_funds'],now))
            from family_guild_history import emit
            emit(db,identity,family['id'],5,f'command:{c.actor}:{c.request_id}',now,self.maintenance_rules.partitions)
            return {'organization':identity,'kind':'guild','revision':1}
        org=self._org(db,c.organization,allow_pending=c.operation in ('resolve_practice','resolve_member_learning'))
        if org['kind']=='guild':
            from guild_offices import prune,member
            if c.operation not in ('apply','resolve_practice','resolve_member_learning'):member(db,org['id'],c.actor)
            prune(db,org)
        if c.operation=='apply':
            if org['kind']=='family':
                if db.execute('SELECT 1 FROM family_members WHERE role_id=?',(c.actor,)).fetchone(): raise ValueError('already_in_family')
                applicant=c.actor
            else:
                family=self._org(db,self._family(db,c.actor),'family')
                if family['leader']!=c.actor: raise ValueError('permission_denied')
                if db.execute('SELECT 1 FROM guild_families WHERE family=?',(family['id'],)).fetchone(): raise ValueError('already_in_guild')
                applicant=family['id']
            count=db.execute('SELECT COUNT(*) FROM organization_applications WHERE organization=?',(org['id'],)).fetchone()[0]
            if count>=p['max_pending'] and not db.execute('SELECT 1 FROM organization_applications WHERE organization=? AND applicant=?',(org['id'],applicant)).fetchone():
                raise ValueError('inbox_full')
            db.execute('INSERT OR IGNORE INTO organization_applications VALUES(?,?)',(org['id'],applicant))
        elif c.operation=='review':
            self._manager(db,org,c.actor)
            applicant,agree=c.args
            if not isinstance(agree,bool): raise ValueError('invalid_decision')
            if not db.execute('SELECT 1 FROM organization_applications WHERE organization=? AND applicant=?',(org['id'],applicant)).fetchone():
                raise ValueError('application_missing')
            if agree and org['kind']=='family':
                if len(self._members(db,org))>=p['family_capacities'][org['level']-1]: raise ValueError('family_full')
                if db.execute('SELECT 1 FROM family_members WHERE role_id=?',(applicant,)).fetchone(): raise ValueError('already_in_family')
                db.execute("INSERT INTO family_members VALUES(?,?,'member',?)",(applicant,org['id'],now))
                from family_projection import new_member
                new_member(db,applicant,p)
            elif agree:
                self._org(db,applicant,'family')
                if db.execute('SELECT 1 FROM guild_families WHERE family=?',(applicant,)).fetchone(): raise ValueError('already_in_guild')
                count=db.execute('SELECT COUNT(*) FROM guild_families WHERE guild=?',(org['id'],)).fetchone()[0]
                if count>=p['guild_family_limit']: raise ValueError('guild_full')
                db.execute('INSERT INTO guild_families VALUES(?,?,?)',(applicant,org['id'],now))
                from guild_offices import new_family
                new_family(db,applicant)
                from guild_projection import admitted_family
                admitted_family(db,org['id'],applicant,self.guild_rules)
                from family_guild_history import emit
                emit(db,org['id'],applicant,5,f'command:{c.actor}:{c.request_id}',now,self.maintenance_rules.partitions)
            db.execute('DELETE FROM organization_applications WHERE organization=? AND applicant=?',(org['id'],applicant))
        elif c.operation=='appoint':
            target,position=c.args
            if org['kind']=='guild':
                from guild_offices import appoint
                appoint(db,org,c.actor,target,position,now,p)
                db.execute('UPDATE organizations SET revision=revision+1 WHERE id=?',(org['id'],))
                return {'organization':org['id'],'revision':org['revision']+1}
            if c.actor!=org['leader']: raise ValueError('permission_denied')
            if target not in self._members(db,org) or position not in ('member','deputy','leader'):
                raise ValueError('invalid_appointment')
            if target==c.actor:
                # Original self-demotion means abdication to the existing
                # deputy, not an organization left without an authority.
                if position=='leader':raise ValueError('invalid_appointment')
                deputy=db.execute("SELECT role_id FROM family_members WHERE family=? AND position='deputy'",(org['id'],)).fetchone()
                if not deputy:raise ValueError('deputy_required')
                db.execute("UPDATE family_members SET position='leader' WHERE role_id=?",(deputy[0],))
                db.execute('UPDATE family_members SET position=? WHERE role_id=?',(position,c.actor))
                db.execute('UPDATE organizations SET leader=?,revision=revision+1 WHERE id=?',(deputy[0],org['id']))
                from family_history import leadership
                leadership(db,org['id'],f'command:{c.actor}:{c.request_id}',now)
                return {'organization':org['id'],'revision':org['revision']+1}
            if position=='deputy' and db.execute("SELECT 1 FROM family_members WHERE family=? AND position='deputy' AND role_id!=?",(org['id'],target)).fetchone():
                raise ValueError('deputy_slot_full')
            if position=='leader':
                prior=db.execute('SELECT position FROM family_members WHERE role_id=?',(target,)).fetchone()[0]
                if prior!='deputy':raise ValueError('deputy_required_for_leadership')
                db.execute("UPDATE family_members SET position='member' WHERE role_id=?",(c.actor,))
                db.execute('UPDATE organizations SET leader=? WHERE id=?',(target,org['id']))
                from family_history import leadership
                leadership(db,org['id'],f'command:{c.actor}:{c.request_id}',now)
            db.execute('UPDATE family_members SET position=? WHERE role_id=?',(position,target))
        elif c.operation in ('leave','expel'):
            target=c.actor if c.operation=='leave' else c.args[0]
            if org['kind']=='family':
                if target not in self._members(db,org): raise ValueError('not_member')
                if target==org['leader']: raise ValueError('transfer_leadership_first')
                if c.operation=='expel':
                    self._manager(db,org,c.actor)
                    if db.execute("SELECT 1 FROM family_members WHERE role_id=? AND position='deputy'",(target,)).fetchone():
                        raise ValueError('demote_first')
                master=db.execute('''SELECT 1 FROM guild_families f JOIN organizations g ON f.guild=g.id
                    WHERE f.family=? AND g.leader=?''',(org['id'],target)).fetchone()
                if master: raise ValueError('guild_leader_cannot_leave')
                db.execute('DELETE FROM family_members WHERE role_id=?',(target,))
            else:
                family=c.args[0]
                row=db.execute('SELECT 1 FROM guild_families WHERE family=? AND guild=?',(family,org['id'])).fetchone()
                if not row: raise ValueError('family_not_in_guild')
                if c.operation=='leave':
                    if self._org(db,family,'family')['leader']!=c.actor: raise ValueError('permission_denied')
                elif org['leader']!=c.actor: raise ValueError('permission_denied')
                if self._family(db,org['leader'])==family: raise ValueError('founding_family_cannot_leave')
                from guild_offices import clear
                for rid in tuple(r[0] for r in db.execute('SELECT role_id FROM family_members WHERE family=?',(family,))):
                    clear(db,org['id'],rid)
                from family_guild_history import emit
                emit(db,org['id'],family,6,f'command:{c.actor}:{c.request_id}',now,self.maintenance_rules.partitions)
                db.execute('DELETE FROM guild_families WHERE family=?',(family,))
        elif c.operation in ('reserve_family_donation','resolve_family_donation'):
            if org['kind']!='family':raise ValueError('invalid_organization_kind')
            from family_donation import reserve,resolve
            if c.operation=='reserve_family_donation':
                reserve(db,org,c,now,self.donation_rules,self.maintenance_rules.partitions)
            else:
                if len(c.args)!=1 or type(c.args[0]) is not str:raise ValueError('invalid_family_donation_resolution')
                resolve(db,org['id'],c.actor,c.args[0],now,self.donation_rules,cancel_unpaid=True)
            revision=db.execute('SELECT revision FROM organizations WHERE id=?',(org['id'],)).fetchone()[0]
            return {'organization':org['id'],'revision':revision}
        elif c.operation=='set_family_products':
            if org['kind']!='family':raise ValueError('invalid_organization_kind')
            from family_products import set_products
            fee=set_products(db,org,c.actor,c.args,self.product_rules)
            if fee:self._spend_organization_funds(db,org,c,fee,now)
        elif c.operation in ('reserve_member_learning','resolve_member_learning'):
            if org['kind']!='guild':raise ValueError('invalid_organization_kind')
            from guild_member_learning import reserve,resolve
            if c.operation=='reserve_member_learning':changed=reserve(db,org,c,now,self.learning_rules)
            else:
                if len(c.args)!=1 or type(c.args[0]) is not str:raise ValueError('invalid_member_learning_resolution')
                changed=resolve(db,org['id'],c.actor,c.args[0])
            if changed:db.execute('UPDATE organizations SET revision=revision+1 WHERE id=?',(org['id'],))
            return {'organization':org['id'],'revision':org['revision']+int(changed)}
        elif c.operation in ('reserve_practice','reserve_pill_practice','resolve_practice'):
            if org['kind']!='guild':raise ValueError('invalid_organization_kind')
            from guild_practice import reserve,resolve
            if c.operation=='resolve_practice':resolve(db,org,c,now,self.practice_rules)
            else:reserve(db,org,c,now,self.practice_rules,mode=1 if c.operation=='reserve_pill_practice' else 0)
        elif c.operation=='choose_building':
            if org['kind']!='guild':raise ValueError('invalid_organization_kind')
            from guild_buildings import choose
            if len(c.args)!=1:raise ValueError('invalid_building_choice')
            fee=choose(db,org,c.actor,c.args[0],self.building_rules)
            self._spend_organization_funds(db,org,c,fee,now)
        elif c.operation in ('set_research','set_practice_open'):
            if org['kind']!='guild':raise ValueError('invalid_organization_kind')
            from guild_training import set_research,set_practice_open
            operation=set_research if c.operation=='set_research' else set_practice_open
            operation(db,org,c.actor,*c.args,self.training_rules)
            if c.operation=='set_practice_open' and c.args[1]:
                funds=db.execute('SELECT funds FROM guild_assets WHERE guild=?',(org['id'],)).fetchone()
                if not funds:raise ValueError('guild_assets_unknown')
                if funds[0]<self.training_rules.open_min_funds:raise ValueError('insufficient_guild_funds')
                self._spend_organization_funds(db,org,c,self.training_rules.open_fee,now)
        elif c.operation in ('resign','set_authority'):
            if org['kind']!='guild':raise ValueError('invalid_organization_kind')
            from guild_offices import resign,set_authority
            if c.operation=='resign':resign(db,org,c.actor,now,p)
            else:set_authority(db,org,c.actor,*c.args,p)
        elif c.operation in ('mute','change_aim'):
            from guild_offices import position as guild_position,member as guild_member
            if org['kind']=='guild':
                guild_member(db,org['id'],c.actor)
                actor_position=guild_position(db,org,c.actor)
            else:actor_position='leader' if c.actor==org['leader'] else 'member'
            allowed=('leader','deputy','left_elder','right_elder') if c.operation=='mute' else ('leader','deputy')
            if actor_position not in allowed:raise ValueError('permission_denied')
            if c.operation=='mute':
                target,=c.args
                if org['kind']!='guild' or target not in self._members(db,org): raise ValueError('not_member')
                if guild_position(db,org,target) in ('leader','deputy','left_elder','right_elder'):
                    raise ValueError('protected_office')
                db.execute('INSERT INTO organization_mutes VALUES(?,?,?) ON CONFLICT(organization,role_id) DO UPDATE SET until_ms=excluded.until_ms',
                           (org['id'],target,now+p['guild_mute_ms']))
            else:
                aim,=c.args
                self._text(org['name'],aim)
                if org['kind']=='family':
                    # Historical cash intents must be resolved/cancelled first;
                    # charging both pools for one intent would be irreconcilable.
                    if db.execute('SELECT 1 FROM organization_funding WHERE actor=? AND request_id=?',
                                  (c.actor,c.request_id)).fetchone():raise ValueError('legacy_cash_aim_requires_revoke')
                self._spend_organization_funds(db,org,c,p['family_aim_fee' if org['kind']=='family' else 'guild_aim_fee'],now)
                db.execute('UPDATE organizations SET aim=? WHERE id=?',(aim,org['id']))
        else: raise ValueError('operation_not_supported')
        db.execute('UPDATE organizations SET revision=revision+1 WHERE id=?',(org['id'],))
        return {'organization':org['id'],'revision':org['revision']+1}

    def _spend_organization_funds(self,db,org,command,amount,now):
        if type(amount) is not int or not 0<amount<2**63:raise ValueError('invalid_family_fee')
        table,key=('family_assets','family') if org['kind']=='family' else ('guild_assets','guild')
        row=db.execute(f'SELECT funds FROM {table} WHERE {key}=?',(org['id'],)).fetchone()
        if not row:raise ValueError(org['kind']+'_assets_unknown')
        if row[0]<amount:raise ValueError('insufficient_'+org['kind']+'_funds')
        balance=row[0]-amount
        db.execute(f'UPDATE {table} SET funds=? WHERE {key}=?',(balance,org['id']))
        db.execute('INSERT INTO organization_fund_ledger VALUES(?,?,?,?,?,?,?)',
                   (org['id'],command.actor,command.request_id,command.operation,-amount,balance,now))

    def family_assets(self,identity):
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            self._org(db,identity,'family',allow_pending=True)
            row=db.execute('SELECT * FROM family_assets WHERE family=?',(identity,)).fetchone()
            if not row:raise ValueError('family_assets_unknown')
            return FamilyAssets(row['family'],row['founder_name'],row['funds'],row['popularity'],row['origin'],row['construction'])

    def family_donation_receipt(self,identity,actor,reservation):
        from family_donation import receipt
        with closing(self.connect()) as db:
            return receipt(db,identity,actor,reservation)

    def pending_family_donations(self,partition,after=None):
        r=self.maintenance_rules
        if type(partition) is not int or not 0<=partition<r.partitions:raise ValueError('invalid_donation_partition')
        if after is not None and (type(after) is not tuple or len(after)!=4
                or any(type(n) is not int or not 0<n<2**63 for n in after[:3])
                or type(after[3]) is not str or not 1<=len(after[3])<=96):raise ValueError('invalid_donation_cursor')
        condition=' AND (created_ms,family,role_id,reservation)>(?,?,?,?)' if after is not None else ''
        args=(partition,)+(() if after is None else after)+(r.batch_limit,)
        with closing(self.connect()) as db:
            return tuple(tuple(row) for row in db.execute('''SELECT family,created_ms,role_id,reservation
                FROM family_donation_permits WHERE partition=? AND status='reserved' '''+condition+
                ' ORDER BY created_ms,family,role_id,reservation LIMIT ?',args))

    def sweep_family_donations(self,command,now):
        from family_donation import validate_sweep,settle_pending
        validate_sweep(command,now)
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            return settle_pending(db,command.family,now,self.donation_rules)

    def family_products_snapshot(self,identity):
        """Trusted frozen read; not NPC admission or permission to mutate."""
        from family_products import snapshot
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            self._org(db,identity,'family')
            return snapshot(db,identity)

    def family_maintenance_snapshot(self,identity):
        from family_maintenance import snapshot
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            self._org(db,identity,'family',allow_pending=True)
            return snapshot(db,identity)

    def family_dissolution_pending(self,identity):
        from family_maintenance import dissolution_pending
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            self._org(db,identity,'family',allow_pending=True)
            return dissolution_pending(db,identity)

    def apply_guild_family_dissolution(self,event,request_id,deadline,now):
        from guild_dissolution import apply
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            return apply(db,event,request_id,deadline,now,self.guild_closure_rules)

    def guild_lifecycle(self,identity):
        """Trusted frozen status read, including retired historical guilds."""
        from guild_dissolution import lifecycle
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return lifecycle(db,identity)

    def pending_family_guild_dissolutions(self,partition,after=None):
        r=self.maintenance_rules
        if type(partition) is not int or not 0<=partition<r.partitions:raise ValueError('invalid_closure_partition')
        if after is not None and (type(after) is not tuple or len(after)!=2
                or any(type(value) is not int or not 0<value<2**63 for value in after)):
            raise ValueError('invalid_closure_cursor')
        condition=' AND (due_ms,family)>(?,?)' if after is not None else ''
        args=(partition,)+(() if after is None else after)+(r.batch_limit,)
        with closing(self.connect()) as db:
            return tuple(tuple(row) for row in db.execute('''SELECT family,due_ms FROM family_dissolution_outbox
                WHERE partition=? AND guild_done=0'''+condition+' ORDER BY due_ms,family LIMIT ?',args))

    def ack_family_guild_dissolution(self,command,now):
        from family_maintenance import ack_guild_closure
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            return ack_guild_closure(db,command,now,self.guild_closure_rules)

    def family_guild_dissolution_done(self,identity,due):
        with closing(self.connect()) as db:
            row=db.execute('SELECT guild_done FROM family_dissolution_outbox WHERE family=? AND due_ms=?',
                (identity,due)).fetchone()
            if not row:raise ValueError('family_dissolution_missing')
            return row[0]==1

    def maintain_family(self,command,now):
        """Trusted system tick, scheduled on this family's organization owner."""
        from family_maintenance import settle,validate
        from family_donation import settle_pending
        validate(command,now,self.maintenance_rules)
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM family_maintenance_receipts WHERE family=? AND due_ms=?',
                    (command.family,command.due_ms)).fetchone():
                settle_pending(db,command.family,now,self.donation_rules,cancel_unpaid=True)
            return settle(db,command,now,self.maintenance_rules)

    def resume_family_maintenance(self,command,now):
        from family_maintenance import resume
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            return resume(db,command,now,self.maintenance_rules)

    def due_family_maintenance(self,partition,now,after=None):
        """Bounded indexed directory hint; the family owner rechecks its clock."""
        r=self.maintenance_rules
        if (type(partition) is not int or not 0<=partition<r.partitions
                or type(now) is not int or not 0<=now<2**63):raise ValueError('invalid_family_maintenance_directory')
        if after is not None and (type(after) is not tuple or len(after)!=2
                or any(type(value) is not int or not 0<value<2**63 for value in after)):
            raise ValueError('invalid_family_maintenance_cursor')
        condition=' AND (next_due_ms,family)>(?,?)' if after is not None else ''
        args=(partition,now)+(() if after is None else after)+(r.batch_limit,)
        with closing(self.connect()) as db:
            return tuple(tuple(row) for row in db.execute('''SELECT family,next_due_ms FROM family_maintenance
                WHERE partition=? AND state='active' AND next_due_ms<=?'''+condition+
                ' ORDER BY next_due_ms,family LIMIT ?',args))

    def pending_family_guild_history(self,partition,after=None):
        from family_guild_history import pending
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return pending(db,partition,after,self.maintenance_rules)

    def family_guild_history_page(self,partition,after=None,ceiling=None):
        from family_guild_history import page
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return page(db,partition,after,ceiling,self.maintenance_rules)

    def family_guild_history_event(self,sequence):
        from family_guild_history import event
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return event(db,sequence)

    def consume_family_guild_history(self,command,now):
        from family_guild_history import validate,consume
        validate(command,now)
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self._org(db,command.event.family,'family',allow_pending=True)
            return consume(db,command,now)

    def ack_family_guild_history(self,command,now):
        from family_guild_history import validate,acknowledge
        validate(command,now)
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self._org(db,command.event.guild,'guild',allow_pending=True)
            return acknowledge(db,command,now)

    def family_products_panel(self,actor,epoch,identity):
        """Current leader/lease-gated projection; caller still proves NPC access."""
        from family_products import panel
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return panel(db,self._org(db,identity,'family'),actor,epoch,self.product_rules)

    def family_audience(self,identity):
        from family_projection import audience
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return audience(db,identity)

    def family_projection(self,actor,epoch,family,generation,online):
        from family_projection import projection
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return projection(db,actor,epoch,family,generation,online,self.policy)

    def family_presence(self,family,actor,epoch,is_online,now):
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(actor,)).fetchone()
            if not self._valid_lease(lease,epoch):raise ValueError('stale_epoch')
            if self._family(db,actor)!=family:raise ValueError('stale_family_membership')
            # Unknown old state remains unknown; presence is not a migration.
            row=db.execute('SELECT generation FROM family_member_state WHERE role_id=?',(actor,)).fetchone()
            if not row:return
            if not is_online:db.execute('UPDATE family_member_state SET offline_ms=? WHERE role_id=?',(now,actor))

    def guild_assets(self,identity):
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            self._org(db,identity,'guild',allow_pending=True)
            row=db.execute('SELECT * FROM guild_assets WHERE guild=?',(identity,)).fetchone()
            if not row:raise ValueError('guild_assets_unknown')
            return GuildAssets(row['guild'],row['funds'],row['origin'])

    def guild_office_snapshot(self,identity):
        from guild_offices import snapshot
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return snapshot(db,self._org(db,identity,'guild'))

    def guild_training_snapshot(self,identity):
        from guild_training import snapshot
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            self._org(db,identity,'guild')
            return snapshot(db,identity)

    def guild_research_snapshot(self,identity):
        from guild_research import snapshot
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            self._org(db,identity,'guild')
            return snapshot(db,identity,self.research_rules)

    def guild_building_snapshot(self,identity):
        from guild_buildings import snapshot
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            self._org(db,identity,'guild')
            return snapshot(db,identity,self.building_rules)

    def guild_maintenance_snapshot(self,identity):
        from guild_maintenance import snapshot
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            self._org(db,identity,'guild',allow_pending=True)
            return snapshot(db,identity,self.guild_maintenance_rules,self.building_rules)

    def maintain_guild(self,command,now):
        from guild_maintenance import validate,settle
        validate(command,now,self.guild_maintenance_rules)
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self._org(db,command.guild,'guild',allow_pending=True)
            return settle(db,command,now,self.guild_maintenance_rules,self.building_rules,self.research_rules,
                self.maintenance_rules.partitions)

    def guild_maintenance_terminal(self,identity,due_ms):
        from guild_maintenance_closure import terminal
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            self._org(db,identity,'guild',allow_pending=True)
            return terminal(db,identity,due_ms)

    def resume_guild_maintenance(self,command,now):
        from guild_maintenance import validate,resume
        validate(command,now,self.guild_maintenance_rules,resume=True)
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self._org(db,command.guild,'guild',allow_pending=True)
            return resume(db,command,now,self.guild_maintenance_rules,self.building_rules)

    def guild_maintenance_page(self,partition,now,after=None,ceiling=None):
        from guild_maintenance import page
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return page(db,partition,now,after,ceiling,self.guild_maintenance_rules)

    def apply_guild_construction(self,command,now):
        from guild_buildings import validate_work,apply_work
        validate_work(command,now)
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            org=self._org(db,command.guild,'guild',allow_pending=True)
            return apply_work(db,org,command,now,self.building_rules)

    def guild_building_panel(self,actor,epoch,guild,family_token,member_token):
        from guild_projection import scope
        from guild_training import authorize
        from guild_buildings import snapshot
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            if scope(db,actor,epoch)!=(guild,family_token,member_token):raise ValueError('guild_membership_changed')
            authorize(db,self._org(db,guild,'guild'),actor,5)
            return snapshot(db,guild,self.building_rules)

    def award_guild_research(self,command,now):
        """Trusted source consumer; caller must prove its event before invoking.

        A guild-maintenance writer can instead call guild_research.award in its
        own transaction. Cross-owner source consumption needs durable inbox/outbox.
        No player/NPC route authorizes this method or supplies research amounts.
        """
        from guild_research import validate,award
        validate(command,now)
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self._org(db,command.guild,'guild',allow_pending=True)
            return award(db,command,now,self.research_rules)

    def guild_scope(self,actor,epoch):
        from guild_projection import scope
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return scope(db,actor,epoch)

    def guild_audience(self,identity):
        from guild_projection import audience
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            return audience(db,identity)

    def guild_practice_materials(self,identity):
        from guild_practice import materials
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            self._org(db,identity,'guild')
            return materials(db,identity)

    def guild_practice_permit(self,actor,epoch,identity,reservation):
        from guild_practice import permit
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(actor,)).fetchone()
            if not self._valid_lease(lease,epoch):raise ValueError('stale_epoch')
            return permit(db,identity,actor,reservation)

    def pending_practices(self,actor,epoch):
        from guild_practice import pending
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(actor,)).fetchone()
            if not self._valid_lease(lease,epoch):raise ValueError('stale_epoch')
            return pending(db,actor,self.practice_rules.receipt_limit)

    def practice_states(self,actor,epoch):
        from role_practice import read
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            role=db.execute('SELECT account_id FROM roles WHERE id=?',(actor,)).fetchone()
            if not role:raise ValueError('role_missing')
            return read(db,role[0],actor,epoch,self.practice_rules)

    def guild_learning_permit(self,actor,epoch,identity,reservation):
        from guild_member_learning import permit
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(actor,)).fetchone()
            if not self._valid_lease(lease,epoch):raise ValueError('stale_epoch')
            return permit(db,identity,actor,reservation)

    def pending_member_learning(self,actor,epoch):
        from guild_member_learning import pending
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(actor,)).fetchone()
            if not self._valid_lease(lease,epoch):raise ValueError('stale_epoch')
            return pending(db,actor)

    def life_skill_states(self,actor,epoch):
        from role_life_skills import read
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            row=db.execute('SELECT account_id FROM roles WHERE id=?',(actor,)).fetchone()
            if row is None:raise ValueError('role_missing')
            return read(db,row[0],actor,epoch,self.life_rules)

    def guild_projection(self,actor,epoch,guild,family_token,member_token,online):
        from guild_projection import projection
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            result=projection(db,actor,epoch,guild,family_token,member_token,online,self.policy)
            if self.research_rules is not None:
                from guild_research import snapshot
                try:result=replace(result,research=snapshot(db,guild,self.research_rules))
                except ValueError as error:
                    if str(error)!='guild_research_state_unknown':raise
            if self.building_rules is not None:
                from guild_buildings import snapshot as buildings
                from guild_training import authorize
                try:
                    authorize(db,self._org(db,guild,'guild'),actor,5)
                    result=replace(result,buildings=buildings(db,guild,self.building_rules))
                except ValueError as error:
                    if str(error) not in ('permission_denied','guild_building_state_unknown'):raise
            return result

    def refresh_guild(self,identity,requester=()):
        """Guild-owner read-model handoff; empty requester is trusted internal work.

        This is not a wire authority bypass. Native requests supply the current
        role/epoch; internal family-change nudges contain only the guild ID.
        """
        from guild_projection import refresh
        if type(requester) is not tuple or len(requester) not in (0,2):raise ValueError('frozen_guild_requester_required')
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self._org(db,identity,'guild')
            return refresh(db,identity,requester,self.guild_rules)

    def family_guild(self,identity):
        with closing(self.connect()) as db:
            row=db.execute('SELECT guild FROM guild_families WHERE family=?',(identity,)).fetchone()
            return row[0] if row else None

    def snapshot(self,identity):
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            org=self._org(db,identity)
            return dict(org),self._members(db,org)

    def membership(self,actor,epoch,kind):
        """Read-only routing hint. The organization owner checks membership again."""
        if kind not in ('family','guild'):raise ValueError('invalid_organization_kind')
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(actor,)).fetchone()
            if not self._valid_lease(lease,epoch):raise ValueError('stale_epoch')
            family=self._family(db,actor)
            if kind=='family':return family
            row=db.execute('SELECT guild FROM guild_families WHERE family=?',(family,)).fetchone()
            if not row:raise ValueError('not_in_guild')
            self._org(db,row[0],'guild')
            return row[0]

    def chat(self,identity,actor,epoch,content,now_ms,request_id='',deadline_ms=None):
        if not content.strip() or len(content)>self.policy['max_chat_text'] or '\0' in content: raise ValueError('invalid_chat')
        if request_id and (len(request_id)>160 or deadline_ms is None or now_ms>deadline_ms):
            raise ValueError('invalid_request_or_deadline')
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(actor,)).fetchone()
            if not self._valid_lease(lease,epoch): raise ValueError('stale_epoch')
            org=self._org(db,identity);members=self._members(db,org)
            if actor not in members: raise ValueError('not_member')
            if request_id:
                fingerprint=hashlib.sha256(json.dumps([identity,content],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
                receipt=db.execute('SELECT fingerprint FROM organization_chat_receipts WHERE actor=? AND request_id=?',
                                   (actor,request_id)).fetchone()
                if receipt:
                    if receipt[0]!=fingerprint:raise ValueError('request_id_conflict')
                    return None
                # Remove only this actor's expired transport requests. A full
                # unexpired window applies backpressure; it never loses dedup.
                db.execute('DELETE FROM organization_chat_receipts WHERE actor=? AND deadline_ms<?',(actor,now_ms))
                count=db.execute('SELECT COUNT(*) FROM organization_chat_receipts WHERE actor=?',(actor,)).fetchone()[0]
                if count>=self.policy['chat_receipt_limit']:raise ValueError('chat_receipts_full')
            mute=db.execute('SELECT until_ms FROM organization_mutes WHERE organization=? AND role_id=?',(identity,actor)).fetchone()
            if mute and mute[0]>now_ms: raise ValueError('muted')
            clock=db.execute('SELECT last_ms FROM organization_chat_clock WHERE organization=? AND role_id=?',(identity,actor)).fetchone()
            if clock and now_ms-clock[0]<self.policy['chat_interval_ms']: raise ValueError('chat_cooldown')
            db.execute('INSERT INTO organization_chat_clock VALUES(?,?,?) ON CONFLICT(organization,role_id) DO UPDATE SET last_ms=excluded.last_ms',
                       (identity,actor,now_ms))
            if request_id:db.execute('INSERT INTO organization_chat_receipts VALUES(?,?,?,?)',(actor,request_id,fingerprint,deadline_ms))
            return OrganizationBroadcast(identity,org['revision'],actor,members,content,self._membership_stamps(db,org))

    def authorize_delivery(self,event,recipient):
        # Recheck authoritative membership at dequeue: a kicked member must not
        # receive a queued message from an obsolete roster snapshot.
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            try:org=self._org(db,event.organization)
            except ValueError as error:
                if str(error) in ('family_dissolution_pending','guild_succession_pending','guild_dissolution_pending'):return False
                raise
            members=self._members(db,org)
            # Any membership/office change invalidates queued old snapshots,
            # including leave -> rejoin with the same role. Conservative until
            # per-membership durable generations replace this revision fence.
            previous={r[0]:r for r in event.memberships}
            current={r[0]:r for r in self._membership_stamps(db,org)}
            return (org['revision']==event.revision and recipient in event.recipients
                    and recipient in members and event.sender in members
                    and current[recipient]==previous.get(recipient)
                    and current[event.sender]==previous.get(event.sender))
