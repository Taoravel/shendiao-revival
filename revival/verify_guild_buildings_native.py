"""Original construction messages/cache/arithmetic; offline image only."""
import json,hashlib,struct
import xml.etree.ElementTree as ET
from dataclasses import replace
from native_inspect import DATA,u32
from verify_social_native import native_payload
from verify_family_donation_native import Native
from guild_buildings import Building,BuildingSnapshot,requirements
from inspect_client import OUT,write_json
import guild_building_protocol as p
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_EIP,UC_X86_REG_ESP,UC_X86_REG_ESI


def original_data(selected,rows):
    head=0x5007000;nodes=[0x5008200+i*0x40 for i in range(len(rows))]
    raw=[(0x10,struct.pack('<II',head,len(rows))),
        (head-0x5001000,struct.pack('<II',nodes[0] if nodes else head,nodes[-1] if nodes else head))]
    for i,(node,row) in enumerate(zip(nodes,rows)):
        raw.append((node-0x5001000,struct.pack('<III3i',nodes[i+1] if i+1<len(nodes) else head,
            nodes[i-1] if i else head,0x2282588,*row)))
    return native_payload(0xe92d80,scalars=[(8,selected)],raw=raw)


def receiver_and_costs(state):
    n=Native();obj,manager,head=0x5001000,0x5004000,0x5007000
    n.write(0x2945570,manager)
    for address in (0x294d190,0x295246c,0x2952484):n.write(address,0)
    n.write(manager+0x338,999,998,997,996,995,994)
    def receive(selected,rows):
        nodes=[0x5008200+i*0x40 for i in range(len(rows))]
        n.write(obj+8,selected&0xffffffff);n.write(obj+0x10,head,len(rows))
        n.write(head,nodes[0] if nodes else head,nodes[-1] if nodes else head)
        for i,(node,row) in enumerate(zip(nodes,rows)):
            n.write(node,nodes[i+1] if i+1<len(nodes) else head,nodes[i-1] if i else head,0x2282588,*row)
        n.run(0x1495020,obj,lambda at:None,args=(0,0))
        assert n.uc.reg_read(UC_X86_REG_EIP)==n.stop
    rows=tuple((b.building_type,b.level,b.construction) for b in state.buildings)
    receive(state.selected,tuple(reversed(rows)))
    assert n.read(manager+0x334)==state.selected
    assert tuple(struct.unpack('<ii',bytes(n.uc.mem_read(manager+0x338+i*8,8))) for i in range(3))==tuple((b.level,b.construction) for b in state.buildings)
    # Empty rows do not invalidate prior cache values in this original handler.
    # The server codec therefore requires three known rows; it never emits an
    # invented zero baseline to clear unknown old state.
    cached=bytes(n.uc.mem_read(manager+0x338,24));receive(-1,())
    assert n.read(manager+0x334)==0xffffffff and bytes(n.uc.mem_read(manager+0x338,24))==cached
    observed=[]
    for index in range(3):
        for level in (0,1,4,19,20):
            n.write(manager+0x338+index*8,level);values=[]
            for address in (0x1486d70,0x1486d00,0x1486d50):
                n.run(address,manager,lambda at:None,args=(index,))
                assert n.uc.reg_read(UC_X86_REG_EIP)==n.stop
                value=n.uc.reg_read(UC_X86_REG_EAX)&0xffffffff
                if address==0x1486d00:value|=(n.uc.reg_read(UC_X86_REG_EDX)&0xffffffff)<<32
                values.append(value)
            cost=requirements(Building(index,level,0))
            assert tuple(values)==(cost.construction,cost.funds,cost.popularity)
            observed.append((index,level,*values))
    assert observed[1]==(0,1,150,600000,200)
    receive(state.selected,rows)
    for index,b in enumerate(state.buildings):
        values=[]
        for address,formatter,wide in ((0x14ad3a5,0x847450,False),(0x14ad4ca,0x490220,True),(0x14ad581,0x490220,True)):
            n.uc.reg_write(UC_X86_REG_ESI,index)
            def observe(at):
                if at==formatter:
                    sp=n.uc.reg_read(UC_X86_REG_ESP)
                    values.append(struct.unpack('<q' if wide else '<i',bytes(n.uc.mem_read(sp+8,8 if wide else 4)))[0])
                    n.uc.emu_stop()
            n.run(address,0,observe)
        cost=requirements(b)
        assert tuple(values)==(cost.construction,cost.funds,cost.popularity)
    return tuple(observed)


