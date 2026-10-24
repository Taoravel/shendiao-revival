"""Original cake preview arithmetic and atomic supported-state confirmed consumption."""
from dataclasses import dataclass,asdict,replace
from fractions import Fraction
from types import MappingProxyType
import json
import struct
import hashlib
from inspect_client import OUT
import pet_growth_store
from pet_cake import PetCakeHistory


def _f32(value):return struct.unpack('<f',struct.pack('<f',float(value)))[0]
def _ftol(value):return int(float(value)) # original helper stores double before cvttsd2si


@dataclass(frozen=True)
class CakePrediction:
    error: int
    client_gain: object
    base_gain: int
    ratio_index: object
    attribute_index: int


class CakeUnavailable(ValueError):
    def __init__(self,message_id):
        self.message_id=message_id
        super().__init__('Cake has no admissible effect: '+str(message_id))


@dataclass(frozen=True)
class EffectRules:
    revision: str
    templates: tuple
    pets: object
    percentages: tuple
    names: tuple
    item_names: tuple

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/pet-cake-effects-v1.json').read_text(encoding='utf-8'))
        if policy['revision']!='2026-10-23.pet-cake-effects.1' or policy['templates']!=[31268,31269,31270,31271,31272]:
            raise ValueError('Cake effect policy requires review')
        def rows(name):return json.loads((OUT/f'catalogs/knight.gsp.{name}.json').read_text(encoding='utf-8'))
        cakes=rows('pet.cpetcake')
        if tuple((int(r['attributes']['id']),int(r['attributes']['ratio'])) for r in cakes)!=tuple((i+1,i) for i in range(100)):
            raise ValueError('Original cake ratio table changed')
        percentages=tuple(int(r['attributes']['percentage']) for r in cakes)
        items={int(r['attributes']['id']):r['attributes'] for r in rows('item.citemattr')}
        for key in policy['templates']:
            if tuple(int(items[key][n]) for n in ('itemtypeid','needLevel','outbattleuse'))!=(129,1,2):
                raise ValueError('Original named cake item gates changed')
        pets={}
        for row in rows('pet.cpetattr'):
            a=row['attributes']
            pets[int(a['id'])]=(int(a['kind']),tuple((int(a[n+'aptmin']),int(a[n+'aptmax']))
                for n in ('attack','defend','phyforce','magic','speed')))
        strings={int(r['attributes']['id']):r['attributes']['msg'] for r in rows('message.cstringres')}
        return cls(policy['revision'],tuple(policy['templates']),MappingProxyType(pets),percentages,
            tuple(strings[2707+i] for i in range(5)),tuple(items[key]['name'] for key in policy['templates']))

    def predict(self,template,item,effective_aptitudes,permille,count,*,stone=(0,)*5):
        if (type(template) is not int or template not in self.pets or type(item) is not int or item not in self.templates
                or type(effective_aptitudes) is not tuple or len(effective_aptitudes)!=5
                or type(stone) is not tuple or len(stone)!=5
                or any(type(v) is not int or not 0<=v<=0x7fffffff for v in (*effective_aptitudes,*stone))
                or any(extra>current for extra,current in zip(stone,effective_aptitudes))
                or type(permille) is not int or not 0<=permille<=150 or type(count) is not int or not 0<=count<=20):
            raise ValueError('Known original supported cake prediction inputs required')
        index=item-31268
        if count==20:return CakePrediction(145133,None,0,None,index)
        kind,ranges=self.pets[template]
        if kind==2:return CakePrediction(145139,None,0,None,index)
        lo,hi=ranges[index];span=hi-lo
        current=_f32(effective_aptitudes[index]-stone[index]);c=Fraction.from_float(current)
        factor=Fraction(1000+permille,1000)
        if _ftol(c)==_ftol(_f32(hi*factor)):
            return CakePrediction(145137,None,0,None,index)
        if span==0:return CakePrediction(0,0,0,None,index)
        if permille==0:base=_ftol(c)
        else:
            unscaled=Fraction.from_float(_f32(c/factor))
            base=_ftol(c-_ftol(c-unscaled))
        ratio_index=max(0,_ftol(Fraction(base-lo,span)*100))
        if ratio_index>=100:return CakePrediction(0,0,0,ratio_index,index)
        rate=Fraction.from_float(_f32(Fraction(self.percentages[ratio_index],10000)))
        base_gain=_ftol(rate*span)
        # Original keeps its final scaling factor as a stored double.
        target=_ftol((base+base_gain)*Fraction.from_float(float(factor)))
        gain=_ftol(Fraction(target)-c)
        return CakePrediction(0,gain,base_gain,ratio_index,index)


