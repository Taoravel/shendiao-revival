"""Ordinary gem composition: original rows, explicit local outcome decisions."""
from dataclasses import dataclass,asdict
import hashlib
import inspect
import json
import struct
from types import MappingProxyType
from inspect_client import OUT
from inventory import ItemState,AssetChange
import role_stamina


def decode(kind,payload):
    """Actual CCombineGem contains exactly two positive signed32 instance keys."""
    if type(kind) is not int or kind!=0xc0424 or type(payload) is not bytes or len(payload)!=8:
        raise ValueError('Exact ordinary CCombineGem required')
    keys=struct.unpack('>ii',payload)
    if min(keys)<=0:raise ValueError('Owned positive gem instance keys required')
    return keys


@dataclass(frozen=True)
class GemRow:
    template: int
    level: int
    next_template: int
    success_percent: int


@dataclass(frozen=True)
class CompositionRules:
    revision: str
    gems: object
    skill_rates: tuple

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/equipment-gem-composition-v1.json').read_text(encoding='utf-8'))
        if (policy['revision']!='2026-10-24.gem-composition.1' or policy['skill_id']!=600005
                or policy['stamina_attribute']!=450 or policy['stamina_maximum_attribute']!=630
                or policy['restricted_flags_mask']!=160 or policy['draw_range']!=10000):
            raise ValueError('Gem composition policy requires explicit implementation review')
        def rows(name):
            return {int(r['attributes']['id']):r['attributes'] for r in
                json.loads((OUT/f'catalogs/knight.gsp.item.{name}.json').read_text(encoding='utf-8'))}
        items,effects,rates=rows('citemattr'),rows('cgemeffect'),rows('cgemcomposesuccessrate')
        if set(rates)!=set(range(7)) or tuple(int(rates[i]['rate']) for i in range(7))!=(0,5,10,18,24,35,50):
            raise ValueError('Original composition study rates changed')
        gems={}
        for family in range(14):
            for level in range(1,16):
                key=35000+family+13*(level-1) if family<13 else 35199+level
                item,effect=items[key],effects[key]
                nxt=(key+13 if family<13 else key+1) if level<15 else 0
                if (int(item['itemtypeid'])!=5 or int(item['level'])!=level or int(item['maxNum'])!=30
                        or int(effect['genegemid'])!=nxt or int(effect['money'])!=0
                        or int(effect['successrate'])!=(100,95,90,85,80,75,70,65,60,55,50,50,50,50,50)[level-1]):
                    raise ValueError('Original ordinary gem chain changed')
                gems[key]=GemRow(key,level,nxt,int(effect['successrate']))
        return cls(policy['revision'],MappingProxyType(gems),tuple(int(rates[i]['rate']) for i in range(7)))


@dataclass(frozen=True)
class CompositionPlan:
    success: bool
    output_template: int | None
    output_binding: int | None
    stamina_cost: int
    success_percent: int
    debits: tuple


def plan(rules,first,second,nonbinding_flags,skill_level,draw):
    """Pure result; inputs are server-owned immutable material snapshots."""
    if (type(skill_level) is not int or not 0<=skill_level<=6
            or type(draw) is not int or not 0<=draw<10000
            or type(nonbinding_flags) is not tuple or len(nonbinding_flags)!=2
            or any(type(v) is not int or not 0<=v<=254 or v&1 for v in nonbinding_flags)):
        raise ValueError('Known study level, captured draw and nonbinding flags required')
    for item,flags in zip((first,second),nonbinding_flags):
        if (type(item) is not ItemState or item.template_id not in rules.gems
                or any(type(v) is not int for v in (item.id,item.role_id,item.quantity,item.binding,item.slot))
                or not 0<item.id<=0x7fffffff or item.role_id<=0 or not 1<=item.quantity<=30
                or item.equipment_slot is not None or item.slot<0 or item.binding not in (0,1)
                or item.quality is not None or item.condition is not None or item.detail is not None
                or flags):
            raise ValueError('Ordinary carried known unrestricted gem required')
    row=rules.gems[first.template_id]
    if first.role_id!=second.role_id or first.template_id!=second.template_id or not row.next_template:
        raise ValueError('Two same ordinary gems below level15 required')
    same=first.id==second.id
    if same and (first!=second or nonbinding_flags[0]!=nonbinding_flags[1] or first.quantity<2):
        raise ValueError('Same-key composition requires one consistent stack of at least two')
    percent=min(100,row.success_percent+rules.skill_rates[skill_level])
    success=draw<percent*100
    debits=(((first.id,2),) if same else ((first.id,1),(second.id,1))) if success else ((second.id,1),)
    return CompositionPlan(success,row.next_template if success else None,
        max(first.binding,second.binding) if success else None,5*(row.level+6),percent,debits)


