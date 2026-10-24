"""Original ordinary-role map marshal/decoder with one explicit growth snapshot."""
from dataclasses import replace
import struct
from inspect_client import OUT,write_json
from item_effects import VitalState
from native_gameplay_probe import probe
from role_attributes import AttributeBaseline,derive_attributes,load_attribute_rules
from role_attribute_storage import RoleAttributeSnapshot
from role_growth import GrowthState
from role_attribute_protocol import encode_role_attributes,growth_refresh,role_detail_vitals,role_detail_profile


def main():
    rules=load_attribute_rules()
    role_id=2**40
    growth=GrowthState(role_id,2,61,1,0,None,(1,1,1,1,1),(0,0,5,0,0),0,1,rules.growth_policy)
    baseline=AttributeBaseline(role_id,1,0,(10,10,10,10,10),(100,100,20,5,40,20,10,20,5))
    attrs=derive_attributes(baseline,growth,rules)
    snapshot=RoleAttributeSnapshot(attrs,VitalState(role_id,1,80,110,46,106))
    kind,body=growth_refresh(growth,snapshot)
    assert kind==0xc32c8
    count=body[0]
    pairs=[struct.unpack_from('>if',body,1+i*8) for i in range(count)]
    values=dict(pairs)
    assert {key:values[key] for key in (490,500,60,70,140,150,640,80,110)}=={
        490:2,500:0,60:80,70:46,140:110,150:106,640:110,80:34,110:64}
    obj=0x5001000;head=obj+0x100;nodes=[obj+0x140+i*32 for i in range(count)]
    fields={8:struct.pack('<III',0,head,count),
            0x100:struct.pack('<IIIIIBB2x',nodes[0],nodes[0],nodes[-1],0,0,0,1)}
    for i,(key,value) in enumerate(pairs):
        fields[0x140+i*32]=struct.pack('<IIIifBB2x',head,head if i==0 else nodes[i-1],
            head if i==count-1 else nodes[i+1],key,value,0,0)
    original,raw=probe(0xec3590,0xec36b0,0xec3730,fields)
    assert original==body and struct.unpack_from('<I',raw,16)[0]==count
    assert role_detail_vitals(role_id,snapshot)==(80,110,110,46,106)
    entry=role_detail_profile(growth,snapshot)
    assert entry.values[:5]==(80,110,110,46,106)
    assert tuple(entry.values[index] for index in (7,8,9,10,11,12,13))==(64,34,8,11,22,27,12)
    assert entry.five_stats==(11,11,16,11,11) and entry.potential==0
    # Use asymmetric END/AGI here: the add-point REQUEST has the opposite
    # last-two order, whereas original RoleDetail must preserve keys40/50.
    from world_protocol import world_snapshot
    entry_growth=replace(growth,allocated_points=(1,2,3,4,5),free_points=7)
    entry_attrs=derive_attributes(baseline,entry_growth,rules)
    entry_snapshot=RoleAttributeSnapshot(entry_attrs,VitalState(role_id,4,90,120,58,118))
    role=dict(id=role_id,name='入场五维',level=2,school=11,shape=1010109,experience=61)
    _,entry_raw=probe(0xfe4160,0xfe45f0,0xfe4630,payload=world_snapshot(
        role,entry_snapshot,growth_snapshot=entry_growth,intro_discriminator=1))
    assert struct.unpack_from('<5h',entry_raw,0xd4)==(12,13,14,15,16)
    assert struct.unpack_from('<i',entry_raw,0xe0)[0]==7
    assert tuple(struct.unpack_from('<i',entry_raw,pos)[0] for pos in (0x70,0x80))==(30,30)
    assert struct.unpack_from('<5i',entry_raw,0x50)==(90,120,120,58,118)
    assert struct.unpack_from('<Q',entry_raw,0xf8)[0]==61
    for operation in (
        lambda:growth_refresh(replace(growth,revision=2),snapshot),
        lambda:role_detail_vitals(role_id+1,snapshot),
        lambda:encode_role_attributes(((60,16777217),)),
        lambda:encode_role_attributes(((490,True),)),
        lambda:encode_role_attributes(((9999,1),)),
        lambda:encode_role_attributes(((60,1),(60,2))),
        lambda:growth_refresh(growth,replace(snapshot,attributes=replace(attrs,five_stats=(11,11,16,32768,11)))),
        lambda:role_detail_profile(growth,replace(snapshot,attributes=replace(attrs,five_stats=(11,11,16,32768,11)))),
    ):
        try:operation()
        except ValueError:pass
        else:raise AssertionError('Invalid role growth display accepted')
    result={'passed':['19 ordinary role attributes match original x86 map serializer and decoder',
        'level490/potential500/current and maximum HP-MP/five stats/combat fields encoded',
        'known RoleDetail first five slots preserve actual wounds and maxima',
        'complete entry profile preserves asymmetric five stats, current potential and known combat slots',
        'production world encoder matches original decoder for asymmetric12/13/14/15/16 and potential7',
        'ordinary five stats beyond native entry signed16 refuse before growth display encoding',
        'stale growth, cross-role, unknown key, duplicate, bool and inexact float refused'],
        'type':hex(kind),'attributes':count,'native_level_handler_executed':False,
        'wound_limit':'designed equal to maxHP for explicit uninjured restoration profile',
        'live_characters_changed':False,'native_gui_tested':False}
    write_json(OUT/'evidence/role-growth-protocol-verification.json',result)
    print(result)


if __name__=='__main__':main()
