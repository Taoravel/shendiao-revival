"""Offline execution of the original EquipObject constructor and detail parser.

Configuration and OS/runtime imports are adapters. Item maps, scalar readers,
container readers and color calculation execute from the original image.
No client process is opened and no production item state is changed.
"""
import json
import struct

from native_inspect import BASE, DATA, u32
from inspect_client import OUT, write_json
from wire import octets


def basic_payload(prefix=1, score=0, properties=((120, 37), (140, 21)),
                  current=80, maximum=100):
    return (struct.pack('>7i', 1, 0, current, maximum, 0, 0, 0)
            + octets(b'') + struct.pack('>3i', prefix, score, 1)
            + struct.pack('>i', len(properties))
            + b''.join(struct.pack('>ii', *pair) for pair in properties)
            + struct.pack('>5i', 0, 0, 0, 0, 0)
            + octets(b'') + struct.pack('>12i', *([0] * 12)) + b'\0\0')


class NativeEquipmentDetail:
    def __init__(self, template=40100, prefix=1):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_ECX,
                                       UC_X86_REG_EAX, UC_X86_REG_EIP)
        self.regs = UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX, UC_X86_REG_EIP
        self.emu = Uc(UC_ARCH_X86, UC_MODE_32)
        self.emu.mem_map(0, 0x1000)
        self.emu.mem_map(BASE, (len(DATA) + 4095) & ~4095)
        self.emu.mem_write(BASE, DATA)
        self.emu.mem_map(0x5000000, 0x800000)
        self.obj, self.stream, self.buf = 0x5001000, 0x5002000, 0x5003000
        self.stack, self.stop, self.heap = 0x5100000, 0x500f000, 0x5200000
        self.lookups, self.trace = [], []
        self.template, self.prefix = template, prefix
        def catalog(name):
            return json.loads((OUT / ('catalogs/knight.gsp.item.' + name + '.json')).read_text(encoding='utf-8'))
        def row(name, key):
            return next(r for r in catalog(name) if int(r['attributes']['id']) == key)
        item = row('citemattr', template)
        effect = row('cequipeffect', template)
        quality = row('cequipprefixconfig', prefix)
        self.managers = {a: 0x5004000 + i * 0x400 for i, a in enumerate(
            (0x89d520, 0x89d730, 0x89d4c0, 0x89d510, 0x89d6a0))}
        self.rows = (0x5006000, 0x5007000, 0x5008000, 0x500a000)
        for i, manager in enumerate(self.managers.values()):
            self.w(manager, manager + 0x100)
            self.w(manager + 0x104, 0x500f200 + i * 0x10)
            self.w(manager + 0x108, 0x500f100 + i * 0x10)
        self.w(self.rows[0], prefix)
        self.w(self.rows[0] + 0x20, int(quality['attributes']['bestcolortype']))
        self.w(self.rows[1], template, int(item['attributes']['itemtypeid']))
        thresholds = tuple(map(int, effect['lists']['scorecolor']))
        self.w(self.rows[2], template)
        self.w(self.rows[2] + 0x2c, 0x5009000, 0x5009000 + len(thresholds) * 4,
               0x5009000 + len(thresholds) * 4)
        self.w(0x5009000, *thresholds)
        # Make-up configuration lookup happens even at enhancement zero. Its
        # contents are not read on the ordinary zero-enhancement branch.
        self.w(self.rows[3], template)
        self.god_ids = tuple(int(r['attributes']['id']) for r in catalog('cgodweapon'))
        self.w(0x500b000, *self.god_ids)
        self.imports = {u32(p): label for p, label in (
            (0x2244890, 'alloc'), (0x2244894, 'free'),
            (0x2244354, 'decrement'), (0x2244334, 'increment'),
            (0x2244514, 'begin'), (0x2244510, 'end'),
            (0x2244450, 'string_ctor'), (0x2244414, 'string_assign_empty'))}
        for page in {a & ~0xfff for a in self.imports if not BASE <= a < BASE + len(DATA)}:
            self.emu.mem_map(page, 0x1000)
        self.emu.hook_add(UC_HOOK_CODE, self.hook)
        self.call(0x107cf80)
        assert self.r(self.obj) == 0x228c5f4
        self.w(self.obj + 0xc, template)

    def w(self, address, *values):
        self.emu.mem_write(address, struct.pack('<' + 'I' * len(values), *[v & 0xffffffff for v in values]))

    def r(self, address):
        return struct.unpack('<I', self.emu.mem_read(address, 4))[0]

    def ret(self, count=0, value=None):
        esp, _, eax, eip = self.regs
        sp = self.emu.reg_read(esp)
        dest = self.r(sp)
        if value is not None:
            self.emu.reg_write(eax, value)
        self.emu.reg_write(esp, sp + 4 + count)
        self.emu.reg_write(eip, dest)

    def hook(self, uc, address, size, user):
        esp, ecx, _, _ = self.regs
        sp = uc.reg_read(esp)
        if address == self.stop:
            uc.emu_stop()
            return
        if address in (0x107de55, 0x107e0d9, 0x107e3ba, 0x107e78d,
                       0x107f1d6, 0x107f39e, 0x107f501, 0x107f521,
                       0x107f66f, 0x107f762, 0x107f782, 0x107f9cd, 0x107fabb):
            self.trace.append((hex(address), self.r(self.stream + 8)))
        label = self.imports.get(address)
        if address in self.managers:
            self.ret(value=self.managers[address])
        elif 0x500f100 <= address <= 0x500f140 and address % 16 == 0:
            index = (address - 0x500f100) // 16
            key = self.r(sp + 4)
            assert key == (self.prefix if index == 0 else self.template)
            self.lookups.append((index, key))
            assert index < 4
            self.ret(4, self.rows[index])
        elif address == 0x500f240:
            result = self.r(sp + 4)
            self.w(result + 4, 0x500b000, 0x500b000 + 4 * len(self.god_ids),
                   0x500b000 + 4 * len(self.god_ids))
            self.ret(4, result)
        elif label == 'alloc' or address == 0x1919178:
            ptr = self.heap
            self.heap += (self.r(sp + 4) + 15) & ~15
            assert self.heap < 0x5700000
            self.ret(value=ptr)
        elif label == 'free' or address == 0x191910c:
            self.ret()
        elif label in ('increment', 'decrement'):
            ptr = self.r(sp + 4)
            value = (self.r(ptr) + (1 if label == 'increment' else -1)) & 0xffffffff
            self.w(ptr, value)
            self.ret(4, value)
        elif label in ('string_ctor', 'string_assign_empty'):
            ptr = uc.reg_read(ecx)
            if label == 'string_assign_empty':
                assert bytes(uc.mem_read(self.r(sp + 4), 2)) == b'\0\0'
            self.w(ptr + 20, 0, 7)
            uc.mem_write(ptr + 4, b'\0\0')
            self.ret(4 if label == 'string_assign_empty' else 0, ptr)
        elif label in ('begin', 'end'):
            ptr, result = uc.reg_read(ecx), self.r(sp + 4)
            data = ptr + 4 if self.r(ptr + 24) < 8 else self.r(ptr + 4)
            self.w(result, ptr, data + (2 * self.r(ptr + 20) if label == 'end' else 0))
            self.ret(4, result)
        elif address == 0x74a6d0:
            ptr = uc.reg_read(ecx)
            assert self.r(sp + 20) == self.r(sp + 24)
            self.w(ptr + 20, 0, 7)
            self.ret(28, ptr)
        elif address == 0x19191c2:
            dest, src, count = (self.r(sp + i) for i in (4, 8, 12))
            if count:
                uc.mem_write(dest, bytes(uc.mem_read(src, count)))
            self.ret(value=dest)
        elif address == 0x1919184:
            self.ret()
        elif address == 0x1919292:
            raise ValueError('Original equipment parser rejected at ' + hex(self.r(sp))
                             + ', consumed=' + str(self.r(self.stream + 8)))

    def call(self, address, *args):
        esp, ecx, _, eip = self.regs
        self.w(self.stack, self.stop, *args)
        self.emu.reg_write(esp, self.stack)
        self.emu.reg_write(ecx, self.obj)
        try:
            self.emu.emu_start(address, self.stop, count=200000)
        except Exception as exc:
            raise RuntimeError(f'Native execution at {self.emu.reg_read(eip):x}: {exc}') from exc
        assert self.emu.reg_read(eip) == self.stop

    def parse(self, payload):
        self.trace = []
        self.w(self.stream, 0x224c100, self.buf, 0)
        self.w(self.buf - 12, len(payload), len(payload), 1)
        self.emu.mem_write(self.buf, payload)
        self.call(0x107d960, self.stream)
        assert self.r(self.stream + 8) == len(payload), (self.r(self.stream + 8), len(payload))
        return {'bytes_consumed': self.r(self.stream + 8),
                'identified': self.r(self.obj + 0x58), 'color': self.r(self.obj + 0x5c),
                'prefix_quality': self.r(self.obj + 0x68), 'score': self.r(self.obj + 0x60),
                'current': self.r(self.obj + 0xc8), 'maximum': self.r(self.obj + 0xcc),
                'properties': self.properties(0x80), 'trace': self.trace}

    def properties(self, offset):
        result = []
        head = self.r(self.obj + offset + 4)
        def visit(node):
            if node == head:
                return
            visit(self.r(node))
            result.append((self.r(node + 12), self.r(node + 16)))
            visit(self.r(node + 8))
        visit(self.r(head + 4))
        assert len(result) == self.r(self.obj + offset + 8)
        return result