@dataclass(frozen=True)
class CompositionStudy:
    """Trusted role skill owner's current600005 basis; missing is not level0."""
    role_id: int
    login_epoch: int | str
    policy: str
    version: int
    level: int
    skill_id: int = 600005
    namespace: str = 'zaxue'

    def __post_init__(self):
        if (type(self.role_id) is not int or self.role_id<=0
                or not (type(self.login_epoch) is int and self.login_epoch>0
                    or type(self.login_epoch) is str and 0<len(self.login_epoch)<=160)
                or type(self.policy) is not str or not 1<=len(self.policy)<=160
                or type(self.version) is not int or not 0<=self.version<2**63-1
                or type(self.level) is not int or not 0<=self.level<=6
                or type(self.skill_id) is not int or self.skill_id!=600005 or self.namespace!='zaxue'):
            raise ValueError('Complete current composition study basis required')


@dataclass(frozen=True)
class CompositionCommand:
    request_id: str
    policy: str
    account_id: int
    inventory_revision: int
    first: ItemState
    second: ItemState
    flags: tuple
    study: CompositionStudy
    stamina: role_stamina.StaminaState
    draw: int

    def __post_init__(self):
        if (type(self.request_id) is not str or not 1<=len(self.request_id.encode('utf-8'))<=120
                or type(self.policy) is not str or not self.policy
                or type(self.account_id) is not int or self.account_id<=0
                or type(self.inventory_revision) is not int or not 0<=self.inventory_revision<2**63-1
                or type(self.first) is not ItemState or type(self.second) is not ItemState
                or type(self.study) is not CompositionStudy or type(self.stamina) is not role_stamina.StaminaState
                or self.first.role_id!=self.second.role_id or self.first.role_id!=self.study.role_id
                or self.first.role_id!=self.stamina.role_id
                or type(self.flags) is not tuple or len(self.flags)!=2
                or any(type(x) is not int or not 0<=x<=254 or x&1 for x in self.flags)
                or type(self.draw) is not int or not 0<=self.draw<10000):
            raise ValueError('Invalid frozen admitted gem command')
        # ItemState is shared and does not enforce primitive immutability itself.
        for item in (self.first,self.second):
            if (any(type(x) is not int for x in (item.id,item.role_id,item.template_id,item.quantity,item.slot,item.binding))
                    or item.equipment_slot is not None or item.quality is not None
                    or item.condition is not None or item.detail is not None):
                raise ValueError('Frozen primitive ordinary material required')


@dataclass(frozen=True)
class CompositionResult:
    request_id: str
    success: bool
    replayed: bool
    snapshot: object
    stamina: role_stamina.StaminaState
    messages: tuple


def prepare(db):
    """Startup only. No DDL or configuration reads occur during commands."""
    rules=CompositionRules.load()
    db.execute('''CREATE TABLE IF NOT EXISTS inventory_gem_materials (
        role_id INTEGER NOT NULL REFERENCES roles(id),item_key INTEGER NOT NULL,
        policy TEXT NOT NULL,origin TEXT NOT NULL,stamp TEXT NOT NULL,flags INTEGER NOT NULL,
        PRIMARY KEY(role_id,item_key))''')
    db.execute('''CREATE TABLE IF NOT EXISTS equipment_gem_composition_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
        policy TEXT NOT NULL,fingerprint TEXT NOT NULL,result TEXT NOT NULL,
        PRIMARY KEY(role_id,request_id))''')
    # Every existing Inventory writer is observed. Even consume+refill back to
    # the same quantity permanently invalidates unknown incoming provenance;
    # only this module can explicitly restore a known resulting material.
    db.execute('''CREATE TRIGGER IF NOT EXISTS inventory_gem_materials_invalidate_update
        AFTER UPDATE OF template_id,quantity,binding,quality ON inventory_items
        BEGIN DELETE FROM inventory_gem_materials WHERE role_id=OLD.role_id AND item_key=OLD.id; END''')
    db.execute('''CREATE TRIGGER IF NOT EXISTS inventory_gem_materials_invalidate_delete
        AFTER DELETE ON inventory_items
        BEGIN DELETE FROM inventory_gem_materials WHERE role_id=OLD.role_id AND item_key=OLD.id; END''')
    return rules


