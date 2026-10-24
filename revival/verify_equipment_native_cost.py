"""Run original NPC repair arithmetic; only configuration lookup is adapted."""
import struct
from equipment_condition import EquipmentRules,EquipmentCondition
from native_inspect import BASE,DATA
from inspect_client import OUT,write_json


class NativeCost:
    def __init__(self):
        from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EIP
        self.SP,self.AX,self.IP=UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EIP
        self.emu=emu=Uc(UC_ARCH_X86,UC_MODE_32)
        emu.mem_map(0,0x1000);emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
        emu.mem_map(0x5000000,0x200000)
        self.wrapper,self.obj,self.manager,self.vt,self.row,self.stack,self.stop=(
            0x5001000,0x5002000,0x5003000,0x5004000,0x5005000,0x5100000,0x500f000)
        def hook(uc,address,size,user):
            if address==self.stop:uc.emu_stop()
            elif address==0x89d550:self.ret(0,self.manager)
            elif address==0x500f100:self.ret(4,self.row)
        emu.hook_add(UC_HOOK_CODE,hook)
        self.w(self.wrapper,self.obj);self.w(self.wrapper+8,8)
        self.w(self.manager,self.vt);self.w(self.vt+8,0x500f100)

    def w(self,address,*values):self.emu.mem_write(address,struct.pack('<'+'I'*len(values),*values))

    def ret(self,count,value):
        sp=self.emu.reg_read(self.SP)
        dest=struct.unpack('<I',self.emu.mem_read(sp,4))[0]
        self.emu.reg_write(self.SP,sp+4+count);self.emu.reg_write(self.IP,dest);self.emu.reg_write(self.AX,value)

    def run(self,level,unit,color,current,maximum):
        self.w(self.wrapper+0x28,level);self.w(self.obj+0x5c,color)
        # Distinct unused family/skill coefficients prove method2 reads the
        # original npcrepair member at +4 rather than a coincidentally equal fee.
        self.w(self.obj+0xc8,current,maximum);self.w(self.row,level,unit,unit+101,unit+202)
        self.w(self.stack,self.stop,self.wrapper,2)
        self.emu.reg_write(self.SP,self.stack)
        self.emu.emu_start(0x10dbb20,self.stop,count=10000)
        assert self.emu.reg_read(self.IP)==self.stop
        return self.emu.reg_read(self.AX)


def main():
    rules=EquipmentRules.load();native=NativeCost();count=0
    for level,unit in rules.costs.items():
        for color in range(1,7):
            for missing in range(1,101):
                state=EquipmentCondition(0,100-missing,100,color)
                value=native.run(level,unit,color,state.current,state.maximum)
                assert rules.npc_cost(state,level)==value,(level,color,missing,rules.npc_cost(state,level),value)
                count+=1
    # A diagnostic example where naive float pow rounds one coin higher.
    state=EquipmentCondition(0,75,100,5)
    assert rules.npc_cost(state,60)==1295 and int(25*(1.2**4)*25)==1296
    report={'passed':['all original NPC repair level rows, colors1..6 and missing1..100 match original arithmetic',
        'tier5 level60 25 missing preserves native1295 instead of naive1296'],
        'comparisons':count,'native_function':'0x10dbb20 ordinary branch',
        'adapter':'configuration table manager/row lookup only; original getters power multiply and truncate execute',
        'config_member_evidence':{'npcrepair':'UTF16 2255a18 -> reader86b4c6 -> record+4',
            'level':'UTF16 2251a44 -> CItemAttr reader86e95a -> record+24 -> wrapper+28'},
        'npc_repair_ui_tested':False,'probability_semantics_proven':False}
    write_json(OUT/'evidence/equipment-native-cost-verification.json',report)
    print('PASS',count,'original NPC repair arithmetic comparisons')


if __name__=='__main__':main()
