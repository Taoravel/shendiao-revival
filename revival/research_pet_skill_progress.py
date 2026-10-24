"""Original progress map codec, dialog merge, lookup and progress-bar math."""
import json
import struct

from inspect_client import OUT,write_json
from native_gameplay_probe import probe


def native_progress(payload,*,selected=7,skill_count=3,threshold=40):
    """Execute actual client consumers; observe terminal config/GUI seams."""
    result=[]
    def observe(uc,target):
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EBX,
            UC_X86_REG_ECX,UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EIP)
        def r(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
        def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
        dialog,tree,pet,root,table,record,stack,stop=(
            0x5300000,0x5302000,0x5303000,0x5308000,0x530a000,
            0x530b000,0x5108000,0x500f000)
        w(dialog+0xd0,tree,0);w(tree,tree,tree,tree)
        uc.mem_write(tree+0x15,b'\x01')
        w(stack,stop,target+8)
        uc.reg_write(UC_X86_REG_ECX,dialog);uc.reg_write(UC_X86_REG_ESP,stack)
        uc.emu_start(0x142f870,0x142f8f2,count=50000)
        assert uc.reg_read(UC_X86_REG_EIP)==0x142f8f2
        copied={}
        def visit(node):
            if node==tree:return
            assert len(copied)<32
            visit(r(node))
            key=struct.unpack('<i',uc.mem_read(node+0xc,4))[0]
            copied[key]=struct.unpack('<H',uc.mem_read(node+0x10,2))[0]
            visit(r(node+8))
        visit(r(tree+4))
        assert len(copied)==r(dialog+0xd4)
        w(dialog+0xac,selected);w(pet+0x48,skill_count)
        uc.mem_write(stack,bytes(0x100));w(stack+0x14,pet)
        uc.reg_write(UC_X86_REG_ESP,stack)
        uc.reg_write(UC_X86_REG_EBX,dialog+0xac)
        uc.reg_write(UC_X86_REG_ESI,dialog)
        uc.emu_start(0x142f009,0x142f00b,count=10)  # original FLDZ
        uc.emu_start(0x142f061,0x142f0ba,count=2000)
        assert uc.reg_read(UC_X86_REG_EIP)==0x142f0ba
        displayed=struct.unpack('<f',uc.mem_read(stack+0x18,4))[0]
        expected=copied.get(selected,0)
        if expected>=32768:expected-=65536
        assert displayed==expected
        # Execute the actual config getter and ratio calculation. The table
        # query supplies original extracted row values; terminal GUI is observed.
        w(0x2945aec,root);w(root+0x658,table);w(table+8,0x500d000)
        w(record,skill_count,threshold)
        queries=[];ratios=[]
        def ret(n,v=0):
            sp=uc.reg_read(UC_X86_REG_ESP);dest=r(sp)
            uc.reg_write(UC_X86_REG_EAX,v);uc.reg_write(UC_X86_REG_ESP,sp+4+n)
            uc.reg_write(UC_X86_REG_EIP,dest)
        def terminal(uc,address,size,user):
            sp=uc.reg_read(UC_X86_REG_ESP)
            if address==0x500d000:
                queries.append(r(sp+4));ret(4,record)
            elif address==0x4ba4b0:
                ratios.append(struct.unpack('<f',uc.mem_read(sp+4,4))[0]);ret(4)
        hook=uc.hook_add(UC_HOOK_CODE,terminal)
        end=0x142f10b if threshold>0 else 0x142f0e6
        uc.emu_start(0x142f0ba,end,count=2000);uc.hook_del(hook)
        assert uc.reg_read(UC_X86_REG_EIP)==end and queries==[skill_count]
        if threshold>0:
            expected_ratio=struct.unpack('<f',struct.pack('<f',displayed/threshold))[0]
            assert ratios==[expected_ratio]
        result.append({'copied':copied,'selected':selected,'displayed_progress':displayed,
            'threshold_key':queries[0],'threshold':threshold,'bar_ratio':ratios})
    probe(0xf21090,0xf213f0,0xf21450,payload=payload,observer=observe)
    return result[0]


def main():
    cases=[]
    thresholds={int(r['attributes']['id']):int(r['attributes']['progress']) for r in
        json.loads((OUT/'catalogs/knight.gsp.item.cpetskillsuccessconfig.json').read_text(encoding='utf-8'))}
    for count,threshold in thresholds.items():
        cases.append(native_progress(b'\2'+struct.pack('>iHiH',7,7,8,19),
                                     skill_count=count,threshold=threshold))
    for raw in (0,32767,32768,65535):
        cases.append(native_progress(b'\1'+struct.pack('>iH',7,raw)))
    cases.append(native_progress(b'\1'+struct.pack('>iH',8,19)))
    assert probe(0xdbcab0,0xdbcad0,0xdbcae0,payload=b'')[0]==b''
    write_json(OUT/'evidence/pet-skill-progress-consumer.json',{
        'source_status':'client_verified','passed':len(cases),'cases':cases,
        'original_request':'c0800 empty; ctor dbcab0',
        'original_reply':'c0801 compact map<i32,i16>; ctorf21090/marshalf213f0/decoderf21450',
        'original_consumer':'142f870..142f8f2 merge;142f061..142f10b lookup/config/math',
        'table_association':'d4234e installs CPetSkillSuccessConfig table vtable225718c at root+658, returned by89d870',
        'adapters':'table query returns original extracted row; terminal progress bar observed; native GUI not rendered',
        'server_progress_algorithm_recovered':False,'native_gui_tested':False})
    print('PASS',len(cases),'original progress map/merge/lookup/signed16/skill-count threshold/UI math cases')


if __name__=='__main__':main()
