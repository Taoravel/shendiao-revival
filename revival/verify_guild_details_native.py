"""Offline original guild details and per-residence gate; never opens game."""
import struct,json,hashlib,re
from dataclasses import replace,FrozenInstanceError
import guild_detail_protocol as p
from inspect_client import OUT,write_json
from native_inspect import DATA,u32
from verify_social_native import native_payload
from verify_family_donation_native import Native
from verify_family_history_native import octets_vector
from unicorn.x86_const import UC_X86_REG_EAX


def original_gate(scenes,template,current,guild=123):
    n=Native();manager,world=0x5001000,0x5004000
    n.write(0x2944564,world);n.write(manager+0x228,guild);n.write(world+0x110,template)
    n.uc.mem_write(world+0x30,struct.pack('<Q',current))
    # The original details consumer receives its bean by value after return.
    for offset,value in zip((0xa8,0xb0,0xb8),(scenes.hall,scenes.workshop,scenes.practice)):
        n.uc.mem_write(n.stack+4+offset,struct.pack('<Q',value))
    n.run(0x14a34f0,manager,lambda at:n.uc.emu_stop() if at==0x14a3598 else None)
    assert bytes(n.uc.mem_read(manager+0x230,24))==struct.pack('<QQQ',scenes.hall,scenes.workshop,scenes.practice)
    n.run(0x148dac0,manager,lambda at:None)
    return n.uc.reg_read(UC_X86_REG_EAX)&0xff


def detail_fixture(scenes):
    return p.GuildDetails(unbound_header='帮派详表',bulletins=(),courses=(),
        raw_i32_at_3c=(101,102),raw_u64_at_48=(2**40+10,2**41+20),raw_i32_at_58=(103,104),
        raw_u64_at_60=(2**42+30,2**43+40,2**44+50),raw_i32_at_78=(105,106,107,108),
        skills=(),practices=(),scenes=scenes,raw_i32_at_c0=109)


def original_detail(view,*,wrapper=False):
    strings=[(4,view.unbound_header)]
    values=[(0x3c,view.raw_i32_at_3c[0]),(0x40,view.raw_i32_at_3c[1]),
        (0x58,view.raw_i32_at_58[0]),(0x5c,view.raw_i32_at_58[1]),
        *zip((0x78,0x7c,0x80,0x84),view.raw_i32_at_78),(0xc0,view.raw_i32_at_c0)]
    for offset,value in zip((0x48,0x50,0x60,0x68,0x70),(*view.raw_u64_at_48,*view.raw_u64_at_60)):
        values.extend(((offset,value&0xffffffff),(offset+4,value>>32)))
    for offset,value in zip((0xa8,0xb0,0xb8),(view.scenes.hall,view.scenes.workshop,view.scenes.practice)):
        values.extend(((offset,value&0xffffffff),(offset+4,value>>32)))
    # Three native containers have their real empty sentinel rather than null.
    raw=[(0x24,struct.pack('<II',0x5007000,0)),(0x8c,struct.pack('<II',0x5008000,0)),
        (0x98,struct.pack('<II',0x5008100,0)),(0xa0,struct.pack('<I',0x2272f0c)),
        (0x6000,struct.pack('<III',0x5007000,0x5007000,0x5007000)),(0x604d,b'\x01'),
        (0x7000,struct.pack('<II',0x5008000,0x5008000)),(0x7100,struct.pack('<II',0x5008100,0x5008100))]
    for field,head,start,rows,vtable in ((0x8c,0x5008000,0x5008200,view.skills,0x228253c),
            (0x98,0x5008100,0x500a200,view.practices,0x22824f0)):
        nodes=[start+i*0x40 for i in range(len(rows))]
        raw.extend(((field,struct.pack('<II',head,len(rows))),
            (head-0x5001000,struct.pack('<II',nodes[0] if nodes else head,nodes[-1] if nodes else head))))
        for index,row in enumerate(rows):
            numbers=(row.skill_id,*row.unbound_values) if vtable==0x228253c else (row.skill_id,row.status)
            raw.append((nodes[index]-0x5001000,struct.pack('<III'+'i'*len(numbers),
                nodes[index+1] if index+1<len(nodes) else head,nodes[index-1] if index else head,vtable,*numbers)))
    courses=[]
    for index,row in enumerate(view.courses):
        start=0x5080000+index*0x100
        vector,buffers=octets_vector(row.parameters,0x5090000+index*0x1000)
        courses.append(struct.pack('<6I',0x22838c8,row.template_id,0,start,start+len(vector),start+len(vector)))
        raw.extend([(start-0x5001000,vector),*buffers])
    if courses:
        end=0x500c000+len(courses)*24
        raw.extend([(0x30,struct.pack('<III',0x500c000,end,end)),(0xb000,b''.join(courses))])
    board=sorted(view.bulletins,key=lambda row:row[0])
    nodes=[0x5140000+i*0x100 for i in range(len(board))];head=0x5007000
    raw.extend([(0x24,struct.pack('<II',head,len(nodes))),
        (head-0x5001000,struct.pack('<III',nodes[0] if nodes else head,nodes[0] if nodes else head,nodes[-1] if nodes else head))])
    for index,(key,row) in enumerate(board):
        node=nodes[index]
        raw.append((node-0x5001000,struct.pack('<IIIiI',head,nodes[index-1] if index else head,
            nodes[index+1] if index+1<len(nodes) else head,key,0x22729f0)))
        strings.extend(((node+0x14-0x5001000,row.unbound_first),(node+0x30-0x5001000,row.unbound_second)))
    if wrapper:
        strings=[(offset+8 if offset<0xc8 else offset,value) for offset,value in strings]
        values=[(8,0x2285d4c)]+[(offset+8,value) for offset,value in values]
        raw=[(offset+8 if offset<0xc8 else offset,value) for offset,value in raw]
    return native_payload(0xf91f00 if wrapper else 0xf90c50,strings=strings,
        scalars=[(offset,value&0xffffffff) for offset,value in values],raw=raw)


