"""Compare organization codecs with this client's original x86 serializers."""
import json
import struct
import hashlib
from verify_social_native import native_payload
from inspect_client import OUT,write_json
import faction_protocol as p


def native_position(address,positions):
    """Execute original cached-roster leader/deputy lookup, not a GUI mock."""
    from native_inspect import DATA,BASE
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EIP
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x10000)
    manager,head,stack,stop=0x5001000,0x5002000,0x5008000,0x500f000
    def w(a,*values):emu.mem_write(a,struct.pack('<'+'I'*len(values),*values))
    nodes=[0x5003000+i*0x40 for i in range(len(positions))]
    w(manager+0xb4,head);w(head,nodes[0] if nodes else head)
    records=[]
    for i,position in enumerate(positions):
        record=0x5004000+i*0x100;records.append(record)
        w(nodes[i],nodes[i+1] if i+1<len(nodes) else head,0,record)
        w(record+0x34,position)
    w(stack,stop);emu.reg_write(UC_X86_REG_ECX,manager);emu.reg_write(UC_X86_REG_ESP,stack)
    emu.emu_start(address,stop,count=5000)
    assert emu.reg_read(UC_X86_REG_EIP)==stop
    found=emu.reg_read(UC_X86_REG_EAX)
    return records.index(found) if found else None