def choice_button(context,target):
    n=Native();dialog,row,network,table,close=0x5001000,0x5003000,0x5004000,0x5006000,0x500e000
    n.write(dialog+0x20,context&0xffffffff,context>>32)
    n.write(dialog+4,table);n.write(table+4,close);n.write(network,table);n.write(table+0x3c,close+16)
    n.write(row+0xc0,target);sent=[]
    def hook(at):
        if at==0x4af0b0:n.ret(value=row)
        elif at==0x813860:n.ret(value=network)
        elif at==close:n.ret(value=1)
        elif at==close+16:
            message=n.read(n.uc.reg_read(UC_X86_REG_ESP)+4)
            sent.append((n.read(message+4),n.read(message+8)|(n.read(message+0xc)<<32),n.read(message+0x10)))
            n.ret(4,value=1)
    n.run(0x14ac980,dialog,hook,args=(0,))
    assert n.uc.reg_read(UC_X86_REG_EIP)==n.stop
    assert sent==[(p.CHOOSE_BUILDING,context,target)]


def main():
    state=BuildingSnapshot(2,1,7,1800,(Building(0,1,37),Building(1,4,99),Building(2,19,1049)),'explicit_fixture')
    rows=tuple((b.building_type,b.level,b.construction) for b in state.buildings)
    assert p.building_data(state)==original_data(state.selected,rows)
    assert native_payload(0x8373a0)==b'' and p.decode_query(b'')==()
    assert p.decode_choice(struct.pack('>Qi',2**40+17,0))==(2**40+17,0)
    assert u32(0xe9267e)==p.BUILDING_DATA and u32(0xd6dddb)==p.QUERY_BUILDINGS and u32(0xd6b649)==p.CHOOSE_BUILDING
    observations=receiver_and_costs(state)
    for target in range(3):choice_button(2**48+1395,target)
    names=[];n=Native()
    for target in range(3):
        def name_lookup(at):
            if at==0x837060:
                names.append(n.read(n.uc.reg_read(UC_X86_REG_ESP)+8));n.uc.emu_stop()
        n.run(0x14aa1b0,0,name_lookup,args=(0x5001000,target))
    assert names==[819,820,821]
    layout=ET.parse(OUT/'decoded/ui/layouts/gangconstruct.layout').getroot()
    table=next(w for w in layout.iter('Window') if w.attrib.get('Name')=='GangConstruct/SlectList')
    headers=[v.attrib['Value'].split(' width:')[0] for v in table.findall('Property') if v.attrib['Name']=='ColumnHeader']
    assert headers==['text:建筑名','text:当前等级','text:当前建设度','text:所需建设度','text:消耗帮派资金','text:消耗人气度']
    for malformed in (replace(state,buildings=()),replace(state,buildings=list(state.buildings)),replace(state,buildings=(1,2,3)),
            replace(state,selected=True),replace(state,buildings=(Building(0,1,150),*state.buildings[1:]))):
        try:p.building_data(malformed)
        except ValueError:pass
        else:raise AssertionError('Malformed construction snapshot encoded')
    report=dict(passed=['original complete c5628 list serializer matches all three current building states',
        'original empty c5627 query, constructors and c5631 full64 context/zero-based selected row button',
        'complete original receiver overwrites all three level/progress pairs; empty response cannot clear stale prior building cache',
        'three original arithmetic functions match15 known building/level rows including level20 zero branch',
        'three original numeric widget-reader slices, building-name lookup and independent layout columns bind types and requirement/funds/popularity'],
        arithmetic_rows=observations,native_image_sha256=hashlib.sha256(DATA).hexdigest(),
        native_gui_verified=False,full_receiver_without_gui_instances_executed=True,live_server_changed=False)
    write_json(OUT/'evidence/guild-buildings-native-verification.json',report);print(json.dumps(report))


if __name__=='__main__':main()