def invalid_views(full):
    return (replace(full,unbound_header=None),replace(full,unbound_header='坏\0文本'),
        replace(full,raw_i32_at_3c=(True,1)),replace(full,raw_i32_at_3c=[1,2]),
        replace(full,raw_u64_at_48=(None,2)),replace(full,raw_u64_at_48=(-1,2)),
        replace(full,raw_u64_at_60=(2**64,0,0)),replace(full,raw_i32_at_c0=2**31),
        replace(full,bulletins=((1,p.GuildBulletin('甲','乙')),(1,p.GuildBulletin('丙','丁')))),
        replace(full,bulletins=((True,p.GuildBulletin('甲','乙')),)),replace(full,bulletins=[]),
        replace(full,bulletins=((-2**31-1,p.GuildBulletin('甲','乙')),)),
        replace(full,bulletins=((2**31,p.GuildBulletin('甲','乙')),)),
        replace(full,courses=(p.GuildCourse(7,('日期','对象')),)),
        replace(full,courses=(p.GuildCourse(8,('日期','对象')),)),
        replace(full,skills=(p.GuildSkill(350001,(1,2,3,4)),)*2),
        replace(full,practices=(p.GuildPractice(360001,1),p.GuildPractice(360001,0))),
        replace(full,skills=tuple(p.GuildSkill(350001+i,(1,2,3,4)) for i in range(65))),
        replace(full,courses=(p.GuildCourse(1,('日期',)),)*101),
        replace(full,bulletins=tuple((i,p.GuildBulletin('甲','乙')) for i in range(33))),
        replace(full,unbound_header='甲'*4097),
        replace(full,bulletins=tuple((i,p.GuildBulletin('甲'*1000,'乙'*1000)) for i in range(32))))


