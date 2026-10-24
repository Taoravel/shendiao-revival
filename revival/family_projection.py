"""Family persistence/read model inside the organization transaction seam.

Only new memberships receive explicit initial prestige. Existing unknown state
is deferred, never zero-filled. No connections, commits, wallets or Sessions.
"""
from dataclasses import dataclass,replace
from datetime import datetime,timezone,timedelta
import uuid
import faction_protocol as p


@dataclass(frozen=True)
class FamilyAudience:
    identity: int
    members: tuple  # (role_id, membership_generation or None)
    applications: tuple


@dataclass(frozen=True)
class FamilyProjection:
    view: p.FamilyView
    members: tuple
    applications: tuple
    manager: bool


def prepare(db):
    columns={row[1] for row in db.execute('PRAGMA table_info(family_assets)')}
    if 'construction' not in columns:db.execute('ALTER TABLE family_assets ADD COLUMN construction INTEGER CHECK(construction>=0)')
    db.executescript('''CREATE TABLE IF NOT EXISTS family_member_state (
        role_id INTEGER PRIMARY KEY REFERENCES family_members(role_id) ON DELETE CASCADE,
        generation TEXT NOT NULL UNIQUE,metadata INTEGER NOT NULL,
        prestige_first INTEGER NOT NULL CHECK(prestige_first>=0),prestige_second INTEGER NOT NULL CHECK(prestige_second>=0),
        offline_ms INTEGER,origin TEXT NOT NULL);''')
    db.execute('''CREATE TABLE IF NOT EXISTS family_join_events (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT,role_id INTEGER NOT NULL,family INTEGER NOT NULL,
        generation TEXT NOT NULL UNIQUE REFERENCES family_member_state(generation) ON DELETE CASCADE)''')


def new_member(db,role_id,policy):
    a,b=policy['family_new_member_prestige']
    generation=uuid.uuid4().hex
    db.execute('INSERT INTO family_member_state VALUES(?,?,?,?,?,?,?)',
        (role_id,generation,policy['family_new_member_metadata'],a,b,None,policy['family_member_origin']))
    # This family-owned record is consumed through each guild's own cursor.
    # Leaving deletes the current membership/event; AUTOINCREMENT prevents a
    # later rejoin from reusing an already-consumed sequence.
    db.execute('INSERT INTO family_join_events(role_id,family,generation) SELECT role_id,family,? FROM family_members WHERE role_id=?',
               (generation,role_id))


def audience(db,identity):
    row=db.execute('SELECT kind FROM organizations WHERE id=?',(identity,)).fetchone()
    if not row or row[0]!='family':return None
    clock=db.execute('SELECT state FROM family_maintenance WHERE family=?',(identity,)).fetchone()
    if clock and clock[0]!='active':return FamilyAudience(identity,(),())
    members=tuple(tuple(r) for r in db.execute('''SELECT m.role_id,s.generation FROM family_members m
        LEFT JOIN family_member_state s ON s.role_id=m.role_id WHERE m.family=? ORDER BY m.role_id''',(identity,)))
    applications=tuple(r[0] for r in db.execute('SELECT applicant FROM organization_applications WHERE organization=? ORDER BY applicant',(identity,)))
    return FamilyAudience(identity,members,applications)


def projection(db,actor,epoch,family,generation,online,policy):
    lease=db.execute('SELECT epoch,active FROM role_leases WHERE role_id=?',(actor,)).fetchone()
    if not lease or str(lease['epoch'])!=str(epoch) or lease['active']!=1:raise ValueError('stale_epoch')
    clock=db.execute('SELECT state FROM family_maintenance WHERE family=?',(family,)).fetchone()
    if clock and clock[0]!='active':raise ValueError('stale_family_membership')
    own=db.execute('''SELECT m.family,m.position,s.generation FROM family_members m
        LEFT JOIN family_member_state s ON s.role_id=m.role_id WHERE m.role_id=?''',(actor,)).fetchone()
    if not own or own['family']!=family or own['generation']!=generation:raise ValueError('stale_family_membership')
    org=db.execute("SELECT * FROM organizations WHERE id=? AND kind='family'",(family,)).fetchone()
    assets=db.execute('SELECT * FROM family_assets WHERE family=?',(family,)).fetchone()
    if not org or not assets or assets['construction'] is None:raise ValueError('family_panel_unknown')
    level=org['level']
    if not 1<=level<=len(policy['family_construction_targets']):raise ValueError('family_level_unknown')
    view=p.FamilyView(family,org['name'],org['aim'],assets['founder_name'],level,assets['funds'],
        assets['popularity'],policy['family_popularity_max'],assets['construction'],policy['family_construction_targets'][level-1])
    from family_history import read
    view=replace(view,history=read(db,family,policy))
    current={rid:str(value) for rid,value in online}
    zone=timezone(timedelta(minutes=policy['family_utc_offset_minutes']))
    members=[]
    for row in db.execute('''SELECT m.role_id,m.position,r.name,r.level,s.*,l.epoch,l.active FROM family_members m
        JOIN roles r ON r.id=m.role_id LEFT JOIN family_member_state s ON s.role_id=m.role_id
        LEFT JOIN role_leases l ON l.role_id=m.role_id WHERE m.family=? ORDER BY m.role_id''',(family,)):
        if row['generation'] is None:raise ValueError('family_member_state_unknown')
        online_now=row['active']==1 and current.get(row['role_id'])==str(row['epoch'])
        stamp='' if online_now else (datetime.fromtimestamp(row['offline_ms']/1000,zone).strftime(policy['family_offline_time_format'])
                                    if row['offline_ms'] is not None else policy['family_unknown_offline_text'])
        members.append(p.FamilyMemberWire(row['role_id'],row['name'],row['metadata'],
                       (row['prestige_first'],row['prestige_second']),row['level'],row['position'],stamp))
    applications=()
    if own['position'] in ('leader','deputy'):
        applications=tuple(p.FamilyApplication(r['id'],r['name'],r['level'],r['school']) for r in db.execute('''
            SELECT r.id,r.name,r.level,r.school FROM organization_applications a JOIN roles r ON r.id=a.applicant
            WHERE a.organization=? ORDER BY a.applicant''',(family,)))
    return FamilyProjection(view,tuple(members),applications,own['position'] in ('leader','deputy'))