@dataclass(frozen=True)
class CakeReceipt:
    request_id: str
    pet_id: int
    item_key: int
    item_template: int
    prediction: CakePrediction
    actual_gain: int
    before: object
    after: object
    cake_before: PetCakeHistory
    cake_after: PetCakeHistory
    policy: str
    replayed: bool=False


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_cake_receipts(
        role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL,result TEXT NOT NULL,pet_id INTEGER REFERENCES inventory_pets(id),
        item_key INTEGER,PRIMARY KEY(role_id,request_id));''')
    # Startup-only audit index migration. Fields are copied from complete
    # existing receipt identities, never inferred from current/deleted items.
    columns={r[1] for r in db.execute('PRAGMA table_info(inventory_pet_cake_receipts)')}
    for name in ('pet_id','item_key'):
        if name not in columns:db.execute(f'ALTER TABLE inventory_pet_cake_receipts ADD COLUMN {name} INTEGER')
    for role,request,body in db.execute('SELECT role_id,request_id,result FROM inventory_pet_cake_receipts WHERE pet_id IS NULL OR item_key IS NULL').fetchall():
        value=json.loads(body);pet,key=value['pet_id'],value['item_key']
        if (value['request_id']!=request or any(type(v) is not int or not 0<v<=0x7fffffff for v in (pet,key))):
            raise ValueError('Cake receipt index needs explicit identity reconciliation')
        db.execute('UPDATE inventory_pet_cake_receipts SET pet_id=?,item_key=? WHERE role_id=? AND request_id=?',(pet,key,role,request))
    db.execute('CREATE INDEX IF NOT EXISTS inventory_pet_cake_use_index ON inventory_pet_cake_receipts(role_id,pet_id,item_key)')


def was_confirmed_cake(db,role,pet,key):
    """Read-only indexed classification; caller already validated current role lease."""
    return db.execute('SELECT 1 FROM inventory_pet_cake_receipts WHERE role_id=? AND pet_id=? AND item_key=? LIMIT 1',
        (role,pet,key)).fetchone() is not None


def _cake(value):return PetCakeHistory(value['version'],value['count'],tuple(value['added_aptitudes']))


def use(db,inv,pet,key,request_id,expected_version):
    rules=inv.cake_effect_rules
    if (type(pet) is not int or not 0<pet<=0x7fffffff or type(key) is not int or not 0<key<=0x7fffffff
            or type(request_id) is not str or not 1<=len(request_id)<=160
            or expected_version is not None and (type(expected_version) is not int or not 0<=expected_version<2**63)):
        raise ValueError('Owned pet/item and stable confirmed cake command required')
    fingerprint=hashlib.sha256(json.dumps([pet,key,expected_version,rules.revision,inv.cake_rules.revision,
        inv.growth_rules.revision,inv.blood_rules.revision]).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result,pet_id,item_key FROM inventory_pet_cake_receipts WHERE role_id=? AND request_id=?',
        (inv.role_id,request_id)).fetchone()
    if old:
        if old[0]!=fingerprint or old[2:]!=(pet,key):raise ValueError('Cake command intent conflict')
        value=json.loads(old[1]);value['prediction']=CakePrediction(**value['prediction'])
        for field in ('before','after'):
            value[field]=pet_growth_store.decode_progress(value[field],inv.role_id,pet,inv.growth_rules,inv.blood_rules)
        for field in ('cake_before','cake_after'):value[field]=_cake(value[field])
        return CakeReceipt(**value,replayed=True)
    current=inv.read_pet_state(db,pet)
    if (current is None or any(v is None for v in (current.progress,current.care,current.traits,current.skills,
            current.flags,current.skill_expiry,current.skill_progress,current.cake)) or current.progress.blood is None
            or current.progress.stones is None
            or type(current.progress.state.version) is not int or not 0<=current.progress.state.version<0x7fffffff
            or expected_version is not None and expected_version!=current.progress.state.version):
        raise ValueError('Known complete current pet/blood/cake state required')
    item=db.execute('SELECT template_id,quantity FROM inventory_items WHERE id=? AND role_id=? AND equipment_slot IS NULL',
        (key,inv.role_id)).fetchone()
    role=db.execute('SELECT level FROM roles WHERE id=? AND account_id=?',(inv.role_id,inv.account_id)).fetchone()
    if not item or item[0] not in rules.templates or not role or role[0]<1:
        raise ValueError('Owned carried named cake and item level required')
    before=current.progress;blood=before.blood
    _,_,num,den=inv.blood_rules.rows[blood.level]
    permille=int(float(Fraction(num,den))*1000.0)
    prediction=rules.predict(current.template_id,item[0],before.effective_profile.aptitudes,permille,current.cake.count,
        stone=before.stones.added_aptitudes)
    if prediction.error:raise CakeUnavailable(prediction.error)
    if prediction.client_gain<=0 or prediction.base_gain<=0:raise CakeUnavailable(145136)
    aptitudes=list(before.profile.aptitudes);i=prediction.attribute_index;aptitudes[i]+=prediction.base_gain
    profile=replace(before.profile,aptitudes=tuple(aptitudes))
    planned=pet_growth_store._project(inv.role_id,pet,profile,before.state,inv.growth_rules,inv.blood_rules,blood,before.stones)
    actual_gain=planned.effective_profile.aptitudes[i]-before.effective_profile.aptitudes[i]
    if actual_gain<=0:raise CakeUnavailable(145136)
    if (not 0<=before.state.hp<=before.attributes.max_hp or not 0<=before.state.mp<=before.attributes.max_mp
            or planned.attributes.max_hp<before.attributes.max_hp or planned.attributes.max_mp<before.attributes.max_mp):
        raise ValueError('Cake requires valid resources and nondecreasing supported caps')
    state=replace(before.state,version=before.state.version+1)
    after=pet_growth_store._project(inv.role_id,pet,profile,state,inv.growth_rules,inv.blood_rules,blood,before.stones)
    added=list(current.cake.added_aptitudes);added[i]+=prediction.base_gain
    cake=PetCakeHistory(current.cake.version+1,current.cake.count+1,tuple(added))
    old_growth=db.execute('SELECT profile,state FROM inventory_pet_growth WHERE pet_id=?',(pet,)).fetchone()
    old_cake=db.execute('SELECT state FROM inventory_pet_cakes WHERE pet_id=?',(pet,)).fetchone()
    if db.execute('UPDATE inventory_pet_growth SET profile=?,state=? WHERE pet_id=? AND revision=? AND profile=? AND state=?',
            (json.dumps(asdict(profile)),json.dumps(asdict(state)),pet,inv.growth_rules.revision,old_growth[0],old_growth[1])).rowcount!=1:
        raise ValueError('Cake growth source changed')
    if db.execute('UPDATE inventory_pet_cakes SET state=? WHERE pet_id=? AND policy=? AND state=?',
            (json.dumps(asdict(cake)),pet,inv.cake_rules.revision,old_cake[0])).rowcount!=1:
        raise ValueError('Cake history source changed')
    if item[1]==1:db.execute('DELETE FROM inventory_items WHERE id=? AND role_id=?',(key,inv.role_id))
    else:db.execute('UPDATE inventory_items SET quantity=quantity-1 WHERE id=? AND role_id=?',(key,inv.role_id))
    db.execute('INSERT INTO inventory_versions VALUES(?,1) ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(inv.role_id,))
    receipt=CakeReceipt(request_id,pet,key,item[0],prediction,actual_gain,before,after,current.cake,cake,rules.revision)
    value=asdict(receipt);value.pop('replayed')
    value['before']=pet_growth_store.encode_progress(before);value['after']=pet_growth_store.encode_progress(after)
    db.execute('INSERT INTO inventory_pet_cake_receipts(role_id,request_id,fingerprint,result,pet_id,item_key) VALUES(?,?,?,?,?,?)',
        (inv.role_id,request_id,fingerprint,json.dumps(value),pet,key))
    return receipt
