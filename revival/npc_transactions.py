"""Transient caller-transaction callback shared by real NPC asset Adapters.

Retains no DB, mutable inventory, rules or Session. The callback is a trusted
startup/integration dependency; its output is encoded before the caller commits.
"""


def precommit_messages(callback,db,inventory,*,replayed):
    if callback is None:return ()
    if not callable(callback) or type(replayed) is not bool or not db.in_transaction:
        raise ValueError('Trusted NPC caller-transaction precommit required')
    messages=callback(db,inventory,inventory.immutable_snapshot_transaction(db),replayed=replayed)
    if (type(messages) is not tuple or any(type(row) is not tuple or len(row)!=2
            or type(row[0]) is not int or not 0<=row[0]<=0xffffffff or type(row[1]) is not bytes
            for row in messages)):
        raise ValueError('NPC precommit must return immutable encoded logical messages')
    return messages
