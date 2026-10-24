"""Silver-box donations at role/family transaction Seams; no connection or send.

Family owns permits, outcomes, funds, construction and membership prestige.
Role owns inventory debits and payment proofs. Caller commits its own fenced
transaction and rolls back on every error. SQLite reads the other owner's
durable proof; a remote Adapter requires corresponding outbox/inbox records.
"""
from dataclasses import dataclass,asdict,field
import hashlib,json


@dataclass(frozen=True)
class DonationRules:
    revision: str
    templates: tuple
    batch_limit: int
    pending_limit: int
    funds: int
    construction: int
    prestige: int
    targets: tuple


@dataclass(frozen=True)
class DonationPermit:
    family: int
    role: int
    reservation: str
    fingerprint: str
    status: str
    epoch: str
    member_token: str
    count: int
    deadline_ms: int
    recipe: str
    units: tuple = field(default=(),kw_only=True)


@dataclass(frozen=True)
class DonationPayment:
    family: int
    role: int
    reservation: str
    count: int
    items: tuple
    inventory: object
    messages: tuple


@dataclass(frozen=True)
class DonationOutcome:
    family: int
    role: int
    reservation: str
    status: str
    count: int
    funds_after: int | None
    level_after: int | None
    construction_after: int | None
    prestige_after: tuple | None
    recipe: str
    funds_before: int | None = None
    level_before: int | None = None
    construction_before: int | None = None
    prestige_before: tuple | None = None


@dataclass(frozen=True)
class DonationSweepCommand:
    family: int
    request_id: str
    deadline_ms: int


def validate_sweep(command,now):
    if (not isinstance(command,DonationSweepCommand)
            or any(type(n) is not int or not 0<n<2**63 for n in (command.family,command.deadline_ms))
            or type(command.request_id) is not str or not 1<=len(command.request_id)<=160
            or type(now) is not int or not 0<=now<2**63 or now>command.deadline_ms):
        raise ValueError('invalid_family_donation_sweep')


