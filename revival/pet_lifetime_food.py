"""Atomic lifetime food with an auditable server-owned random outcome."""
from dataclasses import dataclass,asdict
from decimal import Decimal
from fractions import Fraction
from types import MappingProxyType
import hashlib
import json

from inspect_client import OUT
import pet_care
import pet_growth_store


@dataclass(frozen=True)
class FoodRules:
    revision: str
    formulas: object
    need_levels: object
    draw_denominator: int
    poison_below: int
    aptitude_loss: int

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/pet-toxic-food-v1.json').read_text(encoding='utf-8'))
        poison=policy['poison']
        if (policy['revision']!='2026-10-23.pet-toxic-food.1' or policy['templates']!=[32004,32009]
                or any(type(poison[k]) is not int for k in ('chance_percent','draw_denominator','draw_below','aptitude_loss_each','minimum_base_aptitude'))
                or (poison['chance_percent'],poison['draw_denominator'],poison['draw_below'],poison['aptitude_loss_each'],poison['minimum_base_aptitude'])!=(3,10000,300,1,0)):
            raise ValueError('Toxic lifetime food policy requires review')
        def table(name):return {int(r['attributes']['id']):r for r in json.loads(
            (OUT/f'catalogs/knight.gsp.item.{name}.json').read_text(encoding='utf-8'))}
        formulas,items,effects=table('cfooddrugeffectformula'),table('citemattr'),table('cfoodanddrugeffect')
        frozen={};levels={}
        for key,expected in ((32004,('3.0','0')),(32009,('2.0','50'))):
            row=formulas[key]['lists'];item=items[key]['attributes']
            if (row!={'ai':[expected[0],'0.0','0.0'],'bi':[expected[1],'0','0']}
                    or int(item['needLevel'])!=1 or int(item['outbattleuse'])!=2
                    or int(item['itemtypeid'])!=546 or '3%' not in item['destribe']
                    or int(effects[key]['attributes']['funtionid'])!=0):
                raise ValueError('Original toxic lifetime food data requires review')
            ratio=Fraction(Decimal(row['ai'][0]))
            frozen[key]=(ratio.numerator,ratio.denominator,int(row['bi'][0]));levels[key]=int(item['needLevel'])
        return cls(policy['revision'],MappingProxyType(frozen),MappingProxyType(levels),10000,300,1)

    def amount(self,template,quality):
        if (type(template) is not int or template not in self.formulas
                or type(quality) is not int or not 0<=quality<=0x7fffffff):
            raise ValueError('Known original food and persisted instance quality required')
        numerator,denominator,offset=self.formulas[template]
        amount=abs(quality*numerator+offset*denominator)//denominator
        if amount<=0 or amount>0x7fffffff:raise ValueError('Lifetime food has no representable positive effect')
        return amount


@dataclass(frozen=True)
class FoodReceipt:
    settlement_id: str
    pet_id: int
    item_key: int
    template_id: int
    quality: int
    draw: int
    poisoned: bool
    growth_before: object
    growth_after: object
    care_before: object
    care_after: object
    policy: str
    replayed: bool = False


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_toxic_food_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id),pet_id INTEGER NOT NULL REFERENCES inventory_pets(id),
        settlement_id TEXT NOT NULL,fingerprint TEXT NOT NULL,result TEXT NOT NULL,
        PRIMARY KEY(role_id,settlement_id));''')


def use(db,account,role,pet,key,request_id,draw,expected_version,rules,growth_rules,blood_rules,care_rules):
    if (not db.in_transaction or type(pet) is not int or not 0<pet<=0x7fffffff
            or not db.execute('SELECT 1 FROM inventory_pets p JOIN roles r ON r.id=p.role_id '
                'WHERE p.id=? AND p.role_id=? AND r.account_id=? AND p.released=0',(pet,role,account)).fetchone()
            or type(key) is not int or not 0<key<=0x7fffffff
            or type(request_id) is not str or not 1<=len(request_id)<=160
            or draw is not None and (type(draw) is not int or not 0<=draw<rules.draw_denominator)
            or expected_version is not None and (type(expected_version) is not int or not 0<=expected_version<2**63)):
        raise ValueError('Owned live pet and trusted toxic-food command required')
    fingerprint=hashlib.sha256(json.dumps([pet,key,expected_version,rules.revision,growth_rules.revision,
        blood_rules.revision,care_rules.revision]).encode()).hexdigest()
    old=db.execute('SELECT fingerprint,result FROM inventory_pet_toxic_food_receipts WHERE role_id=? AND settlement_id=?',(role,request_id)).fetchone()
    if old:
        value=json.loads(old[1])
        if old[0]!=fingerprint or value['policy']!=rules.revision or draw is not None and draw!=value['draw']:
            raise ValueError('Toxic-food command intent or captured draw conflict')
        for field in ('growth_before','growth_after'):
            value[field]=pet_growth_store.decode_progress(value[field],role,pet,growth_rules,blood_rules)
        for field in ('care_before','care_after'):value[field]=care_rules.validate(pet_care.PetCare(**value[field]))
        return FoodReceipt(**value,replayed=True)
    if draw is None:raise ValueError('Fresh toxic-food command requires the captured server draw')
    item=db.execute('SELECT i.template_id,i.quantity,i.quality,r.level FROM inventory_items i JOIN roles r ON r.id=i.role_id '
        'WHERE i.id=? AND i.role_id=? AND i.equipment_slot IS NULL',(key,role)).fetchone()
    if not item or item[0] not in rules.formulas or item[1]<1 or item[3]<rules.need_levels[item[0]]:
        raise ValueError('Owned carried original lifetime food and role level required')
    amount=rules.amount(item[0],item[2])
    care=pet_care.load(db,account,role,pet,care_rules)
    before=pet_growth_store.load_pet(db,account,role,pet,growth_rules,blood_rules=blood_rules,grade=care.grade)
    if before.blood is None or expected_version is not None and before.state.version!=expected_version:
        raise ValueError('Current known BASE growth/blood and expected version required')
    if care.lifetime+amount>0x7fffffff:raise ValueError('Lifetime food would overflow current lifetime')
    poisoned=draw<rules.poison_below
    after=pet_growth_store.damage_base_aptitudes(db,account,role,pet,growth_rules,blood_rules,care.grade,before,
        rules.aptitude_loss) if poisoned else before
    child='toxic-food:'+hashlib.sha256(request_id.encode()).hexdigest()
    cared=pet_care.change(db,account,role,pet,care_rules,child,care.version,'increase_lifetime',amount)
    if item[1]==1:db.execute('DELETE FROM inventory_items WHERE id=? AND role_id=?',(key,role))
    else:db.execute('UPDATE inventory_items SET quantity=quantity-1 WHERE id=? AND role_id=?',(key,role))
    receipt=FoodReceipt(request_id,pet,key,item[0],item[2],draw,poisoned,before,after,care,cared,rules.revision)
    value=asdict(receipt);value.pop('replayed')
    value['growth_before']=pet_growth_store.encode_progress(before);value['growth_after']=pet_growth_store.encode_progress(after)
    db.execute('INSERT INTO inventory_pet_toxic_food_receipts VALUES(?,?,?,?,?)',(role,pet,request_id,fingerprint,json.dumps(value)))
    return receipt
