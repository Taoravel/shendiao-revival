"""Guild-owned terminal handoff; family/role/map consumers retain ownership."""
from dataclasses import dataclass,asdict
import hashlib,json


@dataclass(frozen=True)
class GuildTerminal:
    guild: int
    due_ms: int
    revision: int
    families: tuple
    members: tuple
    state: str
    recipe: str


def _json(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS guild_maintenance_terminal_outbox (
        guild INTEGER NOT NULL REFERENCES organizations(id),due_ms INTEGER NOT NULL,
        result TEXT NOT NULL,digest TEXT NOT NULL,PRIMARY KEY(guild,due_ms))''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_maintenance_retired_families (
        guild INTEGER NOT NULL,family INTEGER NOT NULL,family_token TEXT NOT NULL,due_ms INTEGER NOT NULL,
        PRIMARY KEY(guild,family,family_token),
        FOREIGN KEY(guild,due_ms) REFERENCES guild_maintenance_terminal_outbox(guild,due_ms))''')


def terminal(db,guild,due):
    row=db.execute('SELECT result,digest FROM guild_maintenance_terminal_outbox WHERE guild=? AND due_ms=?',(guild,due)).fetchone()
    if row is None:raise ValueError('guild_terminal_source_missing')
    raw=json.loads(row[0])
    if hashlib.sha256(_json(raw).encode()).hexdigest()!=row[1]:raise ValueError('guild_terminal_source_invalid')
    raw['families']=tuple(tuple(v) for v in raw['families']);raw['members']=tuple(tuple(v) for v in raw['members'])
    result=GuildTerminal(**raw)
    if (result.guild,result.due_ms,result.state)!=(guild,due,'pending'):raise ValueError('guild_terminal_source_invalid')
    return result


def retired_family(db,guild,family,token):
    row=db.execute('''SELECT due_ms FROM guild_maintenance_retired_families
        WHERE guild=? AND family=? AND family_token=?''',(guild,family,token)).fetchone()
    if row is None:return False
    event=terminal(db,guild,row[0])
    if (family,token) not in event.families:raise ValueError('guild_terminal_source_invalid')
    from guild_dissolution import lifecycle
    if lifecycle(db,guild).state!='dissolution_pending':raise ValueError('guild_terminal_source_invalid')
    return True


def retire_clock(db,guild):
    db.execute("UPDATE guild_maintenance_clocks SET state='retired' WHERE guild=?",(guild,))


def close(db,command,now,policy,history_partitions,revision):
    guild=command.guild
    families=tuple(tuple(row) for row in db.execute('''SELECT g.family,t.generation FROM guild_families g
        LEFT JOIN guild_family_generations t ON t.family=g.family WHERE g.guild=? ORDER BY g.family LIMIT ?''',
        (guild,policy.member_limit+1)))
    if len(families)>policy.member_limit or any(not token for _,token in families):
        raise ValueError('guild_terminal_membership_unknown')
    members=set(tuple(row) for row in db.execute('''SELECT role_id,family_token,member_token FROM guild_member_state
        WHERE guild=? AND active=1 ORDER BY role_id LIMIT ?''',(guild,policy.member_limit+1)))
    members.update(tuple(row) for row in db.execute('''SELECT m.role_id,t.generation,
        COALESCE(s.generation,'legacy:'||m.joined_ms) FROM family_members m
        JOIN guild_families g ON g.family=m.family JOIN guild_family_generations t ON t.family=m.family
        LEFT JOIN family_member_state s ON s.role_id=m.role_id
        WHERE g.guild=? ORDER BY m.role_id LIMIT ?''',(guild,policy.member_limit+1)))
    if len(members)>policy.member_limit:raise ValueError('guild_terminal_membership_unknown')
    result=GuildTerminal(guild,command.due_ms,revision,families,tuple(sorted(members)),'pending',policy.digest)
    encoded=_json(asdict(result))
    db.execute('INSERT INTO guild_maintenance_terminal_outbox VALUES(?,?,?,?)',
        (guild,command.due_ms,encoded,hashlib.sha256(encoded.encode()).hexdigest()))
    from family_guild_history import emit
    for family,token in families:
        emit(db,guild,family,6,command.request_id,now,history_partitions)
        db.execute('INSERT INTO guild_maintenance_retired_families VALUES(?,?,?,?)',(guild,family,token,command.due_ms))
    db.execute('DELETE FROM guild_families WHERE guild=?',(guild,))
    db.execute('UPDATE guild_member_state SET active=0 WHERE guild=?',(guild,))
    for table in ('guild_offices','guild_patrols','guild_deputy_authority','guild_office_bindings'):
        db.execute('DELETE FROM '+table+' WHERE guild=?',(guild,))
    db.execute('UPDATE organizations SET level=0 WHERE id=?',(guild,))
    db.execute('''UPDATE guild_lifecycle SET state='dissolution_pending',revision=? WHERE guild=?''',(revision,guild))
    retire_clock(db,guild)
    return result