def main():
    scenes=p.GuildSceneIDs(2**40+1393,2**41+1395,2**42+1394)
    actual=native_payload(0xe46020,scalars=[(8,1393),(0xc,256),(0x10,1395),(0x14,512),(0x18,1394),(0x1c,1024)])
    assert actual==p.scene_ids(scenes)==struct.pack('>QQQ',scenes.hall,scenes.workshop,scenes.practice)
    for template,selected in ((1393,scenes.hall),(1394,scenes.practice),(1395,scenes.workshop)):
        assert original_gate(scenes,template,selected)==1
        assert original_gate(scenes,template,selected&0xffffffff)==0
        assert original_gate(scenes,template,selected,guild=0)==0
        assert original_gate(scenes,template,selected+1)==0
        for other in (scenes.hall,scenes.practice,scenes.workshop):
            if other!=selected:assert original_gate(scenes,template,other)==0
    assert original_gate(scenes,1401,scenes.hall)==0
    details=detail_fixture(scenes)
    assert p.guild_details(details)==original_detail(details)
    with_skills=replace(details,skills=(p.GuildSkill(350001,(9,100,200,-1)),p.GuildSkill(350002,(10,110,220,1))),
        practices=(p.GuildPractice(360001,1),p.GuildPractice(360002,0)))
    assert p.guild_details(with_skills)==original_detail(with_skills)
    with_courses=replace(with_skills,courses=(p.GuildCourse(1,('创立时间',)),p.GuildCourse(7,('升级时间','聚义厅','3'))))
    assert p.guild_details(with_courses)==original_detail(with_courses)
    full=replace(with_courses,bulletins=((7,p.GuildBulletin('公告乙','当时署名乙')),(0,p.GuildBulletin('公告甲','当时署名甲'))))
    assert p.guild_details(full)==original_detail(full)
    assert p.DETAILED_GUILD==u32(0xf91cd1)==0xc5624
    assert p.guild_details(full)==original_detail(full,wrapper=True)
    signed_keys=replace(full,bulletins=tuple((key,p.GuildBulletin(str(key),'署名'))
        for key in (2**31-1,-1,0,-2**31)))
    assert p.guild_details(signed_keys)==original_detail(signed_keys)
    assert p.guild_details(signed_keys)==original_detail(signed_keys,wrapper=True)
    extremes=replace(full,raw_i32_at_3c=(-2**31,2**31-1),raw_u64_at_48=(2**64-1,0),
        unbound_header='长'*200+'😀',raw_i32_at_c0=-1)
    assert p.guild_details(extremes)==original_detail(extremes)
    for invalid in invalid_views(full):
        try:p.guild_details(invalid)
        except ValueError:pass
        else:raise AssertionError('Malformed, unknown or unbounded guild details accepted')
    for size,expected in ((0,1),(65535,1),(65536,0)):
        n=Native();n.run(0xf91d40,0,lambda at:None,args=(size,))
        assert n.uc.reg_read(UC_X86_REG_EAX)==expected
    try:full.raw_i32_at_c0=3
    except FrozenInstanceError:pass
    else:raise AssertionError('Mutable guild view')
    catalog=json.loads((OUT/'catalogs/knight.gsp.faction.cfactionprogress.json').read_text(encoding='utf-8'))
    parameters={int(row['attributes']['id']):set(re.findall(r'\$parameter(\d+)\$',row['attributes']['content'])) for row in catalog}
    assert parameters=={i:set(map(str,range(1,(1 if i==1 else 3 if i==7 else 2)+1))) for i in range(1,8)}
    for value in (True,-1,2**63,None):
        try:p.scene_ids(replace(scenes,hall=value))
        except ValueError:pass
        else:raise AssertionError('Malformed guild scene identity accepted')
    result=dict(passed=['original FactionSceneID marshal retains three distinct full64 identities',
        'original details consumer places the three Q values in the manager slots used by the real guild gate',
        'three native template branches select their own slot; high32, different identity, absent guild and other map are rejected',
        'full original FactionDetailedData and c5624 wrapper match every explicit scalar/string field',
        'nonempty original bulletin map retains full signed32 keys in sorted order; guild CourseInfo template7 retains three parameters',
        'nonempty original FactionSkill five-i32 and FactionPractice two-i32 linked lists match without assigning unknown fields',
        'wide UTF16, long strings and full opaque native integer ranges survive original marshal',
        'unknown/mutable/duplicate/malformed/container-limit/body-limit inputs reject; snapshot is frozen',
        'original c5624 size policy accepts up to65535 and refuses65536'],
        image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False,live_server_changed=False,
        organization_admission_policy_implemented=False,full_guild_detail_state_implemented=False,
        actual_npc_registered=False,shared_runtime_integrated=False,
        scope='pure codec and original instructions; temporary explicit unbound scalar fixtures; no GUI initialization',
        original_business_meaning_of_unbound_fields_verified=False)
    write_json(OUT/'evidence/guild-details-native-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
