"""Original 1.6.1 player appearance/screen/movement codecs, fully offline."""
import json
import struct
from pathlib import Path
from contextlib import redirect_stdout
from native_inspect import disasm,u32,BASE,DATA
from verify_world_entities_native import probe
from world_role_protocol import (RoleBasic,role_basic_octets,role_basic,role_screen,
                                 remove_role_screen,role_move,role_stop)

OUT=Path(__file__).parent/'evidence'


def original_handler_projection(shape,packed):
    from verify_world_intro_black_native import Replay
    from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX
    class ProjectionReplay(Replay):
        def __init__(self):
            super().__init__()
            self.ctor,self.copy=u32(0x2244450),u32(0x22444b4)
            for address in (self.ctor,self.copy):
                page=address&~4095
                if not any(begin<=page<=end for begin,end,perms in self.e.mem_regions()):
                    self.e.mem_map(page,4096)
        def hook(self,e,a,size,user):
            sp=e.reg_read(UC_X86_REG_ESP)
            if self.imports.get(a)=='string':
                dst=e.reg_read(UC_X86_REG_ECX);src=self.r(sp+4);units=[]
                while self.r16(src):units.append(self.r16(src));src+=2
                raw=struct.pack('<'+'H'*len(units),*units)
                e.mem_write(dst,bytes(28));self.w(dst+20,len(units));self.w(dst+24,7)
                assert len(units)<=7
                e.mem_write(dst+4,raw+b'\0\0');self.ret(4,dst)
            elif a==self.ctor:
                dst=e.reg_read(UC_X86_REG_ECX)
                e.mem_write(dst,bytes(28));self.w(dst+24,7);self.ret(value=dst)
            elif a==self.copy:
                dst=e.reg_read(UC_X86_REG_ECX);src=self.r(sp+4)
                n=self.r(src+20);p=src+4 if self.r(src+24)<8 else self.r(src+4)
                raw=bytes(e.mem_read(p,n*2))
                assert n<=7
                e.mem_write(dst,bytes(28));self.w(dst+20,n);self.w(dst+24,7)
                e.mem_write(dst+4,raw+b'\0\0');self.ret(4,dst)
            else:super().hook(e,a,size,user)
    r=ProjectionReplay();inner,outer=0x5010000,0x5011000
    role=RoleBasic(123456,'侠客',shape,1680,5311,packed)
    for off,raw in inner_fields(role).items():r.e.mem_write(inner+off,raw)
    r.w(inner+0x28,7)
    for at,marker in ((inner+0x34,0x15),(inner+0x40,0x19)):
        head=at+0x1000;r.w(at+4,head,0);r.w(head,head,head,head);r.e.mem_write(head+marker,b'\1')
    r.w(outer+0xc,0x2278e54)
    r.e.mem_write(outer+0x10,struct.pack('<hhB',role.x,role.y,0))
    r.w(outer+0x1c,0x5013000,0);r.w(0x5013000,0x5013000,0x5013000)
    r.run(0x11dd8a0,r.scene,outer,inner,end=0x11da180)
    sp=r.e.reg_read(UC_X86_REG_ESP);info=r.r(sp+4)
    assert r.r(info)==role.role_id
    assert r.r(info+0x48)==10+(packed&15)
    assert (r.r(info+0x4c),r.r(info+0x50))==(1680,5311)
    assert r.r(info+0x54)==packed>>4
    expected=1010100+shape if shape<=10 else 2010100+shape%100 if shape<300 else shape
    assert r.r(info+0x88)==expected
    return {'original_handler':'0x11dd8a0','captured_create_player_call':'0x11da180',
            'shape_input':shape,'model_output':expected,'packed_2c':packed,
            'RoleInfo_48':r.r(info+0x48),'RoleInfo_54':r.r(info+0x54),
            'position':[r.r(info+0x4c),r.r(info+0x50)],
            'scope':'original handler executed until player create call; engine creation not executed'}


def remote_move_dispatch():
    from verify_world_intro_black_native import Replay
    from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX
    class MoveReplay(Replay):
        def hook(self,e,a,size,user):
            sp=e.reg_read(UC_X86_REG_ESP)
            if a==0x11d5330:
                assert self.r(sp+4)==123456 and self.r(sp+8)==0
                self.ret(8,0x5011000)
            elif a==0x500f080:
                self.calls.append({'this':e.reg_read(UC_X86_REG_ECX),
                    'x':struct.unpack('<i',e.mem_read(sp+4,4))[0],
                    'y':struct.unpack('<i',e.mem_read(sp+8,4))[0]})
                self.ret(8)
            else:super().hook(e,a,size,user)
    r=MoveReplay();r.w(0x294454c,0x5012000)
    r.w(r.packet+8,123456,0);r.e.mem_write(r.packet+0x14,struct.pack('<hh',-123,5311))
    r.w(0x5011000,0x5013000);r.w(0x5013000+0xb0,0x500f080)
    r.run(0x11d7fc0,r.packet,0,0)
    assert r.calls==[{'this':0x5011000,'x':-123,'y':5311}],r.calls
    before=bytes(r.e.mem_read(0x5011000,0x300));r.calls.clear()
    r.run(0x11c56c0,r.packet,0,0)
    assert not r.calls and before==bytes(r.e.mem_read(0x5011000,0x300))
    return {'original_SRoleMove_Process':'0x11d7fc0','remote_virtual_b0_arguments':[-123,5311],
            'original_SRoleStop_Process':'0x11c56c0','stop_no_calls_or_object_writes':True,
            'scope':'original remote dispatch; move method boundary captured, movement simulation not executed'}


