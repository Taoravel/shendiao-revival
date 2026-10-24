"""Caller-owned durable decisions for same-instance relocations.

Startup prepares schema; hot calls use the caller's open role transaction.
The existing full-instance checkpoint remains the position/address authority.
"""
from dataclasses import asdict, dataclass, replace
import json

from world_owner import MapAddress, Location, TransferOffer, RelocationPrepared
from world_transfer_storage import MapInstanceCheckpoint, load_map_instance_transaction


@dataclass(frozen=True)
class RelocationRecord:
    prepared: RelocationPrepared
    stage: str
    checkpoint: MapInstanceCheckpoint
    source_entry_version: int
    source_transfer_id: str


def prepare(db):
    """Startup only, after account/lease/position/full-instance schemas."""
    db.execute('''CREATE TABLE IF NOT EXISTS world_relocations (
        request_id TEXT PRIMARY KEY,
        role_id INTEGER NOT NULL REFERENCES roles(id),
        epoch TEXT NOT NULL,
        stage TEXT NOT NULL CHECK(stage IN ('prepared','committed','cancelled')),
        prepared TEXT NOT NULL,
        entry_version INTEGER NOT NULL,
        entry_transfer_id TEXT NOT NULL)''')
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS world_relocation_pending_role "
               "ON world_relocations(role_id) WHERE stage='prepared'")
    db.execute('CREATE INDEX IF NOT EXISTS world_relocation_role ON world_relocations(role_id)')


def _identifier(value):
    return type(value) is str and 1 <= len(value) <= 128


def _epoch(value):
    return ((type(value) is int and 0 < value < 2**63)
            or _identifier(value))


def _address(value):
    return (type(value) is MapAddress
        and all(type(v) is int and 0 < v < 2**63 for v in (value.map_id, value.instance_id))
        and type(value.partition_id) is int and 0 <= value.partition_id < 2**63)


def _location(value):
    return (type(value) is Location and _address(value.address)
        and all(type(v) is int and 0 < v < 2**63 for v in (value.role_id, value.version))
        and all(type(v) is int and 0 <= v < 32768 for v in (value.x, value.y))
        and _epoch(value.login_epoch))


def _proof(value, role_id, epoch=None):
    if (type(role_id) is not int or not 0 < role_id < 2**63
            or type(value) is not RelocationPrepared or type(value.offer) is not TransferOffer
            or not _identifier(value.owner_generation) or not _identifier(value.preparation_id)
            or not _identifier(value.offer.transfer_id)
            or type(value.movement_state) is not int or not 0 <= value.movement_state <= 255
            or type(value.offer.deadline_ms) is not int or not 0 <= value.offer.deadline_ms < 2**63
            or not all(_location(p) for p in (value.offer.source, value.frozen, value.target))):
        raise ValueError('Exact typed relocation preparation required')
    source = value.offer.source
    target = value.offer.target_position
    if (source.role_id != role_id or source.state != 'active' or source.version >= 2**63-3
            or type(target) is not tuple or len(target) != 3
            or any(type(v) is not int for v in target) or target[0] != source.address.map_id
            or any(not 0 <= v < 32768 for v in target[1:])
            or value.frozen != replace(source, version=source.version+1, state='frozen')
            or value.target != replace(value.frozen, version=source.version+2,
                x=target[1], y=target[2], state='loading')
            or (epoch is not None and (type(source.login_epoch) is not type(epoch)
                                      or source.login_epoch != epoch))):
        raise ValueError('Relocation topology or lease scope mismatch')
    return source


def _encode(proof):
    encoded = json.dumps(asdict(proof), sort_keys=True, separators=(',', ':'))
    if len(encoded) > 32768:
        raise ValueError('Relocation proof exceeds its bounded record budget')
    return encoded


