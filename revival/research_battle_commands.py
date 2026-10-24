"""Execute original button argument setup and action field/marshal code offline."""
import hashlib
import json
from pathlib import Path
from research_battle import NativeBattleDecoder, CLASSES
from native_inspect import DATA, BASE


def native_action(operation, target, operation_id=0, *, is_role=True):
    from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EBP
    n=NativeBattleDecoder()
    n.call(CLASSES['CSendAction'][0])
    manager=n.obj-(0x9c if is_role else 0xb8)
    n.write(n.stack+0x1c,operation,operation_id)
    n.u.reg_write(n.sp,n.stack)
    n.u.reg_write(UC_X86_REG_ESI,manager)
    n.u.reg_write(UC_X86_REG_EBP,target)
    # Execute the original player branch; stop before its network getter.
    n.u.emu_start(0x11962bf if is_role else 0x11962f9,
                  0x11962e7 if is_role else 0x1196321,count=100)
    n.write(n.stream,0x224c100,n.buf,0)
    n.write(n.buf-12,4096,0,1)
    n.call(0xe41550,n.stream)
    return bytes(n.u.mem_read(n.buf,n.read(n.buf-8)))


def button_arguments(start):
    n=NativeBattleDecoder()
    n.write(0x2944798,n.obj-0x9c)
    n.write(n.stack,n.stop)
    n.u.reg_write(n.sp,n.stack)
    # Original callback pushes target, operation and bool, then calls the actual
    # SendBattleCommand entry. No implementation is substituted for that setup.
    n.u.emu_start(start,0x1196060,count=100)
    sp=n.u.reg_read(n.sp)
    return tuple(n.read(sp+i) for i in (4,8,12))


def main():
    from capstone import Cs,CS_ARCH_X86,CS_MODE_32
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    defend=button_arguments(0x11bb230)
    escape=button_arguments(0x11bb644)
    assert defend==(0,4,0) and escape==(0,9,0)
    cases={'attack':native_action(1,21),'defend':native_action(defend[1],0),
           'escape':native_action(escape[1],0)}
    assert cases['attack'].hex()=='0000000100000015000000000100'
    assert cases['defend'].hex()=='0000000400000000000000000100'
    assert cases['escape'].hex()=='0000000900000000000000000100'
    lines=[]
    for a,size in ((0x11962bf,0x28),(0x11bb230,0x15),(0x11bb644,0x11),
                   (0x11bb680,0x980),(0x1195da0,0x2b0)):
        lines.append(f'\nRANGE {a:x}')
        lines.extend(f'{i.address:08x} {i.mnemonic} {i.op_str}'
                     for i in md.disasm(DATA[a-BASE:a-BASE+size],a) if i.mnemonic!='int3')
    out=Path(__file__).parent/'evidence'
    (out/'battle-command-disassembly.txt').write_text('\n'.join(lines),encoding='utf-8')
    report={'image_sha256':hashlib.sha256(DATA).hexdigest(),
            'sender_field_setup':'0x11962bf..0x11962e7',
            'wire_scalar_order':['operation_type','target','operation_id'],
            'native_player_flag':1,'native_manual_flag':0,
            'defend_callback':'0x11bb230','escape_button_callback':'0x11bb470',
            'escape_command_branch':'0x11bb644',
            'button_labels_source':'decoded/ui/layouts/characteroperatedlg.layout skill2/skill7',
            'packets':{k:v.hex() for k,v in cases.items()},
            'round_start_first_i32':'seconds; Process 0x1196013..0x1196025 multiplies by 1000',
            'scope':'original callback argument setup and sender field stores plus original marshal; no live UI execution'}
    (out/'battle-command-native.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
