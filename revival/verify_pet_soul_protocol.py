"""Exact six-field souls and complete map refresh through original codecs."""
from dataclasses import replace
import struct
from pet_souls import SoulBean,SoulProfile,REVISION
from pet_soul_protocol import encode_bean,full_refresh,decode_remove
from native_gameplay_probe import probe


def original_map(profile):
    obj=0x5001000;head=obj+0x100;nodes=[obj+0x180+i*64 for i in range(len(profile.entries))]
    fields={8:struct.pack('<i',profile.pet_id),12:struct.pack('<III',0,head,len(nodes))}
    header=bytearray(48)
    struct.pack_into('<III',header,0,nodes[0] if nodes else head,nodes[0] if nodes else head,nodes[-1] if nodes else head)
    header[45]=1;fields[0x100]=bytes(header)
    for index,(slot,bean) in enumerate(profile.entries):
        values=(bean.item_id,bean.cumulative_exp,bean.soul_skill_id,bean.raw4,bean.raw5,bean.raw6)
        fields[0x180+64*index]=struct.pack('<IIIiI6iBB2x',head,head if index==0 else nodes[index-1],
            head if index==len(nodes)-1 else nodes[index+1],slot,0x227b308,*values,0,0)
    observed={}
    def observer(emu,target):
        read=lambda address:struct.unpack('<I',emu.mem_read(address,4))[0]
        assert read(target+8)==profile.pet_id and read(target+20)==len(profile.entries)
        sentinel=read(target+16)
        def visit(node):
            if node==sentinel:return
            visit(read(node))
            key=read(node+12);observed[key]=tuple(struct.unpack('<6i',emu.mem_read(node+20,24)))
            visit(read(node+8))
        visit(read(sentinel+4))
    body,_=probe(0xf9df90,0xf9e0b0,0xf9e140,fields,observer=observer)
    return body,observed


def main():
    bean=SoulBean(31276,61,10001,104,-105,106)
    body=encode_bean(bean)
    assert body==bytes.fromhex('00007a2c0000003d0000271100000068ffffff970000006a')
    encoded,raw=probe(0xdbf020,0xe40860,0xdbf150,{4:struct.pack('<6i',31276,61,10001,104,-105,106)})
    assert encoded==body and struct.unpack_from('<6i',raw,4)==(31276,61,10001,104,-105,106)
    profile=SoulProfile(9001,17,0,REVISION,'explicit-known-soul-map',
        ((1,bean),(5,SoulBean(31299,120,10002,-204,205,-206))))
    for current in (profile,replace(profile,entries=()),replace(profile,entries=tuple(
            (slot,replace(bean,item_id=31275+slot)) for slot in range(1,6)))):
        kind,payload=full_refresh(current)
        original,observed=original_map(current)
        assert kind==0xc0803 and payload==original
        assert observed=={slot:(b.item_id,b.cumulative_exp,b.soul_skill_id,b.raw4,b.raw5,b.raw6) for slot,b in current.entries}
    assert decode_remove(0xc0805,struct.pack('>ii',17,3))==(17,3)
    original,raw=probe(0xdbaf30,0xe53230,0xdbafe0,{8:struct.pack('<ii',17,3)})
    assert original==struct.pack('>ii',17,3) and struct.unpack_from('<ii',raw,8)==(17,3)
    for bad in (struct.pack('>ii',17,0),struct.pack('>ii',17,6),struct.pack('>ii',0,3),b''):
        try:decode_remove(0xc0805,bad)
        except ValueError:pass
        else:raise AssertionError('Unsafe native remove request accepted')
    try:probe(0xf9df90,0xf9e0b0,0xf9e140,payload=full_refresh(profile)[1][:-1])
    except ValueError:pass
    else:raise AssertionError('Original full soul decoder accepted truncation')
    print('PASS original6-field bean, signed raw values, empty/two/five-slot full map marshal+fresh decoder contents, '
        'c0805 request; no incremental create/delete, server asset or GUI claim')


if __name__=='__main__':main()
