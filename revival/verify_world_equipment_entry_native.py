"""Original entry decoder must receive the current equipment projection."""
from dataclasses import replace
import struct
from equipment_condition import EquipmentCondition
from equipment_detail import EquipmentDetail
from inventory import InventorySnapshot,ItemState
from inspect_client import OUT,write_json
from item_effects import VitalState
from native_gameplay_probe import probe
from role_attributes import AttributeBaseline,derive_attributes,load_attribute_rules
from role_attribute_storage import RoleAttributeSnapshot
from role_equipment import EquipmentAttributeBasis,load_equipment_attribute_rules,project_equipment
from role_growth import GrowthState
from world_protocol import world_snapshot


def main():
    attributes=load_attribute_rules()
    rules=load_equipment_attribute_rules()
    role_id=2**40
    growth=GrowthState(role_id,2,61,1,0,None,(1,1,1,1,1),(0,0,0,0,0),5,1,attributes.growth_policy)
    baseline=AttributeBaseline(role_id,1,0,(10,10,10,10,10),(100,100,20,5,40,20,10,20,5))
    naked=RoleAttributeSnapshot(derive_attributes(baseline,growth,attributes),VitalState(role_id,3,80,110,46,106))
    basis=EquipmentAttributeBasis(role_id,9,0,rules.revision,0,'verified-creation-basis')
    weapon=ItemState(8,role_id,49009,1,-1,0,1,None,EquipmentCondition(0,100,100,1),
                     EquipmentDetail(1,1,0,((81,25),(811,15),(1231,8))))
    inventory=InventorySnapshot(role_id,7,(weapon,),(),40,8)
    equipped=project_equipment(naked,inventory,basis,rules)
    broken=project_equipment(naked,replace(inventory,items=(replace(weapon,
        condition=replace(weapon.condition,current=0)),)),basis,rules)
    role=dict(id=role_id,name='装备入场',level=2,school=111,shape=1010109,experience=61)
    results=[]
    for label,snapshot,expected in (('equipped',equipped,(49,38,8)),
                                    ('broken',broken,(24,23,0)),('legacy_plain',naked,(0,0,0))):
        body=world_snapshot(role,snapshot,intro_discriminator=1)
        _,decoded=probe(0xfe4160,0xfe45f0,0xfe4630,payload=body)
        actual=tuple(struct.unpack_from('<i',decoded,offset)[0] for offset in (0x70,0x80,0x88))
        assert actual == expected, (label,actual,expected)
        assert struct.unpack_from('<5i',decoded,0x50) == (80,110,110,46,106)
        assert struct.unpack_from('<Q',decoded,0xf8)[0] == 61
        assert struct.unpack_from('<Q',decoded,0x48)[0] == 1
        results.append(dict(case=label,native_attack_magic_sealing=actual,
                            native_vitals=(80,110,110,46,106),experience=61,intro=1))
    _,full=probe(0xfe4160,0xfe45f0,0xfe4630,payload=world_snapshot(
        role,equipped,growth_snapshot=growth,intro_discriminator=1))
    assert tuple(struct.unpack_from('<i',full,offset)[0] for offset in (0x70,0x80,0x88))==(49,38,8)
    assert struct.unpack_from('<5h',full,0xd4)==(11,11,11,11,11)
    assert struct.unpack_from('<i',full,0xe0)[0]==5
    results.append(dict(case='equipped_with_current_growth',native_attack_magic_sealing=(49,38,8),
                        native_five_stats=(11,11,11,11,11),potential=5))
    write_json(OUT/'evidence/world-equipment-entry-native.json',dict(cases=results,
        source='current immutable equipment projection; original SEnterWorld decoder',
        production_runtime_projection_tested=False,gui_verified=False,live_server_changed=False))
    print(results)


if __name__ == '__main__':
    main()
