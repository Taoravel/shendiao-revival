"""Original c563a full serializer/receiver and research-cache clearing."""
from dataclasses import replace
from pathlib import Path
import hashlib,json,struct,tempfile
from native_inspect import DATA,u32
from verify_social_native import native_payload
from verify_family_donation_native import Native
from unicorn.x86_const import UC_X86_REG_EIP,UC_X86_REG_ESI,UC_X86_REG_EBX
from verify_guild_research import make
from guild_research import ResearchAward
import guild_research_protocol as p
from inspect_client import OUT,write_json


def original_refresh(selected,rows):
    head=0x5007000;nodes=[0x5008200+i*0x40 for i in range(len(rows))]
    raw=[(0x10,struct.pack('<II',head,len(rows))),
        (head-0x5001000,struct.pack('<II',nodes[0] if nodes else head,nodes[-1] if nodes else head))]
    for i,(node,row) in enumerate(zip(nodes,rows)):
        raw.append((node-0x5001000,struct.pack('<III5i',
            nodes[i+1] if i+1<len(nodes) else head,nodes[i-1] if i else head,0x228253c,*row)))
    return native_payload(0xe92110,scalars=[(8,selected)],raw=raw)


def original_receiver(sequence):
    n=Native();obj,manager,head,cachehead=0x5001000,0x5004000,0x5007000,0x500a000
    n.write(0x2945570,manager);n.write(0x2952494,0);n.write(0x2952464,0)
    n.write(manager+0x31c,cachehead,0);n.write(cachehead,cachehead,cachehead)
    heap=[0x5200000]
    def hook(at):
        if at==0x1919178:
            address=heap[0];heap[0]+=0x100;n.ret(value=address)
        elif at==0x191910c:n.ret()
    for selected,rows in sequence:
        nodes=[0x5008200+i*0x40 for i in range(len(rows))]
        n.write(obj+8,selected);n.write(obj+0x10,head,len(rows))
        n.write(head,nodes[0] if nodes else head,nodes[-1] if nodes else head)
        for i,(node,row) in enumerate(zip(nodes,rows)):
            n.write(node,nodes[i+1] if i+1<len(nodes) else head,nodes[i-1] if i else head,0x228253c,*row)
        n.run(0x149a410,obj,hook,args=(0,0));assert n.uc.reg_read(UC_X86_REG_EIP)==n.stop
        assert n.read(manager+0x324)==selected and n.read(manager+0x320)==len(rows)
        actual=[];node=n.read(cachehead)
        while node!=cachehead:
            values=struct.unpack('<4iqq',bytes(n.uc.mem_read(node+8,32)))
            actual.append((values[0],values[1],values[2],values[4],values[5]));node=n.read(node)
            assert len(actual)<=14
        assert tuple(actual)==rows
    # SLeaveFaction 14a0220 ->149fdd0 ->1499380. The relevant native reset
    # slices zero selected at +fc and clear the actual research list at +f0.
    n.uc.reg_write(UC_X86_REG_ESI,manager+0x228);n.uc.reg_write(UC_X86_REG_EBX,0)
    n.run(0x1499412,0,lambda at:n.uc.emu_stop() if at==0x1499418 else None)
    def clear(at):
        if at==0x191910c:n.ret()
        elif at==0x1499515:n.uc.emu_stop()
    n.run(0x14994de,0,clear)
    assert n.read(manager+0x324)==0 and n.read(manager+0x320)==0 and n.read(cachehead)==cachehead


def main():
    assert u32(0xe918fe)==p.REFRESH_RESEARCH==0xc563a
    with tempfile.TemporaryDirectory() as d:
        f,guild=make(Path(d)/'refresh.db')
        before=f.org.guild_research_snapshot(guild)
        f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
        f.org.award_guild_research(ResearchAward(guild,'refresh-native-source',35,f.now()+5000),f.now())
        after=f.org.guild_research_snapshot(guild)
        sequence=[]
        for view in (before,after,replace(after,skills=tuple(reversed(after.skills)))):
            rows=tuple((s.skill_id,s.level,s.cap,s.experience,s.next_experience) for s in view.skills)
            assert p.refresh(view)==original_refresh(view.selected_skill,rows)
            sequence.append((view.selected_skill,rows))
        empty=original_refresh(0,());assert empty==p.clear_cache()==bytes(5)
        # Clearing then repopulating executes the complete original receiver
        # each time; old nodes/selection must not survive either replacement.
        original_receiver((sequence[0],sequence[1],(0,()),sequence[2]))
    result=dict(passed=['original c563a constructor and full marshal match known fourteen-skill absolute snapshots',
        'complete original receiver replaces selected and nonempty linked-list caches, clears on original empty list, then repopulates',
        'original leave-guild reset slices independently clear selected research and cached research nodes'],
        image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False,
        full_refresh_receiver_without_gui_instances_executed=True,full_leave_handler_executed=False,
        server_maintenance_source_integrated=False,live_server_changed=False)
    write_json(OUT/'evidence/guild-research-refresh-native-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
