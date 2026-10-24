"""Explicit equipment-gem source, separate from base details and raw effects.

This is a caller-transaction CAS, not a paid socket action. The integrating
owner must combine material/cash/tool settlement, complete score/color source,
gem-aware role projection and native encoding before exposing actions.
"""
from dataclasses import dataclass,asdict
import json
from inventory import ItemState
from equipment_detail import EquipmentDetail
from equipment_condition import EquipmentCondition
from equipment_gems import GemState,SocketRequest,validate_equipment


@dataclass(frozen=True)
class EquipmentGemBasis:
    account_id: int
    inventory_revision: int
    item: ItemState
    state: GemState
    equipment_skill: int
    origin: str
    raw_state: str
    detail_source: tuple
    condition_source: tuple

    def __post_init__(self):
        if (type(self.account_id) is not int or self.account_id<=0
                or type(self.inventory_revision) is not int or not 0<=self.inventory_revision<2**63-1
                or type(self.item) is not ItemState or type(self.item.detail) is not EquipmentDetail
                or type(self.item.condition) is not EquipmentCondition or self.item.quality is not None
                or any(type(v) is not int for v in (self.item.id,self.item.role_id,self.item.template_id,
                    self.item.quantity,self.item.slot,self.item.binding))
                or self.item.equipment_slot is not None and type(self.item.equipment_slot) is not int
                or type(self.state) is not GemState or type(self.equipment_skill) is not int
                or self.equipment_skill not in (0,410006,410007)
                or type(self.origin) is not str or type(self.raw_state) is not str
                or type(self.detail_source) is not tuple or len(self.detail_source)!=3
                or type(self.condition_source) is not tuple or len(self.condition_source)!=2
                or any(type(v) is not str for v in self.detail_source+self.condition_source)):
            raise ValueError('Frozen complete current equipment socket basis required')


def prepare(db):
    """Startup only, after Inventory schema preparation."""
    db.execute('''CREATE TABLE IF NOT EXISTS inventory_equipment_gems (
        item_key INTEGER PRIMARY KEY REFERENCES inventory_items(id) ON DELETE CASCADE,
        role_id INTEGER NOT NULL REFERENCES roles(id),policy TEXT NOT NULL,origin TEXT NOT NULL,
        baseline TEXT NOT NULL,state TEXT NOT NULL,equipment_skill INTEGER NOT NULL)''')
    db.execute('''CREATE TRIGGER IF NOT EXISTS inventory_equipment_gems_delete
        AFTER DELETE ON inventory_items BEGIN DELETE FROM inventory_equipment_gems WHERE item_key=OLD.id; END''')
    db.execute('''CREATE TRIGGER IF NOT EXISTS inventory_equipment_gems_template_change
        AFTER UPDATE OF template_id,role_id ON inventory_items
        WHEN OLD.template_id!=NEW.template_id OR OLD.role_id!=NEW.role_id
        BEGIN DELETE FROM inventory_equipment_gems WHERE item_key=OLD.id; END''')


def _json(state):
    return json.dumps(asdict(state),sort_keys=True,separators=(',',':'))


def _owned(db,inventory,key):
    snapshot=inventory.immutable_snapshot_transaction(db)
    if type(key) is not int or not 0<key<=0x7fffffff:raise ValueError('Positive owned equipment key required')
    item=next((i for i in snapshot.items if i.id==key),None)
    if item is None:raise ValueError('Owned equipment unavailable')
    return snapshot,item


def _advance(db,inventory,revision):
    if db.execute('UPDATE inventory_versions SET revision=revision+1 WHERE role_id=? AND revision=?',
            (inventory.role_id,revision)).rowcount!=1:
        raise ValueError('Equipment gem inventory source changed')


def read(db,inventory,rules,key):
    snapshot,item=_owned(db,inventory,key)
    row=db.execute('SELECT policy,origin,state,equipment_skill FROM inventory_equipment_gems WHERE item_key=? AND role_id=?',
        (key,inventory.role_id)).fetchone()
    if row is None:return None
    if row[0]!=rules.revision or row[1] not in ('explicit_known_socket_profile','socket_change'):
        raise ValueError('Unknown equipment gem policy or origin')
    value=json.loads(row[2]);value['templates']=tuple(value['templates']);state=GemState(**value)
    validate_equipment(rules,item,state,row[3])
    detail=db.execute('SELECT revision,origin,detail FROM inventory_equipment_details WHERE item_key=?',(key,)).fetchone()
    condition=db.execute('SELECT revision,state FROM inventory_equipment_conditions WHERE item_key=?',(key,)).fetchone()
    if detail is None or condition is None:raise ValueError('Known full equipment sources required')
    return EquipmentGemBasis(inventory.account_id,snapshot.inventory_revision,item,state,row[3],row[1],row[2],detail,condition)


def request_basis(db,inventory,rules,request):
    """Resolve the proven native column exactly; never search another one."""
    if type(request) is not SocketRequest:raise ValueError('Frozen native socket request required')
    basis=read(db,inventory,rules,request.equipment_key)
    if basis is None:raise ValueError('Current complete equipment socket source is unknown')
    column=1 if basis.item.equipment_slot is None else 4
    if request.source_column!=column:raise ValueError('Current equipment container does not match native request')
    return basis


def initialize(db,inventory,rules,key,state,equipment_skill,origin):
    """Trusted complete import only, including known-empty, never implicit0.

    Saving a candidate is not permission to enable old readers: integration
    must consume the gem source everywhere, with the complete role policy.
    """
    snapshot,item=_owned(db,inventory,key)
    if origin!='explicit_known_socket_profile' or type(state) is not GemState or state.version!=0:
        raise ValueError('Explicit complete equipment socket baseline required')
    validate_equipment(rules,item,state,equipment_skill)
    baseline=json.dumps((state.templates,equipment_skill),separators=(',',':'))
    old=db.execute('SELECT role_id,policy,baseline FROM inventory_equipment_gems WHERE item_key=?',(key,)).fetchone()
    if old:
        if old!=(inventory.role_id,rules.revision,baseline):raise ValueError('Existing gem baseline cannot be reset')
        return read(db,inventory,rules,key)
    db.execute('INSERT INTO inventory_equipment_gems VALUES(?,?,?,?,?,?,?)',
        (key,inventory.role_id,rules.revision,origin,baseline,_json(state),equipment_skill))
    _advance(db,inventory,snapshot.inventory_revision)
    return read(db,inventory,rules,key)


def replace_state(db,inventory,rules,basis,after):
    """Single state CAS, no fee/receipt/connection/commit/send or source guess.

    Paid controller must skip this mutator. All outer errors require rollback.
    A state save alone does not implement insertion/removal asset settlement.
    """
    if (type(basis) is not EquipmentGemBasis or basis.account_id!=inventory.account_id
            or type(after) is not GemState or after.version!=basis.state.version+1):
        raise ValueError('Next version of the complete same equipment source required')
    current=read(db,inventory,rules,basis.item.id)
    if current!=basis:raise ValueError('Equipment gem full source changed')
    validate_equipment(rules,basis.item,after,basis.equipment_skill)
    changed=db.execute('UPDATE inventory_equipment_gems SET origin=?,state=? '
        'WHERE item_key=? AND role_id=? AND policy=? AND origin=? AND state=? AND equipment_skill=?',
        ('socket_change',_json(after),basis.item.id,inventory.role_id,rules.revision,basis.origin,basis.raw_state,basis.equipment_skill)).rowcount
    if changed!=1:raise ValueError('Equipment gem source CAS failed')
    _advance(db,inventory,basis.inventory_revision)
    return read(db,inventory,rules,basis.item.id)
