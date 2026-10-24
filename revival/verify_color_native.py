"""Execute isolated original pixel routines, without a GPU/client process."""
from pathlib import Path
import json
import struct
import sys
sys.path.insert(0, 'D:/Downloads/LCJDTClient/LCJDTClient/revival/.deps')
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ESI, UC_X86_REG_EBX, UC_X86_REG_EAX, UC_X86_REG_ECX


def main():
    base = 0x400000
    data = (Path(__file__).parent / 'evidence/native-image.bin').read_bytes()
    u = Uc(UC_ARCH_X86, UC_MODE_32)
    u.mem_map(base, (len(data)+4095)&~4095)
    u.mem_write(base, data)
    area = 0x5000000
    u.mem_map(area, 0x10000)
    source, dest, stack, context, stop = area, area+0x1000, area+0x2000, area+0x3000, area+0xfff0
    rgba = bytes.fromhex('ffeacaff')
    # SILLY::TGAImageContext pixel writer: CL = B; stack R,G,A.
    u.mem_write(context+4, struct.pack('<I',source))
    u.mem_write(context+0x18,struct.pack('<I',2))
    u.mem_write(stack,struct.pack('<IIII',stop,rgba[0],rgba[1],rgba[3]))
    u.reg_write(UC_X86_REG_ESP,stack)
    u.reg_write(UC_X86_REG_EAX,context)
    u.reg_write(UC_X86_REG_ECX,rgba[2])
    u.emu_start(0x7ad150,stop,count=1000)
    decoded=bytes(u.mem_read(source,4))
    assert decoded == rgba
    # Original Direct3D9Texture RGBA upload inner loop, one pixel only.
    u.mem_write(stack+0x14,struct.pack('<I',source))
    u.reg_write(UC_X86_REG_ESP,stack)
    u.reg_write(UC_X86_REG_EBX,dest)
    u.reg_write(UC_X86_REG_ESI,0)
    u.emu_start(0x796a42,0x796a6f,count=1000)
    uploaded=bytes(u.mem_read(dest,4))
    assert uploaded == bytes([rgba[2],rgba[1],rgba[0],rgba[3]])
    instruction=data[0x79687a-base:0x796882-base]
    assert instruction == bytes.fromhex('c744241420000000')
    result={'input_rgba':list(rgba),'native_tga_decoded_rgba':list(decoded),
            'native_upload_bytes':list(uploaded),'texture_format_original':32,
            'rendered_rgba_if_format_32':list(uploaded),
            'rendered_rgba_if_format_21':[uploaded[2],uploaded[1],uploaded[0],uploaded[3]],
            'candidate_fix_address':'0x79687e','original_byte':'20','candidate_byte':'15',
            'original_instruction':instruction.hex(),'changed_runtime_or_executable':False}
    out=Path(__file__).parent/'evidence/color-native-validation.json'
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
