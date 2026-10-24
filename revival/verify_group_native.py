"""Differential group codecs against original x86 serializers, nested beans too."""
import json
import hashlib
import struct
from verify_social_native import native_payload
from inspect_client import OUT, write_json
import group_protocol as p


def main():
    g=dict(id=567,owner=123,name='江湖群',notice='群公告',managers=[321],
           members=[dict(id=123,name='侠客',level=28)],allow_join=1,flash=0,owner_name='侠客')
    cases=[
      ('CCreatCommonGroup',0xd76170,b'',[],[],[]),
      ('SCreateCommonGroupResponse',0xd7b9f0,b'',[],[],[]),
      ('CSendCommonGroupName',0xe479c0,p.text(g['name']),[(8,g['name'])],[],[]),
      ('SCreatCommonGroup',0xe483a0,p.created(567,g['name']),[(0x10,g['name'])],[(8,567)],[]),
      ('CSearchCommonGroup',0xe47720,p.text(g['name'])+struct.pack('>Qi',567,1),[(8,g['name'])],[(0x28,567),(0x30,1)],[]),
      ('SSearchCommonGroup',0xe490f0,p.searched(g),[(0x10,g['name']),(0x2c,g['notice']),(0x4c,'侠客')],[(8,567),(0x48,1)],[]),
      ('CRequestJoinGroup',0xe47520,struct.pack('>Q',567),[],[(8,567)],[]),
      ('CResponseJoinGroup',0xe47560,struct.pack('>iQQ',0,123,567),[],[(8,0),(0x10,123),(0x18,567)],[]),
      ('SRequestJoinGroup',0xe48c50,p.join_notice(123,567,'侠客'),[(0x18,'侠客')],[(8,123),(0x10,567)],[]),
      ('CLeaveCommonGroup',0xe47030,struct.pack('>Q',567),[],[(8,567)],[]),
      ('SLeaveCommonGroup',0xe487b0,struct.pack('>Q',567),[],[(8,567)],[]),
      ('CSendMessageToCommonGroup',0xed7ec0,p.text('你好')+p.text('正文')+struct.pack('>Q',567)+b'\0',[(8,'你好'),(0x24,'正文')],[(0x40,567)],[]),
      ('SSendMessageToCommonGroup',0xee6270,p.message(567,'侠客','你好','2026-10-23 12:34:56'),[(8,'你好'),(0x24,'侠客'),(0x40,'2026-10-23 12:34:56')],[(0x60,567)],[]),
      ('CommonGroupMemberInfo',0xeda2e0,p.member(g['members'][0],True),[(0x10,'侠客')],[(8,123),(0x2c,28),(0x30,1)],[]),
      ('CInviteToCommonGroup',0xe46fd0,struct.pack('>QQ',123,567),[],[(8,123),(0x10,567)],[]),
      ('CInviteToCommonGroupReply',0xe47000,struct.pack('>iQ',1,567),[],[(8,1),(0x10,567)],[]),
      ('SInvitedToCommonGroup',0xe485f0,p.invited(567,'侠客',g['name']),[(0x10,'侠客'),(0x2c,g['name'])],[(8,567)],[]),
      ('SInviteToCommonGroupResp',0xe485d0,struct.pack('>Q',123),[],[(8,123)],[]),
      ('CExpelCommonGroupMember',0xe46f20,struct.pack('>QQ',123,567),[],[(8,123),(0x10,567)],[]),
      ('CAppointOrCancelManager',0xe468b0,struct.pack('>QQQ',1,567,123),[],[(8,1),(0x10,567),(0x18,123)],[]),
      ('CChangeCommonGroupConfig',0xe46bc0,struct.pack('>Qii',567,1,0)+p.text(g['notice'])+p.text('正文')+struct.pack('>i',1),
       [(0x18,g['notice']),(0x34,'正文')],[(8,567),(0x10,1),(0x14,0),(0x50,1)],[]),
      ('SChangeCommonGroupConfig',0xe48200,p.configured(g),[(0x14,g['notice'])],[(8,567),(0x10,0),(0x30,1)],[]),
      ('CQueryGroupMsgHistory',0xe47050,struct.pack('>Qi',567,-1),[],[(8,567),(0x10,0xffffffff)],[]),
    ]
    row=dict(plain='历史正文',name='侠客',timestamp='2026-10-23 12:34:56')
    cases.append(('HistoryGroupMsg',0xee1980,p.history_entry(row,True),
      [(4,row['plain']),(0x20,row['name']),(0x3c,row['timestamp'])],[],[(0x58,b'\x01')]))
    cases.append(('SQueryGroupMsgHistory-nonempty',0xee15d0,p.history_page(1,True,[row]),
      [(0x804,row['plain']),(0x820,row['name']),(0x83c,row['timestamp'])],
      [(8,1),(0x14,0x5001800),(0x18,0x500187c),(0x1c,0x500187c),(0x800,0x2283b70)],
      [(0xc,b'\x01'),(0x858,b'\x01')]))
    # Real native vector traversal. Children carry their original bean vtables;
    # scalar fields use distinct IDs to detect accidental owner/group swapping.
    strings=[(0x18,g['name']),(0x54,g['notice']),(0x510,'侠客')]
    fields=[(8,123),(0x10,567),(0x70,0),(0x74,1),
      (0x38,0x5001400),(0x3c,0x5001408),(0x40,0x5001408),(0x400,321),
      (0x48,0x5001500),(0x4c,0x5001538),(0x50,0x5001538),
      (0x500,0x22839bc),(0x508,123),(0x52c,28),(0x530,1)]
    cases.append(('CommonGroupInfo-nonempty',0xeda410,p.info(g,{123}),strings,fields,[]))
    # Wrapper embeds a bean at +10. Outer identity is independent of inner bean.
    cases.append(('SUpdateCommonGroupInfo-nonempty',0xee88a0,p.updated(g,{123}),
      [(o+0x10,s) for o,s in strings],[(8,567),(0x10,0x2283994)]+[(o+0x10,v+0x10 if o in (0x38,0x3c,0x40,0x48,0x4c,0x50) else v) for o,v in fields],[]))
    # Init contains one contiguous 0x78-byte bean.
    init_fields=[(0xc,0x5001800),(0x10,0x5001878),(0x14,0x5001878),(0x800,0x2283994)]
    init_fields += [(o+0x800,v+0x800 if o in (0x38,0x3c,0x40,0x48,0x4c,0x50) else v) for o,v in fields]
    cases.append(('SCommonGroupInfoInit-nonempty',0xedb560,p.initial([g],{123}),[(o+0x800,s) for o,s in strings],init_fields,[]))
    passed=[]
    for name,address,expected,strings,scalars,raw in cases:
        actual=native_payload(address,strings,scalars,raw)
        assert actual==expected,(name,actual.hex(),expected.hex())
        passed.append(dict(name=name,serializer=hex(address),bytes=len(actual)))
    from native_inspect import DATA
    result=dict(passed=passed,image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False)
    write_json(OUT/'evidence/group-native-verification.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
