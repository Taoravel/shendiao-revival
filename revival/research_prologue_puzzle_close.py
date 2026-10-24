"""Execute the original quest-puzzle close branch in isolated native memory.

Phase values are controlled fixtures, not evidence of solving a puzzle. This
probe captures original packet construction; it cannot authorize task rewards.
"""
import hashlib
import json
import struct
import zlib
from bxml import decode
from inspect_client import OUT,ROOT,write_json
from native_inspect import DATA
from pfs import PfsArchive
from research_battle import NativeBattleDecoder


def native_puzzle_close(task_id,phase):
    from unicorn import UC_HOOK_CODE
    probe=NativeBattleDecoder()
    dialog=probe.obj;network=0x5007000;net_vtable=0x5008000;ui_vtable=0x5009000
    network_send=0x500a000;ui_close=0x500b000
    probe.write(dialog+4,ui_vtable);probe.write(ui_vtable+4,ui_close)
    probe.write(dialog+0x38,phase);probe.write(dialog+0x80,task_id)
    probe.write(network,net_vtable);probe.write(net_vtable+0x3c,network_send)
    messages=[];closed=[]

    def ret(cleanup=0,value=0):
        sp=probe.u.reg_read(probe.sp)
        probe.u.reg_write(probe.ax,value)
        probe.u.reg_write(probe.ip,probe.read(sp))
        probe.u.reg_write(probe.sp,sp+4+cleanup)

    def hook(emu,address,size,user):
        sp=emu.reg_read(probe.sp)
        if address==0x813860:
            ret(value=network)  # Network singleton only, no protocol logic.
        elif address==network_send:
            packet=probe.read(sp+4)
            kind=probe.read(packet+4)
            if kind!=0xc4a44:raise AssertionError('Unexpected original puzzle packet')
            quest=probe.read(packet+8)
            key=probe.read(packet+0x10)|(probe.read(packet+0x14)<<32)
            option=probe.read(packet+0x18)
            messages.append((kind,struct.pack('>iQi',quest,key,option)))
            ret(4)
        elif address==ui_close:
            closed.append(probe.read(dialog+0x80))
            ret()  # Rendering-only close callback, after original ID reset.

    probe.u.hook_add(UC_HOOK_CODE,hook)
    probe.call(0x1711af0,0)
    assert closed==[0],closed
    assert probe.read(dialog+0x80)==0
    return tuple(messages)


def main():
    raw=PfsArchive(ROOT/'artres/config.pfs').read('autoconfig/knight.gsp.task.cmainmissioninfo.xml')
    records={int(r.get('id')):r for r in decode(raw)}
    scope=json.loads((OUT/'evidence/prologue-restore-scope.json').read_text(encoding='utf-8'))
    candidates={q for route in scope['routes'] for q in route['path']
        if records[q].get('MissionType')=='59'
        and '画卷' in records[q].get('TaskInfoPurposeListA','')}
    assert len(candidates)==10,candidates
    rows=[]
    for task_id in sorted(candidates):
        for phase in (0,1,2,3):
            actual=native_puzzle_close(task_id,phase)
            expected=((0xc4a44,struct.pack('>iQi',task_id,0,0)),) if phase==3 else ()
            assert actual==expected,(task_id,phase,actual)
            rows.append(dict(task_id=task_id,fixture_phase=phase,
                messages=[dict(type=hex(kind),body_hex=body.hex()) for kind,body in actual]))
    report=dict(task_ids=sorted(candidates),cases=rows,
        source_bytes=len(raw),source_crc32=f'{zlib.crc32(raw)&0xffffffff:08x}',
        source_sha256=hashlib.sha256(raw).hexdigest(),image_sha256=hashlib.sha256(DATA).hexdigest(),
        routine='0x1711af0',packet_construction='0x1711b1f..0x1711b64',
        conclusion='Fixture phase3 closes with original CCommit(taskID,npcKey0,option0); other phases send none',
        authority='Native packet construction only; phase3 fixture is not a solved-board proof',
        method='research: original PFS and native code, external network/render callbacks only',
        limits=['Task UI launch and natural solution-to-phase3 transition are not covered',
            'Captured fields use the already verified CCommit wire layout; original marshaller is not re-executed',
            'No task activation, gameplay implementation, reward, live server, client or battle was executed'])
    write_json(OUT/'evidence/prologue-puzzle-native-close.json',report)
    print(dict(tasks=len(candidates),original_close_cases=len(rows),
        sent_when_phase3='CCommit(taskID,0,0)',runtime_implemented=False))


if __name__=='__main__':main()
