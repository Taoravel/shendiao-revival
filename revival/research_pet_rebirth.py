"""Original allocating factories/codecs and super-return UI argument order."""
import struct
from native_gameplay_probe import probe
from native_inspect import BASE,DATA
from inspect_client import OUT,write_json
from pet_protocol import (SUPER_RETURN_PREVIEW,SUPER_RETURN_SUBMIT,SUPER_RETURN_QUERY,
    SUPER_RETURN_CLEAR,decode_super_return_pet_request,super_return_preview_message)


def main():
    requests=[]
    for kind,constructor,marshal,decoder in (
            (SUPER_RETURN_CLEAR,0xdbdc20,0xe538c0,0xdbdc50),
            (SUPER_RETURN_QUERY,0xdbdd70,0xe538e0,0xdbdda0),
            (SUPER_RETURN_SUBMIT,0xdbdec0,0xe53900,0xdbdef0)):
        for key in (1,7,0x7fffffff):
            payload,raw=probe(constructor,marshal,decoder,{8:struct.pack('<i',key)},factory=True)
            assert struct.unpack_from('<i',raw,4)[0]==kind
            assert payload==struct.pack('>i',key) and decode_super_return_pet_request(payload)==key
            requests.append({'type':hex(kind),'pet':key,'body':payload.hex()})
    captured=[]
    def observe(uc,message):
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EIP,UC_X86_REG_ESP
        stack,stop,dialog=0x5108000,0x500f000,0x5300000
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
        def hook(uc,address,size,user):
            if address==0x143c710:
                sp=uc.reg_read(UC_X86_REG_ESP)
                assert uc.reg_read(UC_X86_REG_ECX)==dialog
                captured.append(tuple(r(sp+4+4*i) for i in range(9)))
                dest=r(sp);uc.reg_write(UC_X86_REG_ESP,sp+40);uc.reg_write(UC_X86_REG_EIP,dest)
        h=uc.hook_add(UC_HOOK_CODE,hook)
        w(0x29457cc,dialog);w(stack,stop,0,0)
        uc.reg_write(UC_X86_REG_ECX,message);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x143c870,stop,count=100)
        assert uc.reg_read(UC_X86_REG_EIP)==stop
        uc.hook_del(h)
    examples=((7,(1040,1130,840,585,1025),73,1006,2000),
              (0x7fffffff,(0,1,2,3,4),0,986,0))
    for key,aptitudes,insight,growth,score in examples:
        kind,payload=super_return_preview_message(key,aptitudes,insight,growth,score)
        fields={8+4*i:struct.pack('<i',v) for i,v in enumerate((key,*aptitudes,insight,growth,score))}
        expected,raw=probe(0xdc15a0,0xe54300,0xdc15e0,fields,factory=True,observer=observe)
        assert payload==expected and struct.unpack_from('<i',raw,4)[0]==kind==SUPER_RETURN_PREVIEW
        assert captured[-1]==(key,*aptitudes,insight,growth,score)
    # Actual client sends: submit selected dialog+f0, query selected key,
    # clear each cached preview tree key when the dialog closes.
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBX,UC_X86_REG_ESP
    uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(BASE,(len(DATA)+0xfff)&~0xfff);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x200000);dialog,node,stack=0x5001000,0x5004000,0x5108000
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    def w(a,v):uc.mem_write(a,struct.pack('<I',v))
    w(dialog+0xf0,7);w(node+0xc,7);client=[]
    for kind,start,end,offset,reg,value in (
            (SUPER_RETURN_SUBMIT,0x1436eef,0x1436f18,8,UC_X86_REG_ESI,dialog),
            (SUPER_RETURN_QUERY,0x143df31,0x143df4f,0x10,UC_X86_REG_EDI,dialog+0xf0),
            (SUPER_RETURN_CLEAR,0x1438b6b,0x1438b8a,0x14,UC_X86_REG_EBX,node)):
        uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(reg,value)
        uc.emu_start(start,end,count=100)
        assert (r(stack+offset+4),r(stack+offset+8))==(kind,7)
        client.append({'type':hex(kind),'native_send':hex(start),'pet':7})
    for bad in (b'',b'\0'*3,b'\0'*4,b'\xff'*4,b'\0'*5,bytearray(struct.pack('>i',7))):
        try:decode_super_return_pet_request(bad)
        except ValueError:pass
        else:raise AssertionError('Malformed super-return request accepted')
    for args in ((7,(1,2,3,4),73,1006,1),(7,(1,2,3,4,5),True,1006,1),
                 (7,(1,2,3,4,5),73,1006,None),(7,(1,2,3,4,5),73,1006,2**31)):
        try:super_return_preview_message(*args)
        except ValueError:pass
        else:raise AssertionError('Incomplete/unsafe preview fabricated')
    write_json(OUT/'evidence/pet-rebirth-native.json',{
        'source_status':'client_verified','request_cases':requests,'preview_cases':captured,
        'actual_client_sends':client,
        'wire':'C0811/12/13 one BE32 pet key; S0810 nine BE32: key,attack/defense/vitality/magic/speed aptitudes,insight,growth_raw,score',
        'constructors':'actual original allocating factories, original type+4 and full marshal/unmarshal; not a borrowed constructor',
        'process':'whole143c870 emits exact nine original arguments to143c710; UI cache/renderer terminal not executed',
        'semantics':'preview row+00..10 five aptitudes, +14insight matches current1160 at143bb1b, +18rawgrowth, +1cscore; return UI stores inspected separately',
        'pending_shape':'original UI keeps a map of pet key->preview; close iterates cached pet keys and emits C0813 for each, query/submit carry current selected pet key',
        'limits':['No preview random distribution, item spend or save transaction implemented by this probe',
                  'Ordinary return still uses CUseItem separately; no claim of ordinary preview',
                  'Known score must be supplied; supported current-wire score now independently verified by pet-score-native.json; advanced score remains incomplete',
                  'No live service/client or actual rebirth']})
    print('PASS',len(requests),'original super-return requests and',len(captured),'preview factory/codec/UI-argument cases')


if __name__=='__main__':main()