def _decode(encoded):
    if type(encoded) is not str or not 1 <= len(encoded) <= 32768:
        raise ValueError('Malformed bounded relocation record')
    try:
        data = json.loads(encoded)
        def location(row):
            row = dict(row)
            row['address'] = MapAddress(**row['address'])
            return Location(**row)
        offer = dict(data['offer'])
        offer['source'] = location(offer['source'])
        offer['target_position'] = tuple(offer['target_position'])
        data['offer'] = TransferOffer(**offer)
        data['frozen'], data['target'] = location(data['frozen']), location(data['target'])
        proof = RelocationPrepared(**data)
        _proof(proof, proof.offer.source.role_id)
        if _encode(proof) != encoded:
            raise ValueError('Noncanonical relocation record')
        return proof
    except (TypeError, KeyError, AttributeError, ValueError) as error:
        raise ValueError('Malformed relocation record') from error


def _checkpoint(db, account_id, role_id, epoch):
    # Public existing Interface verifies caller transaction, ownership, current
    # lease and coherent position/version/address. Never infer a legacy instance.
    checkpoint = load_map_instance_transaction(db, account_id, role_id, epoch)
    if checkpoint is None:
        raise ValueError('Relocation requires an explicitly adopted full instance')
    return checkpoint


def _read(db, role_id, request_id, checkpoint):
    if not _identifier(request_id):
        raise ValueError('Explicit relocation request identity required')
    row = db.execute('SELECT role_id,epoch,stage,prepared,entry_version,entry_transfer_id '
                     'FROM world_relocations WHERE request_id=?', (request_id,)).fetchone()
    if row is None:
        return None
    proof = _decode(row[3])
    if (type(row[0]) is not int or row[0] != role_id or proof.offer.source.role_id != role_id
            or str(proof.offer.source.login_epoch) != row[1] or proof.offer.transfer_id != request_id
            or row[2] not in ('prepared', 'committed', 'cancelled')
            or type(row[4]) is not int or not 0 < row[4] <= proof.offer.source.version
            or type(row[5]) is not str or len(row[5]) > 128):
        raise ValueError('Relocation journal identity mismatch')
    return RelocationRecord(proof, row[2], checkpoint, row[4], row[5])


def _entry_matches(record):
    cp, source = record.checkpoint, record.prepared.offer.source
    return (cp.address == source.address and cp.entry_version == record.source_entry_version
            and cp.transfer_id == record.source_transfer_id)


def _exact_source(record):
    source, cp = record.prepared.offer.source, record.checkpoint
    if not _entry_matches(record) or (cp.position, cp.version) != (source.position, source.version):
        raise ValueError('Relocation durable source checkpoint changed')


def _validate_current(record):
    cp, proof = record.checkpoint, record.prepared
    if record.stage == 'prepared':
        if cp.version < proof.offer.source.version:
            raise ValueError('Relocation source version is ahead of durable authority')
        if cp.version == proof.offer.source.version:
            _exact_source(record)
        return
    expected = (proof.target if record.stage == 'committed' else
                replace(proof.frozen, version=proof.target.version, state='active'))
    if (cp.version < expected.version or (cp.version == expected.version
            and (cp.position != expected.position or not _entry_matches(record)))):
        raise ValueError('Relocation decision and current checkpoint disagree')


def _clock(now_ms):
    if type(now_ms) is not int or not 0 <= now_ms < 2**63:
        raise ValueError('Trusted bounded monotonic clock required')


