"""Read-only render diagnosis: visual replay verdict, original code, live state."""
import argparse
import json
from pathlib import Path
from contextlib import redirect_stdout

OUT = Path(__file__).parent / 'evidence'


def visual(path):
    from PIL import Image
    image = Image.open(path).convert('RGB')
    w, h = image.size
    # Interior of the world viewport, excluding HUD and title bar.
    pixels = list(image.crop((int(w*.25), int(h*.25), int(w*.7), int(h*.65))).get_flattened_data())
    black = sum(max(p) < 6 for p in pixels) / len(pixels)
    return {'image': str(path), 'size': [w,h], 'viewport_black_ratio': black,
            'verdict': 'BLACK_WORLD' if black > .98 else 'WORLD_HAS_PIXELS',
            'limit': 'replay viewport symptom; not NPC or loading-complete acceptance'}


def snapshot(pid, sample_count=3, expected_identity=None):
    from black_scene_probe import ProcessReader
    import time
    import struct
    r = ProcessReader(pid)
    try:
        identity=process_identity(pid, reader=r)
        if expected_identity is not None and identity!=expected_identity:
            raise ValueError('Process creation identity changed; no game-memory read performed')
        scene = r.u32(0x2944564)
        world = r.u32(0x29a4a70 + 0x40)
        if not scene or not world:
            return {'pid': pid, 'captured_unix': time.time(), 'status': 'uninitialized',
                    'scene': hex(scene), 'world': hex(world), 'access': 'VM_READ only'}
        def words(ptr, offsets):
            return {hex(off): r.u32(ptr+off) for off in offsets}
        result = {'pid': pid, 'captured_unix': time.time(), 'access': 'VM_READ only',
                  'scene': hex(scene), 'world': hex(world),
                  'scene_words': words(scene, (4, 0xc, 0x14, 0x1c8, 0x288, 0x28c,
                      0x330, 0x338, 0x340, 0x364, 0x378, 0x380, 0x3a0, 0x3dc)),
                  'scene_bytes': {hex(o): r.read(scene+o,1)[0] for o in
                                  (0x58, 0x32c, 0x334, 0x335, 0x33c, 0x344, 0x36c)},
                  'world_words': words(world, (8, 0x1e8, 0x24c, 0x270, 0x278, 0x298,
                      0x27c, 0x29c, 0x2a0, 0x488, 0x48c, 0x490, 0x494, 0x4a8, 0x540,
                      0x65c, 0x660, 0x67c, 0x688, 0x694, 0x6a0, 0x6ac)),
                  'world_bytes': {hex(o): r.read(world+o,1)[0] for o in
                                  (0x24c, 0x24d, 0x24e, 0x66c, 0x66d, 0x66e, 0x66f)},
                  'camera_words': words(world+0x2a0, (0, 0x1c8, 0x1dc,
                      0x1cc, 0x1e8, 0x1ec, 0x1f0, 0x1f4, 0x200, 0x204, 0x208))}
        map_ptr = result['world_words']['0x298']
        if map_ptr:
            result['map_words'] = words(map_ptr, (0, 0xc, 0x10, 0xe4))
            result['map_time_parameters']={'head':hex(r.u32(map_ptr+0xd0)),
                                           'count':r.u32(map_ptr+0xd4)}
            begin, end = r.u32(map_ptr+0x9c), r.u32(map_ptr+0xa0)
            result['map_block_vector'] = {'begin': hex(begin), 'end': hex(end),
                                          'count': (end-begin)//4}
            result['map_background_layers'] = render_vector(r, map_ptr+0x68, 0x38,
                                                            sample_limit=4)
        # Original normal path submits seven 0x24-byte quad lists and two
        # 0x28-byte lists. These counts distinguish a populated camera rect from
        # actual queued geometry; they do not establish a GPU submission.
        result['world_quad_batches'] = [
            dict(group=i, **render_vector(r, world+0x2a4+i*0x10, 0x24))
            for i in range(7)] + [
            dict(group=7+i, **render_vector(r, world+0x384+i*0x10, 0x28))
            for i in range(2)]
        vt = result['camera_words']['0x0']
        result['camera_methods'] = words(vt, (0,4,8,12,16))
        target = result['camera_words']['0x1cc']
        if target:
            method = r.u32(r.u32(target)+0x38)
            result['camera_target'] = {'ptr': hex(target), 'position_method': hex(method)}
            if method == 0x6528d0:
                pose = r.u32(target+0x1a8)
                result['camera_target']['render_xy'] = struct.unpack('<ff', r.read(pose+8,8))
        result['world_ticks'] = []
        engine = 0x29a4a70
        device = r.u32(engine+0x44)
        result['draw_gates'] = {'engine_mode_9c': r.u32(engine+0x9c),
                                'device': hex(device),
                                'device_check_required_1bd': r.read(device+0x1bd,1)[0],
                                'device_check_method_154': hex(r.u32(r.u32(device)+0x154)),
                                'render_aux_a4': hex(r.u32(engine+0xa4))}
        config=r.u32(engine+0x48)
        if config:
            result['world_render_config']={'ptr':hex(config),
                'mode_48':r.u32(config+0x48),
                'composite_alpha_18':struct.unpack('<f',r.read(config+0x18,4))[0],
                'alternate_background_path_3b':r.read(config+0x3b,1)[0]}
        # Device pixel shader selector is used by renderer+0x118/+0x11c.
        # Read availability only, never compile or change the active program.
        backend=r.u32(0x29235d4)
        result['world_pixel_shaders']={'backend_index':backend,
                                     'selected':r.u32(device+0x188),
                                     'applied':r.u32(device+0x18c),'slots':[]}
        if backend<8:
            for i in range(5):
                program=r.u32(device+0x174+i*4)
                info={'slot':i,'program':hex(program)}
                if program:
                    info.update(available=r.read(program+4+backend,1)[0],
                                native_shader=hex(r.u32(program+0xc+backend*4)),
                                parameter_setter=hex(r.u32(r.u32(program)+0x10)))
                    if info['parameter_setter'] in ('0x7117b0','0x7117d0'):
                        info['parameters_8float']=struct.unpack('<8f',r.read(program+0x4c,32))
                result['world_pixel_shaders']['slots'].append(info)
        for i in range(sample_count):
            result['world_ticks'].append({'counter_29b7810': struct.unpack('<Q', r.read(0x29b7810,8))[0],
                                          'world_time_27c': r.u32(world+0x27c),
                                          'engine_tick_e0': r.u32(engine+0xe0),
                                          'update_stamp_29b8e48': r.u32(0x29b8e48),
                                          'draw_stamp_29b8e58': r.u32(0x29b8e58)})
            if i < sample_count-1: time.sleep(.3)
        return result
    finally: r.close()


def render_vector(reader, address, stride, sample_limit=2):
    """Bounded raw vector observation; reject malformed headers before reads."""
    import struct
    begin,end,capacity=(reader.u32(address+x) for x in (4,8,12))
    info={'header':hex(address),'begin':hex(begin),'end':hex(end),
          'capacity_end':hex(capacity),'entry_size':stride}
    if not (begin <= end <= capacity and (end-begin)%stride == 0
            and (capacity-begin)%stride == 0 and capacity-begin <= 16*1024*1024
            and (begin != 0 or capacity == 0)):
        info['status']='invalid_or_changed_vector_header'
        return info
    count=(end-begin)//stride
    info.update(count=count,status='bounded_raw_sample',samples=[])
    for i in range(min(count,sample_limit)):
        raw=reader.read(begin+i*stride,stride)
        info['samples'].append({'index':i,'raw_u32':list(struct.unpack(
            '<'+'I'*(stride//4),raw))})
    return info


def process_identity(pid, reader=None):
    """Query executable and creation time before any game-memory read."""
    from black_scene_probe import ProcessReader
    import ctypes as C
    from ctypes import wintypes as W
    r = reader if reader is not None else ProcessReader(pid)
    try:
        r.kernel.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)]
        r.kernel.QueryFullProcessImageNameW.restype = W.BOOL
        buffer=C.create_unicode_buffer(32768);size=W.DWORD(len(buffer))
        if not r.kernel.QueryFullProcessImageNameW(r.handle,0,buffer,C.byref(size)):
            raise C.WinError(C.get_last_error())
        if Path(buffer.value).name.lower() != 'knightclient.exe':
            raise ValueError('Specified PID is not knightclient.exe; no game-memory read performed')
        r.kernel.GetProcessTimes.argtypes=[W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME)]
        created, exited, kernel, user = (W.FILETIME() for _ in range(4))
        if not r.kernel.GetProcessTimes(r.handle,C.byref(created),C.byref(exited),C.byref(kernel),C.byref(user)):
            raise C.WinError(C.get_last_error())
        return {'executable': buffer.value, 'created_filetime': (created.dwHighDateTime<<32)|created.dwLowDateTime}
    finally:
        if reader is None:r.close()


def watch(pid, seconds, interval):
    """Bounded observation of this PID/creation only; never select another game."""
    import time
    from datetime import datetime, timezone
    if not 0 < seconds <= 600 or not .1 <= interval <= 10:
        raise ValueError('watch-seconds must be (0,600], interval [0.1,10]')
    target=OUT/f'black-world-render-watch-{pid}-{time.time_ns()}.jsonl'
    start=time.monotonic(); identity=None; count=0
    with target.open('x',encoding='utf-8') as f:
        while time.monotonic()-start < seconds:
            tick=time.monotonic()
            event={'pid':pid,'captured_utc':datetime.now(timezone.utc).isoformat(),
                   'elapsed_seconds':round(tick-start,3)}
            try:
                current=process_identity(pid)
                if identity is not None and current!=identity:
                    event.update(status='pid_reused',error='creation identity changed; observation stopped')
                else:
                    identity=current
                    event.update(status='ok',identity=identity,snapshot=snapshot(pid,sample_count=1,expected_identity=identity))
                    if event['snapshot'].get('status')=='uninitialized':event['status']='uninitialized'
            except ValueError as error:
                event.update(status='wrong_process',error=str(error))
            except OSError as error:
                # If identity is still accessible, distinguish unreadable game globals
                # from a process that has exited / become inaccessible.
                try:
                    still=process_identity(pid)
                    status='read_unavailable' if identity is None or still==identity else 'pid_reused'
                except (OSError,ValueError):status='exited_or_inaccessible'
                event.update(status=status,error=str(error))
            f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();count+=1
            if event['status'] in ('pid_reused','wrong_process','exited_or_inaccessible'):break
            delay=min(interval-(time.monotonic()-tick),seconds-(time.monotonic()-start))
            if delay>0:time.sleep(delay)
    print(json.dumps({'pid':pid,'samples':count,'jsonl':str(target),'last_status':event['status']}))
    return target


def evidence():
    from native_inspect import disasm, DATA, BASE, u32
    spans = {'world-update-map-gate': (0x5fd420, 160),
             'engine-final-draw-gates': (0x5a8f42, 104),
             'engine-world-draw-caller': (0x5a9e40, 230),
             'world-real-draw-entry': (0x606860, 365),
             'device-cooperative-state': (0x6d3c70, 97),
             'window-activation-size-state': (0x5a9023, 395),
             'world-map-dimensions': (0x5fcd00, 48),
             'world-camera-getter': (0x5f9920, 32),
             'world-camera-zoom': (0x607dc0, 96),
             'world-camera-target': (0x5fdb00, 193),
             'world-camera-position': (0x603480, 140),
             'camera-follow-position': (0x6528d0, 28),
             'camera-follow-and-clamp': (0x687800, 376),
             'world-time-state-24c': (0x5fe1c0, 208),
             'world-time-state-change-effect': (0x5fdfe0, 440),
             'effect-daytime-randomization': (0x692330, 290),
             'per-draw-parameter-calculator': (0x604b80, 1400),
             'per-draw-parameter-submit': (0x60500d, 249),
             'SGameTime-initialization': (0x81b3e0, 473),
             'pixel-shader-selector-readiness': (0x6e29c0, 133),
             'pixel-shader-parameter-apply': (0x6d3a00, 78),
             'pixel-shader-capability-ps3': (0x711770, 38),
             'pixel-shader-zero-not-default': (0x711c50, 119),
             'pixel-shader-copy-all-eight-parameters': (0x7117b0, 20),
             'world-loop-entry-66c': (0x600d50, 160),
             'world-loop-counter': (0x5fe290, 96),
             'load-completion-66d': (0x5fcb2d, 200),
             'camera-zoom-viewport': (0x6876d0, 288),
             'scene-overlay-render': (0x11c5e20, 280),
             'scene-movieblack-string-adjacent': (0x11c5f70, 18)}
    with (OUT/'black-world-render-native.txt').open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            for label, (addr,size) in spans.items():
                print('\n', label);disasm(addr,size)
    def string_at(addr):
        at=addr-BASE
        return DATA[at:DATA.index(b'\0',at)].decode('ascii')
    header,body=string_at(0x246e970),string_at(0x246e2b8)
    snippets=[string_at(u32(0x2923588+i*4)) for i in range(8)]
    (OUT/'world-colour-native.hlsl').write_text(header+snippets[0]+body,encoding='utf-8')
    (OUT/'world-colour-shader-sources.json').write_text(json.dumps({
        'header_address':hex(0x246e970),'body_address':hex(0x246e2b8),
        'backend_source_table':hex(0x2923588),'header':header,'body':body,
        'backend_snippets':snippets},indent=2),encoding='utf-8')


def replay_gates():
    """Counterfactual replay of ORIGINAL final-draw branch, entirely offline."""
    from native_inspect import DATA, BASE
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EDI, UC_X86_REG_EBX, UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP
    import struct
    results = []
    for mode, device_state, timer, expected in ((0,4,1,'draw'), (1,4,1,'draw'),
            (2,4,1,'skip'), (0,2,1,'skip'), (0,4,0,'skip')):
        emu=Uc(UC_ARCH_X86, UC_MODE_32)
        emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
        emu.mem_map(0x5000000,0x100000)
        engine, device, vt, cvt, stack = 0x5001000,0x5002000,0x5003000,0x5004000,0x5080000
        def w(a,v): emu.mem_write(a,struct.pack('<I',v))
        w(engine+0x9c,mode);w(engine+0x44,device);w(device,vt)
        w(vt+0x154,0x500f200);w(engine+4,cvt);w(cvt+0x44,0x500f100)
        verdict=[]
        def hook(uc,address,size,user):
            if address==0x500f200:
                sp=uc.reg_read(UC_X86_REG_ESP)
                dest=struct.unpack('<I',uc.mem_read(sp,4))[0]
                uc.reg_write(UC_X86_REG_ESP,sp+4)
                uc.reg_write(UC_X86_REG_EAX,device_state)
                uc.reg_write(UC_X86_REG_EIP,dest)
            elif address in (0x500f100,0x5a89f0):
                verdict.append('draw' if address==0x500f100 else 'skip');uc.emu_stop()
        emu.hook_add(UC_HOOK_CODE,hook)
        emu.reg_write(UC_X86_REG_EDI,engine);emu.reg_write(UC_X86_REG_EBX,timer)
        emu.reg_write(UC_X86_REG_ESP,stack)
        emu.emu_start(0x5a8f75,0x5a8faa,count=200)
        assert verdict==[expected],(mode,device_state,timer,verdict)
        results.append({'engine_mode':mode,'device_result':device_state,'timer_ready':timer,
                        'native_branch':verdict[0]})
    (OUT/'black-world-draw-gate-replay.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--image', type=Path)
    p.add_argument('--pid', type=int)
    p.add_argument('--disasm', action='store_true')
    p.add_argument('--replay-gates', action='store_true')
    p.add_argument('--watch-seconds', type=float)
    p.add_argument('--interval', type=float, default=1)
    args = p.parse_args()
    if args.image:
        result = visual(args.image)
        print(json.dumps(result))
        raise SystemExit(2 if result['verdict'] == 'BLACK_WORLD' else 0)
    if args.watch_seconds is not None:
        if not args.pid:p.error('--watch-seconds requires explicit --pid')
        watch(args.pid,args.watch_seconds,args.interval)
    elif args.pid:
        result = snapshot(args.pid)
        (OUT/f'black-world-render-{args.pid}.json').write_text(
            json.dumps(result,indent=2), encoding='utf-8')
        print(json.dumps(result,indent=2))
    if args.disasm: evidence()
    if args.replay_gates: replay_gates()


if __name__ == '__main__': main()
