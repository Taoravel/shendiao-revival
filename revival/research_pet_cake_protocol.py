"""Original cake confirmation sender and cake SSendMsgNotify codecs."""
import struct
from native_inspect import BASE,DATA
from native_gameplay_probe import probe
from pet_protocol import cake_notice
from inspect_client import OUT,write_json
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EIP


def native_notice(payload):
    values=[]
    def observe(uc,message):
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
        begin,end=r(message+0x14),r(message+0x18)
        params=tuple(bytes(uc.mem_read(r(node+4),r(r(node+4)-8))).decode('utf-16le') for node in range(begin,end,8))
        values.append((r(message+8),r(message+12),params))
        # Re-encode the actually decoded nonempty original vector, rather than
        # fabricating a vector layout or proving only the empty constructor.
        stack,stop,stream,buf=0x5108000,0x500f000,0x5002000,0x5003000
        w(buf-8,0);w(stream+8,0);w(stack,stop,stream)
        uc.reg_write(UC_X86_REG_ECX,message);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0xf14c60,stop,count=500000)
        assert uc.reg_read(UC_X86_REG_EIP)==stop
        assert bytes(uc.mem_read(buf,r(buf-8)))==payload
    probe(0xf14ae0,0xf14c60,0xf14b70,payload=payload,observer=observe)
    return values[0]


def main():
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(BASE,(len(DATA)+0xfff)&~0xfff);uc.mem_write(BASE,DATA);uc.mem_map(0x5000000,0x200000)
    dialog,stack=0x5001000,0x5108000;sends=[]
    for pet,key in ((1,7),(7,11),(0x7fffffff,0x7fffffff)):
        uc.mem_write(dialog+0x10,struct.pack('<i',key));uc.mem_write(dialog+0x18,struct.pack('<i',pet))
        uc.reg_write(UC_X86_REG_ESI,dialog);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x1089325,0x1089350,count=100)
        assert struct.unpack('<6I',uc.mem_read(stack+8,24))==(0x2277200,0xc03ff,key,1,pet,0)
        payload,raw=probe(0xd98770,0xe4d740,0xd987a0,
            {8:struct.pack('<i',key),12:struct.pack('<i',1),16:struct.pack('<Q',pet)},factory=True)
        assert payload==struct.pack('>iiQ',key,1,pet)
        sends.append({'pet':pet,'key':key,'body':payload.hex()})
    cases=[]
    for ident,params in ((145133,()),(145135,('外功','7','19')),(145135,('体力','12','0')),
                         (145136,('栗子年糕',)),(145137,()),(145139,())):
        kind,body=cake_notice(ident,params)
        assert native_notice(body)==(ident,0,params)
        cases.append({'type':hex(kind),'message':ident,'parameters':params,'body':body.hex()})
    write_json(OUT/'evidence/pet-cake-protocol-native.json',{
        'source_status':'client_verified','confirm_send_cases':sends,'notice_cases':cases,
        'confirm':'original10a6330 computes forecast,145134 local confirmation callback10892f0; actual1089325..1089350 constructs CUseItem(key,1,u64pet)',
        'notice':'original SSendMsgNotify ctorf14ae0/typec1775/marshalf14c60/decoderf14b70; two BE32 id/default-extra0 then compact vector<Octets UTF16>; nonempty original decoded vector is re-marshaled unchanged',
        'parameters':'original145135 uses attribute CString2707..2711, actual increment, remaining20-count;145136 uses item display name',
        'limits':['no GUI/rendered message verification','extra field semantic not inferred; original constructor default0 retained',
            'client local confirmation has no server-side pending token; server current-state validation remains required']})
    print('PASS',len(sends),'original cake confirmation sends and',len(cases),'original nonempty notify codec roundtrips')


if __name__=='__main__':main()
