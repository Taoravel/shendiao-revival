"""Admitted soul wear/removal joins assets/map/receipts in one role transaction.

Startup-only schema; no connections, commits or sends. The role owner supplies
real current clearance and synchronous source/finalization. All errors require
outer rollback, including late encoding. Original wire has no retry identity.
"""
from dataclasses import dataclass,asdict,replace
import hashlib
import inspect
import json
import struct
from inventory import AssetChange,InventorySnapshot,ItemState
from pet_soul_actions import (SoulActionRules,SoulActionAuthority,plan_wear,plan_remove,removal_materials,REVISION)
from pet_soul_storage import SoulBasis
from pet_soul_item_storage import OrbBasis,OrbSource
from pet_soul_protocol import full_refresh
from pet_soul_bag import current_messages
from role_resource_plan import ResourceRules,RoleResources
from role_equipment import EquipmentAttributeRules
from role_resource_storage import read_role_resources
from role_equipment_storage import current_resource_projection_source
import pet_soul_storage as souls
import pet_soul_item_storage as orbs


@dataclass(frozen=True)
class SoulWearCommand:
    request_id: str
    policy: str
    account_id: int
    before: SoulBasis
    orb: OrbBasis
    authority: SoulActionAuthority
    deadline_ms: int

    def __post_init__(self):
        if (type(self.request_id) is not str or not 1<=len(self.request_id.encode('utf-8'))<=120
                or self.policy!=REVISION or type(self.account_id) is not int or self.account_id<=0
                or type(self.deadline_ms) is not int or not 0<=self.deadline_ms<2**63-1
                or type(self.before) is not SoulBasis or type(self.orb) is not OrbBasis
                or type(self.authority) is not SoulActionAuthority
                or self.account_id!=self.before.account_id or self.account_id!=self.orb.account_id
                or self.before.profile.role_id!=self.orb.source.role_id
                or (self.authority.role_id,self.authority.pet_id)!=(self.before.profile.role_id,self.before.profile.pet_id)):
            raise ValueError('Complete frozen admitted soul wear command required')


@dataclass(frozen=True)
class SoulRemoveCommand:
    request_id: str
    policy: str
    account_id: int
    before: SoulBasis
    slot: int
    tools: tuple
    authority: SoulActionAuthority
    deadline_ms: int

    def __post_init__(self):
        if (type(self.request_id) is not str or not 1<=len(self.request_id.encode('utf-8'))<=120
                or self.policy!=REVISION or type(self.account_id) is not int or self.account_id<=0
                or type(self.deadline_ms) is not int or not 0<=self.deadline_ms<2**63-1
                or type(self.before) is not SoulBasis or type(self.authority) is not SoulActionAuthority
                or self.account_id!=self.before.account_id or type(self.slot) is not int or not 1<=self.slot<=5
                or type(self.tools) is not tuple or len(self.tools)>40 or any(type(i) is not ItemState for i in self.tools)
                or (self.authority.role_id,self.authority.pet_id)!=(self.before.profile.role_id,self.before.profile.pet_id)):
            raise ValueError('Complete frozen admitted soul removal command required')


@dataclass(frozen=True)
class SoulActionResult:
    request_id: str
    operation: str
    slot: int
    replayed: bool
    basis: SoulBasis
    snapshot: InventorySnapshot
    authority: SoulActionAuthority
    effects: tuple
    messages: tuple
    returned_item_key: int | None
    resources: RoleResources


@dataclass(frozen=True)
class SoulResourceRules:
    """Selected real role source policy, including an optional gem carrier.

    The source verifier is shared, while full numeric projection remains in
    the trusted finalizer appropriate to that actual stored equipment policy.
    """
    resource_rules: ResourceRules
    equipment_rules: EquipmentAttributeRules

    def __post_init__(self):
        if type(self.resource_rules) is not ResourceRules or type(self.equipment_rules) is not EquipmentAttributeRules:
            raise ValueError('Frozen selected role resource/equipment policies required')


def prepare(db):
    """Startup only, after original Inventory and both source stores."""
    db.execute('''CREATE TABLE IF NOT EXISTS pet_soul_action_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
        policy TEXT NOT NULL,operation TEXT NOT NULL,fingerprint TEXT NOT NULL,
        result TEXT NOT NULL,PRIMARY KEY(role_id,request_id))''')


def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def _fingerprint(command):return hashlib.sha256(_json(asdict(command)).encode('utf-8')).hexdigest()


def _identity(command):return 'pet-soul-action:'+hashlib.sha256(command.request_id.encode('utf-8')).hexdigest()


def _synchronous(result):
    if inspect.isawaitable(result):
        if inspect.iscoroutine(result):result.close()
        raise ValueError('Soul owner callbacks must complete synchronously in the caller transaction')
    return result


def _authority(db,inventory,pet_id,reader,material_keys=()):
    if not callable(reader):raise ValueError('Actual current soul clearance reader required')
    state=_synchronous(reader(db,inventory,pet_id,material_keys))
    if (type(state) is not SoulActionAuthority or state.role_id!=inventory.role_id
            or state.pet_id!=pet_id or state.login_epoch!=inventory.epoch
            or tuple(key for key,_ in state.material_flags)!=material_keys):
        raise ValueError('Missing, partial or stale current soul clearance')
    return state


