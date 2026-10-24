"""Complete known carried orb source, distinct from the worn pet soul map.

Caller-owned role transaction only. The source records four native fields,
explicit nonbinding flags and exact retained worn raw6 when known. None means
an explicitly supplied absence of worn history, never an invented raw6 zero.
This is source CAS, not equip/remove/fusion permission or asset settlement.
"""
from dataclasses import asdict,dataclass
import json
from inspect_client import OUT
from inventory import ItemState
from pet_souls import SoulRules
from pet_soul_item_data import OrbTips,carried_tip_reply


REVISION='2026-10-24.pet-soul-items.1'


@dataclass(frozen=True)
class OrbRules:
    revision: str
    souls: SoulRules

    def __post_init__(self):
        if self.revision!=REVISION or type(self.souls) is not SoulRules:
            raise ValueError('Frozen original orb source rules required')

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/pet-soul-items-v1.json').read_text(encoding='utf-8'))
        souls=SoulRules.load()
        if (policy['revision']!=REVISION or policy['soul_policy']!=souls.revision
                or policy['wire_fields']!=['cumulative_exp','soul_skill_id','raw5','raw4']
                or policy['maximum_quantity']!=1 or policy['nonbinding_flags_mask']!=0xfffffffe):
            raise ValueError('Orb source policy requires explicit review')
        rows=json.loads((OUT/'catalogs/knight.gsp.item.citemattr.json').read_text(encoding='utf-8'))
        items={int(r['attributes']['id']):r['attributes'] for r in rows}
        if any(tuple(int(items[key][name]) for name in ('itemtypeid','maxNum','needLevel','level','outbattleuse'))
                !=(145,1,1,0,2) for key in souls.souls):
            raise ValueError('Original nonstacking carried orb definitions changed')
        return cls(REVISION,souls)


@dataclass(frozen=True)
class OrbSource:
    role_id: int
    item_key: int
    template_id: int
    version: int
    policy: str
    source_ref: str
    tips: OrbTips
    nonbinding_flags: int
    retained_raw6: int | None

    def __post_init__(self):
        if (type(self.role_id) is not int or not 0<self.role_id<2**63
                or any(type(v) is not int or not 0<v<=0x7fffffff for v in (self.item_key,self.template_id))
                or type(self.version) is not int or not 0<=self.version<2**63-1
                or type(self.policy) is not str or self.policy!=REVISION
                or type(self.source_ref) is not str or not 1<=len(self.source_ref)<=160
                or type(self.tips) is not OrbTips or type(self.nonbinding_flags) is not int
                or not 0<=self.nonbinding_flags<=0xfffffffe or self.nonbinding_flags&1
                or self.retained_raw6 is not None and (type(self.retained_raw6) is not int
                    or not -0x80000000<=self.retained_raw6<=0x7fffffff)):
            raise ValueError('Explicit complete immutable carried orb provenance required')


@dataclass(frozen=True)
class OrbBasis:
    account_id: int
    inventory_revision: int
    item: ItemState
    source: OrbSource
    origin: str
    raw_source: str
    baseline_source: str
    stamp: str

    def __post_init__(self):
        if (type(self.account_id) is not int or self.account_id<=0
                or type(self.inventory_revision) is not int or not 0<=self.inventory_revision<2**63-1
                or type(self.item) is not ItemState or type(self.source) is not OrbSource
                or any(type(v) is not int for v in (self.item.id,self.item.role_id,self.item.template_id,
                    self.item.quantity,self.item.slot,self.item.binding))
                or self.item.quantity!=1 or self.item.slot<0 or self.item.binding not in (0,1)
                or self.item.equipment_slot is not None or self.item.quality is not None
                or self.item.condition is not None or self.item.detail is not None
                or self.item.id!=self.source.item_key or self.item.role_id!=self.source.role_id
                or self.item.template_id!=self.source.template_id
                or any(type(v) is not str for v in (self.origin,self.raw_source,self.baseline_source,self.stamp))):
            raise ValueError('Frozen complete same-item orb source required')


def prepare(db):
    """Startup only. Generic physical item mutations invalidate old provenance."""
    db.execute('''CREATE TABLE IF NOT EXISTS inventory_pet_soul_items (
        item_key INTEGER PRIMARY KEY REFERENCES inventory_items(id) ON DELETE CASCADE,
        role_id INTEGER NOT NULL REFERENCES roles(id),policy TEXT NOT NULL,
        origin TEXT NOT NULL,stamp TEXT NOT NULL,baseline TEXT NOT NULL,state TEXT NOT NULL)''')
    db.execute('''CREATE TRIGGER IF NOT EXISTS pet_soul_item_source_update
        AFTER UPDATE OF template_id,role_id,quantity,binding,quality ON inventory_items
        BEGIN DELETE FROM inventory_pet_soul_items WHERE item_key=OLD.id; END''')
    db.execute('''CREATE TRIGGER IF NOT EXISTS pet_soul_item_source_delete
        AFTER DELETE ON inventory_items
        BEGIN DELETE FROM inventory_pet_soul_items WHERE item_key=OLD.id; END''')


