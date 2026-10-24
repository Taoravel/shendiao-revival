"""Bounded original 100107 Finish/pending and movie10019 end feedback.

No real process, service, DB, GUI or battle. UI/resource/connection boundaries
are synthetic; original Finish decisions, dispatch guard and packet construction
execute unchanged. The movie-end case starts with an explicit active fixture,
not a claim that the task has started that movie.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_inspect import DATA, u32
from inspect_client import ROOT, catalog_rows
from pfs import PfsArchive
from bxml import decode
from research_first_master_dialogue_end import MasterProbe
from research_battle import NativeBattleDecoder
from verify_social_native import native_payload
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EBP, UC_X86_REG_ECX

IMAGE_SHA = '2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'


class FinishProbe(MasterProbe):
    def hook(self, emu, address, size, user):
        if address == 0x1129af0:
            self.calls.append({'ui_factory': 'Finish'})
            self.ret(self.ui)  # No args: pushed task pointer belongs to next call.
        elif address == 0x164beb0:
            self.calls.append({'original_finish_entry': True})
        elif address == 0x12c4140:
            self.calls.append({'cg_start_boundary': self.r(emu.reg_read(self.sp_reg) + 4)})
            self.ret(0, 4)
        else:
            super().hook(emu, address, size, user)


def native_finish_100107():
    from unicorn.x86_const import UC_X86_REG_ESP
    p = FinishProbe(100107, 10019)
    p.sp_reg = UC_X86_REG_ESP
    p.w(0x2945600, 0)
    p.w(p.task + 0x168, 10908)
    p.w(p.task + 0x304, 0x5009000, 0x5009000 + 2 * 28)
    p.w(p.stack + 0x14, 100107)
    p.e.reg_write(UC_X86_REG_ESI, p.task)
    p.e.reg_write(UC_X86_REG_EBP, p.manager)
    p.span(0x125c168, 0x164bf53)
    assert p.r(p.ui + 0x64) == 3 and p.r(p.ui + 0x48) == 100107
    assert p.r(p.manager + 0x70) == 0 and not p.messages
    phase3_initial = tuple(p.calls)
    # Finish text rendering is outside the fixture. Resume the real exhausted
    # continuation at index2/2, then separately execute original phase3 cleanup.
    p.w(p.ui + 0x50, 2)
    p.e.reg_write(UC_X86_REG_ESI, p.ui)
    p.span(0x164c3d6, 0x164c584)
    p.e.reg_write(UC_X86_REG_ESI, p.ui + 4)
    p.span(0x1644c1a, 0x1644cf8)
    expected = (0xc4a52, struct.pack('>i', 100107))
    assert p.messages == [expected], p.calls
    assert native_payload(u32(0x227da98), scalars=[(8, 100107)]) == expected[1]
    assert p.r(p.manager + 0x70) == 10019
    assert not any('cg_start_boundary' in call for call in p.calls)
    count = len(p.calls)
    stop = 0x5000100
    p.w(p.stack, stop, 0)
    p.e.reg_write(UC_X86_REG_ECX, p.manager)
    p.span(0x12550c0, stop)
    assert len(p.calls) == count and p.r(p.manager + 0x70) == 10019
    return dict(state1_finish_initial=phase3_initial, final_trace=p.calls,
                messages=[(hex(k), body.hex()) for k, body in p.messages],
                pending_after_finish=10019, pending_after_dispatch_zero=10019,
                automatic_cg_entry_observed=False)


def native_movie_10019_end():
    p = NativeBattleDecoder()
    manager, section, section_vt, net, net_vt, window = [p.allocate(n) for n in (0x200, 0x30, 0x30, 0x30, 0x50, 0x50)]
    p.write(section, section_vt)
    p.write(section_vt + 12, 0x5000500)
    p.u.mem_write(section + 12, b'\x01')
    p.write(manager + 0x38, 10019)
    p.u.mem_write(manager + 0x3c, b'\x01')
    p.write(manager + 0x60, section)
    p.write(net, net_vt)
    p.write(net_vt + 0x3c, 0x5000510)
    for address in (0x294ef88, 0x294f06c, 0x2944564):
        p.write(address, 0)
    sent = []

    def hook(uc, address, _size, _user):
        sp = uc.reg_read(p.sp)
        def ret(value=0, cleanup=0):
            uc.reg_write(p.ax, value)
            uc.reg_write(p.ip, p.read(sp))
            uc.reg_write(p.sp, sp + 4 + cleanup)
        if address == 0x5000500:
            ret(cleanup=4)  # Section rendering/tick; fixture already completed.
        elif address == 0x12bed80:
            ret(cleanup=4)  # Section removal/destruction boundary.
        elif address in (0x12bfdb0, 0x12bee40, 0x4720a0):
            ret()  # Cleanup/UI boundaries, not network or state decision.
        elif address == 0x473b40:
            ret(window, 4)
        elif address == 0x813860:
            ret(net)
        elif address == 0x5000510:
            packet = p.read(sp + 4)
            sent.append((p.read(packet + 4), p.read(packet + 8)))
            ret(cleanup=4)

    p.u.hook_add(UC_HOOK_CODE, hook)
    p.write(p.stack, p.stop, 0)
    p.u.reg_write(p.sp, p.stack)
    p.u.reg_write(p.cx, manager)
    p.u.emu_start(0x12c0b00, 0x12c0a43, count=3000)
    assert p.u.reg_read(p.ip) == 0x12c0a43
    assert sent == [(0xc0018, 10019)], sent
    assert bytes(p.u.mem_read(manager + 0x3c, 1)) == b'\x00'
    body = native_payload(u32(0x226fab8), scalars=[(8, 10019)])
    assert body == struct.pack('>i', 10019)
    return dict(starting_fixture='active movie10019, completed current section, empty queue',
                natural_tick_entry='0x12c0b00', stop_after_send='0x12c0a43',
                packet_type=hex(sent[0][0]), movie_id=sent[0][1], body_hex=body.hex(),
                active_after_send=False)


def native_explicit_start_entry():
    """Counterexample only: explicit original CG message reaches its entry.

    Stops before the entry executes; this neither establishes a server permit
    nor proves the task should send this message or the movie rendered.
    """
    p = NativeBattleDecoder()
    body = struct.pack('>i', 10019)
    p.write(p.stream, 0x224c100, p.buf, 0)
    p.write(p.buf - 12, 4, 4, 1)
    p.u.mem_write(p.buf, body)
    p.call(0xd57540, p.stream)
    assert p.read(p.obj + 8) == 10019 and p.read(p.stream + 8) == 4
    manager = p.allocate(0x200)
    p.write(0x2945620, manager)
    p.write(p.stack, p.stop, 0, 0)
    p.u.reg_write(p.sp, p.stack)
    p.u.reg_write(p.cx, p.obj)
    p.u.emu_start(0x12c43b0, 0x12c4140, count=40)
    assert p.u.reg_read(p.ip) == 0x12c4140
    assert p.u.reg_read(p.cx) == manager
    assert p.read(p.u.reg_read(p.sp) + 4) == 10019
    return dict(decoder='0xd57540', process='0x12c43b0', stopped_at='0x12c4140',
                movie_id=10019, body_hex=body.hex(), task_start_bridge_verified=False)


def main():
    assert hashlib.sha256(DATA).hexdigest() == IMAGE_SHA
    archive = PfsArchive(ROOT / 'artres/config.pfs')
    raw = archive.read('autoconfig/knight.gsp.task.cmainmissioninfo.xml')
    row = next(r for r in catalog_rows(decode(raw)) if r['attributes']['id'] == '100107')
    attrs = row['attributes']
    assert (attrs['MissionType'], attrs['AIInfoAIID'], attrs['ScenarioInfoAnimationID'], attrs['RewardMapJumpType']) == ('40', '8001', '10019', '0')
    assert row['lists']['PostMissionList'] == ['100179']
    assert len(row['lists']['ScenarioInfoFinishConversationList']) == 2
    movie = archive.read('movie/10019.txt')
    effects = archive.read('autoconfig/knight.gsp.task.cquesteffect.xml')
    assert not any(r.get('id') == '10019' for r in decode(effects))
    text = movie.decode('utf-16')
    commands = [(i, line) for i, line in enumerate(text.splitlines(), 1)
                if line.startswith(('Setmap ', 'Start', 'Return ', 'End'))]
    print(json.dumps(dict(image_sha256=IMAGE_SHA, task_sha256=hashlib.sha256(raw).hexdigest(),
                          movie_sha256=hashlib.sha256(movie).hexdigest(), movie_bytes=len(movie),
                          quest_effect_sha256=hashlib.sha256(effects).hexdigest(),
                          movie_control_commands=commands, finish=native_finish_100107(),
                          explicit_start_counterexample=native_explicit_start_entry(),
                          separately_active_movie_end=native_movie_10019_end(),
                          server_playback_permit_verified=False, gui_verified=False),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
