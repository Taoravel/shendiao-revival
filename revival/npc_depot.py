"""Role-owned NPC warehouse; same item keys/metadata, one caller transaction.

Carried inventory continues to own inventory_items. Stored items live separately
so carried use/equip/task submission cannot select them. No runtime DDL or I/O
outside the role persistence worker. Cash moves between explicit same-role
wallet/depot baselines in the caller's fenced transaction.
"""
from dataclasses import dataclass, replace
import struct
from inventory import BAG_INFO, item_record
from wire import compact
from currency import CurrencyChange,apply_currency,read_wallet,LIMIT

OPEN_DEPOT = 0xc04f0
CLOSE_DEPOT = 0xc04fb
DEPOSIT_MONEY = 0xc03fb
DRAW_MONEY = 0xc03fc
MONEY_TYPES = frozenset((DEPOSIT_MONEY,DRAW_MONEY))


def decode_close(body):
    """Original CColseDeport has no fields; revoke only this role's access."""
    if type(body) is not bytes or body:
        raise ValueError('Warehouse close request must have an empty body')


@dataclass(frozen=True)
class StoredItem:
    id: int
    role_id: int
    template_id: int
    quantity: int
    slot: int
    binding: int
    quality: object
    condition_revision: object = None
    condition_state: object = None
    detail_revision: object = None
    detail_origin: object = None
    detail_state: object = None


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS npc_depot_profiles (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id),cash INTEGER NOT NULL CHECK(cash>=0),
        origin TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS npc_depot_cash_journal (
        role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL,npc_key INTEGER NOT NULL,kind INTEGER NOT NULL,
        amount INTEGER NOT NULL,cash_before INTEGER NOT NULL,cash_after INTEGER NOT NULL,
        depot_before INTEGER NOT NULL,depot_after INTEGER NOT NULL,
        PRIMARY KEY(role_id,request_id))''')
    db.execute('''CREATE TABLE IF NOT EXISTS npc_depot_items (
        id INTEGER PRIMARY KEY,role_id INTEGER NOT NULL REFERENCES roles(id),
        template_id INTEGER NOT NULL,quantity INTEGER NOT NULL CHECK(quantity>0),
        slot INTEGER NOT NULL,binding INTEGER NOT NULL CHECK(binding IN (0,1)),
        quality INTEGER,condition_revision TEXT,condition_state TEXT,
        detail_revision TEXT,detail_origin TEXT,detail_state TEXT,
        UNIQUE(role_id,slot))''')
    columns={r[1] for r in db.execute('PRAGMA table_info(npc_depot_items)')}
    for name in ('detail_revision','detail_origin','detail_state'):
        if name not in columns: db.execute(f'ALTER TABLE npc_depot_items ADD COLUMN {name} TEXT')
    # A new dependent metadata Module must be included before transfers can be
    # enabled. Otherwise DELETE CASCADE would silently destroy unknown state.
    for table, in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        safe=table.replace('"','""')
        for fk in db.execute(f'PRAGMA foreign_key_list("{safe}")'):
            if fk[2]=='inventory_items' and fk[6].upper()=='CASCADE' and table not in (
                    'inventory_equipment_conditions','inventory_equipment_details'):
                raise ValueError('Warehouse metadata preservation required for '+table)


def initialize(db,inventory,cash,origin):
    _owner(db,inventory)
    if type(cash) is not int or not 0<=cash<=2**63-1 or origin not in ('new_restoration_role','explicit_migration'):
        raise ValueError('Warehouse requires an explicit known cash baseline')
    old=db.execute('SELECT cash,origin FROM npc_depot_profiles WHERE role_id=?',(inventory.role_id,)).fetchone()
    if old:
        if old!=(cash,origin): raise ValueError('Warehouse baseline cannot be reset')
        return
    db.execute('INSERT INTO npc_depot_profiles VALUES(?,?,?)',(inventory.role_id,cash,origin))


def _owner(db,inventory):
    if not db.in_transaction or not db.execute(
        'SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
        'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
        (inventory.role_id,inventory.account_id,inventory.epoch)).fetchone():
        raise ValueError('Warehouse requires current role owner transaction')


def decode_money(kind,body):
    if kind not in MONEY_TYPES or type(body) is not bytes or len(body)!=16:
        raise ValueError('Warehouse money request requires two native int64 fields')
    key,amount=struct.unpack('>qq',body)
    if key<0 or amount<1:
        raise ValueError('Warehouse money requires a known NPC and positive signed64 amount')
    return key,amount


def cash_balance(db,inventory):
    _owner(db,inventory)
    row=db.execute('SELECT cash FROM npc_depot_profiles WHERE role_id=?',(inventory.role_id,)).fetchone()
    if row is None or type(row[0]) is not int or not 0<=row[0]<=LIMIT:
        raise ValueError('Known valid warehouse cash baseline required')
    return row[0]


def transfer_cash(db,inventory,command,kind,body,rules,fingerprint):
    """Fresh accepted command only; common retry receipt is owned by the caller.

    The canonical cash ledger and the depot audit join the same transaction.
    No fees, bound-silver substitution, balance initialization or commit here.
    """
    _owner(db,inventory)
    key,amount=decode_money(kind,body)
    if key!=command.entity_key:raise ValueError('Warehouse money NPC key differs from map proof')
    if db.execute('SELECT 1 FROM npc_depot_cash_journal WHERE role_id=? AND request_id=?',
                  (inventory.role_id,command.request_id)).fetchone():
        raise ValueError('Warehouse transfer audit exists without its common receipt')
    depot_before=cash_balance(db,inventory)
    wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,rules)
    cash_before=next(r.balance for r in wallet if r.currency=='cash')
    delta=-amount if kind==DEPOSIT_MONEY else amount
    cash_after,depot_after=cash_before+delta,depot_before-delta
    if not 0<=cash_after<=LIMIT or not 0<=depot_after<=LIMIT:
        raise ValueError('Insufficient or overflowing warehouse transfer balance')
    import hashlib
    identity='nd:'+hashlib.sha256(command.request_id.encode()).hexdigest()
    apply_currency(db,inventory.account_id,inventory.role_id,inventory.epoch,
        CurrencyChange(identity,'npc_depot_transfer',f'npc:{command.npc_id}:depot:{kind}',(('cash',delta),)),rules)
    db.execute('UPDATE npc_depot_profiles SET cash=? WHERE role_id=?',(depot_after,inventory.role_id))
    db.execute('INSERT INTO npc_depot_cash_journal VALUES(?,?,?,?,?,?,?,?,?,?)',
        (inventory.role_id,command.request_id,fingerprint,key,kind,amount,cash_before,cash_after,depot_before,depot_after))


def _rows(db,inventory,column):
    if column==1:
        rows=db.execute('SELECT i.id,i.role_id,i.template_id,i.quantity,i.slot,i.binding,i.quality,c.revision,c.state,'
            'd.revision,d.origin,d.detail '
            'FROM inventory_items i LEFT JOIN inventory_equipment_conditions c ON c.item_key=i.id '
            'LEFT JOIN inventory_equipment_details d ON d.item_key=i.id '
            'WHERE i.role_id=? AND i.equipment_slot IS NULL ORDER BY i.slot',(inventory.role_id,)).fetchall()
    elif column==2:
        rows=db.execute('SELECT * FROM npc_depot_items WHERE role_id=? ORDER BY slot',(inventory.role_id,)).fetchall()
    else:
        raise ValueError('Unsupported warehouse column')
    return tuple(StoredItem(*r) for r in rows)


def carried_items(db,inventory):
    """Frozen carried records with complete currently supported item metadata."""
    _owner(db,inventory)
    return _rows(db,inventory,1)


def take_carried(db,inventory,key):
    _owner(db,inventory)
    item=next((i for i in _rows(db,inventory,1) if i.id==key),None)
    if item is None:raise ValueError('Carried item is unavailable')
    _delete(db,item,1)
    return item


def restore_carried(db,inventory,item):
    _owner(db,inventory)
    if not isinstance(item,StoredItem) or item.role_id!=inventory.role_id:
        raise ValueError('Restored item owner mismatch')
    used={i.slot for i in _rows(db,inventory,1)}
    slot=next((i for i in range(inventory.policy['bag_capacity']) if i not in used),None)
    if slot is None:raise ValueError('Bag full')
    _put(db,replace(item,slot=slot),1)


def messages(db,inventory,capacity,*,include_carried=True):
    _owner(db,inventory)
    profile=db.execute('SELECT cash FROM npc_depot_profiles WHERE role_id=?',(inventory.role_id,)).fetchone()
    if profile is None: raise ValueError('Legacy warehouse cash is unknown; explicit migration required')
    items=_rows(db,inventory,2)
    depot=(BAG_INFO,struct.pack('>iQi',2,profile[0],capacity)+compact(len(items))+b''.join(item_record(
        dict(id=i.id,template_id=i.template_id,quantity=i.quantity,slot=i.slot,binding=i.binding))
        for i in items)+b'\0')
    return (inventory.equipment_bag_messages(db,inventory.epoch)[0],depot) if include_carried else (depot,)


def _delete(db,item,column):
    db.execute('DELETE FROM '+('inventory_items' if column==1 else 'npc_depot_items')+
        ' WHERE id=? AND role_id=?',(item.id,item.role_id))


def _put(db,item,column):
    if column==1:
        db.execute('INSERT INTO inventory_items(id,role_id,template_id,quantity,slot,binding,quality) VALUES(?,?,?,?,?,?,?)',
            (item.id,item.role_id,item.template_id,item.quantity,item.slot,item.binding,item.quality))
        if item.condition_revision is not None:
            db.execute('INSERT INTO inventory_equipment_conditions VALUES(?,?,?)',
                       (item.id,item.condition_revision,item.condition_state))
        if item.detail_revision is not None:
            db.execute('INSERT INTO inventory_equipment_details VALUES(?,?,?,?)',
                       (item.id,item.detail_revision,item.detail_origin,item.detail_state))
    else:
        db.execute('INSERT INTO npc_depot_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (item.id,item.role_id,item.template_id,item.quantity,item.slot,item.binding,item.quality,
             item.condition_revision,item.condition_state,item.detail_revision,item.detail_origin,item.detail_state))


def move(db,inventory,body,capacity):
    """Original CMoveItem body. Split/merge/swap preserves actual metadata."""
    _owner(db,inventory)
    if len(body)!=32:
        raise ValueError('Warehouse move requires 32 bytes')
    source_column,key,source_slot,target_column,target_slot,count,target_role=struct.unpack('>6iq',body)
    if (source_column not in (1,2) or target_column not in (1,2)
            or 2 not in (source_column,target_column) or target_role not in (-1,0,inventory.role_id)
            or key<=0 or count<0):
        raise ValueError('Invalid warehouse move scope')
    sources=_rows(db,inventory,source_column)
    source=next((i for i in sources if i.id==key),None)
    if source is None or source.slot!=source_slot:
        raise ValueError('Warehouse source is unavailable or moved')
    targets=_rows(db,inventory,target_column)
    target_capacity=capacity if target_column==2 else inventory.policy['bag_capacity']
    if target_slot==-1:
        target_slot=next((s for s in range(target_capacity) if all(i.slot!=s for i in targets)),None)
    if target_slot is None or not 0<=target_slot<target_capacity:
        raise ValueError('Warehouse target full or invalid')
    count=count or source.quantity
    if count>source.quantity:
        raise ValueError('Warehouse quantity exceeds source')
    if source_column==target_column and source_slot==target_slot:
        return
    target=next((i for i in targets if i.slot==target_slot),None)
    stack_limit=int(inventory.items[source.template_id]['maxNum'])
    if target and (source.template_id,source.binding,source.quality)==(target.template_id,target.binding,target.quality) \
            and source.condition_state is None and target.condition_state is None and stack_limit>1 \
            and source.detail_state is None and target.detail_state is None:
        count=min(count,stack_limit-target.quantity)
        if count<=0: raise ValueError('Warehouse target stack full')
        _delete(db,target,target_column)
        _put(db,replace(target,quantity=target.quantity+count),target_column)
        _delete(db,source,source_column)
        if count<source.quantity:
            _put(db,replace(source,quantity=source.quantity-count),source_column)
    elif target:
        if count!=source.quantity:
            raise ValueError('Cannot partially swap different warehouse items')
        _delete(db,source,source_column)
        _delete(db,target,target_column)
        _put(db,replace(source,slot=target_slot),target_column)
        _put(db,replace(target,slot=source_slot),source_column)
    elif count==source.quantity:
        _delete(db,source,source_column)
        _put(db,replace(source,slot=target_slot),target_column)
    else:
        if stack_limit<=1 or source.condition_state is not None or source.detail_state is not None:
            raise ValueError('Unique warehouse items cannot be split')
        _delete(db,source,source_column)
        _put(db,replace(source,quantity=source.quantity-count),source_column)
        # Allocate from the inventory's global AUTOINCREMENT namespace, even
        # when splitting wholly within the depot. The temporary row is private
        # to this transaction and removed before the resulting item is stored.
        new_key=db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot,binding,quality) '
            'VALUES(?,?,?,?,?,?)',(inventory.role_id,source.template_id,count,-1000000000,source.binding,source.quality)).lastrowid
        db.execute('DELETE FROM inventory_items WHERE id=?',(new_key,))
        _put(db,replace(source,id=new_key,quantity=count,slot=target_slot),target_column)