def _owned(db,inventory,rules,key):
    if type(rules) is not OrbRules or type(key) is not int or not 0<key<=0x7fffffff:
        raise ValueError('Frozen orb rules and positive item key required')
    snapshot=inventory.immutable_snapshot_transaction(db)
    item=next((i for i in snapshot.items if i.id==key),None)
    if (type(item) is not ItemState or item.template_id not in rules.souls.souls
            or any(type(v) is not int for v in (item.id,item.role_id,item.template_id,item.quantity,item.slot,item.binding))
            or item.quantity!=1 or item.slot<0 or item.equipment_slot is not None
            or item.binding not in (0,1) or item.quality is not None or item.condition is not None or item.detail is not None):
        raise ValueError('Current owned carried single original orb required')
    return snapshot,item


def _json(source):return json.dumps(asdict(source),sort_keys=True,separators=(',',':'))


def _decode(raw):
    data=json.loads(raw);data['tips']=OrbTips(**data['tips'])
    return OrbSource(**data)


def _stamp(item):return json.dumps((item.template_id,item.quantity,item.binding,item.quality),separators=(',',':'))


def _check(source,item,rules):
    if (type(source) is not OrbSource or source.policy!=rules.revision
            or (source.role_id,source.item_key,source.template_id)!=(item.role_id,item.id,item.template_id)
            or source.tips.soul_skill_id!=0 and source.tips.soul_skill_id not in rules.souls.skill_ids):
        raise ValueError('Known same-orb template, soul skill and policy required')


def _advance(db,inventory,revision):
    if db.execute('UPDATE inventory_versions SET revision=revision+1 WHERE role_id=? AND revision=?',
            (inventory.role_id,revision)).rowcount!=1:raise ValueError('Orb inventory source CAS failed')


def read(db,inventory,rules,key):
    """Missing stays None; physical-item ABA never resurrects deleted sources."""
    snapshot,item=_owned(db,inventory,rules,key)
    row=db.execute('SELECT role_id,policy,origin,stamp,baseline,state FROM inventory_pet_soul_items WHERE item_key=?',
        (key,)).fetchone()
    if row is None:return None
    if (row[:2]!=(inventory.role_id,rules.revision) or row[2] not in ('explicit_known_orb_instance','orb_change')
            or row[3]!=_stamp(item)):
        raise ValueError('Unknown or stale full orb provenance')
    baseline,source=_decode(row[4]),_decode(row[5]);_check(baseline,item,rules);_check(source,item,rules)
    if (baseline.version!=0 or baseline.source_ref!=source.source_ref
            or baseline.retained_raw6!=source.retained_raw6 or baseline.nonbinding_flags!=source.nonbinding_flags
            or row[2]=='explicit_known_orb_instance' and baseline!=source):
        raise ValueError('Orb baseline/history requires explicit reconciliation')
    return OrbBasis(inventory.account_id,snapshot.inventory_revision,item,source,row[2],row[5],row[4],row[3])


def initialize(db,inventory,rules,source,origin):
    """Trusted explicit known import; exact retry reads current, never resets."""
    if type(source) is not OrbSource:raise ValueError('Complete explicit orb import required')
    snapshot,item=_owned(db,inventory,rules,source.item_key);_check(source,item,rules)
    if origin!='explicit_known_orb_instance' or source.version!=0:raise ValueError('Explicit original orb source required')
    encoded=_json(source);old=read(db,inventory,rules,source.item_key)
    if old is not None:
        if old.baseline_source!=encoded:raise ValueError('Orb source cannot be reset or re-sourced')
        return old
    db.execute('INSERT INTO inventory_pet_soul_items VALUES(?,?,?,?,?,?,?)',
        (item.id,inventory.role_id,rules.revision,origin,_stamp(item),encoded,encoded))
    _advance(db,inventory,snapshot.inventory_revision)
    return read(db,inventory,rules,item.id)


def replace_source(db,inventory,rules,before,after):
    """Trusted fresh metadata CAS; paid controllers skip this mutator on retry."""
    if (type(before) is not OrbBasis or type(after) is not OrbSource or before.account_id!=inventory.account_id
            or (after.role_id,after.item_key,after.template_id,after.policy,after.source_ref,
                after.retained_raw6,after.nonbinding_flags)!=(before.source.role_id,before.source.item_key,
                before.source.template_id,before.source.policy,before.source.source_ref,
                before.source.retained_raw6,before.source.nonbinding_flags)
            or after.version!=before.source.version+1):
        raise ValueError('Next same-orb source with exact retained history required')
    current=read(db,inventory,rules,after.item_key)
    if current!=before:raise ValueError('Complete orb source changed')
    _check(after,current.item,rules)
    if db.execute('UPDATE inventory_pet_soul_items SET origin=?,state=? WHERE item_key=? AND role_id=? '
            'AND policy=? AND origin=? AND stamp=? AND baseline=? AND state=?',
            ('orb_change',_json(after),after.item_key,inventory.role_id,rules.revision,before.origin,
             before.stamp,before.baseline_source,before.raw_source)).rowcount!=1:raise ValueError('Full orb metadata CAS failed')
    _advance(db,inventory,current.inventory_revision)
    return read(db,inventory,rules,after.item_key)


def tip_message(db,inventory,rules,key):
    current=read(db,inventory,rules,key)
    if current is None:raise ValueError('Current complete carried orb source required')
    return carried_tip_reply(key,current.source.tips)
