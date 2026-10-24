"""Native held-ground click, actor tick, arrival callback and controller report.

Offline Unicorn only. Never call a movement packet builder from the host.
"""
import hashlib
import json
import struct
from pathlib import Path

from native_inspect import DATA, u32
from native_gameplay_probe import probe
from pfs import PfsArchive
from world_grids import maze_grid
from verify_world_click_move_native import ClickMoveProbe
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EIP, UC_X86_REG_ESP


class ClickArrivalProbe(ClickMoveProbe):
    def __init__(self, *args, **kwargs):
        self.messages, self.arrival_trace, self.recent = [], [], []
        self.active_message = None
        super().__init__(*args, **kwargs)
        # Original constructor 12198d2/12198dc/1219944 defaults, before input.
        self.w(self.role + 0x338, 500, 2000)
        self.w(self.role + 0x374, 15000)
        self.integrated_events = self.dynamic_current = True
        self.w(self.path, self.actor)
        self.w(0x29a4a70 + 0x28, 0x2945060)
        for a in (0x29455e8, 0x2945628):
            self.w(a, 0)
        self.uc.mem_write(0x294524d, b'\0')

    def hook(self, emu, addr, size, user):
        self.recent.append(hex(addr))
        self.recent[:] = self.recent[-80:]
        if addr < 0x400000:
            raise AssertionError(('unmapped virtual call', hex(addr), hex(emu.reg_read(UC_X86_REG_ESP))))
        if addr in (0x655c80, 0x655500, 0x6bc7a0, 0x81c670, 0x11d57f0,
                    0x1217580, 0x120c350, 0x12179a0, 0x120c830, 0x12171d0,
                    0x1217f00, 0xe9cd00, 0xe9d6d0, 0x1214110, 0x621f40,
                    0x11f8930, 0x1204990, 0x1218000):
            self.arrival_trace.append(hex(addr))
        sp = emu.reg_read(UC_X86_REG_ESP)
        if addr == 0x120c350:
            return  # Execute real base callback, bypass old report fixture seam.
        if addr == 0x1172740:
            assert self.read(sp + 4) == 0
            self.ret(4)  # Absent render backend: delete null effect handle only.
            return
        if addr == self.stop + 0x100:
            packet = self.read(sp + 4)
            kind = self.read(packet + 4)
            assert kind in (0xc0fa1, 0xc0fa3, 0xc0faa), hex(kind)
            message = {'kind': kind, 'sender_return': hex(self.read(sp))}
            if kind == 0xc0fa1:
                raw = bytes(emu.mem_read(packet, 32))
                message.update(start=struct.unpack_from('<hh', raw, 12),
                    end=struct.unpack_from('<hh', raw, 20), scene_u64=struct.unpack_from('<Q', raw, 24)[0])
                self.role_moves.append(message)
            else:
                message.update(history=self.points(packet + (16 if kind == 0xc0fa3 else 8)),
                    current=struct.unpack('<hh', emu.mem_read(packet + (12 if kind == 0xc0fa3 else 24), 4)),
                    scene_u64=struct.unpack('<Q', emu.mem_read(packet + 32, 8))[0])
            self.messages.append(message)
            self.active_message = message
            self.w(self.stream, 0x224c100, self.stream_buffer, 0)
            self.w(self.stream_buffer - 12, 4096, 0, 1)
            marshal = {0xc0fa1: 0xe50840, 0xc0fa3: 0xe9cd00, 0xc0faa: 0xe9d6d0}[kind]
            # Sender ABI adapter: marshal the LIVE native-built packet before
            # its caller destroys STL nodes; then return success to native caller.
            code = (b'\x53\x56\x57\x8b\x4c\x24\x10\x68' + struct.pack('<I', self.stream)
                    + b'\xb8' + struct.pack('<I', marshal) + b'\xff\xd0'
                    + b'\x5f\x5e\x5b\xb8\x01\x00\x00\x00\xc2\x04\x00')
            stub = self.stop + {0xc0fa1:0x900, 0xc0fa3:0xa00, 0xc0faa:0xb00}[kind]
            emu.mem_write(stub, code)
            emu.reg_write(UC_X86_REG_EIP, stub)
            return
        if addr in (self.stop + 0x913, self.stop + 0xa13, self.stop + 0xb13):
            self.active_message['body_hex'] = bytes(emu.mem_read(self.stream_buffer,
                self.read(self.stream_buffer - 8))).hex()
            self.active_message = None
            return
        super().hook(emu, addr, size, user)

    def snapshot(self):
        self.call(0x12061a0, (self.packet + 0x100,))
        return {'current': struct.unpack('<ii', self.uc.mem_read(self.packet + 0x100, 8)),
            'actor_projected': struct.unpack('<ff', self.uc.mem_read(self.path + 8, 8)),
            'future_engine': self.points(self.path + 0x2c, floats=True),
            'future_character': self.points(self.role + 0x340, floats=True),
            'history_character': self.points(self.role + 0x34c),
            'check_countdown': self.read(self.role + 0x338), 'messages': len(self.messages)}

    def actor_tick(self, now, delta):
        self.uc.reg_write(UC_X86_REG_EAX, self.actor)
        self.uc.reg_write(UC_X86_REG_EBX, now)
        self.call(0x655c80, (delta,))
        return self.snapshot()