def _tools(snapshot):return tuple(i for i in snapshot.items if i.template_id==38045 and i.equipment_slot is None)


def _deadline(deadline_ms,clock_ms):
    if type(deadline_ms) is not int or not 0<=deadline_ms<2**63-1 or not callable(clock_ms):
        raise ValueError('Trusted server monotonic-millisecond deadline and clock required')
    now=_synchronous(clock_ms())
    if type(now) is not int or not 0<=now<2**63-1 or now>deadline_ms:
        raise ValueError('Soul action admission/execution deadline expired or unknown')


def admit(db,inventory,rules,request_id,kind,payload,*,deadline_ms,clock_ms,authority_reader):
    """Freeze a new server identity once; a new identical packet is a new intent."""
    snapshot=inventory.immutable_snapshot_transaction(db)
    _deadline(deadline_ms,clock_ms)
    if type(rules) is not SoulActionRules or type(kind) is not int or type(payload) is not bytes:
        raise ValueError('Exact original soul action request required')
    if kind==0xc03ff and len(payload)==16:
        key,count,pet=struct.unpack('>iiq',payload)
        if key<=0 or count!=1 or not 0<pet<=0x7fffffff:raise ValueError('One carried orb and positive owned pet required')
        slot=None
    elif kind==0xc0805 and len(payload)==8:
        pet,slot=struct.unpack('>ii',payload)
        if pet<=0 or not 1<=slot<=5:raise ValueError('Positive owned pet and exact soul slot required')
    else:raise ValueError('Exact ordinary soul CUseItem or removal request required')
    before=souls.read(db,inventory,rules.orbs.souls,pet)
    if before is None:raise ValueError('Complete current pet soul source required')
    progress=before.pet.progress
    if (progress is None or type(progress.state.hp) is not int or type(progress.state.mp) is not int
            or not 0<=progress.state.hp<=progress.attributes.max_hp
            or not 0<=progress.state.mp<=progress.attributes.max_mp):
        raise ValueError('Known valid settled pet resource source required before soul admission')
    if kind==0xc03ff:
        orb=orbs.read(db,inventory,rules.orbs,key)
        if orb is None:raise ValueError('Complete current carried orb source required')
        authority=_authority(db,inventory,pet,authority_reader)
        command=SoulWearCommand(request_id,rules.revision,inventory.account_id,before,orb,authority,deadline_ms)
        plan_wear(rules,before,orb,authority)
    else:
        tools=_tools(snapshot);materials=removal_materials(rules,before,slot,tools)
        keys=tuple(sorted(key for key,_ in materials.debits))
        authority=_authority(db,inventory,pet,authority_reader,keys)
        command=SoulRemoveCommand(request_id,rules.revision,inventory.account_id,before,slot,tools,authority,deadline_ms)
        plan_remove(rules,before,slot,tools,authority)
    _fingerprint(command)  # Validate serializable frozen intent before accepting it.
    return command


def _result_json(command,selected,returned_key):
    data={'slot':selected.slot,'after':asdict(selected.after)}
    if type(command) is SoulWearCommand:data['source_item_key']=command.orb.item.id
    else:data['returned_item_key']=returned_key
    return _json(data)


def _resources(db,inventory,context):
    value=read_role_resources(db,inventory.account_id,inventory.role_id,inventory.epoch,context.resource_rules)
    actual=current_resource_projection_source(db,inventory.account_id,inventory.role_id,inventory.epoch,context.equipment_rules)
    if value.caps.source!=actual:raise ValueError('Soul action requires an exact current sole role resource source')
    return value


