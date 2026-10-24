"""Ordinary equipment durability and client-matched NPC repair quotes."""
from dataclasses import asdict,dataclass,replace
from decimal import Decimal,localcontext
import json
import hashlib
from types import MappingProxyType
from inspect_client import OUT
from currency import CurrencyChange,apply_currency,read_wallet


@dataclass(frozen=True)
class EquipmentCondition:
    version: int
    current: int
    maximum: int
    color_tier: int

    def __post_init__(self):
        if (any(type(x) is not int for x in (self.version,self.current,self.maximum,self.color_tier))
                or not 0<=self.version<0x7fffffff or not 0<=self.current<=self.maximum<=0x7fffffff
                or self.maximum<1 or not 1<=self.color_tier<=6):
            raise ValueError('Invalid ordinary equipment condition')


@dataclass(frozen=True)
class EquipmentRules:
    revision: str
    initial_current: int
    initial_maximum: int
    initial_color: int
    costs: object
    success_per_mille: int
    failure_loss: int
    minimum_maximum: int

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/equipment-condition-v1.json').read_text(encoding='utf-8'))
        if policy['revision']!='2026-10-23.equipment-condition.2':
            raise ValueError('Equipment condition policy needs implementation review')
        rows=json.loads((OUT/'catalogs/knight.gsp.item.cequiprepairconfig.json').read_text(encoding='utf-8'))
        chances=json.loads((OUT/'catalogs/knight.gsp.item.cequiprepairsuccposs.json').read_text(encoding='utf-8'))
        costs=MappingProxyType({int(r['attributes']['id']):int(r['attributes']['npcrepair']) for r in rows})
        chance=next(int(r['attributes']['probability']) for r in chances if int(r['attributes']['id'])==2)
        g=policy['generation']
        return cls(policy['revision'],g['current'],g['maximum'],g['color_tier'],costs,chance,10,
                   policy['npc_repair']['minimum_repairable_maximum_exclusive'])

    def generate(self):
        return EquipmentCondition(0,self.initial_current,self.initial_maximum,self.initial_color)

    def npc_cost(self, state, level):
        if not isinstance(state,EquipmentCondition) or type(level) is not int or level not in self.costs:
            raise ValueError('Explicit ordinary equipment condition and repair level required')
        if state.maximum<=self.minimum_maximum or state.current==state.maximum:
            raise ValueError('Full or exhausted maximum equipment cannot be repaired')
        # Client 1073d70 raises original binary64 1.2 using x87, then the
        # coefficient is stored as binary64 at 10dbc91. Avoid Python pow's
        # prematurely rounded exponent result (tier5/unit25/25 missing:1295).
        with localcontext() as context:
            context.prec=80
            coefficient=float(Decimal.from_float(1.2)**(state.color_tier-1)*self.costs[level])
        cost=int(coefficient*(state.maximum-state.current))
        if not 1<=cost<=0x7fffffff:
            raise ValueError('Repair cost outside original signed integer consumer')
        return cost

    def repair(self, state, level, draw):
        cost=self.npc_cost(state,level)
        if type(draw) is not int or not 0<=draw<1000:
            raise ValueError('Trusted per-command repair draw required')
        success=draw<self.success_per_mille
        maximum=state.maximum if success else state.maximum-self.failure_loss
        current=maximum if success else min(state.current,maximum)
        return replace(state,version=state.version+1,current=current,maximum=maximum),cost,success

    def wear(self, state, amount):
        if not isinstance(state,EquipmentCondition) or type(amount) is not int or amount<=0:
            raise ValueError('Trusted positive durability loss required')
        return replace(state,version=state.version+1,current=max(0,state.current-amount))


@dataclass(frozen=True)
class RepairReceipt:
    settlement_id: str
    item_key: int
    before: EquipmentCondition
    after: EquipmentCondition
    cost: int
    success: bool


