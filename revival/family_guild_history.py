"""Guild-owned relationship outbox and family-owned historical consumption.

The caller owns its entity transaction. No connections, owner waits or sends.
Only real new transitions emit; unknown historical relationships are not filled.
"""
from dataclasses import dataclass,asdict
import hashlib,json
from faction_protocol import FamilyCourse,family_course


@dataclass(frozen=True)
class FamilyGuildHistoryEvent:
    sequence: int
    guild: int
    family: int
    family_token: str
    template_id: int
    guild_name: str
    created_ms: int
    source_id: str


@dataclass(frozen=True)
class FamilyGuildHistoryCommand:
    event: FamilyGuildHistoryEvent
    request_id: str
    deadline_ms: int


@dataclass(frozen=True)
class FamilyGuildHistoryReceipt:
    sequence: int
    guild: int
    family: int
    family_revision: int
    fingerprint: str


@dataclass(frozen=True)
class FamilyGuildHistoryPage:
    entries: tuple
    ceiling: int | None


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS guild_family_history_outbox (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT,guild INTEGER NOT NULL REFERENCES organizations(id),
        family INTEGER NOT NULL REFERENCES organizations(id),family_token TEXT NOT NULL,
        template_id INTEGER NOT NULL CHECK(template_id IN (5,6)),guild_name TEXT NOT NULL,
        created_ms INTEGER NOT NULL,source_id TEXT NOT NULL,partition INTEGER NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('pending','done')),UNIQUE(guild,family,source_id))''')
    db.execute('CREATE INDEX IF NOT EXISTS guild_family_history_directory ON guild_family_history_outbox(partition,state,family,sequence)')
    db.execute('CREATE INDEX IF NOT EXISTS guild_family_history_order ON guild_family_history_outbox(family,state,sequence)')
    db.execute('''CREATE TABLE IF NOT EXISTS family_guild_history_inbox (
        sequence INTEGER PRIMARY KEY REFERENCES guild_family_history_outbox(sequence),
        family INTEGER NOT NULL REFERENCES organizations(id),fingerprint TEXT NOT NULL,
        result TEXT NOT NULL,created_ms INTEGER NOT NULL)''')


def event(db,sequence):
    if type(sequence) is not int or not 0<sequence<2**63:raise ValueError('invalid_guild_family_history_sequence')
    row=db.execute('''SELECT sequence,guild,family,family_token,template_id,guild_name,created_ms,source_id
        FROM guild_family_history_outbox WHERE sequence=?''',(sequence,)).fetchone()
    if row is None:raise ValueError('guild_family_history_source_missing')
    return FamilyGuildHistoryEvent(*tuple(row))


def emit(db,guild,family,template_id,source_id,now,partitions):
    if (not db.in_transaction or any(type(v) is not int or not 0<v<2**63 for v in (guild,family))
            or type(template_id) is not int or template_id not in (5,6)
            or type(source_id) is not str or not 1<=len(source_id)<=256 or '\0' in source_id
            or type(now) is not int or not 0<=now<2**63
            or type(partitions) is not int or not 0<partitions<2**31):
        raise ValueError('invalid_guild_family_history_source')
    source=db.execute('''SELECT t.generation,o.name FROM guild_families g
        JOIN guild_family_generations t ON t.family=g.family
        JOIN organizations o ON o.id=g.guild AND o.kind='guild'
        JOIN organizations f ON f.id=g.family AND f.kind='family'
        WHERE g.guild=? AND g.family=?''',(guild,family)).fetchone()
    if source is None:raise ValueError('guild_family_history_membership_unknown')
    family_course(FamilyCourse(template_id,('event_time',source[1])))
    old=db.execute('SELECT sequence FROM guild_family_history_outbox WHERE guild=? AND family=? AND source_id=?',
        (guild,family,source_id)).fetchone()
    expected=(guild,family,source[0],template_id,source[1],now,source_id)
    if old:
        previous=event(db,old[0])
        if previous!=FamilyGuildHistoryEvent(old[0],*expected):
            raise ValueError('guild_family_history_source_conflict')
        return previous
    sequence=db.execute('''INSERT INTO guild_family_history_outbox
        (guild,family,family_token,template_id,guild_name,created_ms,source_id,partition,state)
        VALUES(?,?,?,?,?,?,?,?,'pending')''',(*expected,family%partitions)).lastrowid
    return event(db,sequence)


def pending(db,partition,after,policy,through=None):
    if (type(partition) is not int or not 0<=partition<policy.partitions
            or (after is not None and (type(after) is not int or not 0<after<2**63))
            or (through is not None and (type(through) is not int or not 0<through<2**63))):
        raise ValueError('invalid_family_guild_history_directory')
    result=[];cursor=after or 0
    for _ in range(policy.batch_limit):
        row=db.execute('''SELECT family,sequence FROM guild_family_history_outbox
            WHERE partition=? AND state='pending' AND family>? AND family<=?
            ORDER BY family,sequence LIMIT 1''',(partition,cursor,through or 2**63-1)).fetchone()
        if row is None:break
        result.append(tuple(row));cursor=row[0]
    return tuple(result)


def page(db,partition,after,ceiling,policy):
    if (type(partition) is not int or not 0<=partition<policy.partitions
            or (after is not None and (type(after) is not int or not 0<after<2**63))
            or (ceiling is not None and (type(ceiling) is not int or not 0<ceiling<2**63))
            or (after is not None and (ceiling is None or after>ceiling))):
        raise ValueError('invalid_family_guild_history_scan')
    if ceiling is None:
        row=db.execute('''SELECT family FROM guild_family_history_outbox
            WHERE partition=? AND state='pending' ORDER BY family DESC,sequence DESC LIMIT 1''',(partition,)).fetchone()
        if row is None:return FamilyGuildHistoryPage((),None)
        ceiling=row[0]
    return FamilyGuildHistoryPage(pending(db,partition,after,policy,ceiling),ceiling)


def validate(command,now):
    if (not isinstance(command,FamilyGuildHistoryCommand) or not isinstance(command.event,FamilyGuildHistoryEvent)
            or type(command.request_id) is not str or not 1<=len(command.request_id)<=160
            or type(command.deadline_ms) is not int or not 0<=command.deadline_ms<2**63
            or type(now) is not int or not 0<=now<2**63):
        raise ValueError('invalid_family_guild_history_command')
    e=command.event
    if (any(type(v) is not int or not 0<v<2**63 for v in (e.sequence,e.guild,e.family))
            or type(e.template_id) is not int or e.template_id not in (5,6)
            or type(e.family_token) is not str or not 1<=len(e.family_token)<=96
            or type(e.source_id) is not str or not 1<=len(e.source_id)<=256
            or type(e.created_ms) is not int or not 0<=e.created_ms<2**63):
        raise ValueError('invalid_family_guild_history_event')
    family_course(FamilyCourse(e.template_id,('event_time',e.guild_name)))
    if now>command.deadline_ms:raise ValueError('family_guild_history_deadline')


def _proof(db,command,now):
    validate(command,now)
    if not db.in_transaction:raise ValueError('family_guild_history_transaction_required')
    e=command.event
    if event(db,e.sequence)!=e:raise ValueError('family_guild_history_source_conflict')
    return hashlib.sha256(json.dumps(asdict(e),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _receipt(db,e,digest):
    row=db.execute('SELECT family,fingerprint,result FROM family_guild_history_inbox WHERE sequence=?',(e.sequence,)).fetchone()
    if row is None:return None
    if (row[0],row[1])!=(e.family,digest):raise ValueError('family_guild_history_inbox_conflict')
    result=FamilyGuildHistoryReceipt(**json.loads(row[2]))
    if ((result.sequence,result.guild,result.family,result.fingerprint)!=(e.sequence,e.guild,e.family,digest)
            or type(result.family_revision) is not int or result.family_revision<1):
        raise ValueError('family_guild_history_inbox_conflict')
    return result


def _archive(db,e):
    row=db.execute('SELECT template_id,parameters,created_ms FROM family_history WHERE family=? AND source_id=?',
        (e.family,f'guild-family:{e.guild}:{e.sequence}')).fetchone()
    if row is None or (row[0],tuple(json.loads(row[1])),row[2])!=(e.template_id,(e.guild_name,),e.created_ms):
        raise ValueError('family_guild_history_archive_unknown')


def consume(db,command,now):
    digest=_proof(db,command,now);e=command.event
    old=_receipt(db,e,digest)
    if old:
        _archive(db,e)
        return old
    status=db.execute('SELECT state FROM guild_family_history_outbox WHERE sequence=?',(e.sequence,)).fetchone()[0]
    if status=='done':raise ValueError('family_guild_history_outcome_unknown')
    first=db.execute('SELECT sequence FROM guild_family_history_outbox WHERE family=? AND state=? ORDER BY sequence LIMIT 1',
        (e.family,'pending')).fetchone()
    if first is None or first[0]!=e.sequence:raise ValueError('family_guild_history_order_pending')
    from family_history import record
    record(db,e.family,f'guild-family:{e.guild}:{e.sequence}',e.template_id,e.created_ms,e.guild_name)
    db.execute('UPDATE organizations SET revision=revision+1 WHERE id=? AND kind=?',(e.family,'family'))
    revision=db.execute('SELECT revision FROM organizations WHERE id=? AND kind=?',(e.family,'family')).fetchone()
    if revision is None:raise ValueError('family_guild_history_family_missing')
    result=FamilyGuildHistoryReceipt(e.sequence,e.guild,e.family,revision[0],digest)
    db.execute('INSERT INTO family_guild_history_inbox VALUES(?,?,?,?,?)',
        (e.sequence,e.family,digest,json.dumps(asdict(result),separators=(',',':')),now))
    return result


def acknowledge(db,command,now):
    digest=_proof(db,command,now);e=command.event
    result=_receipt(db,e,digest)
    if result is None:raise ValueError('family_guild_history_inbox_missing')
    _archive(db,e)
    db.execute("UPDATE guild_family_history_outbox SET state='done' WHERE sequence=? AND guild=?",(e.sequence,e.guild))
    return result
