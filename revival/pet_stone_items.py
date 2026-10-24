"""Atomic original stone/clearing items; random input belongs to admitted commands."""
from dataclasses import dataclass,asdict,replace
import hashlib
import json
import pet_growth_store
import pet_stones


class StoneUnavailable(ValueError):
    def __init__(self,message_id):
        self.message_id=message_id
        super().__init__('Stone has no admissible effect: '+str(message_id))


@dataclass(frozen=True)
class StoneReceipt:
    request_id: str
    pet_id: int
    item_key: int
    item_template: int
    draws: object
    before: object
    after: object
    policy: str
    replayed: bool=False


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_stone_receipts(
        role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL,result TEXT NOT NULL,pet_id INTEGER NOT NULL REFERENCES inventory_pets(id),
        item_key INTEGER NOT NULL,item_template INTEGER NOT NULL,PRIMARY KEY(role_id,request_id));
        CREATE INDEX IF NOT EXISTS inventory_pet_stone_use_index ON inventory_pet_stone_receipts(role_id,pet_id,item_key);''')


def was_confirmed_stone(db,role,pet,key):
    return db.execute('SELECT 1 FROM inventory_pet_stone_receipts WHERE role_id=? AND pet_id=? AND item_key=? LIMIT 1',
        (role,pet,key)).fetchone() is not None


def use(db,inv,pet,key,request_id,draws,expected_version):
    rules=inv.stone_rules
    if (type(pet) is not int or not 0<pet<=0x7fffffff or type(key) is not int or not 0<key<=0x7fffffff
            or type(request_id) is not str or not 1<=len(request_id)<=160
            or expected_version is not None and (type(expected_version) is not int or not 0<=expected_version<0x7fffffff)):
        raise ValueError('Owned pet/item and stable admitted stone command required')
    if draws is not None:rules.validate_draws(draws)
    fingerprint=hashlib.sha256(json.dumps([pet,key,expected_version,rules.revision,
        inv.growth_rules.revision,inv.blood_rules.revision]).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result,pet_id,item_key,item_template FROM inventory_pet_stone_receipts WHERE role_id=? AND request_id=?',
        (inv.role_id,request_id)).fetchone()
    if old:
        value=json.loads(old[1]);captured=tuple(value['draws']) if value['draws'] is not None else None
        if (old[0]!=fingerprint or old[2:4]!=(pet,key) or old[4]!=value['item_template']
                or value['policy']!=rules.revision or draws is not None and draws!=captured):
            raise ValueError('Stone command intent or captured draws conflict')
        value['draws']=captured
        for field in ('before','after'):
            value[field]=pet_growth_store.decode_progress(value[field],inv.role_id,pet,inv.growth_rules,inv.blood_rules)
        return StoneReceipt(**value,replayed=True)
    current=inv.read_pet_state(db,pet)
    if (current is None or any(v is None for v in (current.progress,current.care,current.traits,current.skills,
            current.flags,current.skill_expiry,current.skill_progress,current.cake,current.evolution))
            or current.progress.blood is None or current.progress.stones is None
            or type(current.progress.state.version) is not int or not 0<=current.progress.state.version<0x7fffffff
            or current.progress.stones.version>=0x7fffffff
            or expected_version is not None and expected_version!=current.progress.state.version):
        raise ValueError('Known complete current stone/blood/growth sources required')
    item=db.execute('SELECT template_id,quantity FROM inventory_items WHERE id=? AND role_id=? AND equipment_slot IS NULL',
        (key,inv.role_id)).fetchone()
    role=db.execute('SELECT level FROM roles WHERE id=? AND account_id=?',(inv.role_id,inv.account_id)).fetchone()
    if not item or item[0] not in rules.templates or not role or role[0]<int(inv.items[item[0]]['needLevel']):
        raise ValueError('Owned carried named stone/clearing item and item level required')
    before=current.progress;stones=before.stones
    if item[0]==70052:
        rules.validate_draws(draws)
        if stones.count>=rules.maximum_count:raise StoneUnavailable(150453)
        added=rules.additions(draws)
        after_stones=pet_stones.PetStones(stones.version+1,stones.count+1,
            tuple(a+b for a,b in zip(stones.added_aptitudes,added)))
        growth=before.profile.growth_raw+rules.growth_per_stone
    else:
        if draws is not None:raise ValueError('Clearing cannot carry random draws')
        if stones.count==0:raise StoneUnavailable(150483)
        after_stones=pet_stones.PetStones(stones.version+1,0,(0,)*5)
        growth=before.profile.growth_raw-rules.growth_per_stone*stones.count
    profile=replace(before.profile,growth_raw=growth)
    planned=pet_growth_store._project(inv.role_id,pet,profile,before.state,inv.growth_rules,inv.blood_rules,before.blood,after_stones)
    if (not 0<=before.state.hp<=before.attributes.max_hp or not 0<=before.state.mp<=before.attributes.max_mp
            or item[0]==70052 and (planned.attributes.max_hp<before.attributes.max_hp or planned.attributes.max_mp<before.attributes.max_mp)
            or item[0]==70053 and (planned.attributes.max_hp>before.attributes.max_hp or planned.attributes.max_mp>before.attributes.max_mp)):
        raise ValueError('Valid current resources and monotone stone caps required')
    state=replace(before.state,version=before.state.version+1,
        hp=min(before.state.hp,planned.attributes.max_hp),mp=min(before.state.mp,planned.attributes.max_mp))
    after=pet_growth_store._project(inv.role_id,pet,profile,state,inv.growth_rules,inv.blood_rules,before.blood,after_stones)
    old_growth=db.execute('SELECT profile,state FROM inventory_pet_growth WHERE pet_id=? AND revision=?',
        (pet,inv.growth_rules.revision)).fetchone()
    old_stone=db.execute('SELECT state FROM inventory_pet_stones WHERE pet_id=? AND policy=?',(pet,rules.revision)).fetchone()
    if db.execute('UPDATE inventory_pet_growth SET profile=?,state=? WHERE pet_id=? AND revision=? AND profile=? AND state=?',
            (json.dumps(asdict(profile)),json.dumps(asdict(state)),pet,inv.growth_rules.revision,*old_growth)).rowcount!=1:
        raise ValueError('Stone growth source changed')
    if db.execute('UPDATE inventory_pet_stones SET state=? WHERE pet_id=? AND policy=? AND state=?',
            (json.dumps(asdict(after_stones)),pet,rules.revision,old_stone[0])).rowcount!=1:
        raise ValueError('Independent stone source changed')
    inv._consume_item(db,key,1)
    db.execute('INSERT INTO inventory_versions VALUES(?,1) ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(inv.role_id,))
    receipt=StoneReceipt(request_id,pet,key,item[0],draws,before,after,rules.revision)
    value=asdict(receipt);value.pop('replayed')
    value['before']=pet_growth_store.encode_progress(before);value['after']=pet_growth_store.encode_progress(after)
    db.execute('INSERT INTO inventory_pet_stone_receipts VALUES(?,?,?,?,?,?,?)',
        (inv.role_id,request_id,fingerprint,json.dumps(value),pet,key,item[0]))
    return receipt
