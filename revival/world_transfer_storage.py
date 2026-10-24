"""Local durable handoff decisions, fenced in the role's SQLite transaction.

Prepared work leaves the source authoritative. A commit atomically records the
target position/version and decision. Recovery does not infer commit on timeout.
Explicitly adopted roles also keep the full MapAddress in that same transaction;
legacy instance identity stays unknown until a trusted caller adopts it.
"""
from contextlib import closing
from dataclasses import asdict,replace,dataclass
import json
from world_owner import (TransferCommit,FrozenTransfer,Reservation,TransferOffer,Location,MapAddress,
                         TransferRecoveryDecision)


@dataclass(frozen=True)
class MapInstanceCheckpoint:
    role_id: int
    login_epoch: int | str
    address: MapAddress
    position: tuple
    version: int
    entry_version: int
    transfer_id: str


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS world_handoffs (
        transfer_id TEXT PRIMARY KEY, role_id INTEGER NOT NULL REFERENCES roles(id),
        epoch TEXT NOT NULL, stage TEXT NOT NULL, source TEXT NOT NULL,
        target TEXT NOT NULL, receipt TEXT NOT NULL DEFAULT '', offer TEXT NOT NULL DEFAULT '')''')
    if 'offer' not in {r[1] for r in db.execute('PRAGMA table_info(world_handoffs)')}:
        db.execute("ALTER TABLE world_handoffs ADD COLUMN offer TEXT NOT NULL DEFAULT ''")
    # A completed legacy receipt contains the exact original offer. Prepared
    # legacy rows have no recoverable deadline: never fabricate that evidence.
    for transfer_id,role_id,epoch,source,target,encoded in db.execute("SELECT transfer_id,role_id,epoch,source,target,receipt FROM world_handoffs "
            "WHERE offer='' AND stage IN ('committed','ready')").fetchall():
        try:
            offer=json.loads(encoded)['frozen']['reservation']['offer']
            if (not isinstance(offer,dict) or set(offer)!={'transfer_id','source','target_position','deadline_ms'}
                    or offer['transfer_id']!=transfer_id or offer['source']['role_id']!=role_id
                    or str(offer['source']['login_epoch'])!=str(epoch)
                    or json.dumps(offer['source'],sort_keys=True)!=source
                    or json.dumps(offer['target_position'])!=target):
                raise ValueError('Malformed offer')
        except (ValueError,KeyError,TypeError) as error:
            raise ValueError('Legacy committed handoff lacks an exact offer') from error
        db.execute('UPDATE world_handoffs SET offer=? WHERE transfer_id=?',
                   (json.dumps(offer,sort_keys=True),transfer_id))
    db.execute('CREATE INDEX IF NOT EXISTS world_handoff_role ON world_handoffs(role_id,epoch,stage)')
    # Optional explicit adoption: legacy rows remain unknown, never guessed
    # from map_id. Coordinates/version keep their existing single authority.
    db.execute('''CREATE TABLE IF NOT EXISTS world_instance_positions (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id), map_id INTEGER NOT NULL,
        instance_id INTEGER NOT NULL, partition_id INTEGER NOT NULL,
        entry_version INTEGER NOT NULL, transfer_id TEXT NOT NULL)''')


def _owner(db,account_id,role_id,epoch):
    if (not db.in_transaction or type(account_id) is not int or account_id<1
            or type(role_id) is not int or not 0<role_id<2**63
            or not ((type(epoch) is int and epoch>0) or (type(epoch) is str and 1<=len(epoch)<=128))
            or not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
                'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1 '
                'AND NOT EXISTS(SELECT 1 FROM role_deletions d WHERE d.role_id=r.id)',
                (role_id,account_id,str(epoch))).fetchone()):
        raise ValueError('Transfer role ownership or current lease mismatch')


def _instance_address(address):
    if (type(address) is not MapAddress
            or any(type(v) is not int or not 0<v<2**63 for v in (address.map_id,address.instance_id))
            or type(address.partition_id) is not int or not 0<=address.partition_id<2**63):
        raise ValueError('Explicit durable map instance address required')


def _instance_checkpoint(db,role_id,epoch):
    row=db.execute('SELECT map_id,instance_id,partition_id,entry_version,transfer_id '
        'FROM world_instance_positions WHERE role_id=?',(role_id,)).fetchone()
    if row is None:
        return None
    address=MapAddress(*row[:3]);_instance_address(address)
    current=db.execute('SELECT p.map_id,p.x,p.y,v.version FROM role_positions p '
        'JOIN position_versions v ON v.role_id=p.role_id WHERE p.role_id=?',(role_id,)).fetchone()
    if (not current or any(type(v) is not int for v in current)
            or current[0]!=address.map_id or not 0<current[3]<2**63
            or any(not 0<=v<32768 for v in current[1:3])
            or type(row[3]) is not int or not 0<row[3]<=current[3]
            or type(row[4]) is not str or len(row[4])>128):
        raise ValueError('Durable instance and current position/version disagree')
    return MapInstanceCheckpoint(role_id,epoch,address,tuple(current[:3]),current[3],row[3],row[4])


def load_map_instance_transaction(db,account_id,role_id,epoch):
    """Read a current-lease checkpoint with its explicitly adopted instance.

    None means legacy/unknown instance, not a default world map. Caller owns
    the transaction and map join/load fences; this never activates membership.
    Later ordinary checkpoints supply current XY/version without duplicating
    either value in the instance table.
    """
    _owner(db,account_id,role_id,epoch)
    return _instance_checkpoint(db,role_id,epoch)


def bind_map_instance_transaction(db,account_id,role_id,epoch,expected):
    """Explicit trusted adoption at an exact durable active checkpoint.

    No automatic migration or instance derivation. Existing bindings can only
    be confirmed here; changing instance belongs to a durable handoff. Caller
    commits before publishing adoption and rolls back on any later failure.
    """
    _owner(db,account_id,role_id,epoch)
    if (type(expected) is not Location or expected.role_id!=role_id
            or type(expected.role_id) is not int or str(expected.login_epoch)!=str(epoch)
            or not ((type(expected.login_epoch) is int and expected.login_epoch>0)
                or (type(expected.login_epoch) is str and 1<=len(expected.login_epoch)<=128))
            or expected.state!='active' or type(expected.version) is not int
            or not 0<expected.version<2**63
            or any(type(v) is not int or not 0<=v<32768 for v in (expected.x,expected.y))):
        raise ValueError('Exact trusted active location required for instance adoption')
    _instance_address(expected.address)
    current=db.execute('SELECT p.map_id,p.x,p.y,v.version FROM role_positions p '
        'JOIN position_versions v ON v.role_id=p.role_id WHERE p.role_id=?',(role_id,)).fetchone()
    if not current or tuple(current)!=(*expected.position,expected.version):
        raise ValueError('Instance adoption requires the exact durable checkpoint')
    existing=_instance_checkpoint(db,role_id,epoch)
    if existing is not None:
        if existing.address!=expected.address:
            raise ValueError('Instance change requires a committed handoff')
        return existing
    db.execute('INSERT INTO world_instance_positions VALUES(?,?,?,?,?,?)',
        (role_id,expected.address.map_id,expected.address.instance_id,
         expected.address.partition_id,expected.version,''))
    return _instance_checkpoint(db,role_id,epoch)


def begin(accounts,account_id,role_id,epoch,offer):
    if (type(offer) is not TransferOffer or type(offer.source) is not Location
            or type(offer.source.role_id) is not int or offer.source.role_id!=role_id
            or str(offer.source.login_epoch)!=str(epoch) or offer.source.state!='active'
            or type(offer.transfer_id) is not str or not 1<=len(offer.transfer_id)<=128
            or type(offer.deadline_ms) is not int or offer.deadline_ms<0
            or type(offer.target_position) is not tuple or len(offer.target_position)!=3
            or any(type(v) is not int for v in offer.target_position)):
        raise ValueError('Trusted current source offer required')
    source=json.dumps(asdict(offer.source),sort_keys=True)
    target=json.dumps(offer.target_position)
    encoded_offer=json.dumps(asdict(offer),sort_keys=True)
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        _owner(db,account_id,role_id,epoch)
        row=db.execute('SELECT role_id,epoch,source,target,stage,offer FROM world_handoffs WHERE transfer_id=?',
                       (offer.transfer_id,)).fetchone()
        if row:
            if tuple(map(str,row[:4]))!=(str(role_id),str(epoch),source,target) or row[5]!=encoded_offer:
                raise ValueError('Transfer id reused')
            if row[4]!='prepared':
                return row[4]
        instance=_instance_checkpoint(db,role_id,epoch)
        if instance is not None and instance.address!=offer.source.address:
            raise ValueError('Prepared transfer source instance disagrees with durable membership')
        if row:
            return row[4]
        db.execute('INSERT INTO world_handoffs(transfer_id,role_id,epoch,stage,source,target,offer) VALUES(?,?,?,?,?,?,?)',
                   (offer.transfer_id,role_id,epoch,'prepared',source,target,encoded_offer))
        return 'prepared'


def _receipt_scope(role_id,epoch,receipt):
    if (type(receipt) is not TransferCommit or type(receipt.frozen) is not FrozenTransfer
            or type(receipt.frozen.reservation) is not Reservation
            or type(receipt.frozen.reservation.offer) is not TransferOffer):
        raise ValueError('Exact target loading receipt required')
    offer=receipt.frozen.reservation.offer
    reservation=receipt.frozen.reservation
    source=offer.source
    location=receipt.location
    if (any(type(p) is not Location for p in (source,receipt.frozen.source,location))
            or any(type(p) is not MapAddress for p in (source.address,reservation.target,location.address))
            or any(type(a.map_id) is not int or a.map_id<1
                   or type(a.instance_id) is not int or a.instance_id<1
                   or type(a.partition_id) is not int or a.partition_id<0
                   for a in (source.address,reservation.target,location.address))
            or any(type(p.role_id) is not int or p.role_id<1 or type(p.version) is not int
                   or p.version<1 or type(p.x) is not int or type(p.y) is not int
                   for p in (source,receipt.frozen.source,location))
            or type(offer.transfer_id) is not str or not 1<=len(offer.transfer_id)<=128
            or type(offer.deadline_ms) is not int or offer.deadline_ms<0
            or type(source.version) is not int or not 0<source.version<2**63-2
            or source.role_id!=role_id or str(source.login_epoch)!=str(epoch) or source.state!='active'
            or type(offer.target_position) is not tuple or len(offer.target_position)!=3
            or any(type(v) is not int for v in (*source.position,*offer.target_position))
            or any(not 0<=v<32768 for v in (*source.position[1:],*offer.target_position[1:]))
            or reservation.target==source.address or reservation.target.map_id!=offer.target_position[0]
            or receipt.frozen.source!=replace(source,version=source.version+1,state='frozen')):
        raise ValueError('Transfer receipt topology or role scope mismatch')
    expected=replace(receipt.frozen.source,address=reservation.target,
        version=source.version+2,x=offer.target_position[1],y=offer.target_position[2],state='loading')
    if location!=expected:
        raise ValueError('Transfer target receipt mismatch')
    return offer,location


def commit_transfer_transaction(db,account_id,role_id,epoch,receipt,*,allow_source_checkpoint_lag=False):
    """Join the caller's current role transaction; never connect or commit.

    True means this transaction wrote the target decision; False is an exact
    previously committed receipt replay and performs no position write. Caller
    still owns commit/rollback and must not publish either result prematurely.
    Default requires the exact durable source checkpoint. The legacy portal
    wrapper explicitly allows an older same-map checkpoint; equal-version
    coordinates, lease, receipt topology and newer checkpoints remain fenced.
    Map bounds/maze and current in-memory ownership are validated by map owners
    before creating this trusted receipt, not by reloading resources here.
    An explicitly adopted instance fences the source and updates the full target
    address atomically. Replays validate the entry provenance without rewinding
    a newer instance. Unadopted legacy roles are not implicitly migrated.
    """
    if (not db.in_transaction or type(account_id) is not int or account_id<1
            or type(role_id) is not int or not 0<role_id<2**63
            or not ((type(epoch) is int and epoch>0) or (type(epoch) is str and 1<=len(epoch)<=128))
            or type(allow_source_checkpoint_lag) is not bool):
        raise ValueError('Current role caller transaction required')
    offer,location=_receipt_scope(role_id,epoch,receipt)
    _owner(db,account_id,role_id,epoch)
    row=db.execute('SELECT role_id,epoch,stage,source,target,receipt,offer FROM world_handoffs WHERE transfer_id=?',
                   (offer.transfer_id,)).fetchone()
    if (not row or row[0]!=role_id or str(row[1])!=str(epoch)
            or row[3]!=json.dumps(asdict(offer.source),sort_keys=True)
            or row[4]!=json.dumps(offer.target_position)
            or row[6]!=json.dumps(asdict(offer),sort_keys=True)):
        raise ValueError('Transfer journal scope mismatch')
    encoded=json.dumps(asdict(receipt),sort_keys=True)
    instance=_instance_checkpoint(db,role_id,epoch)
    if instance is not None:
        _instance_address(location.address)
        old=(*instance.position,instance.version)
    else:
        old=db.execute('SELECT p.map_id,p.x,p.y,v.version FROM role_positions p '
            'JOIN position_versions v ON v.role_id=p.role_id WHERE p.role_id=?',(role_id,)).fetchone()
    if row[2] in ('committed','ready'):
        if row[5]!=encoded:
            raise ValueError('Transfer receipt conflict')
        if (not old or old[3]<location.version
                or (old[3]==location.version and tuple(old[:3])!=location.position)):
            raise ValueError('Committed transfer and current durable position disagree')
        if instance is not None and (instance.entry_version<location.version
                or (instance.entry_version==location.version and (
                    instance.address!=location.address
                    or instance.transfer_id not in ('',offer.transfer_id)))):
            raise ValueError('Committed transfer and durable instance disagree')
        return False
    if row[2]!='prepared' or row[5]:
        raise ValueError('Transfer not prepared')
    source=offer.source
    if instance is not None and instance.address!=source.address:
        raise ValueError('Transfer source instance disagrees with durable membership')
    if old is None:
        present=db.execute('SELECT EXISTS(SELECT 1 FROM role_positions WHERE role_id=?),'
            'EXISTS(SELECT 1 FROM position_versions WHERE role_id=?)',(role_id,role_id)).fetchone()
        # Preserve only the explicit legacy portal adapter's uninitialized
        # position case. One missing half is corruption, never legacy absence.
        if not allow_source_checkpoint_lag or any(present):
            raise ValueError('Missing durable source checkpoint')
    elif (old[0]!=source.address.map_id or old[3]<1 or old[3]>source.version
            or (old[3]==source.version and tuple(old[:3])!=source.position)
            or (not allow_source_checkpoint_lag and (old[3]!=source.version or tuple(old[:3])!=source.position))):
        raise ValueError('Stale or mismatched durable source checkpoint')
    db.execute('INSERT INTO role_positions VALUES(?,?,?,?) ON CONFLICT(role_id) '
        'DO UPDATE SET map_id=excluded.map_id,x=excluded.x,y=excluded.y',(role_id,*location.position))
    db.execute('INSERT INTO position_versions VALUES(?,?) ON CONFLICT(role_id) '
        'DO UPDATE SET version=excluded.version',(role_id,location.version))
    db.execute("UPDATE world_handoffs SET stage='committed',receipt=? WHERE transfer_id=? AND stage='prepared'",
               (encoded,offer.transfer_id))
    if instance is not None:
        db.execute('UPDATE world_instance_positions SET map_id=?,instance_id=?,partition_id=?, '
            'entry_version=?,transfer_id=? WHERE role_id=?',
            (location.address.map_id,location.address.instance_id,location.address.partition_id,
             location.version,offer.transfer_id,role_id))
    return True


def commit(accounts,account_id,role_id,epoch,receipt):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        commit_transfer_transaction(db,account_id,role_id,epoch,receipt,allow_source_checkpoint_lag=True)


def cancel(accounts,account_id,role_id,epoch,transfer_id):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT stage FROM world_handoffs WHERE transfer_id=? AND role_id=? AND epoch=?',
                       (transfer_id,role_id,epoch)).fetchone()
        if not row or row[0] not in ('prepared','cancelled'): raise ValueError('Cannot cancel committed transfer')
        db.execute("UPDATE world_handoffs SET stage='cancelled' WHERE transfer_id=?",(transfer_id,))


def recover(db,role_id,epoch):
    # New login has already fenced old writers. Prepared transactions never
    # changed role_positions. Committed positions survive even if no ready ack.
    db.execute("UPDATE world_handoffs SET stage='cancelled' WHERE role_id=? AND epoch!=? AND stage='prepared'",
               (role_id,str(epoch)))


def _decode_location(value):
    data=dict(value)
    data['address']=MapAddress(**data['address'])
    return Location(**data)


def _decode_offer(value):
    data=dict(value)
    data['source']=_decode_location(data['source'])
    data['target_position']=tuple(data['target_position'])
    return TransferOffer(**data)


def _decode_receipt(value):
    frozen=value['frozen'];reservation=frozen['reservation']
    return TransferCommit(FrozenTransfer(Reservation(_decode_offer(reservation['offer']),
        MapAddress(**reservation['target'])),_decode_location(frozen['source'])),
        _decode_location(value['location']))


def _check_receipt_epoch_types(receipt):
    epochs=(receipt.frozen.reservation.offer.source.login_epoch,
            receipt.frozen.source.login_epoch,receipt.location.login_epoch)
    if any(not ((type(epoch) is int and epoch>0)
            or (type(epoch) is str and 1<=len(epoch)<=128)) for epoch in epochs):
        raise ValueError('Historical receipt requires exact integer or string epochs')


def _read_committed_receipt(db,role_id,transfer_id):
    if type(transfer_id) is not str or not 1<=len(transfer_id)<=128:
        raise ValueError('Exact committed transfer identity required')
    row=db.execute('SELECT role_id,epoch,stage,source,target,receipt,offer FROM world_handoffs '
        'WHERE transfer_id=?',(transfer_id,)).fetchone()
    if not row or row[0]!=role_id or row[2] not in ('committed','ready'):
        raise ValueError('Committed transfer receipt not found')
    try:
        receipt=_decode_receipt(json.loads(row[5]))
        offer,location=_receipt_scope(role_id,row[1],receipt)
        _check_receipt_epoch_types(receipt)
    except (ValueError,TypeError,KeyError,AttributeError) as error:
        raise ValueError('Malformed committed transfer receipt') from error
    if (offer.transfer_id!=transfer_id
            or row[3]!=json.dumps(asdict(offer.source),sort_keys=True)
            or row[4]!=json.dumps(offer.target_position)
            or row[5]!=json.dumps(asdict(receipt),sort_keys=True)
            or row[6]!=json.dumps(asdict(offer),sort_keys=True)):
        raise ValueError('Committed transfer journal identity mismatch')
    _instance_address(offer.source.address)
    _instance_address(location.address)
    return receipt


def load_committed_transfer_transaction(db,account_id,role_id,current_epoch,expected_receipt):
    """Pure SELECT confirmation of history plus the CURRENT full checkpoint.

    Caller owns an already-open transaction and the current valid role lease.
    The exact historical receipt retains its original epoch, even after a new
    lease. Both its journal and current entry provenance must be committed or
    ready. Legacy/unknown instance bindings are refused, never inferred.
    Later walking or another committed instance is returned unchanged; this
    neither replays the old transfer nor authorizes task/reward completion.
    It does not connect, begin, commit, recover, cancel or perform any writes.
    """
    _owner(db,account_id,role_id,current_epoch)
    if type(expected_receipt) is not TransferCommit or type(expected_receipt.location) is not Location:
        raise ValueError('Exact historical transfer receipt required')
    offer,location=_receipt_scope(role_id,expected_receipt.location.login_epoch,expected_receipt)
    _check_receipt_epoch_types(expected_receipt)
    historical=_read_committed_receipt(db,role_id,offer.transfer_id)
    if json.dumps(asdict(historical),sort_keys=True)!=json.dumps(asdict(expected_receipt),sort_keys=True):
        raise ValueError('Historical transfer receipt conflict')
    current=_instance_checkpoint(db,role_id,current_epoch)
    if current is None or current.entry_version<location.version:
        raise ValueError('Committed transfer requires known current instance provenance')
    entry=(historical if current.transfer_id==offer.transfer_id else
           _read_committed_receipt(db,role_id,current.transfer_id))
    if (entry.location.address!=current.address or entry.location.version!=current.entry_version
            or (current.version==current.entry_version and current.position!=entry.location.position)):
        raise ValueError('Current checkpoint and committed entry provenance disagree')
    return historical,current


def prepare_transfer_recovery_transaction(db,account_id,role_id,new_epoch,transfer_id=None):
    """Read the FINAL old-lease outcome under a newly acquired current lease.

    Caller commits cancellation before posting this frozen decision to maps.
    Old writers must already be fenced by lease acquisition. No position is
    written here. An omitted ID selects the role's latest older-lease handoff;
    None means none exists. No timeout or client report determines commitment.
    """
    _owner(db,account_id,role_id,new_epoch)
    if transfer_id is not None and (type(transfer_id) is not str or not 1<=len(transfer_id)<=128):
        raise ValueError('Explicit recovery transfer identity required')
    sql='SELECT transfer_id,epoch,stage,source,target,offer,receipt FROM world_handoffs WHERE role_id=?'
    args=(role_id,)
    if transfer_id is None:
        sql+=' AND epoch!=? ORDER BY rowid DESC LIMIT 1';args+=(str(new_epoch),)
    else:
        sql+=' AND transfer_id=?';args+=(transfer_id,)
    row=db.execute(sql,args).fetchone()
    if row is None:
        if transfer_id is None:return None
        raise ValueError('Recovery handoff not found')
    ident,old_epoch,stage,source_json,target_json,offer_json,receipt_json=row
    if str(old_epoch)==str(new_epoch):
        raise ValueError('Recovery requires a fenced previous lease')
    try:
        source=_decode_location(json.loads(source_json))
        target=tuple(json.loads(target_json))
        offer=_decode_offer(json.loads(offer_json)) if offer_json else None
        receipt=_decode_receipt(json.loads(receipt_json)) if receipt_json else None
    except (ValueError,TypeError,KeyError) as error:
        raise ValueError('Malformed durable recovery record') from error
    if (source.role_id!=role_id or str(source.login_epoch)!=str(old_epoch) or source.state!='active'
            or type(source.role_id) is not int or type(source.version) is not int or source.version<1
            or any(type(v) is not int for v in (source.address.map_id,source.address.instance_id,source.address.partition_id,source.x,source.y))
            or min(source.address.map_id,source.address.instance_id)<1 or source.address.partition_id<0
            or len(target)!=3 or any(type(v) is not int for v in target) or target[0]<1
            or any(not 0<=v<32768 for v in (*source.position[1:],*target[1:]))
            or (offer is not None and (offer.transfer_id!=ident or offer.source!=source or offer.target_position!=target
                or type(offer.deadline_ms) is not int or offer.deadline_ms<0))):
        raise ValueError('Recovery journal identity mismatch')
    position=db.execute('SELECT p.map_id,p.x,p.y,v.version FROM role_positions p '
        'JOIN position_versions v ON v.role_id=p.role_id WHERE p.role_id=?',(role_id,)).fetchone()
    if (not position or any(type(v) is not int for v in position)
            or position[0]<1 or position[3]<1 or any(not 0<=v<32768 for v in position[1:3])):
        raise ValueError('Recovery requires a known durable position/version')
    committed=stage in ('committed','ready')
    if committed:
        if receipt is None:
            raise ValueError('Committed recovery lacks target receipt')
        recovered_offer,location=_receipt_scope(role_id,source.login_epoch,receipt)
        if (recovered_offer.transfer_id!=ident or recovered_offer.source!=source
                or recovered_offer.target_position!=target or (offer is not None and recovered_offer!=offer)
                or position[3]<location.version
                or (position[3]==location.version and tuple(position[:3])!=location.position)):
            raise ValueError('Committed recovery and durable position disagree')
        offer=recovered_offer
    elif (stage not in ('prepared','cancelled') or receipt is not None
            or (stage=='prepared' and (position[0]!=source.address.map_id or position[3]>source.version))):
        raise ValueError('Uncommitted recovery and durable source disagree')
    if stage=='prepared':
        db.execute("UPDATE world_handoffs SET stage='cancelled' WHERE transfer_id=? AND role_id=? AND epoch=? AND stage='prepared'",
            (ident,role_id,str(old_epoch)))
    return TransferRecoveryDecision(ident,source,target,new_epoch,tuple(position[:3]),
        position[3],committed,offer,receipt)