def prepare(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS inventory_equipment_conditions (
            item_key INTEGER PRIMARY KEY REFERENCES inventory_items(id) ON DELETE CASCADE,
            revision TEXT NOT NULL,state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS inventory_equipment_receipts (
            role_id INTEGER NOT NULL REFERENCES roles(id),settlement_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL,result TEXT NOT NULL,
            PRIMARY KEY(role_id,settlement_id));
        CREATE TABLE IF NOT EXISTS inventory_equipment_color_migrations (
            item_key INTEGER NOT NULL, target_revision TEXT NOT NULL,
            fingerprint TEXT NOT NULL, before_revision TEXT NOT NULL,
            before_state TEXT NOT NULL,result TEXT NOT NULL,
            PRIMARY KEY(item_key,target_revision));
    ''')


def _owner(db,account_id,role_id,key):
    if not db.in_transaction:
        raise ValueError('Equipment condition requires an owner transaction')
    row=db.execute('SELECT i.template_id FROM inventory_items i JOIN roles r ON r.id=i.role_id '
                   'WHERE i.id=? AND i.role_id=? AND r.account_id=? AND i.quantity=1',
                   (key,role_id,account_id)).fetchone()
    if not row:raise ValueError('Equipment instance ownership mismatch')
    return row[0]


def _revision(db,role_id):
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role_id,))


def initialize(db,account_id,role_id,key,rules,state):
    _owner(db,account_id,role_id,key)
    if not isinstance(state,EquipmentCondition) or state.version!=0:
        raise ValueError('Explicit initial equipment condition required')
    if db.execute('SELECT 1 FROM inventory_equipment_conditions WHERE item_key=?',(key,)).fetchone():
        raise ValueError('Equipment condition cannot be reset')
    db.execute('INSERT INTO inventory_equipment_conditions VALUES(?,?,?)',
               (key,rules.revision,json.dumps(asdict(state))))
    _revision(db,role_id)
    return state


def load(db,account_id,role_id,key,rules):
    _owner(db,account_id,role_id,key)
    row=db.execute('SELECT revision,state FROM inventory_equipment_conditions WHERE item_key=?',(key,)).fetchone()
    if not row or row[0]!=rules.revision:
        raise ValueError('Equipment condition requires explicit initialization or revision migration')
    return EquipmentCondition(**json.loads(row[1]))


def reconcile_color(db,account_id,role_id,key,rules,expected_version,color_tier):
    """Explicit correction of experimental v1's mislabeled color field.

    A trusted caller supplies the known actual color. Preserve current/max and
    the full original state as audit; never copy old quality_tier as a color.
    """
    _owner(db,account_id,role_id,key)
    if type(expected_version) is not int or expected_version<0 or type(color_tier) is not int or not 1<=color_tier<=6:
        raise ValueError('Explicit known equipment color and version required')
    fingerprint=hashlib.sha256(json.dumps([expected_version,color_tier]).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result FROM inventory_equipment_color_migrations '
                   'WHERE item_key=? AND target_revision=?',(key,rules.revision)).fetchone()
    if old:
        if old[0]!=fingerprint:raise ValueError('Equipment color reconciliation intent conflict')
        return EquipmentCondition(**json.loads(old[1]))
    row=db.execute('SELECT revision,state FROM inventory_equipment_conditions WHERE item_key=?',(key,)).fetchone()
    if not row or row[0]!='2026-10-23.equipment-condition.1':
        raise ValueError('No experimental v1 equipment condition to reconcile')
    before=json.loads(row[1])
    if (set(before)!={'version','current','maximum','quality_tier'}
            or any(type(value) is not int for value in before.values())
            or before['version']!=expected_version or not 1<=before['quality_tier']<=5):
        raise ValueError('Experimental equipment condition version or shape mismatch')
    after=EquipmentCondition(expected_version+1,before['current'],before['maximum'],color_tier)
    result=json.dumps(asdict(after))
    db.execute('UPDATE inventory_equipment_conditions SET revision=?,state=? WHERE item_key=?',
               (rules.revision,result,key))
    db.execute('INSERT INTO inventory_equipment_color_migrations VALUES(?,?,?,?,?,?)',
               (key,rules.revision,fingerprint,row[0],row[1],result))
    _revision(db,role_id)
    return after


def _request(db,role_id,settlement_id,intent):
    if type(settlement_id) is not str or not 1<=len(settlement_id)<=120:
        raise ValueError('Equipment settlement ID must contain 1..120 characters')
    fingerprint=hashlib.sha256(json.dumps(intent,separators=(',',':')).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result FROM inventory_equipment_receipts WHERE role_id=? AND settlement_id=?',
                   (role_id,settlement_id)).fetchone()
    if old and old[0]!=fingerprint:raise ValueError('Equipment settlement payload conflict')
    return fingerprint,json.loads(old[1]) if old else None


def _write(db,role_id,key,settlement_id,fingerprint,state,result):
    db.execute('UPDATE inventory_equipment_conditions SET state=? WHERE item_key=?',(json.dumps(asdict(state)),key))
    db.execute('INSERT INTO inventory_equipment_receipts VALUES(?,?,?,?)',
               (role_id,settlement_id,fingerprint,json.dumps(result)))
    _revision(db,role_id)


def wear(db,account_id,role_id,key,rules,settlement_id,expected_version,amount):
    _owner(db,account_id,role_id,key)
    if type(expected_version) is not int or type(amount) is not int or amount<=0:
        raise ValueError('Invalid equipment wear command')
    fingerprint,old=_request(db,role_id,settlement_id,[rules.revision,'wear',key,expected_version,amount])
    if old:return EquipmentCondition(**old)
    before=load(db,account_id,role_id,key,rules)
    if before.version!=expected_version:raise ValueError('Equipment condition version mismatch')
    after=rules.wear(before,amount)
    _write(db,role_id,key,settlement_id,fingerprint,after,asdict(after))
    return after


def repair(db,account_id,role_id,key,rules,currency_rules,epoch,settlement_id,expected_version,draw,level):
    """Trusted NPC eligibility/draw from owner; debit and condition join its txn.

    The caller validates NPC service and out-of-battle state. A raw client NPC ID
    is not authorization. Public replies must reload current condition/balance,
    not send a historical successful receipt after later wear or spending.
    """
    _owner(db,account_id,role_id,key)
    if type(expected_version) is not int or type(draw) is not int or not 0<=draw<1000:
        raise ValueError('Invalid equipment repair command')
    # Read the current wallet first even on replay: an expired lease cannot
    # acknowledge a historical repair through a newly owned connection.
    read_wallet(db,account_id,role_id,epoch,currency_rules)
    fingerprint,old=_request(db,role_id,settlement_id,[rules.revision,'npc_repair',key,expected_version,draw,level])
    if old:
        old['before']=EquipmentCondition(**old['before']);old['after']=EquipmentCondition(**old['after'])
        return RepairReceipt(**old)
    before=load(db,account_id,role_id,key,rules)
    if before.version!=expected_version:raise ValueError('Equipment condition version mismatch')
    after,cost,success=rules.repair(before,level,draw)
    apply_currency(db,account_id,role_id,epoch,CurrencyChange('equipment-repair:'+settlement_id,
        'equipment_repair',f'item:{key}',(('cash',-cost),)),currency_rules)
    result=RepairReceipt(settlement_id,key,before,after,cost,success)
    _write(db,role_id,key,settlement_id,fingerprint,after,asdict(result))
    return result