def _stamp(item):
    # Quantity/binding/template/quality changes outside this writer invalidate
    # the source. A harmless slot move retains flags, but admission still CASes
    # the full ItemState and inventory revision.
    return json.dumps((item.template_id,item.quantity,item.binding,item.quality),separators=(',',':'))


def _item(snapshot,key):
    found=next((i for i in snapshot.items if i.id==key),None)
    if found is None:raise ValueError('Current owned gem unavailable')
    return found


def _flags(db,inventory,rules,item):
    row=db.execute('SELECT policy,origin,stamp,flags FROM inventory_gem_materials WHERE role_id=? AND item_key=?',
        (inventory.role_id,item.id)).fetchone()
    if (row is None or row[0]!=rules.revision or row[1] not in
            ('explicit_known_gem_instance','composition_result','composition_remainder') or row[2]!=_stamp(item)
            or type(row[3]) is not int or not 0<=row[3]<=254 or row[3]&1):
        raise ValueError('Complete current gem flags source required; no implicit legacy0')
    return row[3]


def initialize_material(db,inventory,rules,key,nonbinding_flags,origin):
    """Explicit known import, never authorized by an ordinary client packet."""
    snap=inventory.immutable_snapshot_transaction(db)
    if type(key) is not int or not 0<key<=0x7fffffff:raise ValueError('Positive owned key required')
    item=_item(snap,key)
    if (origin!='explicit_known_gem_instance' or item.template_id not in rules.gems
            or item.equipment_slot is not None or item.quality is not None
            or type(nonbinding_flags) is not int or not 0<=nonbinding_flags<=254 or nonbinding_flags&1):
        raise ValueError('Explicit complete ordinary gem import required')
    value=(rules.revision,origin,_stamp(item),nonbinding_flags)
    old=db.execute('SELECT policy,origin,stamp,flags FROM inventory_gem_materials WHERE role_id=? AND item_key=?',
        (inventory.role_id,key)).fetchone()
    if old:
        if old!=value:raise ValueError('Existing gem source cannot be silently reset')
    else:
        db.execute('INSERT INTO inventory_gem_materials VALUES(?,?,?,?,?,?)',(inventory.role_id,key,*value))
    return item


def _study(db,inventory,reader):
    if not callable(reader):raise ValueError('Authoritative current role skill reader required')
    state=reader(db,inventory)
    if (type(state) is not CompositionStudy or state.role_id!=inventory.role_id
            or state.login_epoch!=inventory.epoch):
        raise ValueError('Missing, partial or stale composition study source')
    return state


def admit(db,inventory,rules,stamina_rules,request_id,payload,draw,study_source):
    """Freeze once at trusted owner admission; raw wire has no retry ID or RNG.

    The caller retains this exact command across retries. New identical packets
    need a new server ID/draw; they are not deduplicated by payload equality.
    """
    first_key,second_key=decode(0xc0424,payload)
    snap=inventory.immutable_snapshot_transaction(db)
    first,second=_item(snap,first_key),_item(snap,second_key)
    flags=(_flags(db,inventory,rules,first),_flags(db,inventory,rules,second))
    study=_study(db,inventory,study_source)
    stamina=role_stamina.read(db,inventory,stamina_rules)
    command=CompositionCommand(request_id,rules.revision,inventory.account_id,snap.inventory_revision,
        first,second,flags,study,stamina,draw)
    selected=plan(rules,first,second,flags,study.level,draw)
    if stamina.value<selected.stamina_cost:raise ValueError('Insufficient stamina')
    return command


