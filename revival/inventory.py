"""Owned inventory state and confirmed native container queries.

Capacities are local design values. No automatic rewards or original stat claims.
Native layouts are verified offline; carried-item semantics still need UI QA.
"""
from contextlib import closing
from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
import struct
import time
from types import MappingProxyType
from inspect_client import OUT
from wire import compact, octets, read_octets, NeedMoreData
from item_effects import Consumables, VitalState
from pet_growth import GrowthRules
from pet_protocol import (growth_wire_float,LEARN_SKILL_BOOK,decode_skill_book_request,
                          QUERY_SKILL_PROGRESS,skill_progress_message,game_time_message,
                          SUPER_RETURN_QUERY,SUPER_RETURN_SUBMIT,SUPER_RETURN_CLEAR,decode_super_return_pet_request,cake_notice,
                          pet_removal_message,PET_EVOLVE,decode_pet_evolution_request,evolution_notice,
                          stone_attribute_map,stone_attributes_message,stone_notice)
import pet_growth_store
import pet_blood
import pet_lifetime_food
import pet_care
import pet_traits
import pet_cake
import pet_super_return
import pet_ordinary_return
import pet_cake_effects
import pet_evolution
import pet_stones
import pet_stone_items
from pet_score import ScoreRules
import pet_battle_care
import pet_skills
import pet_flags
import pet_skill_progress
import pet_skill_expiry
import equipment_condition
import equipment_detail
from role_attribute_storage import read_attribute_snapshot, update_role_vitals
from item_effect_protocol import role_resource_refresh
from equipment_protocol import REQUEST_ENDURES,endurance_refresh,maximum_refresh
from currency import read_wallet,WalletNotInitialized

QUERY_BAG = 0xc03f2
BAG_INFO = 0xc03f3
QUERY_PETS = 0xc07de
PET_INFO = 0xc07df
RENAME_PET = 0xc07e2
FIGHT_PET = 0xc07d8
REST_PET = 0xc07da
MOVE_ITEM = 0xc03f7
EQUIP_ITEM = 0xc03f5
UNEQUIP_ITEM = 0xc03f6
ADD_PET_POINT = 0xc07d7
REFRESH_PET = 0xc07d5
REFRESH_PET_EXP = 0xc07d6
ARRANGE_BAG = 0xc03f4
FREE_PET = 0xc07e4
REMOVE_PET = 0xc07dd
USE_ITEM = 0xc03ff
ITEM_TIPS = 0xc03fd
ITEM_TIPS_REPLY = 0xc03fe
INVENTORY_TYPES = {QUERY_BAG, QUERY_PETS, RENAME_PET, FIGHT_PET, REST_PET, MOVE_ITEM, EQUIP_ITEM, UNEQUIP_ITEM, ADD_PET_POINT, ARRANGE_BAG, FREE_PET, USE_ITEM, ITEM_TIPS, REQUEST_ENDURES, LEARN_SKILL_BOOK, QUERY_SKILL_PROGRESS,PET_EVOLVE}
INVENTORY_CURRENT_MUTATION_TYPES = frozenset({MOVE_ITEM,ARRANGE_BAG,RENAME_PET,
    FIGHT_PET,REST_PET,FREE_PET,USE_ITEM,ADD_PET_POINT,PET_EVOLVE})


class InventoryNotReady(ValueError):
    """Known operation whose native response semantics are still unconfirmed."""


def _valid_epoch(epoch):
    # Preserve task-domain opaque tokens exactly. Legacy integer identities
    # must also fit the shared storage adapter's signed63-bit lease contract.
    return ((type(epoch) is str and 1<=len(epoch)<=128)
            or (type(epoch) is int and 0<epoch<2**63))


def _server_clock_ms():return time.time_ns()//1000000


@dataclass(frozen=True)
class InventoryConfig:
    policy: object
    items: object
    pets: object
    equipment: object
    equipment_rules: object
    shape_roles: object
    consumables: object
    growth_rules: object
    pet_profiles: object
    care_rules: object
    condition_rules: object
    detail_rules: object
    skill_rules: object
    flag_rules: object
    blood_rules: object
    shape_sexes: object
    toxic_food_rules: object
    battle_care_rules: object
    trait_rules: object
    cake_rules: object
    return_rules: object
    score_rules: object
    ordinary_return_rules: object
    cake_effect_rules: object
    evolution_rules: object


@dataclass(frozen=True)
class AssetChange:
    """Immutable command to pass to the role owner's persistence worker."""
    settlement_id: str
    grants: tuple = ()       # ((template_id, quantity[, binding[, quality]]), ...)
    debits: tuple = ()       # ((owned_item_key, positive_quantity), ...)
    pets: tuple = ()         # (template_id, ...)

    def __post_init__(self):
        if (type(self.settlement_id) is not str or not 1 <= len(self.settlement_id) <= 160
                or type(self.grants) is not tuple or type(self.debits) is not tuple
                or type(self.pets) is not tuple
                or any(type(x) is not tuple or len(x) not in (2,3,4) or any(type(v) is not int for v in x)
                       or (len(x) >= 3 and x[2] not in (0,1))
                       or (len(x) == 4 and not 0 <= x[3] <= 0x7fffffff) for x in self.grants)
                or any(type(x) is not tuple or len(x) != 2 or any(type(v) is not int for v in x)
                       for x in self.debits)
                or any(type(x) is not int for x in self.pets)
                or len(self.grants) + len(self.debits) + len(self.pets) > 256):
            raise ValueError('Invalid asset settlement command')


@dataclass(frozen=True)
class AssetReceipt:
    settlement_id: str
    created_pet_ids: tuple


@dataclass(frozen=True)
class RoleConsumableReceipt:
    """Acknowledges a committed effect; replay is not a current vital snapshot."""
    settlement_id: str
    role_id: int
    item_key: int
    vitals: VitalState


@dataclass(frozen=True)
class EquipmentEvent:
    role_id: int
    login_epoch: int | str
    request_id: str
    item_key: int
    template_id: int
    equipment_slot: int
    inventory_revision: int
    replaced_item_key: object = None
    replayed: bool = False


@dataclass(frozen=True)
class UnequipEvent:
    """Removal fact, deliberately distinct from task-qualified EquipmentEvent."""
    role_id: int
    login_epoch: int | str
    request_id: str
    item_key: int
    template_id: int
    previous_equipment_slot: int
    target_slot: int
    inventory_revision: int
    replayed: bool = False


@dataclass(frozen=True)
class ItemState:
    id: int
    role_id: int
    template_id: int
    quantity: int
    slot: int
    equipment_slot: object
    binding: int = 0
    quality: object = None
    condition: object = None
    detail: object = None


@dataclass(frozen=True)
class EquipmentIdentificationBasis:
    """Server-frozen complete fixed result; no NPC permission or price implied."""
    inventory_revision: int
    item: ItemState
    detail_revision: str
    detail_origin: str
    detail_json: str

    def __post_init__(self):
        if (type(self.inventory_revision) is not int or not 0<=self.inventory_revision<2**63-1
                or type(self.item) is not ItemState
                or any(type(v) is not int for v in (self.item.id,self.item.role_id,self.item.template_id,
                    self.item.quantity,self.item.slot,self.item.binding))
                or not 0<self.item.id<=0x7fffffff or self.item.role_id<=0 or self.item.template_id<=0
                or self.item.quantity!=1 or self.item.equipment_slot is not None or self.item.slot<0
                or self.item.binding not in (0,1) or self.item.quality is not None
                    and (type(self.item.quality) is not int or not 0<=self.item.quality<=0x7fffffff)
                or type(self.item.detail) is not equipment_detail.EquipmentDetail
                or type(self.item.condition) is not equipment_condition.EquipmentCondition
                or type(self.detail_revision) is not str or type(self.detail_origin) is not str
                or type(self.detail_json) is not str):
            raise ValueError('Immutable complete carried identification basis required')


@dataclass(frozen=True)
class EquipmentIdentificationChange:
    before: EquipmentIdentificationBasis
    item: ItemState
    inventory_revision: int


@dataclass(frozen=True)
class PetState:
    id: int
    role_id: int
    template_id: int
    name: str
    fighting: int
    progress: object = None
    released: int = 0
    care: object = None
    skills: object = None
    flags: object = None
    skill_progress: object = None
    skill_expiry: object = None
    traits: object = None
    cake: object = None
    evolution: object = None


@dataclass(frozen=True)
class InventorySnapshot:
    role_id: int
    inventory_revision: int
    items: tuple
    pets: tuple
    bag_capacity: int
    pet_capacity: int


def pet_record(pet):
    # Original f89ba0 / f5df70, verified at refresh consumer: config ID, key, name.
    # Remaining unconfirmed scalars retain constructor defaults; known growth,
    # resources and care replace their independently confirmed fields below.
    tail = bytearray(178)
    progress = pet.get('progress')
    if progress is not None:
        s,a = progress.state,progress.attributes
        # Native refresh consumer 1135091..1135177 maps these exact fields to
        # attribute IDs 490/60/140/70/150/80/100/130/810/820.
        struct.pack_into('>i',tail,0,s.level)
        struct.pack_into('>9i',tail,24,s.hp,a.max_hp,s.mp,a.max_mp,
                         a.physical_attack,a.physical_defense,a.speed,a.magic_attack,a.magic_defense)
        if max(a.five_stats+(a.potential,)) > 32767:
            raise ValueError('Pet points exceed original signed-short wire fields')
        # Consumer 113517c..1135219: five stat IDs10..50, potential ID500.
        struct.pack_into('>6h',tail,61,*a.five_stats,a.potential)
        # Native SRefreshPetData copies bean+80 to internal XP; SRefreshPetExp
        # updates that same internal u64 (1133b9e..1133bae).
        struct.pack_into('>Q',tail,73,s.experience)
        # Attribute IDs540..580: original selected aptitude integers.
        profile=progress.effective_profile or progress.profile
        struct.pack_into('>5i',tail,93,*profile.aptitudes)
        if progress.blood is not None:
            struct.pack_into('>ii',tail,8,progress.blood.state.power,progress.blood.maximum_power)
        # Native refresh1135303 stores bean+ac into pet+30. The original UI
        # multiplies by1000 and truncates; preserve the persisted raw integer.
        struct.pack_into('>f',tail,117,growth_wire_float(progress.profile.growth_raw))
    care = pet.get('care')
    if care is not None:
        # Native11354fb: bean+3c -> pet+2c; original panel140df60 uses this
        # key for CPetXueMaiConfig, independently of growth and evolution.
        struct.pack_into('>i',tail,20,care.grade)
        # Native refresh: msg+98 -> attr510 and msg+b8 -> attr460.
        # Nested Pet bean begins at msg+8: loyalty+90, lifetime+b0.
        struct.pack_into('>i',tail,89,care.loyalty)
        struct.pack_into('>i',tail,121,care.lifetime)
    traits=pet.get('traits')
    if traits is not None:
        if not isinstance(traits,pet_traits.PetTraits):raise ValueError('Known frozen pet traits required')
        # Original refresh bean+38 ->attr1160 ->return UI Wuxing; bean+b4
        # is an i32 whose low byte becomes pet+29 (1 wild /2 baby).
        struct.pack_into('>i',tail,16,traits.insight)
        struct.pack_into('>i',tail,125,traits.origin)
    cake=pet.get('cake')
    if cake is not None:
        if not isinstance(cake,pet_cake.PetCakeHistory):raise ValueError('Known frozen cake history required')
        tail[155]=cake.count # original bean+111, before variable learned/expiry containers
    evolution=pet.get('evolution')
    if evolution is not None:
        if type(evolution) is not pet_evolution.PetEvolution:raise ValueError('Known frozen evolution required')
        tail[154]=evolution.stage # original bean+110 -> signed attr1440
    flags=pet.get('flags')
    if flags is not None:
        if not isinstance(flags,pet_flags.PetFlags):
            raise ValueError('Frozen known pet flags required for native refresh')
        tail[132]=flags.raw
    skills=pet.get('skills')
    expiry=pet.get('skill_expiry')
    if expiry is not None:
        if not isinstance(skills,pet_skills.PetSkills):
            raise ValueError('Known learned skills required to encode expiry')
        pet_skill_expiry.validate(expiry,skills)
        # Expand the later map first so the learned-list offset stays fixed.
        tail=(tail[:130]+compact(len(expiry.entries))
              +b''.join(struct.pack('>iq',key,deadline) for key,deadline in expiry.entries)+tail[131:])
    if skills is not None:
        if not isinstance(skills,pet_skills.PetSkills):
            raise ValueError('Frozen known pet skills required for native refresh')
        # Original Pet+b8 list count is at tail129 after all known scalar
        # fields. Preserve the remaining independent containers and tail.
        tail=(tail[:129]+compact(len(skills.learned))
              +b''.join(struct.pack('>i',key) for key in skills.learned)+tail[130:])
    if progress is not None and progress.stones is not None:
        # Final Pet+134 map, independent of the earlier variable containers.
        tail=tail[:-1]+stone_attribute_map(progress.stones)
    return struct.pack('>ii', pet['template_id'], pet['id']) + octets(pet['name'].encode('utf-16le')) + tail


def item_record(item):
    # Native copy 81a760 and consumers 10817c6/1072e70: +8 flags,
    # +10 position. Bit0 is binding (give branch168375b -> message140857).
    binding=item.get('binding',0)
    if type(binding) is not int or binding not in (0,1):
        raise ValueError('Unknown item binding flags')
    return struct.pack('>iiiiQiQiQ', item['template_id'], binding, item['id'],
                       item['slot'], 0, item['quantity'], 0, 0, 0)


