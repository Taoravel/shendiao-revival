"""The original carried soul orb has four data fields, not six worn fields."""
from dataclasses import replace
import struct
from pet_souls import SoulBean
from pet_soul_item_data import OrbTips,encode_tips,decode_tips,display_tips_from_worn,bag_marker,carried_tip_reply
from native_gameplay_probe import probe
from research_pet_soul_item_data import native_marker


def main():
    tips=OrbTips(61,10001,-205,204)
    expected=bytes.fromhex('0000003d00002711ffffff33000000cc')
    assert encode_tips(tips)==expected and decode_tips(expected)==tips
    original,raw=probe(0xd98f90,0xe4dc30,0xd994a0,{4:struct.pack('<4i',61,10001,-205,204)})
    assert original==expected and struct.unpack_from('<4i',raw,4)==(61,10001,-205,204)
    bean=SoulBean(31277,120,10002,204,205,2)
    projected,marker=display_tips_from_worn(bean)
    assert projected==OrbTips(120,10002,205,204) and marker==1
    assert encode_tips(projected)==bytes.fromhex('0000007800002712000000cd000000cc')
    kind,reply=carried_tip_reply(333,projected)
    assert kind==0xc03fe and reply.hex()=='000000010000014d100000007800002712000000cd000000cc'
    obj=0x5001000;detail=encode_tips(projected)
    full,_=probe(0xd9c110,0xe4e5c0,0xe0a240,{8:struct.pack('<ii',1,333),
        16:struct.pack('<II',0x224c100,obj+0x200),0x1f4:struct.pack('<III',16,16,1),0x200:detail})
    assert full==reply
    assert bean.raw6==2 and bean.raw4==204 and bean.raw5==205
    for flags,expected_bag,expected_worn in ((0,0,0),(1,1,1),(2,0,1),(160,0,1),(161,1,1)):
        assert bag_marker(flags)==expected_bag
        assert display_tips_from_worn(replace(bean,raw6=flags))[1]==expected_worn
    assert display_tips_from_worn(replace(bean,raw6=1))==display_tips_from_worn(bean)
    for value,bag,worn in ((0,0,0),(1,1,1),(2,0,1),(160,0,1),(161,1,1),(-1,1,1),(-2,0,1),(-2147483648,0,1)):
        assert native_marker('bag',value)==bag_marker(value&0xffffffff)==bag
        assert native_marker('worn',value)==display_tips_from_worn(replace(bean,raw6=value))[1]==worn
    # Display projection is deliberately lossy and provides no inverse factory:
    # neither marker1 nor four tips fields proves the exact original raw6.
    for bad in (expected[:-1],expected+b'\0',struct.pack('>6i',31277,120,10002,204,205,2)):
        try:decode_tips(bad)
        except ValueError:pass
        else:raise AssertionError('Wrong-size or six-field carried orb accepted')
    for action in (lambda:OrbTips(True,0,0,0),lambda:OrbTips(-1,0,0,0),lambda:bag_marker(True),
            lambda:carried_tip_reply(True,tips),lambda:carried_tip_reply(0,tips)):
        try:action()
        except ValueError:pass
        else:raise AssertionError('Invalid known soul orb data accepted')
    try:probe(0xd98f90,0xe4dc30,0xd994a0,payload=expected[:-1])
    except ValueError:pass
    else:raise AssertionError('Original four-field decoder accepted truncation')
    print('PASS original16-byte orb codec and complete SItemTips,16 original parser/converter fixtures, signed3/4 fields, worn cross-order mapping, '
        'bag bit0 vs worn nonzero display markers; six-field misuse/invalid/truncation refuses; exact raw6 preserved')


if __name__=='__main__':main()