def _fingerprint(command):
    return hashlib.sha256(json.dumps(asdict(command),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _asset(command,result):
    return AssetChange('gem-compose:'+command.request_id,
        grants=((result.output_template,1,result.output_binding),) if result.success else (),debits=result.debits)


def _save_known_result(db,inventory,rules,item,origin):
    db.execute('INSERT INTO inventory_gem_materials VALUES(?,?,?,?,?,?) '
        'ON CONFLICT(role_id,item_key) DO UPDATE SET policy=excluded.policy,origin=excluded.origin,stamp=excluded.stamp,flags=excluded.flags',
        (inventory.role_id,item.id,rules.revision,origin,_stamp(item),0))


def apply(db,inventory,rules,stamina_rules,command,*,study_source,precommit=None):
    """Join current lease transaction. Caller rolls back on ANY exception.

    precommit follows the existing inventory source contract and must supply
    the root's single current resource synchronization before external commit.
    Results contain encoded logical messages, never encrypted network output.
    """
    snapshot=inventory.immutable_snapshot_transaction(db)
    if (type(command) is not CompositionCommand or command.account_id!=inventory.account_id
            or command.first.role_id!=inventory.role_id or command.policy!=rules.revision):
        raise ValueError('Foreign or incompatible gem command')
    selected=plan(rules,command.first,command.second,command.flags,command.study.level,command.draw)
    change=_asset(command,selected)
    fingerprint=_fingerprint(command)
    old=db.execute('SELECT policy,fingerprint,result FROM equipment_gem_composition_receipts WHERE role_id=? AND request_id=?',
        (inventory.role_id,command.request_id)).fetchone()
    asset=db.execute('SELECT 1 FROM inventory_settlements WHERE role_id=? AND settlement_id=?',
        (inventory.role_id,change.settlement_id)).fetchone()
    encoded_result=json.dumps(asdict(selected),sort_keys=True,separators=(',',':'))
    if old is not None or asset is not None:
        if old!=(rules.revision,fingerprint,encoded_result) or asset is None:
            raise ValueError('Conflicting or incomplete gem/asset receipts')
        # The actual inventory writer alone verifies its fingerprint and parses
        # its receipt. The presence guard above prevents an orphan from being
        # interpreted as a fresh asset settlement by that public interface.
        if inventory.apply_settlement(db,change).created_pet_ids:
            raise ValueError('Gem settlement cannot contain created pets')
        replayed=True
    else:
        if (command.study.login_epoch!=inventory.epoch or snapshot.inventory_revision!=command.inventory_revision
                or _item(snapshot,command.first.id)!=command.first or _item(snapshot,command.second.id)!=command.second
                or (_flags(db,inventory,rules,command.first),_flags(db,inventory,rules,command.second))!=command.flags
                or _study(db,inventory,study_source)!=command.study
                or role_stamina.read(db,inventory,stamina_rules)!=command.stamina):
            raise ValueError('Gem admission source changed')
        if selected.success:
            # Existing generic grants merge by template/binding/quality. Refuse
            # unknown source stacks rather than launder their unknown flags.
            for item in snapshot.items:
                if (item.template_id==selected.output_template and item.binding==selected.output_binding
                        and item.equipment_slot is None and item.quality is None and item.quantity<30):
                    if _flags(db,inventory,rules,item)!=0:raise ValueError('Restricted output merge target')
        role_stamina.consume(db,inventory,stamina_rules,selected.stamina_cost)
        inventory.apply_settlement(db,change)
        current=inventory.immutable_snapshot_transaction(db)
        old_items={i.id:i for i in snapshot.items}
        current_items={i.id:i for i in current.items}
        for key,_ in selected.debits:
            if key not in current_items:
                db.execute('DELETE FROM inventory_gem_materials WHERE role_id=? AND item_key=?',(inventory.role_id,key))
            else:
                _save_known_result(db,inventory,rules,current_items[key],'composition_remainder')
        for item in current.items:
            if item.id not in old_items or item.quantity!=old_items[item.id].quantity and item.template_id==selected.output_template:
                _save_known_result(db,inventory,rules,item,'composition_result')
        db.execute('INSERT INTO equipment_gem_composition_receipts VALUES(?,?,?,?,?)',
            (inventory.role_id,command.request_id,rules.revision,fingerprint,encoded_result))
        replayed=False
    if precommit is not None:
        if not callable(precommit):raise ValueError('Synchronous trusted source callback required')
        synchronized=precommit(db,inventory,inventory.immutable_snapshot_transaction(db),replayed=replayed)
        if inspect.isawaitable(synchronized):
            if inspect.iscoroutine(synchronized):synchronized.close()
            raise ValueError('Gem precommit must complete synchronously in this transaction')
    current=inventory.immutable_snapshot_transaction(db)
    stamina=role_stamina.read(db,inventory,stamina_rules)
    if stamina is None:raise ValueError('Current paid stamina source is unknown')
    messages=tuple(inventory.equipment_bag_messages(db,inventory.epoch))+(role_stamina.refresh(stamina),)
    return CompositionResult(command.request_id,selected.success,replayed,current,stamina,messages)
