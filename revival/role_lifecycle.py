"""Owned roster retirement, preserving role assets and immutable audit references.

No sockets, schema work on commands, physical purge or cross-role mutation.
The caller proves absence of an online owner after reading the lease candidate;
the write transaction then refuses any intervening lease acquisition.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DeletionCandidate:
    account_id: int
    role_id: int
    epoch: str | None
    deleted: bool


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS role_deletions (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id),
        account_id INTEGER NOT NULL REFERENCES accounts(id), deleted_at_ms INTEGER NOT NULL)''')


def candidate(db,account_id,role_id):
    row=db.execute('SELECT l.epoch,d.role_id FROM roles r '
        'LEFT JOIN role_leases l ON l.role_id=r.id LEFT JOIN role_deletions d ON d.role_id=r.id '
        'WHERE r.id=? AND r.account_id=?',(role_id,account_id)).fetchone()
    if row is None:raise ValueError('Delete role ownership mismatch')
    return DeletionCandidate(account_id,role_id,None if row[0] is None else str(row[0]),row[1] is not None)


def retire(db,expected,now_ms):
    if not db.in_transaction or type(expected) is not DeletionCandidate:
        raise ValueError('Delete requires account-owned transaction and candidate')
    if type(now_ms) is not int or now_ms<0:raise ValueError('Invalid deletion clock')
    current=candidate(db,expected.account_id,expected.role_id)
    if current.epoch!=expected.epoch:raise ValueError('Role login changed during deletion')
    if current.deleted:return expected.role_id
    db.execute('INSERT INTO role_deletions VALUES(?,?,?)',(expected.role_id,expected.account_id,now_ms))
    db.execute('UPDATE role_leases SET active=0 WHERE role_id=?',(expected.role_id,))
    return expected.role_id
