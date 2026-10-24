"""Offline original existing-ScenarioQuest receive/classification regression.

Only external lookups and UI notifications are adapted. Original accept,
refresh dispatch, scenario state assignment and classifier execute unmodified.
Never access a client process, service or persistent database.
"""
import json
import struct

from native_inspect import BASE, DATA
from task_protocol import (S_ACCEPT_SCENARIO_QUEST,S_REFRESH_SCENARIO_QUEST_STATE,
    ScenarioQuestInfo,decode_accept_scenario_quest,decode_scenario_state,
    encode_accept_scenario_quest,encode_scenario_state)
from wire import read_compact


class ExistingQuestProbe:
    def __init__(self,task_id,initial_state=0,quest_type=10):
        from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
        from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_ESP,
                                      UC_X86_REG_EIP,UC_X86_REG_ECX)
        self.u=Uc(UC_ARCH_X86,UC_MODE_32)
        self.u.mem_map(BASE,(len(DATA)+4095)&~4095);self.u.mem_write(BASE,DATA)
        self.u.mem_map(0x5000000,0x20000)
        self.task_id=task_id
        self.bean,self.packet,self.manager,self.config=0x5002000,0x5003000,0x5004000,0x5005000
        self.lookup,self.stop,self.sp=0x5000600,0x5000100,0x501f000
        self.regs=(UC_X86_REG_EAX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_ECX)
        self.put(self.bean,0,task_id,initial_state)
        self.put(self.config+0x164,quest_type)
        self.put(0x5007000,0x5008000);self.put(0x5008008,self.lookup)
        self.put(0x2945584,self.manager)
        def ret(value,cleanup):
            _,esp,eip,_=self.regs
            current=self.u.reg_read(esp)
            target=struct.unpack('<I',self.u.mem_read(current,4))[0]
            self.u.reg_write(UC_X86_REG_EAX,value)
            self.u.reg_write(esp,current+4+cleanup);self.u.reg_write(eip,target)
        def hook(u,addr,size,user):
            if addr==self.stop:u.emu_stop()
            elif addr==0x1257ac0:
                requested=struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_ESP)+4,4))[0]
                assert requested==self.task_id
                ret(self.bean,4)
            elif addr in (0x12578e0,0x1256e40):ret(0,4)
            elif addr==0x89ebd0:ret(0x5007000,0)
            elif addr==self.lookup:ret(self.config,4)
            elif addr==0x125d070:
                raise AssertionError('Existing bean unexpectedly inserted/replaced')
            elif addr==0x125a950:ret(0,12)  # NPC/quest UI side effects only.
            elif addr==0x10907c0:ret(0,4)   # UI notification collection.
        self.u.hook_add(UC_HOOK_CODE,hook)

    def put(self,addr,*values):
        self.u.mem_write(addr,struct.pack('<'+'I'*len(values),*values))

    def run(self,address,ecx,*arguments):
        eax,esp,eip,reg_ecx=self.regs
        self.put(self.sp,self.stop,*arguments)
        self.u.reg_write(esp,self.sp);self.u.reg_write(reg_ecx,ecx)
        self.u.emu_start(address,self.stop,count=5000)
        assert self.u.reg_read(eip)==self.stop,'Original routine did not return'
        return self.u.reg_read(eax)

    @property
    def state(self):
        return struct.unpack('<I',self.u.mem_read(self.bean+8,4))[0]

    def receive(self,kind,body):
        if kind==S_ACCEPT_SCENARIO_QUEST:
            info=decode_accept_scenario_quest(body)
            if info.quest_id!=self.task_id:return
            self.put(self.packet,0,kind,0,info.quest_id,info.state,info.value1,info.value2,
                     info.npc_key&0xffffffff,info.npc_key>>32)
            self.run(0x125d5c0,self.packet,0,0)
        elif kind==S_REFRESH_SCENARIO_QUEST_STATE:
            ident,state=decode_scenario_state(body)
            if ident!=self.task_id:return
            if state!=3:raise ValueError('This narrow probe covers ready-state refresh only')
            self.put(self.packet,0,kind,ident,state)
            self.run(0x125ea00,self.packet,0,0)

    def classify(self):
        return self.run(0x1257b20,self.manager,self.task_id)


def _visit_tasks(body):
    offset=8
    for index in range(2):
        count,offset=read_compact(body,offset)
        end=offset+count*4
        assert end<=len(body),'Truncated original SVisitNpc vector'
        ids=tuple(v[0] for v in struct.iter_unpack('>i',body[offset:end]))
        offset=end
        if index==1:
            assert offset==len(body),'Trailing original SVisitNpc data'
            return ids


def assert_ready_before_visit(messages,task_id,*,initial_state=0,quest_type=10):
    """Feed actual logical output to original existing-bean receive routines.

    Assert at each target SVisitNpc that native classification is ready3.
    Existing bean is the deliberate real-world precondition: duplicate Accept
    alone must go red. No fake packet consumer assigns the tested state.
    Returns a small record for the caller's existing regression evidence.
    """
    probe=ExistingQuestProbe(task_id,initial_state,quest_type)
    trace=[];visits=0
    for kind,body in messages:
        if kind in (S_ACCEPT_SCENARIO_QUEST,S_REFRESH_SCENARIO_QUEST_STATE):
            probe.receive(kind,body)
            trace.append((hex(kind),probe.state,probe.classify()))
        elif kind==0xc232a and task_id in _visit_tasks(body):
            visits+=1
            assert probe.classify()==3,(
                f'Existing quest {task_id} remains state{probe.state}/UI{probe.classify()} '
                'at SVisitNpc; duplicate SAccept does not update an existing bean')
    assert visits,'Target quest was never offered in SVisitNpc'
    return dict(task_id=task_id,initial_state=initial_state,trace=trace,visits=visits,
                final_state=probe.state,native_ui_class=probe.classify())


def main():
    from task_dialog_protocol import encode_visit_npc
    task=100186;key=(1100<<32)|44
    accept=(S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(ScenarioQuestInfo(task,3,0,0,key)))
    visit=(0xc232a,encode_visit_npc(key,(),(task,)))
    old=(accept,visit)
    try:assert_ready_before_visit(old,task)
    except AssertionError as exc:red=str(exc)
    else:raise AssertionError('Duplicate-accept-only regression failed to go red')
    corrected=assert_ready_before_visit((accept,(S_REFRESH_SCENARIO_QUEST_STATE,
        encode_scenario_state(task,3)),visit),task)
    print(json.dumps(dict(original_sequence_red=red,corrected_sequence=corrected,
                         original_handlers=['0x125d5c0','0x125ea00','0x125e660','0x125c020','0x1257b20']),indent=2))


if __name__=='__main__':main()