class Inventory:
    """Atomic item/equipment/pet operations behind an ownership checked interface."""
    def __init__(self, accounts, account_id, role_id, config=None, *, epoch=None, currency_rules=None,
                 resource_rules=None,equipment_attribute_rules=None,clock_now_ms=None):
        if not accounts.owned_role(account_id, role_id):
            raise ValueError('Role ownership mismatch')
        self.accounts, self.account_id, self.role_id = accounts, account_id, role_id
        self.clock_now_ms=_server_clock_ms if clock_now_ms is None else clock_now_ms
        if not callable(self.clock_now_ms):raise ValueError('Trusted current Unix-ms clock callable required')
        self.epoch=epoch if epoch is not None else getattr(accounts,'epoch',None)
        self.currency_rules=currency_rules if currency_rules is not None else getattr(accounts,'currency_rules',None)
        if (resource_rules is None)!=(equipment_attribute_rules is None):
            raise ValueError('Role medicine resource/equipment rules must be explicitly paired')
        self.resource_rules,self.equipment_attribute_rules=resource_rules,equipment_attribute_rules
        # Compatibility path only. Integration must call prepare at startup and
        # inject its immutable result; role construction itself runs in a worker.
        config = config or getattr(accounts, 'inventory_config', None)
        if config is None:
            config = self.prepare(accounts)
        self.policy, self.items = config.policy, config.items
        self.pet_types, self.equipment = config.pets, config.equipment
        self.equipment_rules, self.shape_roles = config.equipment_rules, config.shape_roles
        self.shape_sexes = config.shape_sexes
        self.consumables = config.consumables
        self.growth_rules, self.pet_profiles = config.growth_rules, config.pet_profiles
        self.care_rules = config.care_rules
        self.condition_rules = config.condition_rules
        self.detail_rules = config.detail_rules
        self.skill_rules = config.skill_rules
        self.flag_rules = config.flag_rules
        self.blood_rules = config.blood_rules
        self.toxic_food_rules = config.toxic_food_rules
        self.battle_care_rules = config.battle_care_rules
        self.trait_rules = config.trait_rules
        self.cake_rules,self.return_rules,self.score_rules=config.cake_rules,config.return_rules,config.score_rules
        self.ordinary_return_rules=config.ordinary_return_rules
        self.cake_effect_rules=config.cake_effect_rules
        self.evolution_rules=config.evolution_rules
        self.stone_rules=self.growth_rules.stone_rules

    @classmethod
    def prepare(cls, accounts):
        """Startup-only configuration load/migration, before accepting sessions."""
        policy = MappingProxyType(json.loads((OUT / 'design/recovery-baseline.json').read_text(encoding='utf-8'))['inventory'])
        equip_rows = json.loads((OUT / 'catalogs/knight.gsp.item.cequipeffect.json').read_text(encoding='utf-8'))
        rules = {}
        for row in equip_rows:
            lists = row.get('lists', {})
            kinds, values = lists.get('baseEffectType', []), lists.get('baseEffect', [])
            # Six original accessory rows pad values with two zero entries but
            # supply only two attribute IDs. Zero padding contributes no effect.
            if len(values) > len(kinds) and all(int(x) == 0 for x in values[len(kinds):]):
                values = values[:len(kinds)]
            if len(kinds) != len(values):
                raise ValueError('Equipment base effects have inconsistent length')
            rules[int(row['attributes']['id'])] = (tuple(map(int, lists.get('roleNeed', []))),
                                                   tuple(zip(map(int, kinds), map(int, values))))
        roles = json.loads((OUT / 'catalogs/knight.gsp.role.createroleconfig.json').read_text(encoding='utf-8'))
        shapes = {int(row['attributes'][color]): int(row['attributes']['id'])
                  for row in roles for color in ('color1', 'color2', 'color3')}
        # Original SEnterWorld833908..83393c initializes sex from shape's last
        # digit. Freeze only the explicit original creation shapes at startup.
        sexes = {shape: 1 if 1<=shape%10<=5 else 2 for shape in shapes}
        growth_rules = GrowthRules.load()
        pet_rows = json.loads((OUT/'catalogs/knight.gsp.pet.cpetattr.json').read_text(encoding='utf-8'))
        profiles = {}
        for row in pet_rows:
            try:
                profile = growth_rules.profile(row)
            except (ValueError, KeyError):
                continue  # Special/missing baseline fields require an explicit rule.
            profiles[profile.template_id] = profile
        config = InventoryConfig(policy, cls._catalog('knight.gsp.item.citemattr'),
                                 cls._catalog('knight.gsp.pet.cpetattr'),
                                 cls._catalog('knight.gsp.item.cequipeffect'),
                                 MappingProxyType(rules), MappingProxyType(shapes), Consumables.load(),
                                 growth_rules, MappingProxyType(profiles), pet_care.CareRules.load(),
                                 equipment_condition.EquipmentRules.load(), equipment_detail.DetailRules.load(),
                                 pet_skills.SkillRules.load(),pet_flags.FlagRules.load(),pet_blood.BloodRules.load(),
                                 MappingProxyType(sexes),pet_lifetime_food.FoodRules.load(),
                                 pet_battle_care.BattleCareRules.load(),pet_traits.TraitRules.load(),
                                 pet_cake.CakeRules.load(),pet_super_return.ReturnRules.load(),ScoreRules.load(),
                                 pet_ordinary_return.OrdinaryRules.load(),pet_cake_effects.EffectRules.load(),
                                 pet_evolution.EvolutionRules.load())
        with closing(accounts.connect()) as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS inventory_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role_id INTEGER NOT NULL REFERENCES roles(id),
                    template_id INTEGER NOT NULL, quantity INTEGER NOT NULL CHECK(quantity>0),
                    slot INTEGER NOT NULL, equipment_slot INTEGER,
                    binding INTEGER NOT NULL DEFAULT 0 CHECK(binding IN (0,1)),
                    quality INTEGER CHECK(quality IS NULL OR quality>=0),
                    UNIQUE(role_id,slot), UNIQUE(role_id,equipment_slot));
                CREATE TABLE IF NOT EXISTS inventory_pets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role_id INTEGER NOT NULL REFERENCES roles(id),
                    template_id INTEGER NOT NULL, name TEXT NOT NULL,
                    fighting INTEGER NOT NULL DEFAULT 0 CHECK(fighting IN (0,1)),
                    released INTEGER NOT NULL DEFAULT 0 CHECK(released IN (0,1)));
                CREATE UNIQUE INDEX IF NOT EXISTS inventory_one_fighting_pet
                    ON inventory_pets(role_id) WHERE fighting=1;
                CREATE TABLE IF NOT EXISTS inventory_settlements (
                    role_id INTEGER NOT NULL REFERENCES roles(id),
                    settlement_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    receipt TEXT NOT NULL, PRIMARY KEY(role_id,settlement_id));
                CREATE TABLE IF NOT EXISTS inventory_versions (
                    role_id INTEGER PRIMARY KEY REFERENCES roles(id),
                    revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS inventory_role_consumables (
                    role_id INTEGER NOT NULL REFERENCES roles(id),
                    settlement_id TEXT NOT NULL, item_key INTEGER NOT NULL,
                    vitals TEXT NOT NULL, PRIMARY KEY(role_id,settlement_id));
                CREATE TABLE IF NOT EXISTS inventory_pet_consumable_commands (
                    role_id INTEGER NOT NULL REFERENCES roles(id),settlement_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,PRIMARY KEY(role_id,settlement_id));
                CREATE TABLE IF NOT EXISTS inventory_equipment_commands (
                    role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,event TEXT NOT NULL,PRIMARY KEY(role_id,request_id));
            ''')
            if 'binding' not in {r[1] for r in db.execute('PRAGMA table_info(inventory_items)')}:
                db.execute('ALTER TABLE inventory_items ADD COLUMN binding INTEGER NOT NULL DEFAULT 0 CHECK(binding IN (0,1))')
            if 'quality' not in {r[1] for r in db.execute('PRAGMA table_info(inventory_items)')}:
                db.execute('ALTER TABLE inventory_items ADD COLUMN quality INTEGER CHECK(quality IS NULL OR quality>=0)')
            if 'released' not in {r[1] for r in db.execute('PRAGMA table_info(inventory_pets)')}:
                db.execute('ALTER TABLE inventory_pets ADD COLUMN released INTEGER NOT NULL DEFAULT 0 CHECK(released IN (0,1))')
            pet_growth_store.prepare_pet_growth(db)
            pet_care.prepare(db)
            pet_battle_care.prepare(db)
            pet_traits.prepare(db)
            pet_cake.prepare(db)
            pet_super_return.prepare(db)
            pet_ordinary_return.prepare(db)
            pet_cake_effects.prepare(db)
            pet_evolution.prepare(db)
            pet_stone_items.prepare(db)
            pet_lifetime_food.prepare(db)
            equipment_condition.prepare(db)
            equipment_detail.prepare(db)
            pet_skills.prepare(db)
            pet_flags.prepare(db)
            # Domain revision covers legacy writes as well as shared settlements.
            # Trigger creation happens only in startup preparation on new paths.
            for table in ('inventory_items', 'inventory_pets'):
                for action in ('INSERT', 'UPDATE', 'DELETE'):
                    row = 'OLD' if action == 'DELETE' else 'NEW'
                    db.executescript(f'''
                        CREATE TRIGGER IF NOT EXISTS {table}_revision_{action}
                        AFTER {action} ON {table} BEGIN
                            INSERT INTO inventory_versions(role_id,revision) VALUES({row}.role_id,1)
                            ON CONFLICT(role_id) DO UPDATE SET revision=revision+1;
                        END;
                    ''')
        return config

    @staticmethod
    def _catalog(name):
        rows = json.loads((OUT / ('catalogs/' + name + '.json')).read_text(encoding='utf-8'))
        return MappingProxyType({int(r['attributes']['id']): MappingProxyType(dict(r['attributes'])) for r in rows})

    def _owned(self):
        if not self.accounts.owned_role(self.account_id, self.role_id):
            raise ValueError('Role ownership mismatch')

    def snapshot(self):
        self._owned()
        with closing(self.accounts.connect()) as db:
            db.execute('BEGIN')
            return self._snapshot(db)

    def _item_rows(self, db):
        cursor=db.execute('SELECT * FROM inventory_items WHERE role_id=? ORDER BY slot',(self.role_id,))
        names=tuple(x[0] for x in cursor.description)
        return [dict(zip(names,row)) for row in cursor]

    def _snapshot(self, db):
        items=self._item_rows(db)
        for item in items:
            if db.execute('SELECT 1 FROM inventory_equipment_conditions WHERE item_key=?',(item['id'],)).fetchone():
                item['condition']=self.equipment_condition(db,item['id'])
            if db.execute('SELECT 1 FROM inventory_equipment_details WHERE item_key=?',(item['id'],)).fetchone():
                item['detail']=self.equipment_detail(db,item['id'])
        pets = [self._pet_state(db,r[0]) for r in db.execute(
            'SELECT id FROM inventory_pets WHERE role_id=? AND released=0 ORDER BY id',(self.role_id,)).fetchall()]
        revision = db.execute('SELECT revision FROM inventory_versions WHERE role_id=?', (self.role_id,)).fetchone()
        return {'items': items, 'pets': pets, 'inventory_revision': revision[0] if revision else 0,
            'bag_capacity': self.policy['bag_capacity'], 'pet_capacity': self.policy['pet_capacity']}

    def _carried_cash(self, db, epoch=None):
        epoch=self.epoch if epoch is None else epoch
        if epoch is None or self.currency_rules is None:
            raise InventoryNotReady('Carried bag requires a trusted wallet epoch and startup currency rules')
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='role_wallet_profiles'").fetchone():
            raise InventoryNotReady('Wallet storage is not prepared')
        try:
            wallet=read_wallet(db,self.account_id,self.role_id,epoch,self.currency_rules)
        except WalletNotInitialized:
            raise InventoryNotReady('Carried cash is unknown; no zero balance may be fabricated') from None
        cash=next((row.balance for row in wallet if row.currency=='cash'),None)
        if cash is None:
            raise InventoryNotReady('Prepared wallet has no authoritative cash channel')
        return cash

    def _bag_reply(self, db, column, *, epoch=None):
        cash=self._carried_cash(db,epoch) if column==1 else 0
        items=[dict(x,slot=x['equipment_slot']) if column==4 else x for x in self._item_rows(db)
               if (x['equipment_slot'] is not None)==(column==4)]
        capacity=16 if column==4 else self.policy['bag_capacity']
        return BAG_INFO,(struct.pack('>iQi',column,cash,capacity)+compact(len(items))
                         +b''.join(item_record(x) for x in items)+b'\0')

    def _pet_state(self, db, pet_id):
        row=db.execute('SELECT id,role_id,template_id,name,fighting,released FROM inventory_pets '
                       'WHERE id=? AND role_id=? AND released=0',(pet_id,self.role_id)).fetchone()
        if not row:
            raise ValueError('Pet unavailable')
        pet=dict(zip(('id','role_id','template_id','name','fighting','released'),row))
        if db.execute('SELECT 1 FROM inventory_pet_growth WHERE pet_id=?',(pet_id,)).fetchone():
            pet['progress']=self.pet_progress(db,pet_id)
        if db.execute('SELECT 1 FROM inventory_pet_care WHERE pet_id=?',(pet_id,)).fetchone():
            pet['care']=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules)
        if db.execute('SELECT 1 FROM inventory_pet_traits WHERE pet_id=?',(pet_id,)).fetchone():
            pet['traits']=pet_traits.load(db,self.account_id,self.role_id,pet_id,self.trait_rules)
        if db.execute('SELECT 1 FROM inventory_pet_cakes WHERE pet_id=?',(pet_id,)).fetchone():
            pet['cake']=pet_cake.load(db,self.account_id,self.role_id,pet_id,self.cake_rules)
        if db.execute('SELECT 1 FROM inventory_pet_evolution WHERE pet_id=?',(pet_id,)).fetchone():
            pet['evolution']=pet_evolution.load(db,self.account_id,self.role_id,pet_id,self.evolution_rules)
        if db.execute('SELECT 1 FROM inventory_pet_skills WHERE pet_id=?',(pet_id,)).fetchone():
            if 'care' not in pet:
                raise InventoryNotReady('Known pet skills require current blood-color care state')
            pet['skills']=pet_skills.load(db,self.account_id,self.role_id,pet_id,self.skill_rules,pet['care'].grade)
        if db.execute('SELECT 1 FROM inventory_pet_flags WHERE pet_id=?',(pet_id,)).fetchone():
            pet['flags']=pet_flags.load(db,self.account_id,self.role_id,pet_id,self.flag_rules)
        if db.execute('SELECT 1 FROM inventory_pet_skill_progress WHERE pet_id=?',(pet_id,)).fetchone():
            if 'skills' not in pet:raise InventoryNotReady('Known expansion progress requires current learned skills')
            pet['skill_progress']=pet_skill_progress.load(db,self.account_id,self.role_id,pet_id,self.skill_rules.learning_rules)
        if db.execute('SELECT 1 FROM inventory_pet_skill_expiry WHERE pet_id=?',(pet_id,)).fetchone():
            if 'skills' not in pet:raise InventoryNotReady('Known expiry requires current learned skills')
            pet['skill_expiry']=pet_skill_expiry.load(db,self.account_id,self.role_id,pet_id,
                self.skill_rules.expiry_rules,pet['skills'])
        return pet

    def immutable_snapshot(self):
        """Read-only cross-owner message; contains no store, Session or DB handle."""
        return self._freeze_snapshot(self.snapshot())

    def immutable_snapshot_transaction(self, db, *, epoch=None):
        """Current frozen assets in the caller's active, current-lease transaction.

        Includes uncommitted equip/reward changes. No connection, commit or send;
        caller combines role/task projection and logical encoding before commit.
        """
        epoch=self.epoch if epoch is None else epoch
        if not db.in_transaction or not _valid_epoch(epoch):
            raise ValueError('Inventory snapshot requires a trusted lease transaction')
        if not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
            'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
            (self.role_id,self.account_id,epoch)).fetchone():
            raise ValueError('Inventory snapshot lease is obsolete or foreign')
        return self._freeze_snapshot(self._snapshot(db))

    def _freeze_snapshot(self, state):
        return InventorySnapshot(self.role_id, state['inventory_revision'],
                                 tuple(ItemState(**item) for item in state['items']),
                                 tuple(PetState(**pet) for pet in state['pets']),
                                 state['bag_capacity'], state['pet_capacity'])

    def equipment_attributes(self):
        """Versioned immutable raw attribute-ID totals from original baseEffect.

        Values are equipment base effects, not complete character combat stats;
        enhancement, gems and temporary effects are separate restoration work.
        """
        state = self.immutable_snapshot()
        totals = {}
        for item in state.items:
            if item.equipment_slot is not None and (item.condition is None or item.condition.current>0):
                properties=(item.detail.base_properties if item.detail is not None
                            else self.equipment_rules[item.template_id][1])
                for kind, value in properties:
                    totals[kind] = totals.get(kind, 0) + value
        return self.role_id, state.inventory_revision, tuple(sorted(totals.items()))

    def _grant_item(self, db, template_id, quantity, binding=0, quality=None):
        attr = self.items.get(template_id)
        if attr is None or type(quantity) is not int or quantity <= 0 or type(binding) is not int or binding not in (0,1):
            raise ValueError('Invalid item grant')
        if quality is not None and (type(quality) is not int or not 0 <= quality <= 0x7fffffff):
            raise ValueError('Invalid item quality')
        maximum = int(attr.get('maxNum', 1))
        if maximum < 1:
            raise ValueError('Unsupported stack limit')
        used = {r[0] for r in db.execute('SELECT slot FROM inventory_items WHERE role_id=? AND equipment_slot IS NULL', (self.role_id,))}
        for key, count in db.execute('SELECT id,quantity FROM inventory_items WHERE role_id=? AND template_id=? AND binding=? AND quality IS ? AND equipment_slot IS NULL ORDER BY slot', (self.role_id, template_id, binding, quality)).fetchall():
            add = min(maximum - count, quantity)
            if add > 0:
                db.execute('UPDATE inventory_items SET quantity=quantity+? WHERE id=?', (add, key))
                quantity -= add
        while quantity:
            slot = next((i for i in range(self.policy['bag_capacity']) if i not in used), None)
            if slot is None:
                raise ValueError('Bag full')
            add = min(maximum, quantity)
            key=db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot,binding,quality) VALUES(?,?,?,?,?,?)', (self.role_id, template_id, add, slot, binding, quality)).lastrowid
            if self._ordinary_equipment(template_id):
                condition=equipment_condition.initialize(db,self.account_id,self.role_id,key,self.condition_rules,self.condition_rules.generate())
                if template_id in self.detail_rules.templates:
                    equipment_detail.initialize(db,self.account_id,self.role_id,key,self.detail_rules,
                        self.detail_rules.generate(template_id),condition,origin='restoration_grant')
            used.add(slot)
            quantity -= add

    def grant_item(self, template_id, quantity=1, binding=0, quality=None):
        """Legacy single operation. Rewards use apply_settlement in one transaction."""
        self._owned()
        with closing(self.accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            self._grant_item(db, template_id, quantity, binding, quality)

    def _consume_item(self, db, key, quantity):
        if type(quantity) is not int or quantity <= 0:
            raise ValueError('Invalid quantity')
        row = db.execute('SELECT quantity,equipment_slot FROM inventory_items WHERE id=? AND role_id=?', (key, self.role_id)).fetchone()
        if not row or row[1] is not None or row[0] < quantity:
            raise ValueError('Item unavailable')
        if row[0] == quantity:
            db.execute('DELETE FROM inventory_items WHERE id=?', (key,))
        else:
            db.execute('UPDATE inventory_items SET quantity=quantity-? WHERE id=?', (quantity, key))

    def consume_item(self, key, quantity=1):
        """Legacy single operation; effects and consumption need the same transaction."""
        self._owned()
        with closing(self.accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            self._consume_item(db, key, quantity)

    def use_consumable(self, db, key, target, quality=None):
        """Join current role transaction; caller fences version and persists vitals.

        Target state must be authoritative; quality comes from the owned item.
        The optional legacy quality argument is only an equality assertion.
        No-op/rejected effects do not consume an item. Caller commits vitals,
        consumption and its common request receipt together or rolls all back.
        """
        if not db.in_transaction or not isinstance(target, VitalState) or target.target_id != self.role_id:
            raise ValueError('Consumable requires an owned role vital transaction')
        role = db.execute('SELECT level FROM roles WHERE id=? AND account_id=?',
                          (self.role_id, self.account_id)).fetchone()
        item = db.execute('SELECT template_id,quality FROM inventory_items WHERE id=? AND role_id=? AND equipment_slot IS NULL',
                          (key, self.role_id)).fetchone()
        if (not role or not item or int(self.items[item[0]].get('needLevel',0)) > role[0]
                or int(self.items[item[0]].get('outbattleuse',0)) == 0):
            raise ValueError('Consumable unavailable or level restricted')
        if quality is not None and (type(quality) is not int or quality != item[1]):
            raise ValueError('Quality must match the owned instance metadata')
        result = self.consumables.apply(item[0], target, item[1])
        self._consume_item(db, key, 1)
        return result

    def _medicine_resource_context(self, db, epoch, resource_rules, equipment_rules):
        """Resolve the explicitly injected contract; missing provenance stays old."""
        if resource_rules is None and equipment_rules is None:
            resource_rules,equipment_rules=self.resource_rules,self.equipment_attribute_rules
        if resource_rules is None and equipment_rules is None:return None,None,None
        from role_resource_plan import ResourceRules
        from role_equipment import EquipmentAttributeRules
        from role_resource_storage import read_role_resources,ResourceNotInitialized
        if type(resource_rules) is not ResourceRules or type(equipment_rules) is not EquipmentAttributeRules:
            raise ValueError('Prepared immutable resource and equipment rules required')
        try:current=read_role_resources(db,self.account_id,self.role_id,epoch,resource_rules)
        except ResourceNotInitialized:current=None
        return resource_rules,equipment_rules,current

    def _resource_vitals(self, resources):
        return VitalState(self.role_id,resources.version,resources.hp,resources.caps.hp_max,
                          resources.mp,resources.caps.mp_max)

    def use_role_consumable(self, db, key, epoch, settlement_id, *, resource_rules=None,equipment_rules=None):
        """Join a fenced role transaction with authoritative resource storage.

        The role owner checks out-of-battle/request eligibility and commits its
        common receipt in this same transaction. This domain receipt dedupes only
        the item effect; it never commits, sends or initializes missing baselines.
        An explicitly migrated profile requires prepared resource/equipment
        rules, supplied at construction or as a pair here. Its paid replay reads
        current resources without planning another transition. Legacy profiles
        keep the historical acknowledgement; native replies always read current
        authority. Missing provenance is never migrated by a medicine request.
        """
        if (not db.in_transaction or type(key) is not int or key<=0
                or not _valid_epoch(epoch)
                or type(settlement_id) is not str or not 1<=len(settlement_id)<=160):
            raise ValueError('Role medicine requires a valid owner transaction and request key')
        resource_rules,equipment_rules,resources=self._medicine_resource_context(db,epoch,resource_rules,equipment_rules)
        current_vitals=(self._resource_vitals(resources) if resources is not None
                        else read_attribute_snapshot(db,self.account_id,self.role_id,epoch).vitals)
        previous=db.execute('SELECT item_key,vitals FROM inventory_role_consumables '
                            'WHERE role_id=? AND settlement_id=?',(self.role_id,settlement_id)).fetchone()
        if previous:
            if previous[0]!=key:
                raise ValueError('Role medicine settlement payload conflict')
            # A migrated profile acknowledges an already-paid operation using
            # CURRENT resources. Never plan a new heal from the new before.
            vitals=current_vitals if resources is not None else VitalState(**json.loads(previous[1]))
            return RoleConsumableReceipt(settlement_id,self.role_id,key,vitals)
        after=self.use_consumable(db,key,current_vitals)
        if resources is None:
            update_role_vitals(db,self.account_id,self.role_id,epoch,current_vitals,after)
        else:
            from role_equipment_storage import current_equipment_totals
            from role_equipment import resource_caps_from_projection
            from role_resource_plan import plan_resource_values
            from role_resource_storage import apply_resource_transition
            # The actual debit trigger advances the asset revision. Recompute
            # caps from the same transaction's current worn items, not bare HP.
            totals=current_equipment_totals(db,self.account_id,self.role_id,epoch,
                self.immutable_snapshot_transaction(db,epoch=epoch),equipment_rules)
            transition=plan_resource_values(resources,after.hp,after.mp,'medicine',resource_rules,
                current_caps=resource_caps_from_projection(totals))
            paid=apply_resource_transition(db,self.account_id,self.role_id,epoch,transition,settlement_id,
                rules=resource_rules,equipment_rules=equipment_rules)
            after=self._resource_vitals(paid.resources)
        db.execute('INSERT INTO inventory_role_consumables VALUES(?,?,?,?)',
                   (self.role_id,settlement_id,key,json.dumps(asdict(after))))
        return RoleConsumableReceipt(settlement_id,self.role_id,key,after)

    def receive_role_consumable(self, body, epoch, settlement_id, resource_rules=None,equipment_rules=None):
        """Context-aware CUseItem role adapter for the role owner.

        The two-argument legacy receive cannot invent epoch or request identity.
        Integration dispatches role-target CUseItem here with its trusted command
        context, and sends returned logical messages through the connection owner.
        Eligibility such as not-in-battle remains the role owner's responsibility.
        """
        self._owned()
        if len(body)!=16:
            raise ValueError('Invalid role use-item request')
        key,target_kind,target_id=struct.unpack('>iiQ',body)
        if key<=0 or target_kind!=0 or target_id!=self.role_id:
            raise ValueError('Role use-item target mismatch')
        with closing(self.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self.use_role_consumable(db,key,epoch,settlement_id,resource_rules=resource_rules,equipment_rules=equipment_rules)
            _,_,resources=self._medicine_resource_context(db,epoch,resource_rules,equipment_rules)
            current_vitals=(self._resource_vitals(resources) if resources is not None
                            else read_attribute_snapshot(db,self.account_id,self.role_id,epoch).vitals)
            # Validate representation before commit so encoding cannot consume
            # medicine and then silently change the authoritative resource value.
            refresh=role_resource_refresh(current_vitals)
            bag=self._bag_reply(db,1,epoch=epoch)
        return [refresh,bag]

    def use_pet_consumable(self, key, pet_id):
        """Pet resources and item quantity change in the same role transaction."""
        self._owned()
        with closing(self.accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            return self._use_pet_consumable(db,key,pet_id)

    def use_pet_blood_essence(self, db, key, pet_id, epoch, settlement_id, expected_version):
        """One owned essence in the caller's current role transaction."""
        if not db.in_transaction or not _valid_epoch(epoch) or not db.execute(
                'SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
                'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
                (self.role_id,self.account_id,epoch)).fetchone():
            raise ValueError('Blood essence requires the current role owner transaction')
        return pet_blood.use_essence(db,self.account_id,self.role_id,pet_id,key,settlement_id,expected_version,
            self.growth_rules,self.blood_rules,self.care_rules)

    def super_return_candidate(self, db, pet_id, epoch):
        """Read the current per-pet candidate, never a historical paid preview."""
        self.immutable_snapshot_transaction(db,epoch=epoch)
        return pet_super_return.pending(db,self,pet_id)

    def ordinary_return(self, db, pet_id, item_key, epoch, request_id, draws=None,expected_version=None):
        """One ordinary rebirth inside the caller's fenced role transaction."""
        self.immutable_snapshot_transaction(db,epoch=epoch)
        return pet_ordinary_return.change(db,self,pet_id,item_key,request_id,draws,expected_version)

    def evolve_pet(self, db, pet_id, epoch, request_id, expected_version=None):
        """One admitted ordinary evolution, joined to the current role transaction."""
        self.immutable_snapshot_transaction(db,epoch=epoch)
        return pet_evolution.change(db,self,pet_id,request_id,expected_version)

    def initialize_pet_evolution(self, db, pet_id, stage):
        """Trusted complete import; current Profile already contains this bonus."""
        self.immutable_snapshot_transaction(db,epoch=self.epoch)
        return pet_evolution.initialize(db,self.account_id,self.role_id,pet_id,self.evolution_rules,stage,source='explicit_known_import')

    def receive_pet_evolution(self, body, epoch, request_id, *, expected_version=None,now_ms=None,precommit=None):
        """Original confirmed evolution with the trusted admitted command ID."""
        pet=decode_pet_evolution_request(body)
        with closing(self.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            receipt=self.evolve_pet(db,pet,epoch,request_id,expected_version)
            self._run_precommit(db,precommit,replayed=receipt.replayed,epoch=epoch)
            return self._evolution_messages(db,receipt,epoch,now_ms)

    def _evolution_messages(self, db, receipt, epoch, now_ms=None):
        current=self.read_pet_state(db,receipt.pet_id)
        replies=[game_time_message(self.clock_now_ms() if now_ms is None else now_ms),
            (REFRESH_PET,pet_record(vars(current))) if current else pet_removal_message(receipt.pet_id),self._bag_reply(db,1,epoch=epoch)]
        if not receipt.replayed:
            if current is None:raise ValueError('Fresh evolved pet disappeared before reply')
            replies.append(evolution_notice(143571,(current.name,self.evolution_rules.labels[receipt.after.stage]))
                if receipt.growth_after-receipt.growth_before==5 else evolution_notice(148963))
        return replies

    def receive_ordinary_return(self, body, epoch, request_id, draws=None,now_ms=None,precommit=None,expected_version=None):
        """Original ordinary31002/31087 CUseItem; stable draws belong to the admitted role command."""
        if type(body) is not bytes or len(body)!=16:raise ValueError('Invalid ordinary-return item request')
        key,kind,pet=struct.unpack('>iiQ',body)
        if kind!=1 or not 0<pet<=0x7fffffff:raise ValueError('Original owned pet item target required')
        clock=game_time_message(now_ms) if now_ms is not None else None
        with closing(self.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            receipt=self.ordinary_return(db,pet,key,epoch,request_id,draws,expected_version)
            self._run_precommit(db,precommit,replayed=receipt.replayed,epoch=epoch)
            current=self.read_pet_state(db,pet)
            if current is None:return [pet_removal_message(pet),self._bag_reply(db,1,epoch=epoch)]
            if clock is None and current.skill_expiry is not None and current.skill_expiry.entries:
                raise InventoryNotReady('Timed current rebirth reply requires trusted milliseconds')
            replies=([clock] if clock is not None else [])+[(REFRESH_PET,pet_record(vars(current))),self._bag_reply(db,1,epoch=epoch)]
            replies.extend(self.pet_skill_progress_messages(db,epoch,(pet,)))
            return replies

    def super_return(self, db, pet_id, epoch, request_id, action, *, item_key=None,draws=None,expected_candidate=None):
        """Fenced same-transaction preview/save/clear; accepted command context is immutable."""
        self.immutable_snapshot_transaction(db,epoch=epoch)
        return pet_super_return.change(db,self,pet_id,request_id,action,item_key=item_key,
            draws=draws,expected_candidate=expected_candidate)

    def receive_super_return(self, typ, body, epoch, request_id=None, *, draws=None,
                             expected_candidate=None,now_ms=None,precommit=None):
        """Original super-return messages; caller supplies trusted accepted ID/draws/candidate token.

        CUseItem here is exclusively the owned31576 preview. Shared owner must
        route it explicitly; the generic legacy use-item path cannot roll it.
        Query is read-only; paid mutation replies always use CURRENT state.
        """
        if typ==USE_ITEM:
            if type(body) is not bytes or len(body)!=16:raise ValueError('Invalid super-return pill request')
            key,kind,pet=struct.unpack('>iiQ',body)
            if kind!=1 or not 0<pet<=0x7fffffff:raise ValueError('Original pet item target required')
            action='preview'
        elif typ in (SUPER_RETURN_QUERY,SUPER_RETURN_SUBMIT,SUPER_RETURN_CLEAR):
            pet=decode_super_return_pet_request(body);key=None
            action={SUPER_RETURN_QUERY:'query',SUPER_RETURN_SUBMIT:'save',SUPER_RETURN_CLEAR:'clear'}[typ]
        else:raise ValueError('Unsupported super-return request type')
        clock=game_time_message(now_ms) if now_ms is not None else None
        with closing(self.accounts.connect()) as db,db:
            db.execute('BEGIN' if action=='query' else 'BEGIN IMMEDIATE')
            self.immutable_snapshot_transaction(db,epoch=epoch)
            if action=='query':
                if draws is not None or expected_candidate is not None:raise ValueError('Query cannot carry mutation context')
                candidate=self.super_return_candidate(db,pet,epoch)
                return ([clock] if clock is not None else [])+([candidate.message()] if candidate else [])
            receipt=self.super_return(db,pet,epoch,request_id,action,item_key=key,
                draws=draws,expected_candidate=expected_candidate)
            self._run_precommit(db,precommit,replayed=receipt.replayed,epoch=epoch)
            current=self.read_pet_state(db,pet)
            if current is None:
                # Historical commands never resurrect a released pet or pending preview.
                return [pet_removal_message(pet),self._bag_reply(db,1,epoch=epoch)]
            if clock is None and current.skill_expiry is not None and current.skill_expiry.entries:
                raise InventoryNotReady('Timed super-return refresh requires trusted current milliseconds')
            replies=([clock] if clock is not None else [])+[(REFRESH_PET,pet_record(vars(current))),self._bag_reply(db,1,epoch=epoch)]
            if action=='preview':
                candidate=self.super_return_candidate(db,pet,epoch)
                if candidate is not None:replies.append(candidate.message())
            return replies

    def use_pet_toxic_food(self, db, key, pet_id, epoch, settlement_id, draw, expected_version):
        """Owned current-lease caller transaction; draw is trusted admission data."""
        self.immutable_snapshot_transaction(db,epoch=epoch)
        return pet_lifetime_food.use(db,self.account_id,self.role_id,pet_id,key,settlement_id,draw,expected_version,
            self.toxic_food_rules,self.growth_rules,self.blood_rules,self.care_rules)

    def use_pet_cake(self, db, key, pet_id, epoch, settlement_id, expected_version=None):
        """Confirmed original named cake in the caller's current role transaction; no RNG."""
        self.immutable_snapshot_transaction(db,epoch=epoch)
        return pet_cake_effects.use(db,self,pet_id,key,settlement_id,expected_version)

    def use_pet_stone(self, db, key, pet_id, epoch, settlement_id, draws=None,expected_version=None):
        self.immutable_snapshot_transaction(db,epoch=epoch)
        return pet_stone_items.use(db,self,pet_id,key,settlement_id,draws,expected_version)

    def initialize_pet_stones(self,db,pet_id,count,added_aptitudes):
        """Trusted complete import; current profile already has total growth and BASE aptitudes."""
        self.immutable_snapshot_transaction(db,epoch=self.epoch)
        before=self.pet_progress(db,pet_id);stones=pet_stones.PetStones(0,count,added_aptitudes)
        if before.blood is None or before.profile.growth_raw-self.stone_rules.growth_per_stone*count<500:
            raise ValueError('Explicit complete BASE/blood and total growth source required for stone import')
        planned=pet_growth_store._project(self.role_id,pet_id,before.profile,before.state,
            self.growth_rules,self.blood_rules,before.blood,stones)
        if not 0<=before.state.hp<=planned.attributes.max_hp or not 0<=before.state.mp<=planned.attributes.max_mp:
            raise ValueError('Known imported stone resources must fit their effective caps')
        return pet_stones.initialize(db,self.account_id,self.role_id,pet_id,self.stone_rules,count,added_aptitudes,
            source='explicit_known_import')

    def receive_pet_consumable(self, body, epoch, settlement_id, now_ms=None, precommit=None, draw=None,stone_draws=None):
        """Original CUseItem kind1 with durable admitted-command context."""
        self._owned()
        clock=game_time_message(now_ms) if now_ms is not None else None
        if type(body) is not bytes or len(body)!=16:raise ValueError('Invalid context-aware pet item request')
        key,kind,pet=struct.unpack('>iiQ',body)
        if (not 0<key<=0x7fffffff or kind!=1 or not 0<pet<=0x7fffffff or not _valid_epoch(epoch)
                or type(settlement_id) is not str or not 1<=len(settlement_id)<=160):
            raise ValueError('Original owned pet item and trusted command identity required')
        fingerprint=hashlib.sha256(body).hexdigest()
        with closing(self.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self.immutable_snapshot_transaction(db,epoch=epoch)
            live=self.read_pet_state(db,pet)
            current=vars(live) if live is not None else None
            cake_receipt=None;stone_receipt=None
            old=db.execute('SELECT fingerprint FROM inventory_pet_consumable_commands WHERE role_id=? AND settlement_id=?',
                (self.role_id,settlement_id)).fetchone()
            replayed=old is not None
            if old:
                if old[0]!=fingerprint:raise ValueError('Pet item admitted-command intent conflict')
                if db.execute('SELECT 1 FROM inventory_pet_toxic_food_receipts WHERE role_id=? AND settlement_id=?',
                        (self.role_id,settlement_id)).fetchone():
                    self.use_pet_toxic_food(db,key,pet,epoch,settlement_id,draw,None)
                if db.execute('SELECT 1 FROM inventory_pet_stone_receipts WHERE role_id=? AND request_id=?',
                        (self.role_id,settlement_id)).fetchone():
                    stone_receipt=self.use_pet_stone(db,key,pet,epoch,settlement_id,stone_draws)
            else:
                item=db.execute('SELECT template_id FROM inventory_items WHERE id=? AND role_id=? AND equipment_slot IS NULL',
                    (key,self.role_id)).fetchone()
                blood_history=db.execute('SELECT 1 FROM inventory_pet_blood_receipts WHERE role_id=? AND settlement_id=?',
                    (self.role_id,settlement_id)).fetchone()
                food_history=db.execute('SELECT 1 FROM inventory_pet_toxic_food_receipts WHERE role_id=? AND settlement_id=?',
                    (self.role_id,settlement_id)).fetchone()
                cake_history=db.execute('SELECT 1 FROM inventory_pet_cake_receipts WHERE role_id=? AND request_id=?',
                    (self.role_id,settlement_id)).fetchone()
                stone_history=db.execute('SELECT 1 FROM inventory_pet_stone_receipts WHERE role_id=? AND request_id=?',
                    (self.role_id,settlement_id)).fetchone()
                if stone_history or item and item[0] in self.stone_rules.templates:
                    try:stone_receipt=self.use_pet_stone(db,key,pet,epoch,settlement_id,stone_draws)
                    except pet_stone_items.StoneUnavailable as error:return [stone_notice(error.message_id)]
                    replayed=stone_receipt.replayed
                elif food_history or item and item[0] in self.toxic_food_rules.formulas:
                    receipt=self.use_pet_toxic_food(db,key,pet,epoch,settlement_id,draw,None)
                    replayed=receipt.replayed
                elif blood_history or item and item[0]==self.blood_rules.essence_template:
                    receipt=self.use_pet_blood_essence(db,key,pet,epoch,settlement_id,None)
                    replayed=receipt.replayed
                elif cake_history or item and item[0] in self.cake_effect_rules.templates:
                    try:receipt=self.use_pet_cake(db,key,pet,epoch,settlement_id)
                    except pet_cake_effects.CakeUnavailable as error:
                        # All refusals are planned before writes. The client has
                        # normally checked these locally; stale confirmations
                        # still get the original reason without spending.
                        args=((self.cake_effect_rules.item_names[item[0]-31268],) if error.message_id==145136 else ())
                        return [cake_notice(error.message_id,args)]
                    cake_receipt=receipt
                    replayed=receipt.replayed
                else:self._use_pet_consumable(db,key,pet)
                # A validated low-level historical acknowledgement remains a
                # strict read; it does not manufacture a new wrapper payment.
                if not replayed:
                    db.execute('INSERT INTO inventory_pet_consumable_commands VALUES(?,?,?)',
                        (self.role_id,settlement_id,fingerprint))
                live=self.read_pet_state(db,pet)
                current=vars(live) if live is not None else None
            self._run_precommit(db,precommit,replayed=replayed,epoch=epoch)
            if current is None:return [pet_removal_message(pet),self._bag_reply(db,1,epoch=epoch)]
            if stone_receipt is not None and clock is None:clock=game_time_message(self.clock_now_ms())
            if clock is None and current.get('skill_expiry') is not None and current['skill_expiry'].entries:
                raise InventoryNotReady('Timed pet item refresh requires trusted current milliseconds')
            replies=[(REFRESH_PET,pet_record(current)),self._bag_reply(db,1,epoch=epoch)]
            if clock is not None:replies.insert(0,clock)
            if current.get('progress') is not None and current['progress'].stones is not None:
                replies.append(stone_attributes_message(pet,current['progress'].stones))
            if stone_receipt is not None and not replayed:
                args=tuple(str(b-a) for a,b in zip(stone_receipt.before.stones.added_aptitudes,
                    stone_receipt.after.stones.added_aptitudes)) if stone_receipt.item_template==70052 else ()
                replies.append(stone_notice(150454 if stone_receipt.item_template==70052 else 150456,args))
            if cake_receipt is not None and not replayed:
                replies.append(cake_notice(145135,(self.cake_effect_rules.names[cake_receipt.prediction.attribute_index],
                    str(cake_receipt.actual_gain),str(20-cake_receipt.cake_after.count))))
            return replies

    def _use_pet_consumable(self, db, key, pet_id):
        item = db.execute('SELECT template_id,quality FROM inventory_items WHERE id=? AND role_id=? AND equipment_slot IS NULL',
                          (key,self.role_id)).fetchone()
        role = db.execute('SELECT level FROM roles WHERE id=? AND account_id=?',(self.role_id,self.account_id)).fetchone()
        if not item or not role:
            raise ValueError('Pet consumable unavailable')
        if item[0]==self.blood_rules.essence_template:
            raise InventoryNotReady('Blood essence requires receive_pet_consumable or the caller-transaction Interface')
        if item[0] in self.toxic_food_rules.formulas:
            raise InventoryNotReady('Toxic lifetime food requires stable command and captured draw context')
        if item[0]==31576:
            raise InventoryNotReady('Super-return pill requires receive_super_return and captured command/draw context')
        if item[0] in (31002,31087):
            raise InventoryNotReady('Ordinary rebirth pill requires receive_ordinary_return and stable command/draw context')
        if item[0] in self.cake_effect_rules.templates:
            raise InventoryNotReady('Named cake requires receive_pet_consumable or the fenced caller transaction')
        if item[0] in self.stone_rules.templates:
            raise InventoryNotReady('Stone/clearing requires a stable admitted command; stone also needs captured draws')
        attr = self.items[item[0]]
        if int(attr.get('needLevel',0)) > role[0] or int(attr.get('outbattleuse',0)) == 0:
            raise ValueError('Pet consumable level or use restriction')
        if item[0] in self.care_rules.quality_lifetime_food:
            previous=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules)
            self.change_pet_care(db,pet_id,f'pet-lifetime-quality:{pet_id}:{previous.version}:{key}',
                                 previous.version,'feed_lifetime_quality',(item[0],item[1]))
        elif item[0] in self.care_rules.lifetime_food:
            previous=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules)
            self.change_pet_care(db,pet_id,f'pet-lifetime:{pet_id}:{previous.version}:{key}',
                                 previous.version,'feed_lifetime',item[0])
        elif item[0] in self.care_rules.food:
            previous=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules)
            self.change_pet_care(db,pet_id,f'pet-food:{pet_id}:{previous.version}:{key}',
                                 previous.version,'feed',item[0])
        else:
            previous = self.pet_progress(db,pet_id)
            target = VitalState(pet_id,previous.state.version,previous.state.hp,previous.attributes.max_hp,
                                previous.state.mp,previous.attributes.max_mp)
            # Quality comes only from the persisted owned item instance.
            healed = self.consumables.apply(item[0],target,item[1])
            self.change_pet_growth(db,pet_id,f'pet-item:{pet_id}:{previous.state.version}:{key}',
                previous.state.version,'resources',(healed.hp,healed.mp))
        self._consume_item(db,key,1)
        return self._pet_state(db,pet_id)

    def _run_precommit(self, db, callback, *, replayed, epoch=None):
        """Trusted synchronous owner hook, with the actual same-transaction assets."""
        if callback is None:return
        if not callable(callback) or type(replayed) is not bool:
            raise ValueError('Synchronous trusted inventory precommit callback required')
        snapshot=self.immutable_snapshot_transaction(db,epoch=epoch)
        result=callback(db,self,snapshot,replayed=replayed)
        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):result.close()
            raise ValueError('Inventory precommit callback must complete synchronously')
        return result

    def move_item(self, key, target_slot, quantity=0, source_slot=-1, *, precommit=None):
        self._owned()
        with closing(self.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self._move_item(db,key,target_slot,quantity,source_slot)
            self._run_precommit(db,precommit,replayed=False)

    def _move_item(self, db, key, target_slot, quantity=0, source_slot=-1):
        if type(quantity) is not int or quantity < 0:
            raise ValueError('Invalid quantity')
        source = db.execute('SELECT template_id,quantity,slot,binding,quality FROM inventory_items WHERE id=? AND role_id=? AND equipment_slot IS NULL',
                            (key, self.role_id)).fetchone()
        if not source or source_slot not in (-1, source[2]):
            raise ValueError('Source item unavailable or moved')
        count = quantity or source[1]
        if count > source[1]:
            raise ValueError('Insufficient move quantity')
        if target_slot == -1:
            used = {r[0] for r in db.execute('SELECT slot FROM inventory_items WHERE role_id=?', (self.role_id,))}
            target_slot = next((i for i in range(self.policy['bag_capacity']) if i not in used), None)
        if type(target_slot) is not int or not 0 <= target_slot < self.policy['bag_capacity']:
            raise ValueError('No available bag slot')
        if target_slot == source[2]:
            return
        target = db.execute('SELECT id,template_id,quantity,binding,quality FROM inventory_items WHERE role_id=? AND slot=? AND equipment_slot IS NULL',
                            (self.role_id, target_slot)).fetchone()
        if target:
            if target[1] == source[0] and target[3] == source[3] and target[4] == source[4] and int(self.items[source[0]].get('maxNum', 1)) > 1:
                count = min(count, int(self.items[source[0]]['maxNum']) - target[2])
                if count <= 0:
                    raise ValueError('Target stack full')
                db.execute('UPDATE inventory_items SET quantity=quantity+? WHERE id=?', (count, target[0]))
                self._consume_item(db, key, count)
            elif count == source[1]:
                temporary = self.policy['bag_capacity']
                db.execute('UPDATE inventory_items SET slot=? WHERE id=?', (temporary, key))
                db.execute('UPDATE inventory_items SET slot=? WHERE id=?', (source[2], target[0]))
                db.execute('UPDATE inventory_items SET slot=? WHERE id=?', (target_slot, key))
            else:
                raise ValueError('Cannot partially swap different items')
        elif count == source[1]:
            db.execute('UPDATE inventory_items SET slot=? WHERE id=?', (target_slot, key))
        else:
            self._consume_item(db, key, count)
            db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot,binding,quality) VALUES(?,?,?,?,?,?)',
                       (self.role_id, source[0], count, target_slot, source[3], source[4]))

    def arrange_bag(self, *, precommit=None):
        self._owned()
        with closing(self.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self._arrange_bag(db)
            self._run_precommit(db,precommit,replayed=False)

    def _arrange_bag(self, db):
        rows = db.execute('SELECT id,template_id,quantity,slot,binding,quality FROM inventory_items '
                          'WHERE role_id=? AND equipment_slot IS NULL ORDER BY template_id,binding,quality,slot,id',
                          (self.role_id,)).fetchall()
        groups = {}
        for row in rows:
            groups.setdefault((row[1],row[4],row[5]),[]).append(row)
        plan = []
        for (template,binding,quality),members in groups.items():
            maximum = int(self.items[template].get('maxNum',1))
            if maximum <= 0 or any(not 0 < x[2] <= maximum for x in members):
                raise ValueError('Invalid persisted item stack')
            remaining = sum(x[2] for x in members)
            for member in members:
                if remaining <= 0:
                    break
                count = min(remaining,maximum)
                plan.append((member[0],template,count,len(plan),binding,quality))
                remaining -= count
        if plan == rows:
            return
        kept = {x[0] for x in plan}
        for row in rows:
            if row[0] not in kept:
                db.execute('DELETE FROM inventory_items WHERE id=? AND role_id=?',(row[0],self.role_id))
        for i,row in enumerate(plan):
            db.execute('UPDATE inventory_items SET slot=? WHERE id=?',(self.policy['bag_capacity']+i,row[0]))
        for key,template,count,slot,binding,quality in plan:
            db.execute('UPDATE inventory_items SET quantity=?,slot=? WHERE id=?',(count,slot,key))

    def apply_settlement(self, db, change):
        """Join role owner's transaction; never connects, begins, commits or sends.

        Caller checks current login_epoch inside this transaction and rolls back
        on ANY exception, including failures in other modules. Commit only once
        assets, task state/experience and the common settlement receipt are ready.
        """
        if not db.in_transaction or not isinstance(change, AssetChange):
            raise ValueError('Asset settlement requires an active owner transaction')
        if not db.execute('SELECT 1 FROM roles WHERE id=? AND account_id=?',
                          (self.role_id, self.account_id)).fetchone():
            raise ValueError('Role ownership mismatch')
        fingerprint = hashlib.sha256(json.dumps([change.grants, change.debits, change.pets],
                                                separators=(',', ':')).encode()).hexdigest()
        row = db.execute('SELECT fingerprint,receipt FROM inventory_settlements WHERE role_id=? AND settlement_id=?',
                         (self.role_id, change.settlement_id)).fetchone()
        if row:
            if row[0] != fingerprint:
                raise ValueError('Settlement key reused with different assets')
            return AssetReceipt(change.settlement_id, tuple(json.loads(row[1])))
        for key, quantity in change.debits:
            self._consume_item(db, key, quantity)
        for grant in change.grants:
            self._grant_item(db, grant[0], grant[1], grant[2] if len(grant) >= 3 else 0,
                             grant[3] if len(grant) == 4 else None)
        pets = tuple(self._grant_pet(db, template_id) for template_id in change.pets)
        db.execute('INSERT INTO inventory_settlements(role_id,settlement_id,fingerprint,receipt) VALUES(?,?,?,?)',
                   (self.role_id, change.settlement_id, fingerprint, json.dumps(pets)))
        return AssetReceipt(change.settlement_id, pets)

    def require_transferable(self, db, key):
        """Trade/transfer gate; caller uses the same role-owner transaction."""
        if not db.in_transaction:
            raise ValueError('Transfer check requires an owner transaction')
        item = db.execute('SELECT binding,equipment_slot FROM inventory_items WHERE id=? AND role_id=?',
                          (key,self.role_id)).fetchone()
        if not item or item[0] != 0 or item[1] is not None:
            raise ValueError('Bound, equipped or unavailable item cannot transfer')

    def _ordinary_equipment(self, template_id):
        kind=int(self.items[template_id]['itemtypeid'])
        return template_id in self.equipment and (kind&15)==8 and 0<=((kind>>4)&15)<=5

    def initialize_equipment_condition(self, db, key, current, maximum, color_tier):
        row=db.execute('SELECT template_id FROM inventory_items WHERE id=? AND role_id=?',(key,self.role_id)).fetchone()
        if not row or not self._ordinary_equipment(row[0]):
            raise ValueError('Ordinary owned equipment required')
        state=equipment_condition.EquipmentCondition(0,current,maximum,color_tier)
        return equipment_condition.initialize(db,self.account_id,self.role_id,key,self.condition_rules,state)

    def equipment_condition(self, db, key):
        return equipment_condition.load(db,self.account_id,self.role_id,key,self.condition_rules)

    def equipment_detail(self, db, key):
        """Frozen known clean detail; unknown old instances remain unknown."""
        return equipment_detail.load(db,self.account_id,self.role_id,key,self.detail_rules)

    def initialize_equipment_detail(self, db, key, detail):
        """Trusted explicit migration of a known clean, unenhanced instance."""
        return equipment_detail.initialize(db,self.account_id,self.role_id,key,self.detail_rules,
            detail,self.equipment_condition(db,key),origin='explicit_known_clean_instance')

    def equipment_identification_basis(self,db,key,epoch,*,expected_inventory_revision=None):
        """Read-only clean CAS basis. NPC owns ticket, exact quote and admission."""
        if type(key) is not int or not 0<key<=0x7fffffff:raise ValueError('Original positive owned item key required')
        snapshot=self.immutable_snapshot_transaction(db,epoch=epoch)
        if expected_inventory_revision is not None and (type(expected_inventory_revision) is not int
                or not 0<=expected_inventory_revision<2**63-1 or snapshot.inventory_revision!=expected_inventory_revision):
            raise ValueError('Identification query inventory revision changed')
        item=next((i for i in snapshot.items if i.id==key),None)
        if (item is None or item.quantity!=1 or item.equipment_slot is not None
                or not 0<=item.slot<snapshot.bag_capacity or item.template_id not in self.detail_rules.templates
                or int(self.items[item.template_id]['itemtypeid']) in (0x1c8,0x2c8,0x3c8)
                or type(item.condition) is not equipment_condition.EquipmentCondition
                or item.condition.color_tier!=1
                or not self.detail_rules.fixed_clean_unidentified(item.template_id,item.detail)):
            raise ValueError('Known carried fixed canonical clean unidentified result required')
        row=db.execute('SELECT revision,origin,detail FROM inventory_equipment_details WHERE item_key=?',(key,)).fetchone()
        if row is None or row[:2]!=(self.detail_rules.revision,'explicit_known_clean_instance'):
            raise ValueError('Explicit complete fixed-result origin/revision required for identification')
        return EquipmentIdentificationBasis(snapshot.inventory_revision,item,*row)

    def identify_equipment_clean_transaction(self,db,basis,epoch,*,precommit=None):
        """One fenced0->1 CAS in caller transaction; NPC owns paid dedupe/fee/receipt.

        A paid caller reads current replies without invoking this mutator again.
        Stage source and native replies before committing the outer transaction.
        """
        if type(basis) is not EquipmentIdentificationBasis:raise ValueError('Frozen identification basis required')
        current=self.equipment_identification_basis(db,basis.item.id,epoch,expected_inventory_revision=basis.inventory_revision)
        if current!=basis:raise ValueError('Identification inventory or full item/detail source changed')
        detail=equipment_detail._identify_fixed_clean(db,self.account_id,self.role_id,basis.item.id,self.detail_rules,basis.detail_json)
        changed=db.execute('UPDATE inventory_versions SET revision=revision+1 WHERE role_id=? AND revision=?',
            (self.role_id,basis.inventory_revision)).rowcount
        if changed!=1:raise ValueError('Identification inventory revision CAS failed')
        from dataclasses import replace
        result=EquipmentIdentificationChange(basis,replace(current.item,detail=detail),basis.inventory_revision+1)
        self._run_precommit(db,precommit,replayed=False,epoch=epoch)
        return result

    def equipment_tip_message(self,db,key,epoch):
        """Encode CURRENT detail in caller transaction, including uncommitted CAS."""
        if type(key) is not int or not 0<key<=0x7fffffff:raise ValueError('Original positive owned item key required')
        snapshot=self.immutable_snapshot_transaction(db,epoch=epoch)
        item=next((i for i in snapshot.items if i.id==key),None)
        if item is None or item.quantity!=1 or item.detail is None or item.condition is None:
            raise ValueError('Known current owned equipment detail required')
        column=4 if item.equipment_slot is not None else 1
        detail=equipment_detail.encode(item.template_id,item.detail,item.condition,self.detail_rules)
        return ITEM_TIPS_REPLY,struct.pack('>ii',column,key)+octets(detail)

    def reconcile_equipment_color(self, db, key, expected_version, color_tier):
        return equipment_condition.reconcile_color(db,self.account_id,self.role_id,key,self.condition_rules,
                                                   expected_version,color_tier)

    def wear_equipment(self, db, key, settlement_id, expected_version, amount):
        return equipment_condition.wear(db,self.account_id,self.role_id,key,self.condition_rules,
                                         settlement_id,expected_version,amount)

    def repair_equipment(self, db, key, epoch, settlement_id, expected_version, draw, currency_rules):
        row=db.execute('SELECT template_id FROM inventory_items WHERE id=? AND role_id=?',(key,self.role_id)).fetchone()
        if not row or not self._ordinary_equipment(row[0]):
            raise ValueError('Ordinary owned equipment required')
        level=int(self.items[row[0]]['level'])
        return equipment_condition.repair(db,self.account_id,self.role_id,key,self.condition_rules,
            currency_rules,epoch,settlement_id,expected_version,draw,level)

    def equipment_refresh(self, db, key):
        """Current condition logical messages inside caller's owner transaction.

        Use after repair/wear/replay; a historical RepairReceipt is not current
        state. Currency balance refresh is likewise read from the current wallet.
        """
        state=self.equipment_condition(db,key)
        slot=db.execute('SELECT equipment_slot FROM inventory_items WHERE id=? AND role_id=?',
                        (key,self.role_id)).fetchone()[0]
        column=4 if slot is not None else 1
        return (endurance_refresh(column,((key,state.current),)),maximum_refresh(column,key,state.maximum))

    def equip(self, key, equipment_slot):
        """Legacy single operation. Task integration uses equip_transaction."""
        self._owned()
        with closing(self.accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            self._equip(db,key,equipment_slot)

    def _equip(self, db, key, equipment_slot):
        if type(equipment_slot) is not int or not 0 <= equipment_slot < 16:
            raise ValueError('Invalid equipment slot')
        if not db.in_transaction:raise ValueError('Equipment requires an owner transaction')
        row = db.execute('SELECT template_id,quantity,slot,equipment_slot FROM inventory_items WHERE id=? AND role_id=?', (key, self.role_id)).fetchone()
        role=db.execute('SELECT level,shape FROM roles WHERE id=? AND account_id=?',(self.role_id,self.account_id)).fetchone()
        if not role or not row or row[0] not in self.equipment or row[1] != 1 or row[3] is not None:
            raise ValueError('Not an available equipment item')
        attr = self.items[row[0]]
        sex_need = int(self.equipment[row[0]].get('sexNeed',0))
        if sex_need and self.shape_sexes.get(role[1])!=sex_need:
            raise ValueError('Equipment sex requirement')
        allowed_roles = self.equipment_rules[row[0]][0]
        # Original10771d0 tests roleNeed only for weapon slot0; empty is free.
        if (int(attr['itemtypeid']) >> 4) & 15 == 0 and allowed_roles and self.shape_roles.get(role[1]) not in allowed_roles:
            raise ValueError('Equipment character requirement')
        # Original callsite10e1dd4..dda derives the slot from itemtypeid.
        if (int(attr['itemtypeid']) >> 4) & 15 != equipment_slot:
            raise ValueError('Equipment slot mismatch')
        if int(attr.get('needLevel', 0)) > role[0]:
            raise ValueError('Equipment level requirement')
        previous = db.execute('SELECT id FROM inventory_items WHERE role_id=? AND equipment_slot=?', (self.role_id, equipment_slot)).fetchone()
        if previous:
            db.execute('UPDATE inventory_items SET slot=?,equipment_slot=NULL WHERE id=?', (self.policy['bag_capacity'], previous[0]))
        db.execute('UPDATE inventory_items SET equipment_slot=?,slot=? WHERE id=?', (equipment_slot, -equipment_slot-1, key))
        if previous:
            db.execute('UPDATE inventory_items SET slot=? WHERE id=?', (row[2], previous[0]))
        return row[0],previous[0] if previous else None

    def equip_transaction(self, db, key, equipment_slot, epoch, request_id):
        """Equip and freeze a server-confirmed fact in the caller's transaction.

        Caller commits task validation/progress and its common receipt here too.
        A replay acknowledges history (replayed=True), never emits a fresh fact,
        re-equips a later-removed item or rewrites the inventory revision.
        """
        if (not db.in_transaction or type(key) is not int or key<=0
                or type(equipment_slot) is not int or not 0<=equipment_slot<16
                or not _valid_epoch(epoch) or type(request_id) is not str or not 1<=len(request_id)<=160):
            raise ValueError('Trusted equipment transaction context required')
        if not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
            'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
            (self.role_id,self.account_id,epoch)).fetchone():
            raise ValueError('Equipment role lease mismatch')
        fingerprint=hashlib.sha256(json.dumps(['equip',key,equipment_slot],separators=(',',':')).encode()).hexdigest()
        old=db.execute('SELECT fingerprint,event FROM inventory_equipment_commands WHERE role_id=? AND request_id=?',
                       (self.role_id,request_id)).fetchone()
        if old:
            if old[0]!=fingerprint:raise ValueError('Equipment request intent conflict')
            event=json.loads(old[1]);event['replayed']=True
            return EquipmentEvent(**event)
        template,previous=self._equip(db,key,equipment_slot)
        revision=db.execute('SELECT revision FROM inventory_versions WHERE role_id=?',(self.role_id,)).fetchone()[0]
        event=EquipmentEvent(self.role_id,epoch,request_id,key,template,equipment_slot,revision,previous)
        db.execute('INSERT INTO inventory_equipment_commands VALUES(?,?,?,?)',
                   (self.role_id,request_id,fingerprint,json.dumps(asdict(event))))
        return event

    def equipment_bag_messages(self, db, epoch):
        """Current carried/equipped replies in the caller's fenced transaction.

        Stage these before committing equip/task state; unknown cash or encoding
        failure then rolls back the same transaction. Send only after commit.
        """
        if not db.in_transaction:raise ValueError('Equipment replies require an owner transaction')
        return self._bag_reply(db,1,epoch=epoch),self._bag_reply(db,4)

    def unequip(self, key, target_slot=-1):
        self._owned()
        with closing(self.accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            self._unequip(db,key,target_slot)

    def unequip_transaction(self, db, key, target_slot, epoch, request_id):
        """Join owner transaction; historical retry never removes later gear.

        Caller stages current inventory, absolute role attributes and logical
        replies in this same transaction, then commits before delivery.
        """
        if (not db.in_transaction or type(key) is not int or not 0<key<=0x7fffffff
                or type(target_slot) is not int or not -1<=target_slot<self.policy['bag_capacity']
                or not _valid_epoch(epoch) or type(request_id) is not str or not 1<=len(request_id)<=160):
            raise ValueError('Trusted unequip transaction context required')
        if not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
            'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
            (self.role_id,self.account_id,epoch)).fetchone():
            raise ValueError('Unequip role lease mismatch')
        fingerprint=hashlib.sha256(json.dumps(['unequip',key,target_slot],separators=(',',':')).encode()).hexdigest()
        old=db.execute('SELECT fingerprint,event FROM inventory_equipment_commands WHERE role_id=? AND request_id=?',
                       (self.role_id,request_id)).fetchone()
        if old:
            if old[0]!=fingerprint:raise ValueError('Equipment request intent conflict')
            event=json.loads(old[1]);event['replayed']=True
            return UnequipEvent(**event)
        template,previous,slot=self._unequip(db,key,target_slot)
        revision=db.execute('SELECT revision FROM inventory_versions WHERE role_id=?',(self.role_id,)).fetchone()[0]
        event=UnequipEvent(self.role_id,epoch,request_id,key,template,previous,slot,revision)
        db.execute('INSERT INTO inventory_equipment_commands VALUES(?,?,?,?)',
                   (self.role_id,request_id,fingerprint,json.dumps(asdict(event))))
        return event

    def _unequip(self, db, key, target_slot):
        if not db.in_transaction:raise ValueError('Unequip requires an owner transaction')
        item=db.execute('SELECT template_id,equipment_slot FROM inventory_items '
                        'WHERE id=? AND role_id=? AND equipment_slot IS NOT NULL',(key,self.role_id)).fetchone()
        if not item:raise ValueError('Equipment unavailable')
        used = {r[0] for r in db.execute('SELECT slot FROM inventory_items WHERE role_id=?', (self.role_id,))}
        slot = (next((i for i in range(self.policy['bag_capacity']) if i not in used), None)
                if target_slot == -1 else target_slot)
        if slot is None:
            raise ValueError('Bag full')
        if type(slot) is not int or not 0 <= slot < self.policy['bag_capacity'] or slot in used:
            raise ValueError('Unequip target unavailable')
        changed = db.execute('UPDATE inventory_items SET equipment_slot=NULL,slot=? WHERE id=? AND role_id=? AND equipment_slot IS NOT NULL', (slot, key, self.role_id)).rowcount
        if not changed:
            raise ValueError('Equipment unavailable')
        return item[0],item[1],slot

    def _grant_pet(self, db, template_id):
        attr = self.pet_types.get(template_id)
        role = db.execute('SELECT level FROM roles WHERE id=? AND account_id=?',
                          (self.role_id, self.account_id)).fetchone()
        if not role or not attr or int(attr.get('takelevel', 0)) > role[0]:
            raise ValueError('Pet level requirement or unknown pet')
        if db.execute('SELECT COUNT(*) FROM inventory_pets WHERE role_id=? AND released=0', (self.role_id,)).fetchone()[0] >= self.policy['pet_capacity']:
            raise ValueError('Pet column full')
        profile = self.pet_profiles.get(template_id)
        if profile is None:
            raise ValueError('Pet template needs an explicit growth profile rule')
        key = db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)', (self.role_id, template_id, attr['name'])).lastrowid
        pet_growth_store.initialize_pet(db,self.account_id,self.role_id,key,profile,self.growth_rules)
        grade=self.care_rules.initial_grade
        pet_care.initialize(db,self.account_id,self.role_id,key,self.care_rules,grade,
                            self.care_rules.maximum(grade),int(attr['life']))
        pet_battle_care.initialize(db,self.account_id,self.role_id,key,self.battle_care_rules,0)
        pet_traits.initialize(db,self.account_id,self.role_id,key,self.trait_rules,
            self.trait_rules.initial_origin,self.trait_rules.initial_insight,source='new_restoration_pet')
        pet_cake.initialize(db,self.account_id,self.role_id,key,self.cake_rules,0,(0,)*5,source='new_restoration_pet')
        pet_evolution.initialize(db,self.account_id,self.role_id,key,self.evolution_rules,0,source='new_restoration_pet')
        pet_stones.initialize(db,self.account_id,self.role_id,key,self.stone_rules,0,(0,)*5,source='new_restoration_pet')
        pet_skills.initialize(db,self.account_id,self.role_id,key,self.skill_rules,
            self.skill_rules.generate(template_id,grade),grade)
        pet_flags.initialize(db,self.account_id,self.role_id,key,self.flag_rules,self.flag_rules.initial_raw)
        pet_skill_progress.initialize(db,self.account_id,self.role_id,key,self.skill_rules.learning_rules,
                                      self.skill_rules.learning_rules.initial_progress)
        pet_skill_expiry.initialize(db,self.account_id,self.role_id,key,self.skill_rules.expiry_rules,
            self.skill_rules.generate(template_id,grade),())
        pet_blood.initialize(db,self.account_id,self.role_id,key,self.blood_rules,0,grade)
        return key

    def initialize_pet_flags(self, db, pet_id, raw):
        """Trusted one-time import of a complete known byte; unknown stays None."""
        return pet_flags.initialize(db,self.account_id,self.role_id,pet_id,self.flag_rules,raw)

    def require_pet_transferable(self, db, pet_id):
        """Reservation gate only; cross-role delivery needs a trade state machine."""
        flags=pet_flags.load(db,self.account_id,self.role_id,pet_id,self.flag_rules)
        if flags.bound:raise ValueError('Bound pet cannot transfer')
        if flags.raw:raise InventoryNotReady('Other pet flag transfer rules are not restored')
        if db.execute('SELECT fighting FROM inventory_pets WHERE id=?',(pet_id,)).fetchone()[0]:
            raise ValueError('Fighting pet cannot transfer')
        return flags

    def initialize_pet_skills(self, db, pet_id, learned):
        """Explicit known full ordinary learned list; never infer old skills."""
        care=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules)
        return pet_skills.initialize(db,self.account_id,self.role_id,pet_id,self.skill_rules,
                                    pet_skills.PetSkills(0,learned),care.grade)

    def initialize_pet_skill_progress(self, db, pet_id, points):
        """Trusted known historical points, never inferred or reset to zero."""
        care=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules)
        pet_skills.load(db,self.account_id,self.role_id,pet_id,self.skill_rules,care.grade)
        return pet_skill_progress.initialize(db,self.account_id,self.role_id,pet_id,
                                            self.skill_rules.learning_rules,points)

    def initialize_pet_skill_expiry(self, db, pet_id, entries):
        """One complete trusted historical map; () explicitly means permanent."""
        care=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules)
        skills=pet_skills.load(db,self.account_id,self.role_id,pet_id,self.skill_rules,care.grade)
        return pet_skill_expiry.initialize(db,self.account_id,self.role_id,pet_id,
            self.skill_rules.expiry_rules,skills,entries)

    def pet_skill_view(self, db, pet_id, epoch, now_ms):
        """Frozen effective IDs for another owner, at a trusted fixed time."""
        if not db.in_transaction or not _valid_epoch(epoch) or not db.execute(
                'SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
                'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
                (self.role_id,self.account_id,epoch)).fetchone():
            raise ValueError('Timed skills require current owner transaction')
        care=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules)
        skills=pet_skills.load(db,self.account_id,self.role_id,pet_id,self.skill_rules,care.grade)
        expiry=pet_skill_expiry.load(db,self.account_id,self.role_id,pet_id,self.skill_rules.expiry_rules,skills)
        return pet_skill_expiry.view(skills,expiry,now_ms)

    def grant_pet_timed_skill(self, db, command, epoch, now_ms):
        """Join a trusted same-role reward transaction with an explicit deadline."""
        if not isinstance(command,pet_skill_expiry.TimedSkillGrant):
            raise ValueError('Immutable timed skill command required')
        self.pet_skill_view(db,command.pet_id,epoch,now_ms)
        self.pet_progress(db,command.pet_id)
        care=pet_care.load(db,self.account_id,self.role_id,command.pet_id,self.care_rules)
        return pet_skill_expiry.grant(db,self.account_id,self.role_id,command,now_ms,self.skill_rules,care.grade)

    def pet_skill_time_messages(self, db, epoch, now_ms, pet_ids=None):
        """Current clock then current Pet beans, staged inside caller transaction.

        Root uses this for timed refresh/admitted timer events. A timer changes
        no asset state; generation/epoch and current scene guards stay at root.
        """
        clock=game_time_message(now_ms)
        if not db.in_transaction or not _valid_epoch(epoch) or not db.execute(
                'SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
                'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
                (self.role_id,self.account_id,epoch)).fetchone():
            raise ValueError('Timed pet refresh requires current owner transaction')
        if pet_ids is None:
            pet_ids=tuple(row[0] for row in db.execute('SELECT id FROM inventory_pets '
                'WHERE role_id=? AND released=0 ORDER BY id',(self.role_id,)))
        if (type(pet_ids) is not tuple or len(pet_ids)>128
                or any(type(key) is not int or not 0<key<=0x7fffffff for key in pet_ids)
                or len(set(pet_ids))!=len(pet_ids)):
            raise ValueError('Distinct owned timed pet IDs required')
        replies=[clock]
        for key in pet_ids:
            self.pet_skill_view(db,key,epoch,now_ms)
            replies.append((REFRESH_PET,pet_record(self._pet_state(db,key))))
        return tuple(replies)

    def receive_pet_query(self, body, epoch, now_ms):
        """Original c07de query with current trusted clock and fenced snapshot."""
        self._owned();clock=game_time_message(now_ms)
        if type(body) is not bytes or len(body)!=12:
            raise ValueError('Invalid timed pet query payload')
        column,target=struct.unpack('>iQ',body)
        if column!=1 or target not in (0,self.role_id):
            raise ValueError('Timed pet query ownership or column mismatch')
        with closing(self.accounts.connect()) as db:
            db.execute('BEGIN')
            snapshot=self.immutable_snapshot_transaction(db,epoch=epoch)
            replies=[clock,(PET_INFO,struct.pack('>i',1)+compact(len(snapshot.pets))
                +b''.join(pet_record(p.__dict__) for p in snapshot.pets)
                +struct.pack('>iB',snapshot.pet_capacity,0))]
            for pet in snapshot.pets:
                if pet.progress is not None:
                    replies.append((REFRESH_PET_EXP,struct.pack('>iQ',pet.id,pet.progress.state.experience)))
                    if pet.progress.stones is not None:replies.append(stone_attributes_message(pet.id,pet.progress.stones))
                if pet.fighting:replies.append((0xc07d9,struct.pack('>i',pet.id)))
            return replies

    def current_mutation_messages_transaction(self, db, kind, body, epoch, now_ms=None):
        """Current replies for a VERIFIED paid command, without its old action.

        Caller validates the durable command fingerprint and strict current
        resource source first. This method owns no receipt, commit or source
        repair, and never opens another connection or invokes a mutation.
        """
        if (type(kind) is not int or kind not in INVENTORY_CURRENT_MUTATION_TYPES
                or type(body) is not bytes or not _valid_epoch(epoch)):
            raise ValueError('Original admitted mutation and trusted current epoch required')
        target=None
        if kind==MOVE_ITEM:
            if len(body)!=32:raise ValueError('Invalid paid item move payload')
            source,key,slot,destination,to,count,role=struct.unpack('>6iq',body)
            if source!=1 or destination!=1 or key<=0 or count<0 or role not in (-1,0,self.role_id):
                raise ValueError('Paid local bag move identity mismatch')
        elif kind==ARRANGE_BAG:
            if len(body)!=12:raise ValueError('Invalid paid arrange payload')
            column,role=struct.unpack('>iQ',body)
            if column!=1 or role not in (0,self.role_id):raise ValueError('Paid bag column/role mismatch')
        elif kind in (FIGHT_PET,FREE_PET,PET_EVOLVE):
            if len(body)!=4:raise ValueError('Invalid paid pet identity payload')
            target=struct.unpack('>i',body)[0]
        elif kind==REST_PET:
            if body:raise ValueError('Paid pet rest payload must be empty')
        elif kind==USE_ITEM:
            if len(body)!=16:raise ValueError('Invalid paid pet item payload')
            key,target_kind,target=struct.unpack('>iiQ',body)
            if key<=0 or target_kind!=1:raise ValueError('Paid pet item target mismatch')
        elif kind==ADD_PET_POINT:
            if len(body)!=24:raise ValueError('Invalid paid pet allocation payload')
            target,*points=struct.unpack('>6i',body)
            if min(points)<0 or not any(points):raise ValueError('Invalid paid pet allocation values')
        elif kind==RENAME_PET:
            if len(body)<5:raise ValueError('Invalid paid rename payload')
            target=struct.unpack('>i',body[:4])[0]
            try:name,end=read_octets(body,4,limit=32)
            except NeedMoreData:raise ValueError('Truncated paid rename payload') from None
            if end!=len(body):raise ValueError('Trailing paid rename payload')
            name.decode('utf-16le')
        if target is not None and not 0<target<=0x7fffffff:
            raise ValueError('Original positive native pet identity required')
        snapshot=self.immutable_snapshot_transaction(db,epoch=epoch)
        if kind in (MOVE_ITEM,ARRANGE_BAG):return (self._bag_reply(db,1,epoch=epoch),)
        if kind==PET_EVOLVE or kind==USE_ITEM and (pet_cake_effects.was_confirmed_cake(db,self.role_id,target,key)
                or pet_stone_items.was_confirmed_stone(db,self.role_id,target,key)):
            # The legacy shared dispatcher supplies owner monotonic time here.
            # New evolution/cake replies synchronize original UNIX-ms time;
            # deleted cake items are classified through their indexed audit.
            now_ms=self.clock_now_ms()
        clock=game_time_message(now_ms) if now_ms is not None else None
        pets=snapshot.pets
        if any(type(p.fighting) is not int or p.fighting not in (0,1) for p in pets) or sum(p.fighting for p in pets)>1:
            raise ValueError('Current owned pet selection must be unique and explicit')
        if clock is None and any(p.skill_expiry is not None and p.skill_expiry.entries for p in pets):
            raise InventoryNotReady('Timed current pet replies require trusted current milliseconds')
        replies=[(PET_INFO,struct.pack('>i',1)+compact(len(pets))
            +b''.join(pet_record(p.__dict__) for p in pets)+struct.pack('>iB',snapshot.pet_capacity,0))]
        current=next((p for p in pets if p.id==target),None)
        if current is not None:replies.append((REFRESH_PET,pet_record(current.__dict__)))
        elif target is not None:replies.append((REMOVE_PET,struct.pack('>ii',1,target)))
        replies.extend(stone_attributes_message(p.id,p.progress.stones) for p in pets
            if p.progress is not None and p.progress.stones is not None)
        replies.extend((REFRESH_PET_EXP,struct.pack('>iQ',p.id,p.progress.state.experience))
            for p in pets if p.progress is not None)
        selected=next((p for p in pets if p.fighting),None)
        replies.append((0xc07d9,struct.pack('>i',selected.id)) if selected else (0xc07db,b''))
        if kind in (USE_ITEM,PET_EVOLVE):replies.append(self._bag_reply(db,1,epoch=epoch))
        if clock is not None:replies.insert(0,clock)
        return tuple(replies)

    def pet_skill_progress_messages(self, db, epoch, pet_ids=None):
        """Current progress in caller transaction; missing old values refuse."""
        if not db.in_transaction or not _valid_epoch(epoch) or not db.execute(
                'SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
                'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
                (self.role_id,self.account_id,epoch)).fetchone():
            raise ValueError('Pet progress reply requires current owner transaction')
        if pet_ids is None:
            pet_ids=tuple(row[0] for row in db.execute('SELECT id FROM inventory_pets '
                'WHERE role_id=? AND released=0 ORDER BY id',(self.role_id,)))
        if (type(pet_ids) is not tuple or any(type(key) is not int or not 0<key<=0x7fffffff for key in pet_ids)
                or len(set(pet_ids))!=len(pet_ids)):
            raise ValueError('Known distinct pet IDs required for expansion progress')
        rows=tuple((key,pet_skill_progress.load(db,self.account_id,self.role_id,key,
                    self.skill_rules.learning_rules).points) for key in pet_ids)
        return (skill_progress_message(rows),)

    def receive_pet_skill_progress(self, body, epoch):
        self._owned()
        if type(body) is not bytes or body:
            raise ValueError('Pet expansion progress query has an empty original payload')
        with closing(self.accounts.connect()) as db:
            db.execute('BEGIN')
            return list(self.pet_skill_progress_messages(db,epoch))

    def learn_pet_skill(self, db, key, pet_id, epoch, settlement_id, expected_version, draws, *, options=None,now_ms=None):
        """Join current role transaction: known pet, one book, skills and receipt.

        Two fixed server draws0..9999 belong to the admitted command, never wire input.
        None expected_version is reserved for the context-aware native adapter:
        it acts on current owner state and dedupes by the same stable request ID.
        """
        if (not db.in_transaction or not _valid_epoch(epoch)
                or type(pet_id) is not int or not 0<pet_id<=0x7fffffff):
            raise ValueError('Trusted pet skill owner transaction required')
        if not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
            'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
            (self.role_id,self.account_id,epoch)).fetchone():
            raise ValueError('Pet skill role lease mismatch')
        # A complete native refresh must never replace unknown old resources.
        self.pet_progress(db,pet_id)
        care=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules)
        return pet_skills.learn_book(db,self.account_id,self.role_id,pet_id,key,settlement_id,
            expected_version,draws,self.skill_rules,care.grade,self.flag_rules,options=options,now_ms=now_ms)

    def receive_pet_skill_book(self, body, epoch, settlement_id, draws, now_ms=None, precommit=None):
        """Native c07ff Adapter; caller validates nonbattle state/request context."""
        self._owned()
        if type(settlement_id) is not str or not 1<=len(settlement_id)<=160:
            raise ValueError('Trusted stable skill-book request ID required')
        request=decode_skill_book_request(body)
        pet,key=request.pet_id,request.item_key
        with closing(self.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            replayed=db.execute('SELECT 1 FROM inventory_pet_skill_receipts WHERE role_id=? AND settlement_id=?',
                (self.role_id,settlement_id)).fetchone() is not None
            receipt=self.learn_pet_skill(db,key,pet,epoch,settlement_id,None,draws,options=request.options,now_ms=now_ms)
            self._run_precommit(db,precommit,replayed=replayed,epoch=epoch)
            current_pet=self._pet_state(db,pet)
            replies=[(REFRESH_PET,pet_record(current_pet)),self._bag_reply(db,1,epoch=epoch)]
            if now_ms is not None:
                replies.insert(0,game_time_message(now_ms))
            elif current_pet.get('skill_expiry') is not None and current_pet['skill_expiry'].entries:
                raise InventoryNotReady('Timed pet notification requires current trusted server milliseconds')
            if db.execute('SELECT 1 FROM inventory_pet_skill_progress WHERE pet_id=?',(pet,)).fetchone():
                replies.extend(self.pet_skill_progress_messages(db,epoch,(pet,)))
            if receipt.flags_after is not None:
                # The original complete column converter rebuilds +69, whereas
                # SRefreshPetFlag and SRefreshPetData preserve the old cache.
                pets=[self._pet_state(db,row[0]) for row in db.execute(
                    'SELECT id FROM inventory_pets WHERE role_id=? AND released=0 ORDER BY id',
                    (self.role_id,)).fetchall()]
                if now_ms is None and any(p.get('skill_expiry') is not None and p['skill_expiry'].entries for p in pets):
                    raise InventoryNotReady('Timed pet column requires current trusted server milliseconds')
                replies.append((PET_INFO,struct.pack('>i',1)+compact(len(pets))
                    +b''.join(pet_record(p) for p in pets)+struct.pack('>iB',self.policy['pet_capacity'],0)))
                replies.extend((0xc07d9,struct.pack('>i',p['id'])) for p in pets if p['fighting'])
        return replies

    def initialize_pet_care(self, db, pet_id, grade, loyalty=None, lifetime=None):
        """Explicit legacy import requires actual care values; never regenerate."""
        if loyalty is None or lifetime is None:
            raise ValueError('Legacy care initialization requires explicit loyalty and lifetime')
        return pet_care.initialize(db,self.account_id,self.role_id,pet_id,self.care_rules,
                                   grade,loyalty,lifetime)

    def initialize_pet_traits(self, db, pet_id, origin, insight):
        """One-time authoritative legacy import; unknown values are never filled."""
        return pet_traits.initialize(db,self.account_id,self.role_id,pet_id,self.trait_rules,
                                     origin,insight,source='explicit_known_import')

    def initialize_pet_cakes(self, db, pet_id, count, added_aptitudes):
        """Trusted complete import; current profile already includes these historical additions."""
        return pet_cake.initialize(db,self.account_id,self.role_id,pet_id,self.cake_rules,count,
            added_aptitudes,source='explicit_known_import')

    def change_pet_care(self, db, pet_id, settlement_id, expected_version, operation, value):
        return pet_care.change(db,self.account_id,self.role_id,pet_id,self.care_rules,
                               settlement_id,expected_version,operation,value)

    def initialize_pet_battle_care_counter(self, db, pet_id, mod3):
        """Explicit authoritative legacy import; never infer prior battle count."""
        return pet_battle_care.initialize(db,self.account_id,self.role_id,pet_id,self.battle_care_rules,mod3)

    def pet_battle_care_counter(self, db, pet_id):
        return pet_battle_care.load(db,self.account_id,self.role_id,pet_id,self.battle_care_rules)

    def settle_pet_battle_care(self, db, event, epoch):
        """Trusted finalized battle event, before admission growth/resources change."""
        self.immutable_snapshot_transaction(db,epoch=epoch)
        return pet_battle_care.settle(db,self.account_id,self.role_id,event,self.battle_care_rules,
                                     self.care_rules,self.growth_rules,self.blood_rules)

    def initialize_pet_growth(self, db, pet_id):
        """Explicit one-time legacy initialization; never automatically rerolls."""
        row = db.execute('SELECT template_id FROM inventory_pets WHERE id=? AND role_id=?', (pet_id,self.role_id)).fetchone()
        if not row or row[0] not in self.pet_profiles:
            raise ValueError('Pet growth profile unavailable')
        return pet_growth_store.initialize_pet(db,self.account_id,self.role_id,pet_id,
                                              self.pet_profiles[row[0]],self.growth_rules)

    def pet_progress(self, db, pet_id):
        grade=None
        if db.execute('SELECT 1 FROM inventory_pet_blood WHERE pet_id=?',(pet_id,)).fetchone():
            grade=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules).grade
        return pet_growth_store.load_pet(db,self.account_id,self.role_id,pet_id,self.growth_rules,
            blood_rules=self.blood_rules,grade=grade)

    def initialize_pet_blood(self, db, pet_id, power):
        """Trusted complete ordinary import with a known BASE aptitude profile.

        Import preserves current absolute HP/MP. It never credits a historical
        consumable or guesses whether an old profile already includes a bonus.
        """
        care=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules)
        self.pet_progress(db,pet_id)
        result=pet_blood.initialize(db,self.account_id,self.role_id,pet_id,self.blood_rules,power,care.grade)
        current=self.pet_progress(db,pet_id)
        if current.state.hp>current.attributes.max_hp or current.state.mp>current.attributes.max_mp:
            raise ValueError('Imported blood profile cannot contain out-of-range current resources')
        return result

    def selected_fighting_pet(self, db):
        """Freeze the selected owned pet within the caller's existing transaction.

        None means no active selected instance. Legacy instances still return
        their key with progress=None so reward decisions can retain an audit and
        explicitly reconcile the unknown baseline instead of picking another pet.
        """
        if not db.in_transaction or not db.execute('SELECT 1 FROM roles WHERE id=? AND account_id=?',
                (self.role_id,self.account_id)).fetchone():
            raise ValueError('Selected pet requires an owned role transaction')
        row=db.execute('SELECT id FROM inventory_pets WHERE role_id=? AND fighting=1 AND released=0',
                       (self.role_id,)).fetchone()
        return self.read_pet_state(db,row[0]) if row else None

    def read_pet_state(self, db, pet_id):
        """Read one owned active pet as a frozen message in the current txn.

        Missing, foreign or released instance returns None; an invalid role or
        transaction is rejected. Existing unknown growth/care remains unknown.
        """
        if (not db.in_transaction or type(pet_id) is not int or pet_id<=0
                or not db.execute('SELECT 1 FROM roles WHERE id=? AND account_id=?',
                                  (self.role_id,self.account_id)).fetchone()):
            raise ValueError('Pet snapshot requires an owned role transaction')
        row=db.execute('SELECT id FROM inventory_pets WHERE id=? AND role_id=? AND released=0',
                       (pet_id,self.role_id)).fetchone()
        return PetState(**self._pet_state(db,pet_id)) if row else None

    def change_pet_growth(self, db, pet_id, settlement_id, expected_version, operation, value):
        grade=None
        if db.execute('SELECT 1 FROM inventory_pet_blood WHERE pet_id=?',(pet_id,)).fetchone():
            grade=pet_care.load(db,self.account_id,self.role_id,pet_id,self.care_rules).grade
        return pet_growth_store.change_pet(db,self.account_id,self.role_id,pet_id,self.growth_rules,
            settlement_id,expected_version,operation,value,blood_rules=self.blood_rules,grade=grade)

    def grant_pet(self, template_id):
        self._owned()
        with closing(self.accounts.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            return self._grant_pet(db, template_id)

    def rename_pet(self, key, name, *, precommit=None):
        self._owned()
        with closing(self.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self._rename_pet(db,key,name)
            self._run_precommit(db,precommit,replayed=False)

    def _rename_pet(self, db, key, name):
        if not 1 <= len(name) <= self.policy['pet_name_max_chars'] or not all(c.isalnum() for c in name):
            raise ValueError('Invalid pet name')
        if not db.execute('UPDATE inventory_pets SET name=? WHERE id=? AND role_id=? AND released=0', (name, key, self.role_id)).rowcount:
            raise ValueError('Pet unavailable')

    def fight_pet(self, key=None, *, precommit=None):
        self._owned()
        with closing(self.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self._fight_pet(db,key)
            self._run_precommit(db,precommit,replayed=False)

    def _fight_pet(self, db, key=None):
        if key is not None and not db.execute('SELECT 1 FROM inventory_pets WHERE id=? AND role_id=? AND released=0', (key, self.role_id)).fetchone():
            raise ValueError('Pet unavailable')
        if key is not None and db.execute('SELECT 1 FROM inventory_pet_care WHERE pet_id=?',(key,)).fetchone():
            care=pet_care.load(db,self.account_id,self.role_id,key,self.care_rules)
            # Original help36001/36002 explicitly allows low-life pets to stay
            # selected; the ordinary battle care gate requires lifetime>=50.
            if care.loyalty==0:
                raise ValueError('Pet loyalty exhausted')
        db.execute('UPDATE inventory_pets SET fighting=0 WHERE role_id=?', (self.role_id,))
        if key is not None:
            db.execute('UPDATE inventory_pets SET fighting=1 WHERE id=?', (key,))

    def free_pet(self, key, *, precommit=None):
        self._owned()
        with closing(self.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            self._free_pet(db,key)
            self._run_precommit(db,precommit,replayed=False)

    def _free_pet(self, db, key):
        pet = db.execute('SELECT fighting FROM inventory_pets WHERE id=? AND role_id=? AND released=0',
                         (key,self.role_id)).fetchone()
        if not pet or pet[0]:
            raise ValueError('Pet unavailable or still fighting')
        # Keep the instance and settlement audit; do not invalidate reward FK.
        db.execute('UPDATE inventory_pets SET released=1 WHERE id=?',(key,))

    def receive(self, kind, body, precommit=None):
        if kind==PET_EVOLVE:
            pet=decode_pet_evolution_request(body)
            if precommit is None:raise InventoryNotReady('Evolution requires accepted-command precommit or receive_pet_evolution')
            with closing(self.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                self.immutable_snapshot_transaction(db,epoch=self.epoch)
                current=self.read_pet_state(db,pet)
                if current is None or current.progress is None:raise ValueError('Current evolution target required')
                identity=f'evolution-current:{pet}:{current.progress.state.version}'
                receipt=self.evolve_pet(db,pet,self.epoch,identity,current.progress.state.version)
                if receipt.replayed:raise ValueError('Fresh common evolution command conflicts with committed asset fact')
                self._run_precommit(db,precommit,replayed=False)
                return self._evolution_messages(db,receipt,self.epoch)
        self._owned()
        if kind==LEARN_SKILL_BOOK:
            raise InventoryNotReady('Pet skill books require trusted epoch/request/draw context via receive_pet_skill_book')
        if kind==QUERY_SKILL_PROGRESS:
            return self.receive_pet_skill_progress(body,self.epoch)
        if kind==REQUEST_ENDURES:
            if len(body)!=4:raise ValueError('Invalid endurance query')
            column=struct.unpack('>i',body)[0]
            if column not in (1,4):raise InventoryNotReady('Endurance column not restored')
            with closing(self.accounts.connect()) as db:
                db.execute('BEGIN')
                rows=db.execute('SELECT id,template_id,equipment_slot FROM inventory_items WHERE role_id=? ORDER BY id',
                                (self.role_id,)).fetchall()
                states=[]
                for key,template,slot in rows:
                    if (slot is not None)==(column==4) and self._ordinary_equipment(template):
                        if not db.execute('SELECT 1 FROM inventory_equipment_conditions WHERE item_key=?',(key,)).fetchone():
                            raise InventoryNotReady('Legacy equipment condition is unknown')
                        states.append((key,self.equipment_condition(db,key)))
                return [endurance_refresh(column,tuple((k,s.current) for k,s in states))]+[
                    maximum_refresh(column,k,s.maximum) for k,s in states]
        if kind == ITEM_TIPS:
            if len(body) != 8:
                raise ValueError('Invalid item-tips request')
            column,key = struct.unpack('>ii',body)
            if column not in (1,4):
                raise InventoryNotReady('Item tip column not restored')
            with closing(self.accounts.connect()) as db:
                db.execute('BEGIN')
                row=db.execute('SELECT template_id,quality,equipment_slot FROM inventory_items '
                    'WHERE id=? AND role_id=?',(key,self.role_id)).fetchone()
                if row is None or (row[2] is not None)!=(column==4):
                    raise ValueError('Item tips ownership or column mismatch')
                template,quality,_=row
                if template in self.detail_rules.templates:
                    if not db.execute('SELECT 1 FROM inventory_equipment_details WHERE item_key=?',(key,)).fetchone():
                        raise InventoryNotReady('Legacy equipment detail is unknown')
                    detail=equipment_detail.encode(template,self.equipment_detail(db,key),
                        self.equipment_condition(db,key),self.detail_rules)
                elif template == 32000 and column==1:
                    detail=b''
                elif template in tuple(range(32001,32014))+(32042,32043) and column==1:
                    if quality is None:
                        raise InventoryNotReady('Item quality metadata is missing')
                    detail=struct.pack('>i',quality)
                else:
                    raise InventoryNotReady('Item detail type requires a separate native bean')
            return [(ITEM_TIPS_REPLY,struct.pack('>ii',column,key)+octets(detail))]
        if kind == USE_ITEM:
            if len(body) != 16:
                raise ValueError('Invalid use-item request')
            key,target_kind,target_id = struct.unpack('>iiQ',body)
            if key <= 0:
                raise ValueError('Invalid use-item key')
            if target_kind != 1:
                raise InventoryNotReady('Role consumables require owner epoch/request context via receive_role_consumable')
            with closing(self.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                carried=db.execute('SELECT template_id FROM inventory_items WHERE id=? AND role_id=? AND equipment_slot IS NULL',
                    (key,self.role_id)).fetchone()
                cake=None;stone=None
                if carried and carried[0] in self.cake_effect_rules.templates:
                    if precommit is None:
                        raise InventoryNotReady('Generic cake needs the accepted-command precommit; explicit callers use receive_pet_consumable')
                    before=self.read_pet_state(db,target_id)
                    if before is None or before.progress is None:raise ValueError('Known owned cake target required')
                    # The shared dispatcher owns accepted-command dedupe. This
                    # internal fact key belongs to the monotonic pre-write
                    # source version; it is not a client retry ID substitute.
                    fact=f'cake-current:{target_id}:{before.progress.state.version}:{key}'
                    try:cake=self.use_pet_cake(db,key,target_id,self.epoch,fact,before.progress.state.version)
                    except pet_cake_effects.CakeUnavailable as error:
                        args=((self.cake_effect_rules.item_names[carried[0]-31268],) if error.message_id==145136 else ())
                        return [cake_notice(error.message_id,args)]
                    if cake.replayed:raise ValueError('Current cake fact already committed; reconcile accepted command')
                    pet=self._pet_state(db,target_id)
                elif carried and carried[0]==70053:
                    if precommit is None:
                        raise InventoryNotReady('Generic clearing needs accepted-command precommit; explicit callers use receive_pet_consumable')
                    before=self.read_pet_state(db,target_id)
                    if before is None or before.progress is None:raise ValueError('Known owned stone target required')
                    fact=f'stone-current:{target_id}:{before.progress.state.version}:{key}'
                    try:stone=self.use_pet_stone(db,key,target_id,self.epoch,fact,expected_version=before.progress.state.version)
                    except pet_stone_items.StoneUnavailable as error:return [stone_notice(error.message_id)]
                    if stone.replayed:raise ValueError('Current stone fact already committed; reconcile accepted command')
                    pet=self._pet_state(db,target_id)
                else:pet=self._use_pet_consumable(db,key,target_id)
                self._run_precommit(db,precommit,replayed=False)
                refresh=REFRESH_PET,pet_record(pet)
                bag=self._bag_reply(db,1)
                replies=[refresh,bag]
                if stone is not None:
                    replies.insert(0,game_time_message(self.clock_now_ms()))
                    replies.append(stone_attributes_message(target_id,pet['progress'].stones))
                    replies.append(stone_notice(150456))
                if cake is not None:
                    replies.insert(0,game_time_message(self.clock_now_ms()))
                    replies.append(cake_notice(145135,(self.cake_effect_rules.names[cake.prediction.attribute_index],
                        str(cake.actual_gain),str(20-cake.cake_after.count))))
            return replies
        if kind == FREE_PET:
            if len(body) != 4:
                raise ValueError('Invalid free-pet request')
            key = struct.unpack('>i',body)[0]
            with closing(self.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                self._free_pet(db,key)
                self._run_precommit(db,precommit,replayed=False)
                replies=[(REMOVE_PET,struct.pack('>ii',1,key))]
            return replies
        if kind == ARRANGE_BAG:
            if len(body) != 12:
                raise ValueError('Invalid arrange-bag request')
            column,target = struct.unpack('>iQ',body)
            if column != 1 or target not in (0,self.role_id):
                raise ValueError('Unsupported arrange target')
            with closing(self.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                self._arrange_bag(db)
                self._run_precommit(db,precommit,replayed=False)
                replies=[self._bag_reply(db,1)]
            return replies
        if kind == ADD_PET_POINT:
            if len(body) != 24:
                raise ValueError('Invalid pet point request')
            key,*increments = struct.unpack('>6i',body)
            if key <= 0 or min(increments) < 0 or not any(increments):
                raise ValueError('Invalid pet point allocation')
            with closing(self.accounts.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                previous = self.pet_progress(db,key)
                progress = self.change_pet_growth(db,key,f'pet-point:{key}:{previous.state.version}',
                    previous.state.version,'allocate',tuple(increments))
                pet = self._pet_state(db,key)
                self._run_precommit(db,precommit,replayed=False)
                replies=[(REFRESH_PET,pet_record(pet)),
                         (REFRESH_PET_EXP,struct.pack('>iQ',key,progress.state.experience))]
            return replies
        if kind in (EQUIP_ITEM, UNEQUIP_ITEM):
            if len(body) != 8:
                raise ValueError('Invalid equipment request')
            key, slot = struct.unpack('>ii', body)
            with closing(self.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                if kind == EQUIP_ITEM:self._equip(db,key,slot)
                else:self._unequip(db,key,slot)
                self._run_precommit(db,precommit,replayed=False)
                replies=self.equipment_bag_messages(db,self.epoch)
            return list(replies)
        if kind == MOVE_ITEM:
            if len(body) != 32:
                raise ValueError('Invalid item move length')
            source_bag, key, source_slot, target_bag, target_slot, count, target_role = struct.unpack('>6iq', body)
            if target_role not in (-1, 0, self.role_id):
                raise ValueError('Cross-role move unsupported')
            if source_bag != 1 or target_bag != 1:
                raise InventoryNotReady('Only local carried-bag moves are implemented')
            with closing(self.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                self._move_item(db,key,target_slot,count,source_slot)
                self._run_precommit(db,precommit,replayed=False)
                replies=[self._bag_reply(db,1)]
            return replies
        if kind == REST_PET:
            if body:
                raise ValueError('Invalid pet rest request')
            with closing(self.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                self._fight_pet(db)
                self._run_precommit(db,precommit,replayed=False)
                replies=[(0xc07db,b'')]
            return replies
        if kind == FIGHT_PET:
            if len(body) != 4:
                raise ValueError('Invalid fight pet request')
            key = struct.unpack('>i', body)[0]
            with closing(self.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                pet=self._pet_state(db,key)
                level=db.execute('SELECT level FROM roles WHERE id=? AND account_id=?',(self.role_id,self.account_id)).fetchone()[0]
                if int(self.pet_types[pet['template_id']].get('uselevel',0))>level:
                    raise ValueError('Pet cannot fight at this role level')
                self._fight_pet(db,key)
                self._run_precommit(db,precommit,replayed=False)
                replies=[(0xc07d9,body)]
            return replies
        if kind == RENAME_PET:
            if len(body) < 5:
                raise ValueError('Invalid pet rename request')
            key = struct.unpack('>i', body[:4])[0]
            try:
                name, end = read_octets(body, 4, limit=32)
            except NeedMoreData:
                raise ValueError('Truncated pet rename') from None
            if end != len(body):
                raise ValueError('Trailing pet rename data')
            with closing(self.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                self._rename_pet(db,key,name.decode('utf-16le'))
                self._run_precommit(db,precommit,replayed=False)
                replies=[(0xc07e3,struct.pack('>Qi',self.role_id,key)+octets(name))]
            return replies
        if len(body) != 12:
            raise ValueError('Invalid inventory query length')
        column, target = struct.unpack('>iQ', body)
        if target not in (0, self.role_id):
            raise ValueError('Inventory ownership mismatch')
        if column != 1 and not (kind == QUERY_BAG and column == 4):
            raise InventoryNotReady('Unconfirmed inventory column')
        # Do not silently hide persisted data with an empty, fabricated reply.
        if kind == QUERY_BAG:
            with closing(self.accounts.connect()) as db:
                db.execute('BEGIN')
                return [self._bag_reply(db,column)]
        if kind == QUERY_PETS:
            state=self.snapshot()
            replies = [(PET_INFO, struct.pack('>i', column) + compact(len(state['pets']))
                     + b''.join(pet_record(p) for p in state['pets'])
                     + struct.pack('>iB', state['pet_capacity'], 0))]
            for pet in state['pets']:
                if pet.get('progress') is not None:
                    replies.append((REFRESH_PET_EXP,struct.pack('>iQ',pet['id'],pet['progress'].state.experience)))
                if pet['fighting']:
                    replies.append((0xc07d9,struct.pack('>i',pet['id'])))
            return replies
        raise ValueError('Unknown inventory query')