def apply(db,inventory,rules,currency_rules,command,*,resource_context,clock_ms,authority_reader,precommit):
    """Actual current-owner settlement. Caller must roll back on ANY exception.

    precommit joins the real inventory-resource source hook/final projections;
    it cannot commit or await. Paid branches only read current assets/profiles.
    Result.effects is current raw modifiers, not a complete pet battle formula.
    """
    snapshot=inventory.immutable_snapshot_transaction(db)
    if (type(rules) is not SoulActionRules or type(command) not in (SoulWearCommand,SoulRemoveCommand)
            or command.policy!=rules.revision or command.account_id!=inventory.account_id
            or command.before.profile.role_id!=inventory.role_id
            or type(resource_context) is not SoulResourceRules
            or not callable(clock_ms)
            or not callable(precommit) or inspect.iscoroutinefunction(precommit)):
        raise ValueError('Owned soul command and synchronous current-source finalizer required')
    resources_before=_resources(db,inventory,resource_context)
    wear=type(command) is SoulWearCommand;operation='wear' if wear else 'remove'
    selected=(plan_wear(rules,command.before,command.orb,command.authority) if wear else
        plan_remove(rules,command.before,command.slot,command.tools,command.authority))
    change=AssetChange(_identity(command),grants=selected.grants,debits=selected.debits)
    fingerprint=_fingerprint(command)
    returned_key=None
    old=db.execute('SELECT policy,operation,fingerprint,result FROM pet_soul_action_receipts '
        'WHERE role_id=? AND request_id=?',(inventory.role_id,command.request_id)).fetchone()
    asset=db.execute('SELECT 1 FROM inventory_settlements WHERE role_id=? AND settlement_id=?',
        (inventory.role_id,change.settlement_id)).fetchone()
    if old is not None or asset is not None:
        if old is None or asset is None:raise ValueError('Incomplete soul/action asset receipts')
        if not wear:
            returned_key=json.loads(old[3]).get('returned_item_key')
            if type(returned_key) is not int or not 0<returned_key<=0x7fffffff:
                raise ValueError('Invalid original returned orb receipt key')
        if old!=(rules.revision,operation,fingerprint,_result_json(command,selected,returned_key)):
            raise ValueError('Conflicting or incomplete soul/action asset receipts')
        if inventory.apply_settlement(db,change).created_pet_ids:
            raise ValueError('Soul asset receipt cannot contain created pets')
        replayed=True
    else:
        _deadline(command.deadline_ms,clock_ms)
        keys=() if wear else tuple(sorted(key for key,_ in selected.debits))
        if (command.authority.login_epoch!=inventory.epoch
                or souls.read(db,inventory,rules.orbs.souls,command.before.profile.pet_id)!=command.before
                or _authority(db,inventory,command.authority.pet_id,authority_reader,keys)!=command.authority
                or wear and orbs.read(db,inventory,rules.orbs,command.orb.item.id)!=command.orb
                or not wear and _tools(snapshot)!=command.tools):
            raise ValueError('Admitted soul source, tools or clearance changed')
        # The map CAS fences the original inventory revision. Asset debits
        # happen AFTER it, preserving the public source Interface's contract.
        saved=souls.replace_profile(db,inventory,rules.orbs.souls,command.before,selected.after)
        if wear:
            current_orb=orbs.read(db,inventory,rules.orbs,command.orb.item.id)
            if current_orb!=replace(command.orb,inventory_revision=saved.inventory_revision):
                raise ValueError('Orb changed after the immediate map CAS')
        elif _tools(inventory.immutable_snapshot_transaction(db))!=command.tools:
            raise ValueError('Removal tools changed after the immediate map CAS')
        if inventory.apply_settlement(db,change).created_pet_ids:
            raise ValueError('Soul action cannot create pets')
        if not wear:
            old_keys={i.id for i in snapshot.items}
            created=tuple(i for i in inventory.immutable_snapshot_transaction(db).items if i.id not in old_keys)
            if (len(created)!=1 or created[0].template_id!=selected.grants[0][0]
                    or created[0].quantity!=1 or created[0].binding!=1):
                raise ValueError('Expected exactly one new nonstacking returned orb')
            item=created[0];returned_key=item.id
            source=OrbSource(inventory.role_id,item.id,item.template_id,0,rules.orbs.revision,
                'soul-removal:'+hashlib.sha256(command.request_id.encode('utf-8')).hexdigest(),
                selected.returned_tips,selected.returned_nonbinding_flags,selected.retained_raw6)
            orbs.initialize(db,inventory,rules.orbs,source,'explicit_known_orb_instance')
        db.execute('INSERT INTO pet_soul_action_receipts VALUES(?,?,?,?,?,?)',
            (inventory.role_id,command.request_id,rules.revision,operation,fingerprint,_result_json(command,selected,returned_key)))
        replayed=False
    snapshot=inventory.immutable_snapshot_transaction(db)
    _synchronous(precommit(db,inventory,snapshot,replayed=replayed,request_id=command.request_id))
    resources=_resources(db,inventory,resource_context)
    if (resources.version,resources.hp,resources.mp,resources.caps.hp_max,resources.caps.mp_max)!=(
            resources_before.version,resources_before.hp,resources_before.mp,resources_before.caps.hp_max,resources_before.caps.mp_max):
        raise ValueError('Soul source finalization cannot change human resources or caps')
    if not replayed:_deadline(command.deadline_ms,clock_ms)
    current=souls.read(db,inventory,rules.orbs.souls,command.before.profile.pet_id)
    if current is None or not replayed and current.profile!=selected.after:
        raise ValueError('Current settled soul map is missing or changed by finalization')
    current_authority=_authority(db,inventory,current.profile.pet_id,authority_reader)
    if not replayed and current_authority!=replace(command.authority,material_flags=()):
        raise ValueError('Soul clearance changed during finalization')
    effects=rules.orbs.souls.effects(current.pet.template_id,current.profile,current_authority.known_flag22)
    messages=current_messages(db,inventory,rules.orbs,currency_rules)+(full_refresh(current.profile),)
    if not replayed:_deadline(command.deadline_ms,clock_ms)
    return SoulActionResult(command.request_id,operation,selected.slot,replayed,current,
        inventory.immutable_snapshot_transaction(db),current_authority,effects,messages,returned_key,resources)
