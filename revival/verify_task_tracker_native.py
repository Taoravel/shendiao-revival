"""Offline original x86 tracker dispatch; no client or live database access."""
import json
import struct
from pathlib import Path
from native_inspect import BASE, DATA
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_ESI, UC_X86_REG_EBX, UC_X86_REG_EAX, UC_X86_REG_EIP
from pfs import PfsArchive
from bxml import decode


def run(state):
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(0, 4096)
    uc.mem_map(BASE, (len(DATA)+4095)&~4095)
    uc.mem_write(BASE, DATA)
    uc.mem_map(0x5000000, 0x10000)
    stack, bean, ui, owner = 0x5008000, 0x5001000, 0x5002000, 0x5003000
    uc.mem_write(bean+8, struct.pack('<I', state))
    uc.mem_write(stack+0x14, struct.pack('<I', bean))
    uc.reg_write(UC_X86_REG_ESP, stack)
    uc.reg_write(UC_X86_REG_ESI, owner)
    uc.reg_write(UC_X86_REG_EBX, ui)
    result = {'state': state}
    def hook(uc, address, size, _):
        if address == 0x160d560:
            sp = uc.reg_read(UC_X86_REG_ESP)
            result.update(branch='failure', helper=hex(address),
                          item=hex(struct.unpack('<I', uc.mem_read(sp+4, 4))[0]),
                          data=struct.unpack('<I', uc.mem_read(sp+8, 4))[0])
            uc.emu_stop()
        elif address == 0x160db18:
            result.update(branch='normal_config_trace', next=hex(address))
            uc.emu_stop()
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(0x160daf5, 0, count=30)
    assert 'branch' in result
    return result


def trace_path(state):
    """Classify an original ScenarioQuestInfo.state on existing tracker update."""
    return run(state)


def failure_text():
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, (len(DATA)+4095)&~4095)
    uc.mem_write(BASE, DATA)
    uc.mem_map(0x5000000, 0x10000)
    stack, table, config, fn = 0x5008000, 0x5001000, 0x5002000, 0x5003000
    def w(at, value): uc.mem_write(at, struct.pack('<I', value))
    w(table, table+16); w(table+24, fn); w(config, 1000); w(config+0x88, 100)
    uc.reg_write(UC_X86_REG_ESP, stack)
    uc.reg_write(UC_X86_REG_EBX, 0)
    result = {}
    def ret(value, pop=0):
        sp=uc.reg_read(UC_X86_REG_ESP)
        dest=struct.unpack('<I',uc.mem_read(sp,4))[0]
        uc.reg_write(UC_X86_REG_EAX,value)
        uc.reg_write(UC_X86_REG_ESP,sp+4+pop)
        uc.reg_write(UC_X86_REG_EIP,dest)
    def hook(uc,address,size,_):
        if address == 0x89ea90: ret(table)
        elif address == fn:
            sp=uc.reg_read(UC_X86_REG_ESP)
            result['config_id']=struct.unpack('<I',uc.mem_read(sp+4,4))[0]
            ret(config,4)
        elif address == 0x74b0f0:
            sp=uc.reg_read(UC_X86_REG_ESP)
            result['field_offset']=hex(struct.unpack('<I',uc.mem_read(sp+4,4))[0]-config)
            uc.emu_stop()
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.emu_start(0x160d765,0,count=50)
    assert result == {'config_id':1000,'field_offset':'0x90'}
    return result


if __name__ == '__main__':
    cases=[run(s) for s in (0,2,3)]
    assert [c['branch'] for c in cases] == ['normal_config_trace','failure','normal_config_trace']
    assert cases[1]['data']==0
    result={'dispatch':cases,'failure':failure_text()}
    archive=PfsArchive(Path(__file__).parents[1]/'artres/config.pfs')
    root=decode(archive.read('autoconfig/knight.gsp.specialquest.cspecialquestconfig.xml'))
    row=next(x for x in root if x.attrib.get('id')=='1000')
    result['failure']['text']=row.attrib['tracdiscribe']
    assert '任务已失败' in result['failure']['text']
    print(json.dumps(result,ensure_ascii=False,indent=2))
