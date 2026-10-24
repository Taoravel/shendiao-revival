"""Execute original depot cash request/refresh codecs and wallet consumers."""
import hashlib
import struct
from native_gameplay_probe import probe
from native_inspect import BASE,DATA
from currency_protocol import encode_balance
from inspect_client import OUT,write_json


def native_wallet_write(payload,slot):
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ESI,UC_X86_REG_EIP
    _,raw=probe(0xd9e1a0,0xe4e9a0,0xd9e250,payload=payload)
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(0,4096);uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x200000)
    wallet,msg,stack=0x5001000,0x5002000,0x5100000
    uc.mem_write(0x2944628,struct.pack('<I',wallet));uc.mem_write(msg,raw)
    uc.mem_write(wallet+0xb0,struct.pack('<QQ',2**63-1,55))
    stop=0x10a1623 if slot==1 else 0x10a0db9
    uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ESI,msg)
    def hook(emu,address,size,user):
        if address==stop:emu.emu_stop()
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.emu_start(0x10a159a,stop,count=10000)
    assert uc.reg_read(UC_X86_REG_EIP)==stop
    return struct.unpack('<QQ',uc.mem_read(wallet+0xb0,16))


def main():
    cases=[]
    for name,ctor,marshal,decoder,kind in (
            ('CDepositMoney',0xd8fc20,0xe4be80,0xd8fcd0,0xc03fb),
            ('CDrawMoney',0xd8fef0,0xe4bf00,0xd8ffa0,0xc03fc)):
        for key,amount in ((1,1),(0x123456789,0x100000007),(0x123456789abcdef,2**63-1)):
            expected=struct.pack('>qq',key,amount)
            native,raw=probe(ctor,marshal,decoder,{8:struct.pack('<q',key),16:struct.pack('<q',amount)})
            assert native==expected and struct.unpack_from('<qq',raw,8)==(key,amount)
            assert struct.unpack_from('<I',raw,4)[0]==kind
            cases.append({'name':name,'npc_key':key,'amount':amount,'bytes':native.hex()})
        for amount in (0,-1):
            try:probe(ctor,marshal,decoder,payload=struct.pack('>qq',1,amount))
            except (ValueError,RuntimeError):pass
            else:raise AssertionError('Invalid amount accepted by original decoder')
        try:probe(ctor,marshal,decoder,payload=expected[:-1])
        except ValueError:pass
        else:raise AssertionError('Truncation accepted by original decoder')
    for slot in (1,2):
        for amount in (0,4295066068,2**63-1):
            kind,payload=encode_balance('money_'+str(slot),amount);assert kind==0xc03fa
            native,_=probe(0xd9e1a0,0xe4e9a0,0xd9e250,
                {8:struct.pack('<i',slot),16:struct.pack('<q',amount)})
            assert native==payload
            assert native_wallet_write(payload,slot)==((amount,55) if slot==1 else (2**63-1,amount))
    report={'scope':'original codecs and wallet field writes; runtime route and GUI separate',
        'passed':['deposit/draw original16byte codecs retain64bit NPC key and amount',
            'original positive signed64 constraints and truncation rejection',
            'both SRefreshMoney slots original codec and consumers preserve sibling balance'],
        'cases':cases,'native_dialog_dispatch':'0x10ca451..0x10ca4db',
        'consumer_executed':'0x10a159a..0x10a1623 for cash;0x10a159a->0x10a0da0..0x10a0db9 for depot',
        'consumer_limit':'stop before recalculation/observers; no visual rendering proof',
        'native_image_sha256':hashlib.sha256(DATA).hexdigest(),'native_gui_verified':False}
    write_json(OUT/'evidence/npc-depot-money-native.json',report);print(report['passed'])


if __name__=='__main__':main()