def main():
    root = Path(__file__).resolve().parent
    archive = PfsArchive(root / 'runtime/client/artres/map.pfs')
    mn, rn = 'map_1100_gumupai/maze.dat', 'map_1100_gumupai/map.rmp'
    maze, rmp = archive.read(mn), archive.read(rn)
    grid = maze_grid(maze)
    run = ClickArrivalProbe(grid.width, grid.height, grid.cells, (1488,1152),
        render_size=struct.unpack_from('<II', rmp, 8))
    run.w(run.scene + 0x30, 1100, 0)
    try:
        run.uc.mem_write(0x2945438, b'\1')
        run.w(run.scene + 0x39c, 0x12345678)
        locked = run.input_tick()
        assert locked['sent_count'] == locked['mouse_reads'] == 0
        run.call(0x12b9a10, ecx=run.packet)
        initial = run.input_tick()
        # Original setter. 1.0 is a deterministic multiplier; do not infer the
        # original server's speed formula, clock units or real elapsed time.
        run.call(0x6529b0, (0x3f800000,), ecx=run.actor)
        at_endpoint = run.actor_tick(1016, 16)
        consumed = run.actor_tick(1017, 1)
    except Exception:
        print(json.dumps({'recent': run.recent, 'trace': run.arrival_trace, 'messages': run.messages,
            'engine_events': run.engine_events, 'events': run.events}, indent=2))
        raise
    assert initial['original_current'] == (1488,1152)
    assert initial['history_character'] == [(1488,1152)]
    assert initial['future_engine'] == initial['future_character'] == [(1504.,1152.)]
    assert at_endpoint['current'] == (1504,1152)
    assert at_endpoint['future_engine'] == [(1504.,1152.)]
    assert at_endpoint['messages'] == 1  # Equality does not consume or send STOP.
    assert consumed['current'] == (1504,1152)
    assert consumed['future_engine'] == consumed['future_character'] == []
    assert consumed['history_character'] == []  # Native STOP drains history.
    assert [m['kind'] for m in run.messages] == [0xc0fa1,0xc0faa]
    stop = run.messages[-1]
    assert stop['history'] == [(1488,1152)] and stop['current'] == (1504,1152)
    assert stop['scene_u64'] == 1100 and stop['sender_return'] == '0x1217fce'
    stop_body = bytes.fromhex(stop['body_hex'])
    assert stop_body.hex() == '0105d0048005e00480000000000000044c'
    decoded_history = []
    def observe_stop(emu, target):
        read = lambda a: struct.unpack('<I',emu.mem_read(a,4))[0]
        head = read(target + 12)
        node = read(head)
        while node != head:
            assert len(decoded_history) < 16
            decoded_history.append(struct.unpack('<hh',emu.mem_read(node + 12,4)))
            node = read(node)
        assert len(decoded_history) == read(target + 16)
    _, decoded = probe(0xe9d5e0,0xe9d6d0,0xe9d780,payload=stop_body,observer=observe_stop)
    assert decoded_history == stop['history']
    assert struct.unpack_from('<hh',decoded,24) == (1504,1152)
    assert struct.unpack_from('<Q',decoded,32)[0] == 1100
    assert [e['event'] for e in run.engine_events] == [0,1]
    required = {hex(a) for a in (0x655c80,0x655500,0x6bc7a0,0x81c670,0x11d57f0,
        0x1217580,0x120c350,0x11f8930,0x1218000,0x1217f00,0xe9d6d0)}
    assert required <= set(run.arrival_trace)
    result = {'all_passed':True, 'image_sha256':hashlib.sha256(DATA).hexdigest(),
        'map_id':1100,'source':[1488,1152],'destination':[1504,1152],
        'locked':locked, 'initial':initial,'at_endpoint':at_endpoint,'consumed':consumed,
        'original_stop_body_hex':stop_body.hex(),'stop_message_type':0xc0faa,
        'original_move_body_hex':run.messages[0]['body_hex'],'move_message_type':0xc0fa1,
        'stop_native_decoder_verified':True,'native_decoded_stop_history':decoded_history,
        'original_sender_messages':run.messages,
        'actor_tick_fixture':{'speed_setter':hex(0x6529b0),'multiplier':1.0,
            'ticks':[{'clock_argument':1016,'budget_argument':16},{'clock_argument':1017,'budget_argument':1}],
            'units':'deterministic native tick inputs; no real-time or original server speed claim'},
        'trace':run.arrival_trace,'engine_events':run.engine_events,'events':run.events,
        'native_DDA_samples':run.dda_trace,
        'sources':[{'entry':n,'sha256':hashlib.sha256(raw).hexdigest(),'CRC_checked':True}
            for n,raw in ((mn,maze),(rn,rmp))],
        'scope':'same object native click -> actor update -> full arrival callback -> native STOP builder/marshal; not full App frame or OS input',
        'unverified':['original server speed/time units','full MainCharacter timed-update CHECK chain','GUI and production transport']}
    out = root / 'evidence/world-click-arrival-native.json'
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'all_passed':True,'original_stop_body_hex':stop_body.hex(),
        'messages':len(run.messages),'result':str(out)}))


if __name__ == '__main__':
    main()
