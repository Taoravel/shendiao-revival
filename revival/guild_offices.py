"""Guild offices inside the organization owner's transaction; no I/O ownership.

Named offices hide native enum values. Delegated authority belongs to the
current deputy and is cleared whenever that office changes or resigns.
"""
from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class GuildOfficeSnapshot:
    guild: int
    leader: int
    offices: tuple  # (role_id, named position)
    deputy_authority: int


def prepare(db):
    # The old UNIQUE(guild,position) incorrectly capped every elder kind at one.
    # Preserve that table as a migration archive; copy exactly once under DDL tx.
    old_unique=False
    for row in db.execute('PRAGMA index_list(guild_offices)'):
        if row[2] and tuple(r[0] for r in db.execute('SELECT name FROM pragma_index_info(?) ORDER BY seqno',(row[1],)))==('guild','position'):
            old_unique=True
    if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
    if old_unique:
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='guild_offices_legacy_v1'").fetchone():
            raise ValueError('guild_office_migration_conflict')
        db.execute('ALTER TABLE guild_offices RENAME TO guild_offices_legacy_v1')
        db.execute('''CREATE TABLE guild_offices(guild INTEGER NOT NULL REFERENCES organizations(id),
            role_id INTEGER NOT NULL REFERENCES roles(id),position TEXT NOT NULL,PRIMARY KEY(guild,role_id))''')
        db.execute('INSERT INTO guild_offices SELECT guild,role_id,position FROM guild_offices_legacy_v1')
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS guild_deputy_slot ON guild_offices(guild) WHERE position='deputy'")
    db.execute('''CREATE TABLE IF NOT EXISTS guild_patrols(guild INTEGER NOT NULL REFERENCES organizations(id),
        role_id INTEGER NOT NULL REFERENCES roles(id),PRIMARY KEY(guild,role_id))''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_deputy_authority(guild INTEGER PRIMARY KEY REFERENCES organizations(id),
        role_id INTEGER NOT NULL REFERENCES roles(id),mask INTEGER NOT NULL CHECK(mask>=0))''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_family_generations(family INTEGER PRIMARY KEY
        REFERENCES guild_families(family) ON DELETE CASCADE,generation TEXT NOT NULL UNIQUE)''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_office_bindings(guild INTEGER NOT NULL,role_id INTEGER NOT NULL,
        family_token TEXT NOT NULL,member_token TEXT NOT NULL,PRIMARY KEY(guild,role_id))''')
    db.execute('CREATE TABLE IF NOT EXISTS guild_office_schema(name TEXT PRIMARY KEY,version INTEGER NOT NULL)')
    for row in tuple(db.execute('SELECT family FROM guild_families')):new_family(db,row[0])
    if not db.execute("SELECT 1 FROM guild_office_schema WHERE name='bindings'").fetchone():
        for row in tuple(db.execute('SELECT guild,role_id FROM guild_offices')):
            try:current=member(db,row['guild'],row['role_id'])
            except ValueError:continue
            bind(db,row['guild'],row['role_id'],current)
        db.execute("INSERT INTO guild_office_schema VALUES('bindings',1)")


def new_family(db,family):
    db.execute('INSERT OR IGNORE INTO guild_family_generations VALUES(?,?)',(family,uuid.uuid4().hex))


def member(db,guild,role):
    cursor=db.execute('''SELECT m.family,m.position,MAX(m.joined_ms,g.joined_ms) AS joined_ms,f.leader,
        t.generation AS family_token,COALESCE(s.generation,'legacy:'||m.joined_ms) AS member_token
        FROM family_members m JOIN guild_families g ON g.family=m.family JOIN organizations f ON f.id=m.family
        JOIN guild_family_generations t ON t.family=m.family
        LEFT JOIN family_member_state s ON s.role_id=m.role_id
        LEFT JOIN family_maintenance c ON c.family=m.family
        WHERE g.guild=? AND m.role_id=? AND COALESCE(c.state,'active')='active' ''',(guild,role))
    row=cursor.fetchone()
    if not row:raise ValueError('not_member')
    return dict(zip((c[0] for c in cursor.description),row))


def position(db,org,role):
    if role==org['leader']:return 'leader'
    try:current=member(db,org['id'],role)
    except ValueError:return 'member'
    binding=db.execute('SELECT family_token,member_token FROM guild_office_bindings WHERE guild=? AND role_id=?',
                       (org['id'],role)).fetchone()
    if not binding or tuple(binding)!=(current['family_token'],current['member_token']):return 'member'
    row=db.execute('SELECT position FROM guild_offices WHERE guild=? AND role_id=?',(org['id'],role)).fetchone()
    if row:return row[0]
    return 'patrol' if db.execute('SELECT 1 FROM guild_patrols WHERE guild=? AND role_id=?',(org['id'],role)).fetchone() else 'member'


def authority(db,org):
    row=db.execute('''SELECT a.mask FROM guild_deputy_authority a JOIN guild_offices o
        ON o.guild=a.guild AND o.role_id=a.role_id AND o.position='deputy' WHERE a.guild=?''',(org['id'],)).fetchone()
    if not row:return 0
    deputy=db.execute("SELECT role_id FROM guild_offices WHERE guild=? AND position='deputy'",(org['id'],)).fetchone()
    return row[0] if deputy and position(db,org,deputy[0])=='deputy' else 0