def begin_relocation_transaction(db, account_id, role_id, epoch, proof, *, now_ms):
    """Journal a frozen preparation; source remains durable authority.

    Caller owns transaction/rollback. Authorization and maze validation precede
    this call on the actual map; this Interface does not authenticate a client.
    """
    cp = _checkpoint(db, account_id, role_id, epoch)
    _proof(proof, role_id, epoch)
    _clock(now_ms)
    previous = _read(db, role_id, proof.offer.transfer_id, cp)
    if previous is not None:
        if _encode(previous.prepared) != _encode(proof):
            raise ValueError('Relocation request identity reused')
        _validate_current(previous)
        return previous.stage
    pending = RelocationRecord(proof, 'prepared', cp, cp.entry_version, cp.transfer_id)
    _exact_source(pending)
    if now_ms >= proof.offer.deadline_ms:
        raise ValueError('Relocation preparation expired')
    if (db.execute("SELECT 1 FROM world_relocations WHERE role_id=? AND stage='prepared'", (role_id,)).fetchone()
            or db.execute("SELECT 1 FROM world_handoffs WHERE role_id=? AND stage='prepared'", (role_id,)).fetchone()):
        raise ValueError('Another durable position operation is pending')
    db.execute('INSERT INTO world_relocations VALUES(?,?,?,?,?,?,?)',
        (proof.offer.transfer_id, role_id, str(epoch), 'prepared', _encode(proof), cp.entry_version, cp.transfer_id))
    return 'prepared'


def _expected_record(db, account_id, role_id, epoch, proof):
    cp = _checkpoint(db, account_id, role_id, epoch)
    _proof(proof, role_id, epoch)
    record = _read(db, role_id, proof.offer.transfer_id, cp)
    if record is None or _encode(record.prepared) != _encode(proof):
        raise ValueError('Exact journalled relocation preparation required')
    return record


def _write_position(db, role_id, source, target):
    position = db.execute('UPDATE role_positions SET map_id=?,x=?,y=? '
        'WHERE role_id=? AND map_id=? AND x=? AND y=?', (*target.position, role_id, *source.position))
    if position.rowcount != 1:
        raise ValueError('Relocation position CAS failed')
    version = db.execute('UPDATE position_versions SET version=? WHERE role_id=? AND version=?',
                        (target.version, role_id, source.version))
    if version.rowcount != 1:
        raise ValueError('Relocation version CAS failed')


def commit_relocation_transaction(db, account_id, role_id, epoch, proof, *, now_ms):
    """Atomically write planned target/version/decision in caller transaction.

    Same instance entry provenance stays unchanged. Exact committed retries
    return False without rewinding later walking or another current instance.
    """
    record = _expected_record(db, account_id, role_id, epoch, proof)
    _clock(now_ms)
    if record.stage == 'committed':
        _validate_current(record)
        return False
    if record.stage != 'prepared':
        raise ValueError('Relocation already cancelled')
    _exact_source(record)
    if now_ms >= proof.offer.deadline_ms:
        raise ValueError('Relocation decision expired before commitment')
    if db.execute("SELECT 1 FROM world_handoffs WHERE role_id=? AND stage='prepared'", (role_id,)).fetchone():
        raise ValueError('Another durable transfer is pending')
    _write_position(db, role_id, proof.offer.source, proof.target)
    changed = db.execute("UPDATE world_relocations SET stage='committed' WHERE request_id=? AND stage='prepared'",
                         (proof.offer.transfer_id,))
    if changed.rowcount != 1:
        raise ValueError('Relocation decision CAS failed')
    return True


def load_relocation_transaction(db, account_id, role_id, current_epoch, request_id):
    """Pure SELECT history plus CURRENT full checkpoint under a valid lease."""
    cp = _checkpoint(db, account_id, role_id, current_epoch)
    record = _read(db, role_id, request_id, cp)
    if record is not None:
        _validate_current(record)
    return record


def cancel_relocation_transaction(db, account_id, role_id, epoch, proof):
    """Durably retain source/version before the map resumes its frozen member.

    Caller rollback owns all partial failures. A committed target cannot cancel;
    an exact cancelled replay observes current state without writing it back.
    """
    record = _expected_record(db, account_id, role_id, epoch, proof)
    if record.stage == 'cancelled':
        _validate_current(record)
        return False
    if record.stage != 'prepared':
        raise ValueError('Committed relocation cannot be cancelled')
    _exact_source(record)
    if db.execute("SELECT 1 FROM world_handoffs WHERE role_id=? AND stage='prepared'", (role_id,)).fetchone():
        raise ValueError('Another durable transfer is pending')
    _finish_cancel(db, proof, write_source=True)
    return True