def inner_fields(role):
    raw=role.name.encode('utf-16le')
    assert len(raw)<=14
    return {8:struct.pack('<q',role.role_id),0x14:raw+b'\0\0',
            0x24:struct.pack('<I',len(raw)//2),0x2c:bytes([role.packed_2c]),
            0x30:struct.pack('<i',role.shape),0x4c:bytes([role.field_4c])}


def main():
    results=[]
    role=RoleBasic(0x123456789,'同屏侠客',9,1680,5311,0x31,2,1)
    payload,decoded=probe(0xfad590,0xfad940,0xfae280,fields=inner_fields(role))
    assert payload==role_basic_octets(role)
    for off in (8,0x2c,0x30,0x4c):
        value=inner_fields(role)[off];assert decoded[off:off+len(value)]==value
    results.append({'class':'RoleBasicOctets','native_encode_decode':True,'hex':payload.hex()})
    rich=RoleBasic(42,'甲',9,1,2,0x71,properties=((1,1010109),(7,-3)),
                   octets_properties=((1,b'\x01\x02'),(17,b'opaque')))
    payload,decoded=probe(0xfad590,0xfad940,0xfae280,payload=role_basic_octets(rich))
    assert struct.unpack_from('<I',decoded,0x3c)[0]==2
    assert struct.unpack_from('<I',decoded,0x48)[0]==2
    results.append({'class':'RoleBasicOctets-both-maps','native_decoder':True,
                    'native_serializer':False,'hex':payload.hex()})
    blob=role_basic_octets(role);obj=0x5001000
    fields={8:struct.pack('<I',obj+0x440),0x434:struct.pack('<III',len(blob),len(blob),1),
            0x440:blob,0x10:struct.pack('<hh',role.x,role.y),0x14:bytes([role.screen_flag])}
    payload,decoded=probe(0xfc6bf0,0xfc6d30,0xfc6c80,fields=fields)
    assert payload==role_basic(role)
    assert decoded[0x10:0x15]==struct.pack('<hhB',role.x,role.y,role.screen_flag)
    results.append({'class':'RoleBasic-outer','native_encode_decode':True,'hex':payload.hex()})
    head,node,raw,pathhead=0x5001400,0x5001440,0x5001580,0x5001600
    screen_fields={0xc:struct.pack('<II',head,1),0x400:struct.pack('<II',node,node),
        0x440:struct.pack('<II',head,head),0x448:struct.pack('<III',0x228683c,0x224c100,raw),
        0x454:struct.pack('<IhhB',0x2278e54,role.x,role.y,role.screen_flag),
        0x464:struct.pack('<II',pathhead,0),0x574:struct.pack('<III',len(blob),len(blob),1),
        0x580:blob,0x600:struct.pack('<II',pathhead,pathhead)}
    payload,decoded=probe(0xfc5f40,0xfc68f0,0xfc69a0,fields=screen_fields)
    assert payload==role_screen((role,)),payload.hex()
    assert struct.unpack_from('<I',decoded,0x10)[0]==1
    results.append({'class':'SAddUserScreen-one-real-role','native_encode_decode':True,'hex':payload.hex()})
    pathrole=RoleBasic(42,'甲',9,-1,2,0x71,path=((1,2),(3,-4)))
    payload,decoded=probe(0xfc6bf0,0xfc6d30,0xfc6c80,payload=role_basic(pathrole))
    assert struct.unpack_from('<I',decoded,0x20)[0]==2
    results.append({'class':'RoleBasic-two-path-nodes','native_decoder':True,'native_serializer':False})
    payload,decoded=probe(0xe6e9e0,0xe6ea90,0xe6eb20,fields={
        0xc:struct.pack('<II',head,1),0x400:struct.pack('<II',node,node),
        0x440:struct.pack('<IIq',head,head,role.role_id)})
    assert payload==remove_role_screen((role.role_id,))
    results.append({'class':'SRemoveUserScreen-one-role','native_encode_decode':True,'hex':payload.hex()})
    for cls,ctor,mar,dec,encode in (
        ('SRoleMove',0xdacd10,0xe50d90,0xdacdc0,role_move),
        ('SRoleStop',0xdad130,0xe50e60,0xdad1e0,role_stop)):
        for x,y in ((1680,5311),(-123,32767)):
            payload,decoded=probe(ctor,mar,dec,fields={8:struct.pack('<q',role.role_id),
                                                    0x14:struct.pack('<hh',x,y)})
            assert payload==encode(role.role_id,x,y)
            assert decoded[0x14:0x18]==struct.pack('<hh',x,y)
            results.append({'class':cls,'native_encode_decode':True,'x':x,'y':y,'hex':payload.hex()})
    results += [original_handler_projection(9,0x71),original_handler_projection(10,0x32)]
    results.append(remote_move_dispatch())
    (OUT/'world-role-native.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    with (OUT/'world-role-native-disassembly.txt').open('w',encoding='utf-8') as stream:
        with redirect_stdout(stream):
            for address,size in ((0xfad590,183),(0xfad940,437),(0xfae280,496),
                (0xfc6bf0,142),(0xfc6d30,206),(0xfc6c80,169),(0x11dd901,122),
                (0x11de719,40),(0x11da214,80),(0x11d8147,14),(0x11c56c0,3)):
                print('\n',hex(address));disasm(address,size)
    print(json.dumps({'passed':len(results),'results':results},indent=2))


if __name__=='__main__':main()
