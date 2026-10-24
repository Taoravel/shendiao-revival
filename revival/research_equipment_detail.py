"""Execute original basic equipment detail parsing and native color derivation.

Stops before advanced property containers. A prefix pass is not a complete tip.
"""
import struct
import json
from native_inspect import BASE,DATA,u32
from inspect_client import OUT,write_json
from wire import octets


def parse_prefix(template,prefix,score,current=80,maximum=100):
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EAX,UC_X86_REG_EIP
    item_rows=json.loads((OUT/'catalogs/knight.gsp.item.citemattr.json').read_text(encoding='utf-8'))
    equip_rows=json.loads((OUT/'catalogs/knight.gsp.item.cequipeffect.json').read_text(encoding='utf-8'))
    prefix_rows=json.loads((OUT/'catalogs/knight.gsp.item.cequipprefixconfig.json').read_text(encoding='utf-8'))
    kind=next(int(r['attributes']['itemtypeid']) for r in item_rows if int(r['attributes']['id'])==template)
    thresholds=tuple(map(int,next(r['lists']['scorecolor'] for r in equip_rows if int(r['attributes']['id'])==template)))
    cap=next(int(r['attributes']['bestcolortype']) for r in prefix_rows if int(r['attributes']['id'])==prefix)
    payload=struct.pack('>7i',1,0,current,maximum,0,0,0)+octets(b'')+struct.pack('>3i',prefix,score,1)
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(0,0x1000);emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x400000)
    obj,stream,buf,stack,stop=0x5001000,0x5002000,0x5003000,0x5100000,0x500f000
    managers={0x89d520:0x5004000,0x89d730:0x5004100,0x89d4c0:0x5004200}
    row_prefix,row_item,row_effect=0x5006000,0x5007000,0x5008000
    def w(a,*v):emu.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def read(a):return struct.unpack('<I',emu.mem_read(a,4))[0]
    def ret(count=0,value=None):
        sp=emu.reg_read(UC_X86_REG_ESP);dest=read(sp)
        if value is not None:emu.reg_write(UC_X86_REG_EAX,value)
        emu.reg_write(UC_X86_REG_ESP,sp+4+count);emu.reg_write(UC_X86_REG_EIP,dest)
    w(obj+0xc,template);w(obj+0xe4+24,7)
    w(stream,0x224c100,buf,0);w(buf-12,len(payload),len(payload),1);emu.mem_write(buf,payload)
    w(stack,stop,stream)
    for i,manager in enumerate(managers.values()):
        vt=manager+0x200;w(manager,vt);w(vt+8,0x500f100+i*0x10)
    w(row_prefix,prefix);w(row_prefix+0x20,cap)
    w(row_item,template,kind)
    w(row_effect,template);w(row_effect+0x2c,0x5009000,0x5009000+4*len(thresholds),0x5009000+4*len(thresholds))
    w(0x5009000,*thresholds)
    imports={u32(p):label for p,label in ((0x2244890,'alloc'),(0x2244894,'free'),
        (0x2244354,'decrement'),(0x2244334,'increment'),(0x2244514,'begin'),(0x2244510,'end'))}
    for page in {a&~0xfff for a in imports if not BASE<=a<BASE+len(DATA)}:emu.mem_map(page,0x1000)
    heap=[0x5200000];lookups=[]
    def hook(uc,address,size,user):
        if address in (stop,0x107de55):uc.emu_stop();return
        sp=uc.reg_read(UC_X86_REG_ESP);label=imports.get(address)
        if address in managers:ret(value=managers[address]);return
        if address in (0x500f100,0x500f110,0x500f120):
            index=(address-0x500f100)//16;key=read(sp+4)
            assert key==(prefix if index==0 else template)
            lookups.append(('prefix','item','effect')[index])
            ret(4,(row_prefix,row_item,row_effect)[index]);return
        if label=='alloc':
            ptr=heap[0];heap[0]+=(read(sp+4)+15)&~15;ret(value=ptr)
        elif label=='free':ret()
        elif label in ('increment','decrement'):
            ptr=read(sp+4);value=(read(ptr)+(1 if label=='increment' else -1))&0xffffffff
            w(ptr,value);ret(4,value)
        elif label in ('begin','end'):
            ptr=uc.reg_read(UC_X86_REG_ECX);result=read(sp+4)
            data=ptr+4 if read(ptr+24)<8 else read(ptr+4)
            w(result,ptr,data+(read(ptr+20)*2 if label=='end' else 0));ret(4,result)
        elif address==0x74a6d0:
            ptr=uc.reg_read(UC_X86_REG_ECX);begin,end=read(sp+20),read(sp+24)
            assert begin==end  # This probe intentionally has an empty UTF16 field.
            w(ptr+20,0);w(ptr+24,7);ret(28,ptr)
        elif address==0x19191c2:
            dest,src,count=read(sp+4),read(sp+8),read(sp+12)
            if count:uc.mem_write(dest,bytes(uc.mem_read(src,count)))
            ret(value=dest)
        elif address==0x1919184:ret()
        elif address==0x1919292:raise ValueError('Original equipment prefix rejected')
    emu.hook_add(UC_HOOK_CODE,hook)
    emu.reg_write(UC_X86_REG_ESP,stack);emu.reg_write(UC_X86_REG_ECX,obj)
    emu.emu_start(0x107d960,0x107de55,count=100000)
    assert emu.reg_read(UC_X86_REG_EIP)==0x107de55 and read(stream+8)==len(payload)
    return {'template':template,'prefix_quality':prefix,'score':score,'color':read(obj+0x5c),
        'next_color_score':read(obj+0x64),'identified':read(obj+0x58),
        'current':read(obj+0xc8),'maximum':read(obj+0xcc),
        'prefix_bytes_consumed':read(stream+8),'lookups':lookups,'thresholds':thresholds,'quality_color_cap':cap}


def main():
    examples=[]
    for prefix,score in ((1,0),(1,292),(1,364),(1,9999),(5,9999)):
        row=parse_prefix(40100,prefix,score)
        examples.append(row)
    assert [r['color'] for r in examples]==[1,2,3,3,6]
    assert examples[0]['next_color_score']==292
    assert examples[-1]['next_color_score']==0
    assert all((r['identified'],r['current'],r['maximum'])==(1,80,100) for r in examples)
    result={'source':'original EquipObject parser107d960, stopped at107de55',
        'examples':examples,'consumed_prefix_bytes':41,
        'adapter':'configuration lookup, allocation and empty UTF16 string assignment; original scalar reads and color arithmetic execute',
        'complete_tip_parser_executed':False,'native_ui_tested':False,
        'remaining':'advanced attribute/gem/skill containers and later extension fields'}
    write_json(OUT/'evidence/equipment-detail-prefix.json',result)
    print('PASS original equipment detail prefix and color/quality distinction:',[r['color'] for r in examples])


if __name__=='__main__':main()