def main():
    cases=[
      ('CCreateFamily',p.CREATE_FAMILY,0xe44d60,p.create_request(123,1,'江湖家族','同心协力',2),
       [(0x14,'江湖家族'),(0x30,'同心协力')],[(8,123),(0x10,1),(0x4c,2)]),
      ('CResponseFamilyApply',p.FAMILY_REVIEW,0xe454f0,struct.pack('>Qi',123,1),[],[(8,123),(0x10,1)]),
      ('CChangeMemberPosition',p.FAMILY_POSITION,0xe44ce0,struct.pack('>Qi',123,2),[],[(8,123),(0x10,2)]),
      ('CAppointFactionMember',p.FACTION_POSITION,0xe44b70,struct.pack('>Qi',123,2),[],[(8,123),(0x10,2)]),
      ('CExpelFamilyMember',p.EXPEL_MEMBER,0xe44fd0,struct.pack('>Q',123),[],[(8,123)]),
      ('CRequestFamilyInfo',p.REQUEST_FAMILY,0xe45350,struct.pack('>i',7),[],[(8,7)]),
      ('CJoinOtherFaction',p.JOIN_FACTION,0xe45160,struct.pack('>i',7),[],[(8,7)]),
      ('CResponseCreateFaction',p.CREATE_FACTION_RESPONSE,0xe45390,struct.pack('>i',1),[],[(8,1)]),
      ('CResponseFactionApply',p.FACTION_REVIEW,0xe454c0,struct.pack('>ii',7,1),[],[(8,7),(0xc,1)]),
      ('CLeaveFamily',p.LEAVE_FAMILY,0xd6d380,b'',[],[]),
      ('CLeaveFaction',p.LEAVE_FACTION,0xd6d290,b'',[],[]),
      ('CRequestFactionData',p.REQUEST_FACTION,0x837310,b'',[],[]),
    ]
    result=[]
    for name,kind,address,expected,strings,scalars in cases:
        assert native_payload(address,strings,scalars)==expected,name
        p.decode(kind,expected)
        try:p.decode(kind,expected+b'\0')
        except ValueError:pass
        else:raise AssertionError('Trailing packet accepted')
        result.append({'name':name,'type':hex(kind),'serializer':hex(address),'bytes':len(expected)})
    # Native panel fields have distinct identities and 64-bit balances. These
    # cannot be replaced with constructor-zero snapshots or the leader's cash.
    view=p.FamilyView(17,'江湖家族','同心协力','创始侠客',3,2**40+7,1000,5000,7,20)
    fields=[(4,17),(0x5c,3),(0x60,7),(0x64,256),(0x68,1000),(0x6c,5000),(0x70,7),(0x74,20)]
    strings=[(8,view.founder_name),(0x24,view.name),(0x40,view.aim)]
    expected=p.family_data(view)
    assert native_payload(0xed7340,strings,fields)==expected
    result.append(dict(name='FamilyData-known-fields',serializer='0xed7340',bytes=len(expected)))
    assert native_payload(0xed7cf0,[(o+8,s) for o,s in strings],[(8,0x22838a0)]+[(o+8,v) for o,v in fields])==p.family_update(view)
    result.append(dict(name='SUpdateFamilyData-known-fields',type=hex(p.UPDATE_FAMILY),serializer='0xed7cf0',bytes=len(expected)))
    try:p.family_data(p.FamilyView(17,'江湖家族','同心协力','侠客',3,None))
    except ValueError:pass
    else:raise AssertionError('Unknown family funds silently defaulted')
    members=(p.FamilyMemberWire(2**40+123,'现任族长',11,(22,33),44,'leader','2026-10-22 23:01:02'),
             p.FamilyMemberWire(456,'副族长乙',-1,(32,21),10,'deputy',''))
    def member_fields(member,shift=0):
        values=[(8,member.role_id&0xffffffff),(0xc,member.role_id>>32)]
        values.extend((0x2c+i*4,v&0xffffffff) for i,v in enumerate((member.unbound_metadata,*member.prestige_values,member.level)))
        values.append((0x3c,p.FAMILY_POSITIONS[member.position]))
        return [(shift+o,v) for o,v in values]
    for m in members:
        strings=[(0x10,m.name),(0x40,m.last_offline_text)]
        expected=p.family_member(m)
        assert native_payload(0xe45d20,strings,member_fields(m))==expected
        assert native_payload(0xd74260,[(o+8,s) for o,s in strings],
                              [(8,0x22733a4)]+member_fields(m,8))==expected
        result.extend([dict(name='FamilyMemberData-'+m.position,serializer='0xe45d20',bytes=len(expected)),
                       dict(name='SUpdateMemberData-'+m.position,type=hex(p.UPDATE_FAMILY_MEMBER),serializer='0xd74260',bytes=len(expected))])
    # Original SAddFamilyMember stores an std::list of native beans. Supply the
    # actual linked head/nodes/vtables; do not replace its serializer with Python.
    for rows in ((),members[:1],members):
        head=0x5001400;nodes=[0x5001600+i*0x100 for i in range(len(rows))]
        raw=[(0x400,struct.pack('<II',nodes[0] if nodes else head,nodes[-1] if nodes else head))]
        scalars=[(0xc,head),(0x10,len(rows))];strings=[]
        for i,(node,m) in enumerate(zip(nodes,rows)):
            offset=node-0x5001000
            raw.append((offset,struct.pack('<II',nodes[i+1] if i+1<len(nodes) else head,nodes[i-1] if i else head)))
            scalars.extend([(offset+8,0x22733a4)]+member_fields(m,offset+8))
            strings.extend([(offset+0x18,m.name),(offset+0x48,m.last_offline_text)])
        expected=p.family_members(rows)
        assert native_payload(0xe8c120,strings,scalars,raw)==expected
        result.append(dict(name='SAddFamilyMember-'+str(len(rows)),type=hex(p.ADD_FAMILY_MEMBERS),serializer='0xe8c120',bytes=len(expected)))
    for name,kind,address,body,fields in (
        ('SRemoveFamilyMember',p.REMOVE_FAMILY_MEMBER,0xe464c0,p.removed_family_member(2**40+123),[(8,123),(0xc,256)]),
        ('SExpelFamilyMember',p.EXPELLED_FAMILY_MEMBER,0xe46000,p.removed_family_member(2**40+123),[(8,123),(0xc,256)]),
        ('SLeaveFamily',p.LEFT_FAMILY,0xd71de0,b'',[]),
        ('SLeaveFaction',p.LEFT_FACTION,0xd71d00,b'',[])):
        assert native_payload(address,scalars=fields)==body
        result.append(dict(name=name,type=hex(kind),serializer=hex(address),bytes=len(body)))
    join=p.family_join_request((17,23))
    assert native_payload(0xe6a4f0,scalars=[(0xc,0x5001400),(0x10,0x5001408),(0x14,0x5001408)],raw=[(0x400,struct.pack('<ii',17,23))])==join
    assert p.decode(p.JOIN_FAMILY,join)==((17,23),0)
    result.append(dict(name='CJoinOtherFamily-two',type=hex(p.JOIN_FAMILY),serializer='0xe6a4f0',bytes=len(join)))
    applicant=p.FamilyApplication(2**40+123,'申请侠客',42,12,'推荐甲')
    expected=p.family_application(applicant)
    fields=[(8,123),(0xc,256),(0x2c,42),(0x30,12)]
    strings=[(0x10,applicant.name),(0x34,applicant.recommender)]
    assert native_payload(0xe8b3e0,strings,fields)==expected
    result.append(dict(name='FamilyApplyData',serializer='0xe8b3e0',bytes=len(expected)))
    header=[(0xc,0x5001400),(0x10,1)]
    raw=[(0x400,struct.pack('<II',0x5001600,0x5001600)),(0x600,struct.pack('<II',0x5001400,0x5001400))]
    assert native_payload(0xe8b5e0,[(o+0x608,s) for o,s in strings],
        header+[(0x608,0x2282304)]+[(o+0x608,v) for o,v in fields],raw)==p.family_applications((applicant,))
    result.append(dict(name='SAddFamilyApply-one',type=hex(p.ADD_FAMILY_APPLICATIONS),serializer='0xe8b5e0',bytes=len(expected)+1))
    assert native_payload(0xe6a980,scalars=header+[(0x608,123),(0x60c,256)],raw=raw)==p.removed_family_applications((applicant.role_id,))
    result.append(dict(name='SRemoveFamilyApply-one',type=hex(p.REMOVE_FAMILY_APPLICATIONS),serializer='0xe6a980',bytes=9))
    from native_inspect import DATA
    assert native_position(0x1496ec0,(0,1,2))==2
    assert native_position(0x1496f20,(2,0,1))==2
    assert native_position(0x1496ec0,(0,1)) is None
    assert native_position(0x1496f20,()) is None
    assert "image:Fuzuzhang" in DATA[0x22b33c8-0x400000:0x22b33c8-0x400000+128].decode('utf-16le')
    assert "image:Zuzhang" in DATA[0x228a148-0x400000:0x228a148-0x400000+128].decode('utf-16le')
    report={'passed':result,'scope':'wire layouts only; raw enum/NPC-context semantics not bound',
            'family_view':'name/level/funds/founder/purpose plus popularity pair and construction pair traced to original UI; identity/course vector retain defaults; source family management projection wired, GUI pending',
            'family_roster':'position +3c -> cached +34; level +38 -> cached +30 -> original level formatter; prestige pair +30/+34 -> cached +28/+2c -> column 2; offline text +40 -> cached +38 -> column 3, empty=online; metadata/spending semantics unbound; source management roster wired, GUI pending',
            'original_roster_lookup_passed':['leader 2 from cached roster','deputy 1 from cached roster','missing leader returns null','empty roster returns null'],
            'live_client_verified':False,'image_sha256':hashlib.sha256(DATA).hexdigest()}
    write_json(OUT/'evidence/faction-native-verification.json',report)
    print(json.dumps(report))


if __name__=='__main__':main()
