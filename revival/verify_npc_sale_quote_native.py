"""Execute original equipment sale arithmetic against production quote logic."""
from dataclasses import asdict
import json
from types import SimpleNamespace
from equipment_condition import EquipmentCondition
from npc_depot import StoredItem
from npc_shop_sales import SaleRules,quote
from verify_equipment_native_cost import NativeCost
from inspect_client import OUT,write_json


def main():
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX
    native=NativeCost()
    def hook(uc,address,size,user):
        if address==0x89d4c0:native.ret(0,native.manager)
        elif address==0x1079ad0:native.ret(0,0) # Explicit clean ordinary branch.
    native.emu.hook_add(UC_HOOK_CODE,hook)
    rows=json.loads((OUT/'catalogs/knight.gsp.item.cequipeffect.json').read_text(encoding='utf-8'))
    coefficients=sorted({(int(r['attributes']['sellpricecoef']),int(r['attributes']['endurecoef']))
        for r in rows if int(r['attributes'].get('endurecoef',0))>0})
    inv=SimpleNamespace(items={40200:{'bCanSaleToNpc':'1','level':'1'}},
        condition_rules=SimpleNamespace(revision='condition'),detail_rules=SimpleNamespace(revision='detail'))
    count=0
    for numerator,denominator in coefficients:
        rules=SaleRules('fixture',(10011,),{}, {40200:(numerator,denominator)},20,3600,40)
        for current in (0,1,17,80,100):
            native.w(native.wrapper+8,8)
            native.w(native.obj+0xc8,current)
            native.w(native.obj+0xdc,0)
            native.w(native.row+0x4c,numerator,denominator)
            native.w(native.stack,native.stop)
            native.emu.reg_write(native.SP,native.stack)
            native.emu.reg_write(UC_X86_REG_ECX,native.wrapper)
            native.emu.emu_start(0x107a6e0,native.stop,count=10000)
            assert native.emu.reg_read(native.IP)==native.stop
            expected=native.emu.reg_read(native.AX)
            item=StoredItem(7,1,40200,1,0,1,None,'condition',json.dumps(asdict(
                EquipmentCondition(0,current,100,1))),'detail','fixture','{}')
            assert quote(rules,inv,item,10011)==('bound_silver',expected),(numerator,denominator,current,expected)
            count+=1
    report={'passed':['known clean ordinary equipment quote matches original107a6e0 including binary32 rounding and minimum1'],
        'comparisons':count,'coefficient_pairs':len(coefficients),
        'original_branches_not_covered':['special1079ad0 branch','special object+dc=0x6419c multiplier'],
        'native_gui_verified':False}
    write_json(OUT/'evidence/npc-sale-quote-native.json',report);print(report)


if __name__=='__main__':main()
