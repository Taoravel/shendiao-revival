"""Original pet refresh stores, growth UI arithmetic and blood-color lookup."""
import json
import struct

from native_inspect import BASE, DATA
from inspect_client import OUT, write_json


class NativePetPresentation:
    def __init__(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_ESI, UC_X86_REG_EBX,
            UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_FPCW, UC_X86_REG_EDI)
        self.regs = dict(sp=UC_X86_REG_ESP, si=UC_X86_REG_ESI, bx=UC_X86_REG_EBX,
                         ax=UC_X86_REG_EAX, cx=UC_X86_REG_ECX, ip=UC_X86_REG_EIP, di=UC_X86_REG_EDI)
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(0, 0x1000)
        self.uc.mem_map(BASE, (len(DATA) + 4095) & ~4095)
        self.uc.mem_write(BASE, DATA)
        self.uc.mem_map(0x5000000, 0x200000)
        self.message, self.pet, self.panel, self.stack = 0x5001000, 0x5002000, 0x5003000, 0x5100000
        self.manager, self.row = 0x5004000, 0x5005000
        self.w(self.manager, self.manager + 0x100)
        self.w(self.manager + 0x108, 0x500f000)
        self.w(0x2945724, 0)  # No GUI observer exists in this offline probe.
        self.uc.reg_write(UC_X86_REG_FPCW, 0x37f)
        rows = json.loads((OUT / 'catalogs/knight.gsp.pet.cpetxuemaiconfig.json').read_text(encoding='utf-8'))
        self.skills = {int(r['attributes']['id']): int(r['attributes']['skillnumber']) for r in rows}
        self.lookup_keys = []
        self.uc.hook_add(UC_HOOK_CODE, self.hook)

    def w(self, addr, *values):
        self.uc.mem_write(addr, struct.pack('<' + 'I' * len(values), *values))

    def r(self, addr):
        return struct.unpack('<I', self.uc.mem_read(addr, 4))[0]

    def ret(self, count=0, value=None):
        sp = self.uc.reg_read(self.regs['sp'])
        dest = self.r(sp)
        if value is not None:
            self.uc.reg_write(self.regs['ax'], value)
        self.uc.reg_write(self.regs['sp'], sp + 4 + count)
        self.uc.reg_write(self.regs['ip'], dest)

    def hook(self, uc, addr, size, user):
        if addr == 0x89e3b0:
            self.ret(value=self.manager)
        elif addr == 0x500f000:
            key = self.r(uc.reg_read(self.regs['sp']) + 4)
            assert key in self.skills
            self.lookup_keys.append(key)
            self.w(self.row, key)
            self.w(self.row + 0x28, self.skills[key])
            self.ret(4, self.row)

    def run(self, start, end, **registers):
        self.uc.reg_write(self.regs['sp'], self.stack)
        for name, value in registers.items():
            self.uc.reg_write(self.regs[name], value)
        self.uc.emu_start(start, end, count=1000)
        assert self.uc.reg_read(self.regs['ip']) == end

    def consume(self, native_message):
        self.uc.mem_write(self.message, native_message)
        self.run(0x1135303, 0x1135310, si=self.message, bx=self.pet)
        self.run(0x11354fb, 0x113551c, si=self.message, bx=self.pet)
        return self.growth_integer(), self.r(self.pet + 0x2c)

    def growth_integer(self, *, cpu_sse=True):
        # Both paths execute the original conversion helper. This flag models
        # the original CPU capability switch, not a replacement arithmetic rule.
        self.w(0x29b8ef8, int(cpu_sse))
        self.run(0x1130d35, 0x1130d43, si=self.pet)
        return self.uc.reg_read(self.regs['ax'])

    def color_skill_slots(self):
        self.w(self.panel + 0x158, self.pet)
        self.run(0x140df60, 0x140df92, di=self.panel)
        return self.r(self.stack + 0x24)


def main():
    native = NativePetPresentation()
    samples = []
    for raw in (986, 996, 1006, 1256):
        wire_float = struct.unpack('<f', struct.pack('<f', raw / 1000))[0]
        native.uc.mem_write(native.pet + 0x30, struct.pack('<f', wire_float))
        samples.append({'raw': raw, 'nearest_float32': wire_float,
                        'original_integer': native.growth_integer(),
                        'original_x87_integer': native.growth_integer(cpu_sse=False)})
    result = {'source': 'original refresh1135303..1135310/11354fb..113551c and UI1130d35..1130d43/140df60..140df92',
        'growth_scale': 'native stored float times original binary64 1000, original truncation helper',
        'nearest_float_examples': samples,
        'blood_color': 'message+44 (bean+3c) -> pet+2c -> original89e3b0 CPetXueMaiConfig lookup',
        'config_identity': 'constructor d436fc writes vtable225ce24 at root+c1c; 89e3b0 returns same offset',
        'skill_slots_member': 'UTF16 skillnumber225cdcc parsed886d20..886d49 to record+28',
        'adapter': 'configuration lookup only; original floating store/multiply/conversion and grade lookup argument execute',
        'native_gui_tested': False}
    write_json(OUT / 'evidence/pet-presentation-native.json', result)
    print('Original float32 growth projection:', [(x['raw'], x['original_integer']) for x in samples])


if __name__ == '__main__':
    main()
