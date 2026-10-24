"""Full native guild member/basic-data serialization, including 64-bit fields."""
import hashlib
import json
import struct
from inspect_client import OUT,write_json
from native_inspect import DATA,BASE,u32
from verify_social_native import native_payload
import guild_protocol as g
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP


def rank_label(rank):
    uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(0,4096)
    uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
    uc.mem_map(0x5000000,0x20000)
    constructor=u32(0x22443f0)
    if not BASE<=constructor<BASE+len(DATA):
        uc.mem_map(constructor&~4095,4096);uc.mem_write(constructor,b'\xc3')
    stack,stop=0x5010000,0x500f000
    uc.mem_write(stack,struct.pack('<III',stop,0x5001000,rank));uc.reg_write(UC_X86_REG_ESP,stack)
    labels=[]
    def hook(machine,at,size,user):
        sp=machine.reg_read(UC_X86_REG_ESP)
        if at==0x837060:
            labels.append(('cstringres',struct.unpack('<I',machine.mem_read(sp+8,4))[0]));machine.emu_stop()
        elif at==constructor:
            ptr=struct.unpack('<I',machine.mem_read(sp+4,4))[0];raw=bytearray()
            for i in range(64):
                pair=bytes(machine.mem_read(ptr+i*2,2))
                if pair==b'\x00\x00':break
                raw.extend(pair)
            labels.append(('literal',raw.decode('utf-16le')));machine.emu_stop()
    uc.hook_add(UC_HOOK_CODE,hook);uc.emu_start(0x1486190,stop,count=2000)
    assert len(labels)==1
    return labels[0]


def fields(m,shift=0):
    scalars=[(8,m.role_id&0xffffffff),(0xc,m.role_id>>32)]
    scalars.extend((0x10+i*4,v&0xffffffff) for i,v in enumerate((*m.metadata,m.level)))
    scalars.extend((0x3c+i*4,v&0xffffffff) for i,v in enumerate((m.school,*m.prestige)))
    scalars.extend(((0x48,m.weekly_dues&0xffffffff),(0x4c,m.weekly_dues>>32),
        (0x50,m.historical_dues&0xffffffff),(0x54,m.historical_dues>>32),
        (0x58,g.FAMILY_POSITIONS[m.family_position]),(0x5c,g.GUILD_POSITIONS[m.guild_position]),(0x7c,m.family)))
    return [(shift+o,v) for o,v in scalars]


def main():
    passed=[]
    rows=(g.GuildMemberWire(2**40+123,'甲家主',44,12,17,'第一家族','leader','leader',
        (11,22,33),(55,66),2**40+7,2**41+9,'2026-10-22 23:01:02'),
        g.GuildMemberWire(456,'乙帮众',40,11,18,'第二家族','deputy','left_elder',(-1,0,7),(2,3),4,5,''),
        g.GuildMemberWire(457,'丙族长',40,11,18,'第三家族','leader','family_leader',(0,0,0),(0,0),0,0,''))
    for m in rows:
        strings=[(0x20,m.name),(0x60,m.family_name),(0x80,m.offline_text)]
        expected=g.guild_member(m)
        assert native_payload(0xe458d0,strings,fields(m))==expected
        assert native_payload(0xd726c0,[(o+8,s) for o,s in strings],[(8,0x2273130)]+fields(m,8))==expected
        passed.append('FactionMemberData and SRefreshMemberData '+m.guild_position)
    for members in ((),rows[:1],rows):
        head=0x5001400;nodes=[0x5001600+i*0x100 for i in range(len(members))]
        raw=[(0x400,struct.pack('<II',nodes[0] if nodes else head,nodes[-1] if nodes else head))]
        scalars=[(0xc,head),(0x10,len(members))];strings=[]
        for i,(node,m) in enumerate(zip(nodes,members)):
            offset=node-0x5001000
            raw.append((offset,struct.pack('<II',nodes[i+1] if i+1<len(nodes) else head,nodes[i-1] if i else head)))
            scalars.extend([(offset+8,0x2273130)]+fields(m,offset+8))
            strings.extend((o+offset+8,s) for o,s in ((0x20,m.name),(0x60,m.family_name),(0x80,m.offline_text)))
        assert native_payload(0xe8a7b0,strings,scalars,raw)==g.guild_members(members)
        passed.append('SAddFactionMember original linked list '+str(len(members)))
    view=g.GuildView(27,'原生帮派','共同进退',3,19)
    strings=[(8,view.name),(0x24,view.aim)];scalars=[(4,27),(0x40,3),(0x44,19)]
    assert native_payload(0xe465a0,strings,scalars)==g.guild_data(view)
    assert native_payload(0xd73dd0,[(o+8,s) for o,s in strings],[(8,0x2273330)]+[(o+8,v) for o,v in scalars])==g.guild_data(view)
    passed.append('FactionData and SUpdateFactionData name/aim/level/reserved')
    assert native_payload(0xe464a0,scalars=[(8,123),(0xc,256)])==g.removed_guild_member(2**40+123)
    passed.append('SRemoveFactionMember preserves full role identity')
    labels={0:'帮众',1:'巡察使',2:'族长',3:'左长老',4:'右长老',5:'副帮主',6:'帮主'}
    catalog={int(r['attributes']['id']):r['attributes'] for r in json.loads(
        (OUT/'catalogs/knight.gsp.message.cstringres.json').read_text('utf-8'))}
    actual={}
    for rank,expected in labels.items():
        source,value=rank_label(rank)
        actual[rank]=value if source=='literal' else catalog[value]['msg']
        assert actual[rank]==expected
    # The original roster renderer passes its guild-rank cache field directly.
    assert DATA[0x14bc41f-BASE:0x14bc41f-BASE+4]==b'\x8b\x57\x54\x52'
    passed.append('original rank formatter and roster cache: member/patrol/family leader/elders/deputy/head')
    result=dict(passed=passed,image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False,
        original_rank_labels=actual,rank_formatter='0x1486190',roster_rank_cache='+0x54',
        scope='original serializers, not GUI; member reserved metadata and basic-data final int remain unbound')
    write_json(OUT/'evidence/guild-native-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
