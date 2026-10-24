"""Original book request and ordinary learned list; no live client or socket."""
import struct

from native_gameplay_probe import probe
from pet_protocol import decode_skill_book,decode_skill_book_request,LEARN_SKILL_BOOK
from inspect_client import OUT,write_json


def native_drag_request():
    from native_inspect import BASE,DATA
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x200000)
    dialog,event,data,item,stack=0x5001000,0x5002000,0x5003000,0x5004000,0x5100000
    def w(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    w(dialog+0xac,7);w(stack+0x38,event);w(event+8,data);w(data+0x278,item);w(item+0x10,91)
    uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,dialog)
    uc.emu_start(0x142d844,0x142d885,count=100)
    assert uc.reg_read(UC_X86_REG_EIP)==0x142d885
    assert struct.unpack('<I',uc.mem_read(stack+0xc,4))[0]==LEARN_SKILL_BOOK
    return struct.unpack('<6i',uc.mem_read(stack+0x10,24))


def main():
    values=native_drag_request()
    assert values==(7,91,-1,-1,-1,-1)
    body,raw=probe(0xdbc7a0,0xe53610,0xdbc880,{8:struct.pack('<6i',*values)})
    assert body==struct.pack('>6i',*values) and decode_skill_book(body)==(7,91)
    assert struct.unpack_from('<6i',raw,8)==values
    for selected in ((7,91,92,-1,200091,-1),(7,91,92,93,200091,200061)):
        native,decoded=probe(0xdbc7a0,0xe53610,0xdbc880,{8:struct.pack('<6i',*selected)})
        request=decode_skill_book_request(native)
        assert (request.pet_id,request.item_key,*request.options.wire_values)==selected
        assert struct.unpack_from('<6i',decoded,8)==selected
    for bad in (body[:-1],body+b'\0',struct.pack('>6i',0,91,-1,-1,-1,-1),
                struct.pack('>6i',7,91,0,-1,-1,-1)):
        try:decode_skill_book(bad)
        except ValueError:pass
        else:raise AssertionError('Unsupported book request accepted')
    report={'passed':['original drag-use branch emits c07ff with canonical last4=-1',
        'all six request fields match original marshal/unmarshal',
        'owned pet/book identity slots remain distinct from skill/template IDs',
        'full decoder preserves native certification instance keys and protected exact IDs',
        'truncated/extra/nonpositive refuse; legacy canonical decoder excludes options'],
        'original_ui_slice':'142d844..142d885 before transport',
        'native_gui_tested':False,'live_server_changed':False}
    write_json(OUT/'evidence/pet-skill-protocol-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
