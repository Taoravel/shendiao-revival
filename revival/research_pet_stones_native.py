"""Original Pet tail float map and distinct attr::SRefreshPetData consumer."""
import struct
from native_gameplay_probe import probe
from inspect_client import OUT,write_json
from wire import compact


KEYS=(1930,1940,1950,1960,1970,1980)


def _pairs(uc,map_address):
    def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
    head=r(map_address+4);values=[]
    def visit(node):
        if node==head:return
        visit(r(node));values.append((r(node+12),struct.unpack('<f',uc.mem_read(node+16,4))[0]));visit(r(node+8))
    visit(r(head+4));assert len(values)==r(map_address+8)
    return tuple(values)


def native_stone_attributes(payload):
    """Whole original map decoder/handler loop, only owned pet/slot terminals."""
    result=[]
    def observe(uc,message):
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EAX,UC_X86_REG_EIP
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
        pairs=_pairs(uc,message+0x10);assert tuple(k for k,v in pairs)==KEYS
        column,pet_id=r(message+8),r(message+12);assert column==1 and 0<pet_id<=0x7fffffff
        pet,manager,stack,stop=0x5300000,0x5302000,0x5108000,0x500f000
        w(0x2944550,manager);w(0x29455cc,1);w(0x29b8ef8,1)
        cells={key:0x5304000+4*i for i,key in enumerate(KEYS)};calls=[]
        for cell in cells.values():w(cell,12345)
        def ret(n,value):
            sp=uc.reg_read(UC_X86_REG_ESP);target=r(sp)
            uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_ESP,sp+4+n);uc.reg_write(UC_X86_REG_EIP,target)
        def hook(uc,address,size,user):
            sp=uc.reg_read(UC_X86_REG_ESP)
            if address==0x112ffd0:
                assert (r(sp+4),r(sp+8))==(pet_id,1);ret(8,pet)
            elif address==0x4e8e00:
                key=r(r(sp+4));assert key in cells and uc.reg_read(UC_X86_REG_ECX)==pet+0x34
                calls.append(key);ret(4,cells[key])
        handle=uc.hook_add(UC_HOOK_CODE,hook)
        w(stack,stop,0,0);uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,message)
        uc.emu_start(0x113daa0,0x113e24d,count=100000)
        assert uc.reg_read(UC_X86_REG_EIP)==0x113e24d and tuple(calls)==KEYS
        assigned=tuple((key,r(cells[key])) for key in KEYS)
        assert assigned==tuple((key,int(value)) for key,value in pairs)
        uc.hook_del(handle)
        # Remarshal the actually decoded nonempty balanced map.
        stream,buf=0x5002000,0x5003000;w(buf-8,0);w(stream+8,0);w(stack,stop,stream)
        uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,message)
        uc.emu_start(0xec3250,stop,count=100000)
        assert bytes(uc.mem_read(buf,r(buf-8)))==payload
        result.append(assigned)
    probe(0xec30c0,0xec3250,0xec32f0,payload=payload,observer=observe)
    return result[0]


def native_pet_stones(payload):
    """Original Pet codec, then actual CPet constructor's six map-to-attr stores."""
    result=[]
    def observe(uc,pet_bean):
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_ESI,UC_X86_REG_EAX,UC_X86_REG_EIP
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
        pairs=_pairs(uc,pet_bean+0x134);assert tuple(k for k,v in pairs)==KEYS
        stack,pet=0x5108000,0x5300000;cells={key:0x5304000+4*i for i,key in enumerate(KEYS)};calls=[]
        def hook(uc,address,size,user):
            if address==0x4e8e00:
                sp=uc.reg_read(UC_X86_REG_ESP);key=r(r(sp+4))
                assert key in cells and uc.reg_read(UC_X86_REG_ECX)==pet+0x34
                calls.append(key);uc.reg_write(UC_X86_REG_EAX,cells[key])
                uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+8)
        # Same native map representation at the by-value Pet argument's+134;
        # all keys exist, so original10c2300 performs lookups without inserts.
        uc.mem_write(stack+0x170,bytes(uc.mem_read(pet_bean+0x134,12)));w(0x29b8ef8,1)
        handle=uc.hook_add(UC_HOOK_CODE,hook)
        uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ESI,pet+0x34)
        uc.emu_start(0x10c301c,0x10c317e,count=20000)
        assert tuple(calls)==KEYS
        values=tuple((key,r(cells[key])) for key in KEYS)
        assert values==tuple((key,int(value)) for key,value in pairs)
        uc.hook_del(handle);result.append(values)
    probe(0xf89ba0,0xf5df70,0xf5f1f0,payload=payload,observer=observe)
    return result[0]


def main():
    default,_=probe(0xf89ba0,0xf5df70,0xf5f1f0,{4:struct.pack('<i',500001),8:struct.pack('<i',7)})
    assert default[-1:]==b'\0'
    cases=[]
    for count,added in ((0,(0,)*5),(1,(50,0,0,0,0)),(1,(0,0,0,0,50)),(2,(20,20,20,20,20)),(5,(250,0,0,0,0)),(0,(0,)*5)):
        pairs=tuple(zip(KEYS,(count,*added)))
        body=compact(6)+b''.join(struct.pack('>if',key,float(value)) for key,value in pairs)
        record=default[:-1]+body;refresh=struct.pack('>ii',1,7)+body
        assert native_pet_stones(record)==native_stone_attributes(refresh)==pairs
        cases.append({'count':count,'added':added,'record_bytes':len(record),'attr_type':'0xc32c9','body':refresh.hex()})
    write_json(OUT/'evidence/pet-stones-native.json',{'source_status':'client_verified','cases':cases,
        'initial':'original Pet last field+134 map<int,float32>; original10c301c..10c317c six actual map lookups/ftol/store ->1930/1940..1980',
        'refresh':'distinct attr::SRefreshPetData ctor ec30c0/typec32c9, marshalec3250/decoderec32f0; BE32 column1+BE32 pet key+compact float map; whole113daa0 map handler until before UI listeners writes six absolute attrs including explicit zeros',
        'oracle':'original constructor/scalar/map codecs, balanced-tree traversal, original10c2300 lookups and original x87 conversion; only current pet lookup/owned attr slots and host allocation terminals',
        'limits':['pet::SRefreshPetData c07d5 alone does not update these extras','no original server random algorithm/GUI or gameplay state changed']})
    print('PASS six original Pet tail maps/constructor stores and distinct absolute stone refresh codecs/whole assignment loops')


if __name__=='__main__':main()
