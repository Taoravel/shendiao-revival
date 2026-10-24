"""Immutable explicit pre-gem score authority; no display/asset mutations.

Only trusted complete imports establish this baseline. Missing history stays
unknown, and later socket changes retain the same baseline instead of guessing
it by subtracting a score bonus from a current item.
"""
from dataclasses import asdict
import json
from equipment_gem_score import GemScoreBasis,validate_current
import equipment_gem_storage as sockets


def prepare(db):
    """Startup only, after Inventory/socket tables are prepared."""
    db.execute('''CREATE TABLE IF NOT EXISTS inventory_equipment_gem_score_bases (
        item_key INTEGER PRIMARY KEY REFERENCES inventory_items(id) ON DELETE CASCADE,
        role_id INTEGER NOT NULL REFERENCES roles(id),policy TEXT NOT NULL,
        origin TEXT NOT NULL,basis TEXT NOT NULL)''')
    db.execute('''CREATE TRIGGER IF NOT EXISTS equipment_gem_score_basis_delete
        AFTER DELETE ON inventory_items BEGIN DELETE FROM inventory_equipment_gem_score_bases WHERE item_key=OLD.id; END''')
    db.execute('''CREATE TRIGGER IF NOT EXISTS equipment_gem_score_basis_template_change
        AFTER UPDATE OF template_id,role_id ON inventory_items
        WHEN OLD.template_id!=NEW.template_id OR OLD.role_id!=NEW.role_id
        BEGIN DELETE FROM inventory_equipment_gem_score_bases WHERE item_key=OLD.id; END''')


def _item(db,inventory,key):
    snapshot=inventory.immutable_snapshot_transaction(db)
    if type(key) is not int or not 0<key<=0x7fffffff:raise ValueError('Positive owned equipment key required')
    item=next((v for v in snapshot.items if v.id==key),None)
    if item is None:raise ValueError('Current owned equipment unavailable')
    return item


def read(db,inventory,rules,key):
    item=_item(db,inventory,key)
    row=db.execute('SELECT role_id,policy,origin,basis FROM inventory_equipment_gem_score_bases WHERE item_key=?',(key,)).fetchone()
    if row is None:return None
    if row[:3]!=(inventory.role_id,rules.revision,'explicit_known_pre_gem_score'):
        raise ValueError('Unknown pre-gem score policy, owner or provenance')
    basis=GemScoreBasis(**json.loads(row[3]))
    if basis.role_id!=item.role_id or basis.item_key!=key or basis.policy!=rules.revision:
        raise ValueError('Persisted pre-gem score scope mismatch')
    return basis


def initialize(db,inventory,rules,gem_rules,basis,origin):
    """Explicit same-transaction immutable import, never a client authority."""
    if type(basis) is not GemScoreBasis or origin!='explicit_known_pre_gem_score' or basis.role_id!=inventory.role_id:
        raise ValueError('Complete trusted pre-gem score import required')
    current=sockets.read(db,inventory,gem_rules,basis.item_key)
    if current is None:raise ValueError('Complete known socket profile is required before score baseline')
    encoded=json.dumps(asdict(basis),sort_keys=True,separators=(',',':'))
    old=db.execute('SELECT role_id,policy,origin,basis FROM inventory_equipment_gem_score_bases WHERE item_key=?',
        (basis.item_key,)).fetchone()
    if old is not None:
        if old!=(inventory.role_id,rules.revision,origin,encoded):raise ValueError('Existing pre-gem score baseline cannot be reset')
        return read(db,inventory,rules,basis.item_key)
    validate_current(rules,gem_rules,current.item,current.state,basis)
    db.execute('INSERT INTO inventory_equipment_gem_score_bases VALUES(?,?,?,?,?)',
        (basis.item_key,inventory.role_id,rules.revision,origin,encoded))
    return read(db,inventory,rules,basis.item_key)
