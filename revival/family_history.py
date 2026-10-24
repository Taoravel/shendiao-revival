"""Family-owned history, atomically recorded with the operation it describes.

No historical backfill, connection, commit or send. The panel reads the latest
bounded window; older durable rows remain in the archive. Timestamp display is
local design using the existing family timezone/format, not a recovered date.
"""
from datetime import datetime,timezone,timedelta
import json
from faction_protocol import FamilyCourse,MAX_FAMILY_COURSES,family_course


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS family_history (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT,family INTEGER NOT NULL REFERENCES organizations(id),
        source_id TEXT NOT NULL,template_id INTEGER NOT NULL,parameters TEXT NOT NULL,
        created_ms INTEGER NOT NULL,UNIQUE(family,source_id))''')
    db.execute('CREATE INDEX IF NOT EXISTS family_history_panel ON family_history(family,sequence DESC)')


def record(db,family,source_id,template_id,now,detail):
    if (not db.in_transaction or type(family) is not int or not 0<family<2**63
            or type(source_id) is not str or not 1<=len(source_id)<=256
            or type(now) is not int or not 0<=now<2**63
            or type(template_id) is not int or template_id not in (1,2,3,4,5,6)
            or (template_id==1 and detail is not None)):
        raise ValueError('invalid_family_history_event')
    details=() if template_id==1 else (detail,)
    family_course(FamilyCourse(template_id,('event_time',*details)))
    encoded=json.dumps(details,ensure_ascii=False,separators=(',',':'))
    old=db.execute('SELECT template_id,parameters,created_ms FROM family_history WHERE family=? AND source_id=?',
        (family,source_id)).fetchone()
    if old:
        if tuple(old)!=(template_id,encoded,now):raise ValueError('family_history_intent_conflict')
        return
    db.execute('INSERT INTO family_history(family,source_id,template_id,parameters,created_ms) VALUES(?,?,?,?,?)',
        (family,source_id,template_id,encoded,now))


def read(db,family,policy):
    rows=tuple(db.execute('''SELECT template_id,parameters,created_ms FROM family_history WHERE family=?
        ORDER BY sequence DESC LIMIT ?''',(family,MAX_FAMILY_COURSES)))
    zone=timezone(timedelta(minutes=policy['family_utc_offset_minutes']))
    return tuple(FamilyCourse(row[0],(datetime.fromtimestamp(row[2]/1000,zone).strftime(policy['family_offline_time_format']),
        *json.loads(row[1]))) for row in reversed(rows))


def leadership(db,family,source_id,now):
    name=db.execute('SELECT r.name FROM organizations o JOIN roles r ON r.id=o.leader WHERE o.id=? AND o.kind=?',
        (family,'family')).fetchone()
    if not name:raise ValueError('family_history_leader_unknown')
    record(db,family,source_id,4,now,name[0])
