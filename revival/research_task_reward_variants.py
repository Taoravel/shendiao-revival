"""Run shipped quest reward selection branch offline; never access a process."""
import hashlib
import json
import struct
import sys
from pathlib import Path

from native_inspect import BASE, DATA
from pfs import PfsArchive
from bxml import decode


def native_items(items, nums, selectors, shape):
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import (UC_X86_REG_ESI, UC_X86_REG_EDI,
        UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP)
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, (len(DATA)+4095)&~4095)
    uc.mem_write(BASE, DATA)
    uc.mem_map(0x5000000, 0x20000)
    config, role, sp = 0x5001000, 0x5002000, 0x501f000
    def put(a, *values):
        uc.mem_write(a, struct.pack('<'+'I'*len(values), *values))
    for off, values, addr in ((0x128,items,0x5004000),
            (0x138,nums,0x5005000),(0x148,selectors,0x5006000)):
        put(config+off, addr if values else 0, addr+len(values)*4 if values else 0)
        if values:
            uc.mem_write(addr, struct.pack('<'+'i'*len(values),*values))
    put(0x2944550, role)
    put(role+0x120, shape)
    selected=[]
    def hook(cpu, addr, size, user):
        if addr==0x17c5aaa:
            cpu.emu_stop()
        elif addr==0x15ff710:
            current=cpu.reg_read(UC_X86_REG_ESP)
            ret, bean=struct.unpack('<II',cpu.mem_read(current,8))
            selected.append(struct.unpack('<ii',cpu.mem_read(bean+4,8)))
            cpu.reg_write(UC_X86_REG_ESP,current+8)
            cpu.reg_write(UC_X86_REG_EIP,ret)
    uc.hook_add(UC_HOOK_CODE, hook)
    for reg,value in ((UC_X86_REG_ESI,config),(UC_X86_REG_EDI,0),
                      (UC_X86_REG_EBP,0),(UC_X86_REG_ESP,sp)):
        uc.reg_write(reg,value)
    uc.emu_start(0x17c5950,0x17c5aaa,count=10000)
    assert uc.reg_read(UC_X86_REG_EIP)==0x17c5aaa
    return selected


def main():
    root=Path(__file__).resolve().parents[1]
    archive=PfsArchive(root/'artres/config.pfs')
    audit=[]; tables={}
    for name in ('knight.gsp.task.cmainmissioninfo','knight.gsp.role.createroleconfig'):
        entry='autoconfig/'+name+'.xml'
        data=archive.read(entry)
        tree=decode(data)
        tables[name]=list(tree)
        # Compare scalar and list data rather than insignificant XML formatting.
        cat=json.loads((root/'revival/catalogs'/ (name+'.json')).read_text(encoding='utf8'))
        assert [(dict(r.attrib),{c.tag:[v.text for v in c] for c in r}) for r in tree]==[(r['attributes'],r['lists']) for r in cat]
        audit.append(dict(entry=entry,rows=len(tree),bytes=len(data),crc32=f'{archive.entries[entry].crc:08x}',sha256=hashlib.sha256(data).hexdigest()))
    choices=tables['knight.gsp.role.createroleconfig']
    shapes=[(int(r.attrib['id']),int(r.attrib[color])) for r in choices for color in ('color1','color2','color3')]
    assert all((s%10 or 10)==rid for rid,s in shapes)
    cases=[]
    for row in tables['knight.gsp.task.cmainmissioninfo']:
        lists={c.tag:[int(v.text) for v in c] for c in row if c.tag.startswith('RewardItem')}
        selectors=lists.get('RewardItemShapeIDList',[])
        if not selectors: continue
        items,nums=lists['RewardItemIDList'],lists['RewardItemNumList']
        for rid,shape in shapes:
            actual=native_items(items,nums,selectors,shape)
            expected=[(item,nums[i]) for i,item in enumerate(items) if i>=len(selectors) or not 1<=selectors[i]<=10 or selectors[i]==rid]
            assert actual==expected,(row.attrib['id'],rid,actual,expected)
        cases.append(dict(task=int(row.attrib['id']),items=items,selectors=selectors,
                          role1=native_items(items,nums,selectors,1010101),
                          role10=native_items(items,nums,selectors,1010110)))
    for selectors in ([],[0],[-1],[11],[2]):
        actual=native_items([100,101],[2,3],selectors,1010101)
        assert actual==([(101,3)] if selectors==[2] else [(100,2),(101,3)])
    print(json.dumps(dict(image_sha256=hashlib.sha256(DATA).hexdigest(),audit=audit,
        cases=cases,native_cases=len(cases)*len(shapes)+5,
        scope='original selection and original modulo getter; only vector-push allocation replaced'),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