def _finish_cancel(db, proof, *, write_source):
    if write_source:
        restored = replace(proof.frozen, version=proof.target.version, state='active')
        _write_position(db, proof.offer.source.role_id, proof.offer.source, restored)
    changed = db.execute("UPDATE world_relocations SET stage='cancelled' WHERE request_id=? AND stage='prepared'",
                         (proof.offer.transfer_id,))
    if changed.rowcount != 1:
        raise ValueError('Relocation cancellation CAS failed')


def prepare_relocation_recovery_transaction(db, account_id, role_id, new_epoch, request_id=None,
                                          *, expected_prepared=None):
    """Resolve an older lease's final SQL outcome, then return CURRENT authority.

    Acquire the new lease first; caller commits before retiring any old map
    state. A supplied exact map proof also covers freeze-before-journal failure.
    Unknown instances and contradictory checkpoints are never guessed. This
    does not clear memory, join a map, establish a send fence or run a client.
    """
    # No history is a normal result for legacy roles. Authenticate first, but
    # require a known instance only when an actual relocation is being resolved.
    cp = load_map_instance_transaction(db, account_id, role_id, new_epoch)
    if expected_prepared is not None:
        _proof(expected_prepared, role_id)
        if request_id is None:
            request_id = expected_prepared.offer.transfer_id
        if request_id != expected_prepared.offer.transfer_id:
            raise ValueError('Recovery request and supplied proof disagree')
    if request_id is None:
        latest = db.execute('SELECT request_id FROM world_relocations WHERE role_id=? AND epoch!=? '
                            'ORDER BY rowid DESC LIMIT 1', (role_id, str(new_epoch))).fetchone()
        if latest is None:
            return None
        request_id = latest[0]
    if cp is None:
        raise ValueError('Recovery of a relocation requires a known full instance')
    record = _read(db, role_id, request_id, cp)
    if record is None:
        if expected_prepared is None:
            raise ValueError('Recovery relocation not found')
        proof = expected_prepared
    else:
        proof = record.prepared
        if expected_prepared is not None and _encode(expected_prepared) != _encode(proof):
            raise ValueError('Recovery preparation conflicts with durable history')
    if str(proof.offer.source.login_epoch) == str(new_epoch):
        raise ValueError('Recovery requires a fenced previous lease')
    if record is not None:
        _validate_current(record)
        if record.stage != 'prepared':
            return record
    if db.execute("SELECT 1 FROM world_handoffs WHERE role_id=? AND stage='prepared'", (role_id,)).fetchone():
        raise ValueError('Resolve the pending cross-instance transfer first')
    if record is None:
        record = RelocationRecord(proof, 'prepared', cp, cp.entry_version, cp.transfer_id)
        _exact_source(record)
        if db.execute("SELECT 1 FROM world_relocations WHERE role_id=? AND stage='prepared'", (role_id,)).fetchone():
            raise ValueError('Another durable relocation needs recovery first')
        db.execute('INSERT INTO world_relocations VALUES(?,?,?,?,?,?,?)',
            (request_id, role_id, str(proof.offer.source.login_epoch), 'prepared', _encode(proof),
             cp.entry_version, cp.transfer_id))
    exact = (_entry_matches(record) and cp.position == proof.offer.source.position
             and cp.version == proof.offer.source.version)
    if not exact and cp.version <= proof.target.version:
        raise ValueError('Prepared relocation and recovery checkpoint disagree')
    # An authoritative later checkpoint is preserved. Only the older pending
    # journal is cancelled; it must never drag the new lease back to its source.
    _finish_cancel(db, proof, write_source=exact)
    result = _read(db, role_id, request_id, _checkpoint(db, account_id, role_id, new_epoch))
    _validate_current(result)
    return result
