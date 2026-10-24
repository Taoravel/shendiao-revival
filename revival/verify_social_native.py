"""Execute original x86 social serializers with host allocation/CRT adapters.

No network codec is replaced. These are layout checks, not UI acceptance.
"""
import json
import struct
import sys
sys.path.insert(0, 'D:/Downloads/LCJDTClient/LCJDTClient/revival/.deps')
from native_inspect import DATA, BASE, u32
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX


def native_payload(address, strings=(), scalars=(), raw=(), maps=()):
    emu = Uc(UC_ARCH_X86, UC_MODE_32)
    emu.mem_map(0, 0x1000)
    emu.mem_map(BASE, (len(DATA)+4095)&~4095)
    emu.mem_write(BASE, DATA)
    emu.mem_map(0x5000000, 0x800000)
    obj, stream, buf, stack, stop = 0x5001000, 0x5002000, 0x5003000, 0x5100000, 0x500f000
    def w(a, *v): emu.mem_write(a, struct.pack('<'+'I'*len(v), *v))
    def r(a): return struct.unpack('<I', emu.mem_read(a, 4))[0]
    w(stream, 0x224c100, buf, 0)
    w(buf-12, 0x7000, 0, 1)
    heap = [0x5200000]
    for offset in maps:
        head = heap[0]; heap[0] += 64
        w(head, head, head, head)
        emu.mem_write(head+0x21, b'\x01')
        w(obj+offset+4, head)
    for offset, value in strings:
        data = value.encode('utf-16-le')
        ptr = heap[0]; heap[0] += (len(data)+31)&~15
        emu.mem_write(ptr, data+b'\0\0')
        w(obj+offset+4, ptr); w(obj+offset+20, len(data)//2, max(8, len(data)//2))
    for offset, value in scalars: w(obj+offset, value)
    for offset, value in raw: emu.mem_write(obj+offset, value)
    imports = {u32(x): k for x, k in ((0x2244890, 'alloc'), (0x2244894, 'free'),
               (0x2244354, 'decrement'), (0x2244334, 'increment'))}
    imports[0x1919178] = 'alloc'
    for page in {a&~4095 for a in imports if not BASE <= a < BASE+len(DATA)}:
        emu.mem_map(page, 4096)
    def ret(count=0, value=None):
        sp = emu.reg_read(UC_X86_REG_ESP)
        emu.reg_write(UC_X86_REG_EIP, r(sp)); emu.reg_write(UC_X86_REG_ESP, sp+4+count)
        if value is not None: emu.reg_write(UC_X86_REG_EAX, value)
    def hook(uc, a, size, user):
        sp = uc.reg_read(UC_X86_REG_ESP)
        if a == stop: uc.emu_stop(); return
        k = imports.get(a)
        if k == 'alloc':
            ptr = heap[0]; heap[0] += (r(sp+4)+15)&~15; ret(value=ptr)
        elif k == 'free': ret()
        elif k in ('decrement', 'increment'):
            ptr = r(sp+4); v = (r(ptr)+(-1 if k == 'decrement' else 1))&0xffffffff
            w(ptr, v); ret(4, v)
        elif a == 0x19191c2:
            dst, src, n = r(sp+4), r(sp+8), r(sp+12)
            if n: uc.mem_write(dst, bytes(uc.mem_read(src, n)))
            ret(value=dst)
        elif a == 0x1919184: ret()
        elif a == 0x1919292: raise AssertionError('Native constraint failed')
    emu.hook_add(UC_HOOK_CODE, hook)
    w(stack, stop, stream)
    emu.reg_write(UC_X86_REG_ECX, obj); emu.reg_write(UC_X86_REG_ESP, stack)
    try: emu.emu_start(address, stop, count=800000)
    except Exception as e: raise RuntimeError(f'native at {emu.reg_read(UC_X86_REG_EIP):x}') from e
    assert emu.reg_read(UC_X86_REG_EIP) == stop
    return bytes(emu.mem_read(buf, r(buf-8)))


if __name__ == '__main__':
    import hashlib
    import social_protocol as p
    from inspect_client import OUT, write_json
    role = {'id': 123, 'name': '测试侠客', 'level': 18, 'school': 12, 'shape': 1010101}
    identity = [(8, 123)]
    profile_fields = identity+[(0x2c, 18), (0x30, 12), (0x34, 1010101)]
    cases = [
        ('FriendInfo', 0xedc7b0, p.friend_info(role, True),
         [(0x10,role['name']), (0x34,''), (0x54,'')], identity,
         [(0x50,struct.pack('<h',18)), (0x70,b'\x01')], ()),
        ('SAddFriend', 0xe47bb0, p.friend_added(role, True),
         [(0x10,role['name']), (0x30,''), (0x50,'')], identity,
         [(0x4c,struct.pack('<h',18)), (0x6c,b'\x01'), (0x75,b'\x01')], ()),
        ('SSearchFriend', 0xee5160, p.profile(role),
         [(0x10,role['name']), (0x38,''), (0x60,''), (0x7c,''), (0x98,'')], profile_fields, [], (0xbc,)),
        ('SSearchRole', 0xee56d0, p.profile(role,True),
         [(0x10,role['name']), (0x38,''), (0x54,''), (0x70,'')], profile_fields, [], (0x98,)),
        ('SSendMessageToRole', 0xee6790, p.private_message(role,'你好'),
         [(0x10,role['name']), (0x2c,'你好'), (0x48,''), (0x70,'')], identity, [], ()),
        ('SSendChatMsg', 0xf143c0, p.chat_message(role,5,'你好'),
         [(0x10,role['name']), (0x34,'你好')], identity+[(0x2c,18),(0x30,5)], [], ()),
        ('SFriendsInfoInit-empty', 0xedcb90, bytes(5), [], [], [], ()),
        ('SFriendsInfoInit-contact', 0xedcb90, b'\x01'+p.friend_info(role,True)+bytes(4),
         [(0x410,role['name']), (0x434,''), (0x454,'')],
         [(0xc,0x5001400),(0x10,0x5001480),(0x14,0x5001480),(0x400,0x2283a2c),(0x408,123)],
         [(0x450,struct.pack('<h',18)),(0x470,b'\x01')], ()),
        ('SFriendIsOnline', 0xe48580, struct.pack('>Qi',123,1), [], identity+[(0x10,1)], [], ()),
        ('SBreakOffRelation', 0xe48030, struct.pack('>Q',123), [], identity, [], ()),
        ('CSearchFriend', 0xe477f0, struct.pack('>Q',123), [], identity, [], ()),
        ('CSearchRole', 0xe47830, p.text('测试侠客')+bytes(12), [(8,'测试侠客')], [], [], ()),
        ('CAddFriend', 0xe467d0, struct.pack('>Q',123)+p.text(''), [(0x10,'')], identity, [], ()),
        ('CBreakOffRelation', 0xe46930, struct.pack('>Q',123)+p.text(''), [(0x10,'')], identity, [], ()),
        ('CSendChatMsg', 0xf127b0, struct.pack('>i',5)+p.text('你好')+p.text('')+b'\0',
         [(0xc,'你好'),(0x28,'')], [(8,5)], [], ()),
        ('CSendMessageToRole', 0xed8270, struct.pack('>Q',123)+p.text('你好')+p.text('')+bytes(5),
         [(0x10,'你好'),(0x2c,'')], identity, [], ()),
        ('CRequestAddFriend',0xe47410,p.text('你好')+struct.pack('>Q',123),[(8,'你好')],[(0x28,123)],[],()),
        ('SRequestAddFriend',0xe48a80,p.request_notice(role,'你好'),
         [(8,'你好'),(0x30,role['name']),(0x4c,'')],[(0x28,123),(0x68,18)],[],()),
        ('CAgreeAddedFriend',0xe46890,struct.pack('>Q',123),[],identity,[],()),
        ('CRefuseAddFriend',0xe47080,p.text('暂不添加')+struct.pack('>Q',123),[(8,'暂不添加')],[(0x28,123)],[],()),
        ('SRefuseAddFriend',0xe48830,p.refusal_notice(role,'暂不添加'),
         [(8,role['name']),(0x24,'暂不添加')],[(0x40,123)],[],()),
        ('CRoleMoveTeam',0xe475f0,p.text(p.GROUP_BLACK)+struct.pack('>Q',123)+p.text(''),
         [(8,p.GROUP_BLACK),(0x30,'')],[(0x28,123)],[],()),
        ('SRoleMoveTeam',0xe49030,p.moved_group(123,p.GROUP_BLACK),[(8,p.GROUP_BLACK)],[(0x28,123)],[],()),
        ('CBreakOffBlackRelation',0xe468f0,struct.pack('>Q',123),[],identity,[],()),
        ('SBreakOffBlackRelation',0xe47ff0,struct.pack('>Q',123),[],identity,[],()),
        ('CToTryAddFriend',0xe47af0,struct.pack('>Q',123)+p.text(''),[(0x10,'')],identity,[],()),
        ('SToTryAddFriend',0xe492e0,p.try_add_info(role),[(0x10,role['name'])],identity+[(0x2c,18)],[],()),
        ('FriendInfo-native-group',0xedc7b0,p.friend_info(role,True,p.GROUP_FRIEND),
         [(0x10,role['name']),(0x34,''),(0x54,p.GROUP_FRIEND)],identity,
         [(0x50,struct.pack('<h',18)),(0x70,b'\x01')],()),
        ('SAddFriend-native-group',0xe47bb0,p.friend_added(role,True,p.GROUP_BLACK),
         [(0x10,role['name']),(0x30,''),(0x50,p.GROUP_BLACK)],identity,
         [(0x4c,struct.pack('<h',18)),(0x6c,b'\x01'),(0x75,b'\x01')],()),
    ]
    results = []
    for name, address, expected, strings, scalars, raw, maps in cases:
        actual = native_payload(address, strings, scalars, raw, maps)
        assert actual == expected, (name, actual.hex(), expected.hex())
        results.append({'name':name,'native_serializer':hex(address),'bytes':len(actual)})
    result = {'image_sha256':hashlib.sha256(DATA).hexdigest(), 'passed':results,
              'channel_button_table':[u32(0x22be000+i*4) for i in range(8)],
              'real_client_social_verified':False}
    write_json(OUT/'evidence/social-native-verification.json',result)
    print(json.dumps(result))
