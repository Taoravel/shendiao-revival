"""Guild-owned material reservations for role-owned cash practice.

SQLite is the local compatibility Adapter: guild resolution reads the durable
role receipt in its transaction. A remote Adapter needs an outbox/inbox saga.
No role asset, skill, wallet, lease or connection is written here.
"""
from dataclasses import dataclass,asdict
import hashlib,json
from guild_offices import member
import role_practice as p


@dataclass(frozen=True)
class PracticeMaterials:
    guild: int
    available: int
    revision: int
    origin: str


@dataclass(frozen=True)
class PracticePermit:
    guild: int
    role: int
    reservation: str
    fingerprint: str
    status: str
    epoch: str
    family_token: str
    member_token: str
    before: p.PracticeState
    cash: int
    materials: int
    deadline_ms: int
    policy: str
    mode: int = 0
    gain: int = 10
    item_template: int = 0
    pill_recipe: str = ''


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS guild_practice_materials (
        guild INTEGER PRIMARY KEY REFERENCES organizations(id),available INTEGER NOT NULL CHECK(available>=0),
        revision INTEGER NOT NULL,origin TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS guild_practice_permits (
        guild INTEGER NOT NULL REFERENCES organizations(id),role_id INTEGER NOT NULL REFERENCES roles(id),
        reservation TEXT NOT NULL,fingerprint TEXT NOT NULL,body TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('reserved','committed','cancelled')),
        PRIMARY KEY(guild,role_id,reservation))''')
    db.execute('CREATE INDEX IF NOT EXISTS guild_practice_pending_role ON guild_practice_permits(role_id,status,guild,reservation)')


def new_guild(db,guild,rules):
    db.execute('INSERT INTO guild_practice_materials VALUES(?,?,0,?)',(guild,rules.initial_materials,rules.materials_origin))


def materials(db,guild):
    row=db.execute('SELECT guild,available,revision,origin FROM guild_practice_materials WHERE guild=?',(guild,)).fetchone()
    if not row:raise ValueError('practice_materials_unknown')
    result=PracticeMaterials(*tuple(row))
    if not 0<=result.available<2**63 or not 0<=result.revision<2**63:raise ValueError('invalid_practice_materials')
    return result


def permit(db,guild,role,reservation):
    row=db.execute('SELECT fingerprint,body,status FROM guild_practice_permits WHERE guild=? AND role_id=? AND reservation=?',
        (guild,role,reservation)).fetchone()
    if not row:raise ValueError('practice_reservation_missing')
    data=json.loads(row[1]);data['before']=p.PracticeState(**data['before'])
    return PracticePermit(guild,role,reservation,row[0],row[2],**data)


def pending(db,role,limit):
    if type(limit) is not int or not 1<=limit<=10000:raise ValueError('invalid_practice_recovery_limit')
    rows=tuple(db.execute('''SELECT guild,reservation FROM guild_practice_permits
        WHERE role_id=? AND status='reserved' ORDER BY guild,reservation LIMIT ?''',(role,limit)))
    from faction_types import GuildRecoveryProblem
    result=[]
    for guild,reservation in rows:
        try:result.append(permit(db,guild,role,reservation))
        except (ValueError,TypeError,KeyError) as error:
            result.append(GuildRecoveryProblem(guild,role,reservation,str(error) or type(error).__name__))
    return tuple(result)


def eligibility(db,guild,role,now,rules):
    m=member(db,guild,role)
    if now-m['joined_ms']<rules.tenure_ms:raise ValueError('practice_tenure')
    state=db.execute('''SELECT prestige FROM guild_member_state WHERE guild=? AND role_id=?
        AND family_token=? AND member_token=? AND active=1''',(guild,role,m['family_token'],m['member_token'])).fetchone()
    if not state:raise ValueError('practice_member_state_unknown')
    role_row=db.execute('SELECT account_id,level FROM roles WHERE id=?',(role,)).fetchone()
    return m,role_row[0],role_row[1],state[0]


def require_open(db,guild,skill):
    if not db.execute('SELECT 1 FROM guild_practice_open WHERE guild=? AND skill_id=?',(guild,skill)).fetchone():
        raise ValueError('practice_not_open')


def reserve(db,org,command,now,rules,*,mode=0):
    if (len(command.args)!=2 or any(type(n) is not int for n in command.args)
        or type(mode) is not int or mode not in (0,1)
        or command.args[0] not in rules.skills or not 0<=command.args[1]<2**63-1
        or len(command.request_id)>96):raise ValueError('invalid_practice_reservation')
    skill,revision=command.args
    m,account,level,prestige=eligibility(db,org['id'],command.actor,now,rules)
    require_open(db,org['id'],skill)
    before=next(s for s in p.read(db,account,command.actor,command.epoch,rules) if s.skill==skill)
    if before.revision!=revision:raise ValueError('practice_revision_conflict')
    p.plan(before,level,prestige,rules,mode=mode)
    if mode==0:
        resources=materials(db,org['id'])
        if resources.revision==2**63-1:raise ValueError('practice_material_revision_overflow')
        if resources.available<rules.materials:raise ValueError('insufficient_practice_materials')
    if db.execute("SELECT COUNT(*) FROM guild_practice_permits WHERE role_id=? AND status='reserved'",(command.actor,)).fetchone()[0]>=rules.receipt_limit:
        raise ValueError('practice_pending_full')
    data=dict(epoch=str(command.epoch),family_token=m['family_token'],member_token=m['member_token'],before=asdict(before),
        cash=rules.cash_costs[skill] if mode==0 else 0,materials=rules.materials if mode==0 else 0,
        deadline_ms=command.deadline_ms,policy=rules.revision,mode=mode,
        gain=rules.gain if mode==0 else rules.pill_gains[skill],item_template=0 if mode==0 else rules.pill_item,
        pill_recipe='' if mode==0 else rules.pill_recipe)
    body=json.dumps(data,sort_keys=True,separators=(',',':'))
    fingerprint=hashlib.sha256(json.dumps([org['id'],command.actor,command.request_id,body],separators=(',',':')).encode()).hexdigest()
    db.execute('INSERT INTO guild_practice_permits VALUES(?,?,?,?,?,?)',
        (org['id'],command.actor,command.request_id,fingerprint,body,'reserved'))
    if mode==0:
        db.execute('UPDATE guild_practice_materials SET available=available-?,revision=revision+1 WHERE guild=?',
            (rules.materials,org['id']))


def resolve(db,org,command,now,rules):
    if len(command.args)!=1 or type(command.args[0]) is not str:raise ValueError('invalid_practice_resolution')
    current=permit(db,org['id'],command.actor,command.args[0])
    if current.policy!=rules.revision:raise ValueError('practice_policy_migration_required')
    if current.status!='reserved':return
    receipt=db.execute('SELECT fingerprint FROM role_practice_receipts WHERE role_id=? AND guild=? AND reservation=?',
        (command.actor,org['id'],current.reservation)).fetchone()
    if receipt:
        if receipt[0]!=current.fingerprint:raise ValueError('practice_receipt_conflict')
        status='committed'
    else:
        child='practice:'+str(org['id'])+':'+current.reservation
        if current.mode==0:
            paid=db.execute('SELECT 1 FROM role_wallet_receipts WHERE role_id=? AND settlement_id=?',(command.actor,child)).fetchone()
        elif current.mode==1:
            paid=db.execute('SELECT 1 FROM inventory_settlements WHERE role_id=? AND settlement_id=?',(command.actor,child)).fetchone()
        else:raise ValueError('unsupported_practice_mode')
        # A child payment without the common role receipt contradicts the
        # atomic transaction contract. Keep the hold for explicit repair.
        if paid:raise ValueError('practice_outcome_unknown')
        if current.materials:
            resources=materials(db,org['id'])
            if resources.revision==2**63-1:raise ValueError('practice_material_revision_overflow')
            if resources.available>2**63-1-current.materials:raise ValueError('practice_material_refund_overflow')
            db.execute('UPDATE guild_practice_materials SET available=available+?,revision=revision+1 WHERE guild=?',
                (current.materials,org['id']))
        status='cancelled'
    db.execute('UPDATE guild_practice_permits SET status=? WHERE guild=? AND role_id=? AND reservation=?',
        (status,org['id'],command.actor,current.reservation))
