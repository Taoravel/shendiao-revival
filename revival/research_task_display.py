"""Offline original NPC quest menu classification evidence; no live process access."""
import hashlib
import argparse
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,'D:/Downloads/LCJDTClient/LCJDTClient/revival/.deps')
from native_inspect import BASE, DATA, disasm

FUNCTIONS={'visit_process':(0x1214250,0x157),
           'quest_menu_click':(0x1636acf,0xcc),
           'quest_ui_class':(0x1257b20,0x72),
           'dialogue_class_dispatch':(0x164d780,0x114),
           'accept_process':(0x125d5c0,0x27),
           'dialogue_resource':(0x164b530,0x8e)}


def classify(state, quest_type=10):
    """Execute original classification routine; adapt only its lookup dependencies."""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EIP
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x10000)
    stack,stop,manager,bean,config,lookup=0x500f000,0x5000100,0x5001000,0x5002000,0x5003000,0x5000600
    def w(addr,*v):emu.mem_write(addr,struct.pack('<'+'I'*len(v),*v))
    w(stack,stop,100104);w(bean+8,state or 0);w(config+0x164,quest_type)
    w(0x5004000,0x5005000);w(0x5005008,lookup)
    def ret(uc,value,cleanup):
        sp=uc.reg_read(UC_X86_REG_ESP)
        target=struct.unpack('<I',uc.mem_read(sp,4))[0]
        uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_ESP,sp+4+cleanup)
        uc.reg_write(UC_X86_REG_EIP,target)
    def hook(uc,addr,size,user):
        if addr==stop:uc.emu_stop()
        elif addr==0x1257ac0:ret(uc,bean if state is not None else 0,4)
        elif addr==0x12578e0:ret(uc,0,4)
        elif addr==0x89ebd0:ret(uc,0x5004000,0)
        elif addr==lookup:ret(uc,config,4)
    emu.hook_add(UC_HOOK_CODE,hook)
    emu.reg_write(UC_X86_REG_ESP,stack);emu.reg_write(UC_X86_REG_ECX,manager)
    emu.emu_start(0x1257b20,stop,count=1000)
    assert emu.reg_read(UC_X86_REG_EIP)==stop
    return emu.reg_read(UC_X86_REG_EAX)


def main():
    p=argparse.ArgumentParser();p.add_argument('--disasm',choices=FUNCTIONS)
    args=p.parse_args()
    if args.disasm:
        disasm(*FUNCTIONS[args.disasm]);return
    cases=[]
    for state,kind,expected in ((None,10,1),(0,10,2),(1,10,2),(2,10,2),(3,10,3),(4,10,2),(2,40,3)):
        actual=classify(state,kind)
        assert actual==expected
        cases.append({'bean_state':state,'quest_type':kind,'native_ui_class':actual})
    result={'source_image_sha256':hashlib.sha256(DATA).hexdigest(),'original_function':'0x1257b20',
            'scope':'original branch code; lookup adapters only; no UI or network execution',
            'cases':cases,'passed':len(cases)}
    target=Path(__file__).parent/'evidence/task-display-native-predicates.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
