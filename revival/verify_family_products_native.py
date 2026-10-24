"""Original x86 buttons/serializers, adapted network edges; no GUI claim."""
import hashlib,json,struct
from native_inspect import DATA,BASE,u32
from inspect_client import OUT,write_json
from verify_social_native import native_payload
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX
import family_products_protocol as p
from family_products import FamilyProducts


def click(address):
    uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(0,4096)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x800000)
    network,table,stack,stop,send=0x5001000,0x5002000,0x5100000,0x500f000,0x500e010
    def w(a,*values):uc.mem_write(a,struct.pack('<'+'I'*len(values),*values))
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    def ret(count=0,value=None):
        sp=uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4+count)
        if value is not None:uc.reg_write(UC_X86_REG_EAX,value)
    w(network,table);w(table+0x3c,send)
    sent=[]
    def hook(machine,at,size,user):
        if at==stop:uc.emu_stop()
        elif at==0x813860:ret(value=network)
        elif at==0x1919184:ret()
        elif at==send:
            obj=r(uc.reg_read(UC_X86_REG_ESP)+4)
            sent.append((r(obj+4),tuple(struct.unpack('<i',uc.mem_read(obj+offset,4))[0] for offset in (8,12))))
            ret(4,1)
    uc.hook_add(UC_HOOK_CODE,hook)
    w(stack,stop,0x5003000);uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,0x5004000)
    uc.emu_start(address,stop,count=100000)
    assert uc.reg_read(UC_X86_REG_EIP)==stop and len(sent)==1
    return sent[0]


def main():
    passed=[]
    for address,choices in ((0x14cc580,(1,-1)),(0x14cc600,(0,-1)),
            (0x14cc670,(-1,1)),(0x14cc6f0,(-1,0))):
        assert click(address)==(p.SET_PRODUCTS,choices)
        wire=native_payload(0xe450f0,raw=[(8,struct.pack('<ii',*choices))])
        assert wire==struct.pack('>ii',*choices) and p.decode_set(wire)==choices
        passed.append(dict(button_handler=hex(address),type=hex(p.SET_PRODUCTS),choices=choices,wire=wire.hex()))
    state=FamilyProducts(123,True,False,17,23,4,'explicit_fixture')
    actual=native_payload(0xe46090,scalars=[(8,123),(12,256),(16,17),(20,1),
        (24,456),(28,512),(32,23),(36,0)])
    assert actual==p.information(state,2**40+123,2**41+456)==struct.pack('>QiiQii',2**40+123,17,1,2**41+456,23,0)
    passed.append(dict(name='SFamilyProductsInfo native QiiQii retains 64-bit cost',type=hex(p.PRODUCTS_INFO),serializer='0xe46090'))
    assert u32(0xd6cdc9)==p.SET_PRODUCTS and u32(0xd71719)==p.PRODUCTS_INFO
    result=dict(passed=passed,image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False,
        live_server_changed=False,native_npc_route_integrated=False,
        scope='original buttons construct exact two switch values; original native serializers; mocked network acquisition/send and CRT only')
    write_json(OUT/'evidence/family-products-native-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