def main():
    native = NativeEquipmentDetail()
    first = native.parse(basic_payload())
    assert first['properties'] == [(120, 37), (140, 21)]
    second = native.parse(basic_payload(properties=((70, 9),), score=364, current=20))
    assert second['properties'] == [(70, 9)]
    assert (second['color'], second['current']) == (3, 20)
    for payload in (basic_payload()[:-1], basic_payload()[:-2]):
        try:
            native.parse(payload)
        except RuntimeError as exc:
            assert 'Original equipment parser rejected' in str(exc)
        else:
            raise AssertionError('Missing required extension flags accepted')
    try:
        native.parse(basic_payload() + b'\0')
    except AssertionError:
        pass
    else:
        raise AssertionError('Extra equipment detail bytes silently counted as consumed')
    result = {'source': 'original constructor107cf80 and parser107d960 through natural return107fd97',
              'examples': [first, second], 'original_containers_executed': True,
              'configuration_adapter': 'prefix cap/item type/score thresholds from original catalogs; make-up zero branch; full original god-weapon ID set',
              'runtime_adapters': 'allocation/free, atomic reference counts, empty UTF16 string assignment, memcpy, cookie',
              'advanced_features_enabled': False, 'native_ui_tested': False}
    write_json(OUT / 'evidence/equipment-detail-full.json', result)
    print('PASS original full ordinary equipment detail parsing and map replacement:',
          first['bytes_consumed'], second['bytes_consumed'])


if __name__ == '__main__':
    main()
