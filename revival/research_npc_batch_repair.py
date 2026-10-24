"""Offline first-party batch repair codecs and UI identity; no process/DB/network."""
import contextlib
import hashlib
import io
import json
import struct
from pathlib import Path
from native_inspect import BASE, DATA, u32, vtables, disasm
from native_gameplay_probe import probe
from research_npc_submenu import Machine

OUT = Path(__file__).parent / 'evidence'


def roundtrip(ctor, marshal, unmarshal, payload, expected=None):
    """Actual decoder then actual serializer on the decoded object, not a Python codec."""
    from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
    result = []
    def observe(uc, target):
        stream, buf, stack, stop = 0x5002000, 0x5003000, 0x5100000, 0x500f000
        uc.mem_write(buf-12, struct.pack('<III', 0x7000, 0, 1))
        uc.mem_write(stream+8, bytes(4))
        uc.mem_write(stack, struct.pack('<II', stop, stream))
        uc.reg_write(UC_X86_REG_ECX, target)
        uc.reg_write(UC_X86_REG_ESP, stack)
        uc.emu_start(marshal, stop, count=1000000)
        assert uc.reg_read(UC_X86_REG_EIP) == stop
        length = struct.unpack('<I', uc.mem_read(buf-8, 4))[0]
        result.append(bytes(uc.mem_read(buf, length)))
    probe(ctor, marshal, unmarshal, payload=payload, observer=observe)
    assert result == [payload if expected is None else expected], result
    return result[0].hex()


def single_ui_send():
    """Real CEquipRepairDlg callback with selected-item/UI/network dependencies adapted."""
    m = Machine()
    window, item, bean, net, vt, send = (0x5003000+i*0x1000 for i in range(6))
    key = 0x1234567800000004
    m.w(m.stack, m.stop, 0)
    m.w(m.ui+0x14, window)
    m.w(window+0x278, item)
    m.w(item, bean)
    m.w(bean+0x14, 91)
    m.w(m.ui+0x198, key & 0xffffffff, key >> 32, 2, 4)
    m.w(net, vt)
    m.w(vt+0x3c, send)
    sent = []
    def hook(uc, address, size, user):
        sp = uc.reg_read(m.spreg)
        if address == 0x813860:
            m.ret(net)
        elif address == send:
            obj = m.r(sp+4)
            assert m.r(obj) == 0x2276c04 and m.r(obj+4) == 0xc0413
            fields = (m.r(obj+8), m.r(obj+0x10), m.r(obj+0x14), m.r(obj+0x18), m.r(obj+0x1c))
            assert fields == (2, key & 0xffffffff, key >> 32, 4, 91), fields
            sent.append({'type': hex(m.r(obj+4)), 'method': fields[0],
                         'npc_key': key, 'column': fields[3], 'item_key': fields[4]})
            m.ret(1, 4)
        elif address == 0x10ddae1:
            uc.emu_stop()  # Post-send UI redraw is outside the protocol question.
    m.run(0x10dda40, hook)
    assert len(sent) == 1
    return sent[0]


def main():
    assert vtables('.?AVCRepairEquipItemMulit@item@gsp@knight@@') == [0x2281560]
    assert vtables('.?AVSRepairEquipItemMulit@item@gsp@knight@@') == [0x2284478]
    assert vtables('.?AVCEquipCarryWithRepairDlg@@') == [0x228dae0]
    assert vtables('.?AVCEquipRepairDlg@@') == [0x228e5f8]
    idx = DATA[0x163f340-BASE+513-0x117]
    assert idx == 35 and u32(0x163f2a8+idx*4) == 0x1638029
    cases = []
    for method in (0, 1):
        for first, second in (((), ()), ((91, 7, 91), (44,)), ((-1, 2147483647), (-2147483648,))):
            payload = struct.pack('>i', method)
            for values in (first, second):
                payload += bytes([len(values)]) + b''.join(struct.pack('>i', x) for x in values)
            cases.append({'request_method': method, 'first': first, 'second': second,
                          'hex': roundtrip(0xe6c6b0, 0xe6c880, 0xe6c780, payload)})
    for method in (-1, 2):
        try:
            roundtrip(0xe6c6b0, 0xe6c880, 0xe6c780, struct.pack('>i', method)+bytes(2))
        except ValueError:
            cases.append({'rejected_method': method})
        else:
            raise AssertionError('Original method constraint missing')
    # Unsorted input proves a map: decoded keys marshal back in sorted order.
    response = b'\2'+struct.pack('>iiii', 91, 1, 7, 0)+b'\1'+struct.pack('>ii',44,1)
    sorted_response = b'\2'+struct.pack('>iiii', 7, 0, 91, 1)+b'\1'+struct.pack('>ii',44,1)
    cases.append({'response_two_maps': roundtrip(0xefe8c0,0xefe9a0,0xefea30,response,sorted_response)})
    cases.append({'response_empty': roundtrip(0xefe8c0,0xefe9a0,0xefea30,bytes(2))})
    single = single_ui_send()
    sections = [(0xe6c6b0,0x27c),(0x82db40,0x165),(0xefe8c0,0x1f0),
                (0x10cc250,0x225),(0x10cdb00,0x790),(0x10cbc60,0x38),
                (0x10cc920,0x140),(0x1637fad,0x31),(0x1638029,0x2e),
                (0x16299a0,0xa0),(0x10dca07,0x50),(0x10dc580,0x70),
                (0x10dda40,0xa9),(0x10de1e0,0x47)]
    with (OUT/'npc-batch-repair-native-disassembly.txt').open('w',encoding='utf-8') as f:
        with contextlib.redirect_stdout(f):
            for address, length in sections:
                print('\nREGION',hex(address),hex(length)); disasm(address,length)
    report = {'image_sha256':hashlib.sha256(DATA).hexdigest(), 'cases':cases,
              'single_ui_send':single, 'service513_target':'0x1638029',
              'batch_class':'CEquipCarryWithRepairDlg','batch_layout':'EquipRepair.layout',
              'single_class':'CEquipRepairDlg','single_layout':'EquipmentRepairSmiple.layout',
              'native_gui_verified':False,'production_changed':False,'live_process_accessed':False}
    (OUT/'npc-batch-repair-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