def clear(db,guild,role):
    db.execute('DELETE FROM guild_offices WHERE guild=? AND role_id=?',(guild,role))
    db.execute('DELETE FROM guild_patrols WHERE guild=? AND role_id=?',(guild,role))
    db.execute('DELETE FROM guild_deputy_authority WHERE guild=? AND role_id=?',(guild,role))
    db.execute('DELETE FROM guild_office_bindings WHERE guild=? AND role_id=?',(guild,role))


def bind(db,guild,role,current):
    db.execute('INSERT OR REPLACE INTO guild_office_bindings VALUES(?,?,?,?)',
               (guild,role,current['family_token'],current['member_token']))


def prune(db,org):
    # Only the guild owner writes office cleanup. Family exits merely change
    # membership; the token comparison revokes authority immediately and also
    # prevents leave -> rejoin from resurrecting a stale office before cleanup.
    roles={r[0] for r in db.execute('SELECT role_id FROM guild_offices WHERE guild=?',(org['id'],))}
    roles.update(r[0] for r in db.execute('SELECT role_id FROM guild_patrols WHERE guild=?',(org['id'],)))
    for role in roles:
        if position(db,org,role)=='member':clear(db,org['id'],role)


def appoint(db,org,actor,target,desired,now,policy):
    source=member(db,org['id'],actor);destination=member(db,org['id'],target)
    if target==actor or desired not in ('member','patrol','left_elder','right_elder','deputy','leader'):
        raise ValueError('invalid_appointment')
    current=position(db,org,target)
    actor_position=position(db,org,actor)
    if current=='leader':raise ValueError('protected_leader')
    if desired==current:raise ValueError('position_unchanged')
    family_patrol=(desired=='patrol' and source['leader']==actor and source['family']==destination['family']
                   and destination['position']=='member')
    delegated=(actor_position=='deputy' and authority(db,org)&(1<<policy['guild_appointment_authority_bit']))
    if actor!=org['leader'] and not delegated and not family_patrol:raise ValueError('permission_denied')
    if actor!=org['leader'] and desired=='leader':raise ValueError('permission_denied')
    if desired=='patrol' and (current not in ('member','patrol') or destination['position']=='leader'):
        raise ValueError('demote_first')
    if desired=='deputy':
        row=db.execute("SELECT role_id FROM guild_offices WHERE guild=? AND position='deputy'",(org['id'],)).fetchone()
        if row and row[0]!=target:raise ValueError('deputy_slot_full')
    if desired in ('left_elder','right_elder'):
        count=db.execute('SELECT COUNT(*) FROM guild_offices WHERE guild=? AND position=?',(org['id'],desired)).fetchone()[0]
        if count>=org['level']//policy['guild_elder_level_divisor']:raise ValueError('elder_slots_full')
    if desired=='leader':
        if now-destination['joined_ms']<policy['guild_leader_tenure_ms']:raise ValueError('leadership_tenure')
        # Changing leader invalidates every delegated deputy authority, even if
        # a different deputy remains in place under the incoming leader.
        db.execute('DELETE FROM guild_deputy_authority WHERE guild=?',(org['id'],))
        db.execute('UPDATE organizations SET leader=? WHERE id=?',(target,org['id']))
    clear(db,org['id'],target)
    if desired in ('deputy','left_elder','right_elder'):
        db.execute('INSERT INTO guild_offices VALUES(?,?,?)',(org['id'],target,desired))
    elif desired=='patrol':db.execute('INSERT INTO guild_patrols VALUES(?,?)',(org['id'],target))
    if desired not in ('member','leader'):bind(db,org['id'],target,destination)


def resign(db,org,actor,now,policy):
    member(db,org['id'],actor)
    current=position(db,org,actor)
    if current=='leader':
        deputy=db.execute("SELECT role_id FROM guild_offices WHERE guild=? AND position='deputy'",(org['id'],)).fetchone()
        if not deputy:raise ValueError('deputy_required')
        successor=member(db,org['id'],deputy[0])
        if now-successor['joined_ms']<policy['guild_leader_tenure_ms']:raise ValueError('leadership_tenure')
        clear(db,org['id'],deputy[0])
        db.execute('DELETE FROM guild_deputy_authority WHERE guild=?',(org['id'],))
        db.execute('UPDATE organizations SET leader=? WHERE id=?',(deputy[0],org['id']))
    elif current=='member':raise ValueError('not_officer')
    clear(db,org['id'],actor)


def set_authority(db,org,actor,target,bit,enabled,policy):
    if actor!=org['leader']:raise ValueError('permission_denied')
    member(db,org['id'],target)
    if position(db,org,target)!='deputy':raise ValueError('deputy_required')
    if type(bit) is not int or not 0<=bit<policy['guild_authority_bit_count'] or type(enabled) is not bool:
        raise ValueError('invalid_authority')
    previous=authority(db,org)
    mask=previous|(1<<bit) if enabled else previous&~(1<<bit)
    db.execute('''INSERT INTO guild_deputy_authority VALUES(?,?,?) ON CONFLICT(guild)
        DO UPDATE SET role_id=excluded.role_id,mask=excluded.mask''',(org['id'],target,mask))


def snapshot(db,org):
    rows=list(db.execute('SELECT role_id,position FROM guild_offices WHERE guild=?',(org['id'],)))
    rows.extend((r[0],'patrol') for r in db.execute('SELECT role_id FROM guild_patrols WHERE guild=?',(org['id'],)))
    rows=[tuple(r) for r in rows if position(db,org,r[0])==r[1]]
    return GuildOfficeSnapshot(org['id'],org['leader'],tuple(sorted(rows)),authority(db,org))
