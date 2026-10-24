"""Offline original x86 serializers for newly wired NPC gameplay requests."""
import hashlib
import struct
from native_inspect import DATA,BASE,u32
from verify_social_native import native_payload
from inspect_client import OUT,write_json


def depot_wallet_projection(body):
    from native_gameplay_probe import probe
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EIP
    _,raw=probe(0xef6220,u32(0x2284234),u32(0x2284238),payload=body)
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(0,0x1000);emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x200000)
    wallet,msg,stack=0x5001000,0x5002000,0x5100000
    emu.mem_write(wallet+0xb0,struct.pack('<Q',12345));emu.mem_write(msg,raw)
    emu.mem_write(stack,struct.pack('<IIII',0x500f000,2,msg+0x10,0))
    def hook(uc,address,size,user):
        if address==0x10a48ad: uc.emu_stop()
    emu.hook_add(UC_HOOK_CODE,hook)
    emu.reg_write(UC_X86_REG_ESP,stack);emu.reg_write(UC_X86_REG_ECX,wallet)
    emu.emu_start(0x10a4840,0x10a48ad,count=10000)
    assert emu.reg_read(UC_X86_REG_EIP)==0x10a48ad
    return struct.unpack('<Q',emu.mem_read(wallet+0xb0,8))[0],struct.unpack('<Q',emu.mem_read(wallet+0xb8,8))[0]


def main():
    key=(1100<<32)|1
    cases=(('CBuyItemFromNpc',0xe516d0,[(0x10,32000),(0x14,2),(0x18,0)],
            struct.pack('>qiii',key,32000,2,0)),
           ('COpenDeportDlg',0xe4cb50,[],struct.pack('>q',key)),
           ('CNpcService',0x83b5a0,[(0x10,216)],struct.pack('>qi',key,216)))
    passed=[]
    for name,serializer,scalars,expected in cases:
        actual=native_payload(serializer,scalars=scalars,raw=[(8,struct.pack('<q',key))])
        assert actual==expected,(name,actual.hex(),expected.hex())
        passed.append({'name':name,'serializer':hex(serializer),'body':actual.hex()})
    # Actual original dispatch jump table: buy opens local shop, warehouse opens
    # its dedicated path, carriage falls through to server service dispatch.
    branches={sid:hex(u32(0x163f09c+DATA[0x163f1c0-BASE+sid-2]*4)) for sid in (2,6,216)}
    assert branches=={2:'0x1636d38',6:'0x1636df2',216:'0x163efbb'}
    assert depot_wallet_projection(struct.pack('>iQi',2,98765,40)+bytes(2))==(12345,98765)
    report={'image_sha256':hashlib.sha256(DATA).hexdigest(),'passed':passed,
        'original_menu_branches':branches,'depot_column2_wallet_projection':{
            'carried_cash_unchanged':12345,'second_silver_slot':98765},
        'native_gui_verified':False,'live_client_changed':False}
    write_json(OUT/'evidence/npc-gameplay-native.json',report);print(report)


if __name__=='__main__':main()