def rules(policy):
    raw=policy['family_donation']
    result=DonationRules(raw['revision'],tuple(raw['templates']),raw['batch_limit'],raw['pending_limit'],
        raw['funds_per_box'],raw['construction_per_box'],raw['prestige_per_box'],tuple(policy['family_construction_targets']))
    if (type(result.revision) is not str or not result.revision or result.templates!=(36076,36201)
            or any(type(n) is not int or not 0<n<2**31 for n in
                (result.batch_limit,result.pending_limit,result.funds,result.construction,result.prestige))
            or result.batch_limit>100 or result.pending_limit>128 or result.construction!=1 or result.prestige!=5
            or len(result.targets)!=5 or any(type(n) is not int or not 0<n<2**31 for n in result.targets[:-1])
            or type(result.targets[-1]) is not int or result.targets[-1]!=0
            or raw['growth']!='consume_threshold_carry_remainder_cap_zero'
            or raw['prestige_projection']!='increment_both_unbound_slots'):
        raise ValueError('invalid_family_donation_policy')
    return result


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS family_donation_permits (
        family INTEGER NOT NULL REFERENCES organizations(id),role_id INTEGER NOT NULL REFERENCES roles(id),
        reservation TEXT NOT NULL,fingerprint TEXT NOT NULL,body TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('reserved','committed','cancelled')),
        created_ms INTEGER NOT NULL,partition INTEGER NOT NULL,PRIMARY KEY(family,role_id,reservation))''')
    db.execute('CREATE INDEX IF NOT EXISTS family_donation_directory ON family_donation_permits(partition,status,created_ms,family,role_id,reservation)')
    db.execute('CREATE INDEX IF NOT EXISTS family_donation_role_pending ON family_donation_permits(role_id,status)')
    db.execute('''CREATE TABLE IF NOT EXISTS role_family_donation_payments (
        family INTEGER NOT NULL,role_id INTEGER NOT NULL,reservation TEXT NOT NULL,
        fingerprint TEXT NOT NULL,child_id TEXT NOT NULL,items TEXT NOT NULL,
        asset_fingerprint TEXT NOT NULL,created_ms INTEGER NOT NULL,
        PRIMARY KEY(family,role_id,reservation),FOREIGN KEY(family,role_id,reservation)
        REFERENCES family_donation_permits(family,role_id,reservation))''')
    db.execute('''CREATE TABLE IF NOT EXISTS family_donation_receipts (
        family INTEGER NOT NULL,role_id INTEGER NOT NULL,reservation TEXT NOT NULL,
        fingerprint TEXT NOT NULL,result TEXT NOT NULL,created_ms INTEGER NOT NULL,
        PRIMARY KEY(family,role_id,reservation),FOREIGN KEY(family,role_id,reservation)
        REFERENCES family_donation_permits(family,role_id,reservation))''')


def permit(db,family,role,reservation):
    row=db.execute('''SELECT fingerprint,body,status FROM family_donation_permits
        WHERE family=? AND role_id=? AND reservation=?''',(family,role,reservation)).fetchone()
    if not row:raise ValueError('family_donation_permit_missing')
    raw=json.loads(row[1])
    if 'units' in raw:raw['units']=tuple(tuple(unit) for unit in raw['units'])
    return DonationPermit(family,role,reservation,row[0],row[2],**raw)


def member(db,family,role):
    row=db.execute('''SELECT s.generation,s.prestige_first,s.prestige_second FROM family_members m
        JOIN family_member_state s ON s.role_id=m.role_id WHERE m.family=? AND m.role_id=?''',(family,role)).fetchone()
    if not row:raise ValueError('family_donation_membership_unknown')
    return tuple(row)


def active(db,family):
    row=db.execute("SELECT level,revision FROM organizations WHERE id=? AND kind='family'",(family,)).fetchone()
    if not row:raise ValueError('organization_missing')
    clock=db.execute('SELECT state FROM family_maintenance WHERE family=?',(family,)).fetchone()
    if clock and clock[0]!='active':raise ValueError('family_dissolution_pending')
    return tuple(row)


def reserve(db,org,command,now,policy,partitions):
    if (len(command.args) not in (1,2) or type(command.args[0]) is not int or not 1<=command.args[0]<=policy.batch_limit
            or len(command.request_id)>96):raise ValueError('invalid_family_donation_count')
    if len(command.args)==2:
        from family_donation_protocol import validate_units
        if validate_units(command.args[1],policy.batch_limit)!=command.args[0]:raise ValueError('family_donation_selected_count_mismatch')
    level,revision=active(db,org['id']);token,*prestige=member(db,org['id'],command.actor)
    assets=db.execute('SELECT funds,construction FROM family_assets WHERE family=?',(org['id'],)).fetchone()
    if not assets or assets[1] is None:raise ValueError('family_construction_unknown')
    if (type(level) is not int or not 1<=level<=len(policy.targets)
            or type(revision) is not int or not 0<revision<2**63-1
            or any(type(n) is not int or not 0<=n<2**31 for n in (*prestige,assets[1]))
            or not 0<=assets[0]<2**63):raise ValueError('family_donation_state_unknown')
    if (db.execute("SELECT COUNT(*) FROM family_donation_permits WHERE family=? AND status='reserved'",(org['id'],)).fetchone()[0]>=policy.pending_limit
            or db.execute("SELECT COUNT(*) FROM family_donation_permits WHERE role_id=? AND status='reserved'",(command.actor,)).fetchone()[0]>=policy.pending_limit):
        raise ValueError('family_donation_pending_full')
    body=dict(epoch=str(command.epoch),member_token=token,count=command.args[0],deadline_ms=command.deadline_ms,recipe=policy.revision)
    if len(command.args)==2:body['units']=command.args[1]
    encoded=json.dumps(body,sort_keys=True,separators=(',',':'))
    fingerprint=hashlib.sha256(json.dumps([org['id'],command.actor,command.request_id,encoded],separators=(',',':')).encode()).hexdigest()
    db.execute('INSERT INTO family_donation_permits VALUES(?,?,?,?,?,?,?,?)',
        (org['id'],command.actor,command.request_id,fingerprint,encoded,'reserved',now,org['id']%partitions))


def owner(db,account,role,epoch):
    if not db.in_transaction:raise ValueError('family_donation_role_transaction_required')
    if (any(type(n) is not int or not 0<n<2**63 for n in (account,role))
            or type(epoch) not in (str,int) or isinstance(epoch,bool)):
        raise ValueError('invalid_family_donation_role')
    if not db.execute('''SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id
        WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1''',(role,account,str(epoch))).fetchone():
        raise ValueError('family_donation_stale_role_lease')


def child_id(family,role,reservation):
    return 'family-donation:'+hashlib.sha256(json.dumps([family,role,reservation],separators=(',',':')).encode()).hexdigest()


def pay(db,account,role,epoch,family,reservation,now,policy,inventory,*,precommit):
    from inventory import Inventory,AssetChange
    from npc_transactions import precommit_messages
    owner(db,account,role,epoch)
    if (not isinstance(inventory,Inventory) or (inventory.account_id,inventory.role_id)!=(account,role)
            or str(inventory.epoch)!=str(epoch) or not callable(precommit)):
        raise ValueError('family_donation_inventory_projection_required')
    if (type(reservation) is not str or not 1<=len(reservation)<=96 or type(now) is not int or not 0<=now<2**63):
        raise ValueError('invalid_family_donation_payment')
    grant=permit(db,family,role,reservation)
    if grant.recipe!=policy.revision:raise ValueError('family_donation_policy_migration_required')
    paid=db.execute('''SELECT fingerprint,child_id,items,asset_fingerprint FROM role_family_donation_payments
        WHERE family=? AND role_id=? AND reservation=?''',(family,role,reservation)).fetchone()
    child=child_id(family,role,reservation)
    if paid:
        asset=db.execute('SELECT fingerprint FROM inventory_settlements WHERE role_id=? AND settlement_id=?',(role,child)).fetchone()
        if (paid[0]!=grant.fingerprint or paid[1]!=child or not asset or asset[0]!=paid[3] or grant.status=='cancelled'):
            raise ValueError('family_donation_payment_inconsistent')
        selected=tuple(tuple(row) for row in json.loads(paid[2]));replayed=True
    else:
        if grant.status!='reserved' or grant.epoch!=str(epoch) or now>=grant.deadline_ms:
            raise ValueError('family_donation_permit_expired_or_stale')
        active(db,family)
        if member(db,family,role)[0]!=grant.member_token:raise ValueError('family_donation_membership_changed')
        if db.execute('SELECT 1 FROM inventory_settlements WHERE role_id=? AND settlement_id=?',(role,child)).fetchone():
            raise ValueError('family_donation_orphan_asset_receipt')
        selected=[]
        if grant.units:
            from family_donation_protocol import validate_units
            if validate_units(grant.units,policy.batch_limit)!=grant.count:raise ValueError('family_donation_selected_count_mismatch')
            for key,quantity in grant.units:
                item=db.execute('''SELECT template_id,binding,quantity FROM inventory_items
                    WHERE id=? AND role_id=? AND equipment_slot IS NULL''',(key,role)).fetchone()
                if not item or item[0] not in policy.templates or item[2]<quantity:
                    raise ValueError('family_donation_selected_box_unavailable')
                selected.append((key,item[0],item[1],quantity))
        else:
            rows=db.execute('''SELECT id,template_id,binding,quantity FROM inventory_items WHERE role_id=?
                AND template_id IN (?,?) AND equipment_slot IS NULL AND quantity>0 ORDER BY binding DESC,slot,id''',
                (role,*policy.templates)).fetchall()
            remaining=grant.count
            for key,template,binding,quantity in rows:
                amount=min(remaining,quantity);selected.append((key,template,binding,amount));remaining-=amount
                if not remaining:break
            if remaining:raise ValueError('family_donation_boxes_unavailable')
        selected=tuple(selected)
        inventory.apply_settlement(db,AssetChange(child,debits=tuple((row[0],row[3]) for row in selected)))
        asset=db.execute('SELECT fingerprint FROM inventory_settlements WHERE role_id=? AND settlement_id=?',(role,child)).fetchone()[0]
        db.execute('INSERT INTO role_family_donation_payments VALUES(?,?,?,?,?,?,?,?)',
            (family,role,reservation,grant.fingerprint,child,json.dumps(selected),asset,now))
        replayed=False
    messages=precommit_messages(precommit,db,inventory,replayed=replayed)
    return DonationPayment(family,role,reservation,grant.count,selected,
        inventory.immutable_snapshot_transaction(db,epoch=epoch),messages)


def receipt(db,family,role,reservation):
    row=db.execute('SELECT result FROM family_donation_receipts WHERE family=? AND role_id=? AND reservation=?',
        (family,role,reservation)).fetchone()
    if not row:raise ValueError('family_donation_receipt_missing')
    raw=json.loads(row[0])
    for name in ('prestige_after','prestige_before'):
        raw[name]=tuple(raw[name]) if raw.get(name) is not None else None
    return DonationOutcome(**raw)


def resolve(db,family,role,reservation,now,policy,*,cancel_unpaid=False):
    grant=permit(db,family,role,reservation)
    if grant.recipe!=policy.revision:raise ValueError('family_donation_policy_migration_required')
    if grant.status!='reserved':return receipt(db,family,role,reservation)
    paid=db.execute('''SELECT fingerprint,child_id,items,asset_fingerprint FROM role_family_donation_payments
        WHERE family=? AND role_id=? AND reservation=?''',(family,role,reservation)).fetchone()
    child=child_id(family,role,reservation)
    asset=db.execute('SELECT fingerprint FROM inventory_settlements WHERE role_id=? AND settlement_id=?',(role,child)).fetchone()
    if not paid:
        if asset:raise ValueError('family_donation_outcome_unknown')
        if not cancel_unpaid and now<grant.deadline_ms:return None
        result=DonationOutcome(family,role,reservation,'cancelled',grant.count,None,None,None,None,policy.revision)
    else:
        if paid[0]!=grant.fingerprint or paid[1]!=child or not asset or asset[0]!=paid[3]:raise ValueError('family_donation_payment_inconsistent')
        level,revision=active(db,family);level_before=level
        assets=db.execute('SELECT funds,construction FROM family_assets WHERE family=?',(family,)).fetchone()
        if not assets or assets[1] is None:raise ValueError('family_construction_unknown')
        funds=assets[0]+grant.count*policy.funds;construction=assets[1]+grant.count*policy.construction
        if (not 1<=level<=len(policy.targets) or type(revision) is not int or not 0<revision<2**63-1
                or not 0<=funds<2**63 or not 0<=construction<2**31):raise ValueError('family_donation_growth_overflow')
        while level<len(policy.targets) and construction>=policy.targets[level-1]:
            construction-=policy.targets[level-1];level+=1
        if level==len(policy.targets):construction=0
        membership=db.execute('''SELECT m.family,s.generation,s.prestige_first,s.prestige_second
            FROM family_members m LEFT JOIN family_member_state s ON s.role_id=m.role_id
            WHERE m.role_id=?''',(role,)).fetchone()
        if membership and membership[0]==family and membership[1] is None:
            raise ValueError('family_donation_membership_unknown')
        current=tuple(membership[2:]) if membership and tuple(membership[:2])==(family,grant.member_token) else None
        if current is not None and any(type(n) is not int or not 0<=n<2**31 for n in current):
            raise ValueError('family_donation_prestige_unknown')
        prestige=tuple(n+grant.count*policy.prestige for n in current) if current else None
        if prestige is not None:
            if any(not 0<=n<2**31 for n in prestige):raise ValueError('family_donation_prestige_overflow')
            db.execute('UPDATE family_member_state SET prestige_first=?,prestige_second=? WHERE role_id=? AND generation=?',
                (*prestige,role,grant.member_token))
        db.execute('UPDATE family_assets SET funds=?,construction=? WHERE family=?',(funds,construction,family))
        db.execute('UPDATE organizations SET level=?,revision=revision+1 WHERE id=?',(level,family))
        if level!=level_before:
            from family_history import record
            record(db,family,child,2,now,str(level))
        db.execute('INSERT INTO organization_fund_ledger VALUES(?,?,?,?,?,?,?)',
            (family,role,child,'donate_family_box',grant.count*policy.funds,funds,now))
        result=DonationOutcome(family,role,reservation,'committed',grant.count,funds,level,construction,prestige,
            policy.revision,assets[0],level_before,assets[1],tuple(current) if current else None)
    db.execute('UPDATE family_donation_permits SET status=? WHERE family=? AND role_id=? AND reservation=?',
        (result.status,family,role,reservation))
    db.execute('INSERT INTO family_donation_receipts VALUES(?,?,?,?,?,?)',
        (family,role,reservation,grant.fingerprint,json.dumps(asdict(result)),now))
    return result


def settle_pending(db,family,now,policy,*,cancel_unpaid=False):
    rows=tuple(db.execute('''SELECT role_id,reservation FROM family_donation_permits
        WHERE family=? AND status='reserved' ORDER BY created_ms,role_id,reservation LIMIT ?''',
        (family,policy.pending_limit+1)))
    if len(rows)>policy.pending_limit:raise ValueError('family_donation_pending_limit_inconsistent')
    return tuple(result for role,reservation in rows
        if (result:=resolve(db,family,role,reservation,now,policy,cancel_unpaid=cancel_unpaid)) is not None)
