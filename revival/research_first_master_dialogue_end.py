"""Original first-master Start completion, offline; never run a client/server.

Display resources and network/UI effects are captured. Original Start count,
phase2 dispatch, type10 submit, phase3 guard and post-effect branch are retained.
"""
import json
import struct

from bxml import decode
from inspect_client import ROOT
from pfs import PfsArchive
from research_task_jiaxing_scenario import Probe
from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EDI


class MasterProbe(Probe):
    def __init__(self,quest_id,effect_id):
        super().__init__(quest_id)
        self.e.mem_map(0,0x1000)  # Isolated x86 FS:[0] exception-chain fixture.
        self.effect_id=effect_id
        self.messages=[]
        self.w(self.task+0x2ac,effect_id)
        self.w(self.task+0x164,10)
        self.w(self.ui+4,0x500b000)
        self.w(0x500b004,0x5000500)

    def hook(self,emu,addr,size,user):
        from unicorn.x86_const import UC_X86_REG_ESP
        sp=emu.reg_read(UC_X86_REG_ESP)
        if addr==0x1919184:
            self.ret()  # Compiler cookie check, no gameplay branch.
        elif addr==0x5000500:
            self.calls.append({'ui_close_phase':self.r(self.ui+0x64)})
            self.ret()
        elif addr==0x11ca790:
            effect=self.r(self.r(sp+4))
            self.calls.append({'scene_effect_boundary':effect})
            self.ret(0,4)
        elif addr==0x5000400:
            packet=self.r(sp+4);kind=self.r(packet+4)
            if kind==0xc4a44:
                quest=self.r(packet+8)
                key=self.r(packet+0x10)|(self.r(packet+0x14)<<32)
                option=self.r(packet+0x18)
                body=struct.pack('>iQi',quest,key,option)
                self.calls.append({'sent_type':hex(kind),'quest_id':quest,'npc_key':key,'option':option})
            elif kind==0xc4a52:
                quest=self.r(packet+8);body=struct.pack('>i',quest)
                self.calls.append({'sent_type':hex(kind),'quest_id':quest})
            else:raise AssertionError(f'Unexpected native output {kind:x}')
            self.messages.append((kind,body));self.ret(0,4)
        else:
            super().hook(emu,addr,size,user)


def native_start_completion(task_id=100186,npc_key=(1100<<32)|44):
    """Return (actual native messages, trace, last_phase) for final Start click.

    First probe the original last-line count branch (index2 of3) up to renderer,
    then execute its real post-display index increment. Rendering itself is not
    emulated. On the next continue event, run the complete original exhausted
    Start function and original type10 submit via the phase2 dispatch.
    """
    archive=PfsArchive(ROOT/'artres/config.pfs')
    raw=archive.read('autoconfig/knight.gsp.task.cmainmissioninfo.xml')
    row=next(r for r in decode(raw) if r.get('id')==str(task_id))
    lines=row.find('ScenarioInfoNpcConversationList')
    assert row.get('MissionType')=='10' and row.get('ProcessBarTime')=='0'
    assert lines is not None and len(lines)==3
    assert row.find('ScenarioInfoFinishConversationList') is None
    assert not row.get('ScenarioInfoBranchNote')
    effect=int(row.get('ScenarioInfoAnimationID'))
    p=MasterProbe(task_id,effect)
    p.w(p.task+0x2e4,0x5009000,0x5009000+3*0x1c)
    p.w(p.ui+0x48,task_id);p.w(p.ui+0x38,npc_key&0xffffffff,npc_key>>32)
    p.w(p.ui+0x64,2);p.w(p.ui+0x50,2)
    # Original remaining-line decision: final line still enters display.
    p.e.reg_write(UC_X86_REG_EDI,p.ui)
    from unicorn.x86_const import UC_X86_REG_EBX
    p.e.reg_write(UC_X86_REG_EBX,p.task)
    p.span(0x164b581,0x164baad)
    assert p.r(p.ui+0x50)==2 and not p.messages
    p.e.reg_write(UC_X86_REG_EDI,p.ui)
    p.span(0x164be0f,0x164be13)
    assert p.r(p.ui+0x50)==3
    p.calls.append({'last_line_display_boundary':2,'original_next_index':3})
    # Real phase2 continue -> exhausted Start -> real submit -> UI close.
    p.e.reg_write(UC_X86_REG_ESI,p.ui)
    p.span(0x164c3d6,0x164c584)
    phase=p.r(p.ui+0x64)
    expected=(0xc4a44,struct.pack('>iQi',task_id,npc_key,0))
    assert p.messages==[expected],p.calls
    assert phase==2
    # Same UI close guard uses this+4, therefore +60==main UI+64.
    p.e.reg_write(UC_X86_REG_ESI,p.ui+4)
    before=len(p.messages)
    p.span(0x1644c1a,0x1644cf8)
    assert len(p.messages)==before and not any('scene_effect_boundary' in c for c in p.calls)
    p.calls.append({'start_phase2_cleanup_sent_dialog_end':False})
    return tuple(p.messages),tuple(p.calls),phase


def native_synthetic_finish_cleanup(task_id=100186,effect_id=20006):
    """Counterexample only: phase3 can emit DialogEnd, but Start never set it."""
    p=MasterProbe(task_id,effect_id)
    p.w(p.ui+0x48,task_id,0)
    p.w(p.ui+0x64,3)
    p.e.reg_write(UC_X86_REG_ESI,p.ui+4)
    p.span(0x1644c1a,0x1644cf8)
    assert p.messages==[(0xc4a52,struct.pack('>i',task_id))]
    assert {'scene_effect_boundary':effect_id} in p.calls
    return tuple(p.messages),tuple(p.calls)


def main():
    messages,trace,phase=native_start_completion()
    finish,finish_trace=native_synthetic_finish_cleanup()
    print(json.dumps(dict(start_messages=[(hex(k),b.hex()) for k,b in messages],
        start_trace=trace,last_phase=phase,
        synthetic_finish_messages=[(hex(k),b.hex()) for k,b in finish],
        synthetic_finish_trace=finish_trace,
        scope='Original local branch/submit/guard; rendering and network captured, not GUI play'),indent=2))


if __name__=='__main__':main()
