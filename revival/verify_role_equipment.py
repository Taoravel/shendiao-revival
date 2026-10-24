"""Equipment recomposition from the same immutable public snapshot inputs.

Pure behavior plus original ordinary-map codec. No storage, live characters,
client, socket, server, equipment transaction or battle is executed.
"""
from dataclasses import replace
import struct

from equipment_condition import EquipmentCondition
from equipment_detail import EquipmentDetail
from inventory import InventorySnapshot, ItemState
from inspect_client import OUT, write_json
from item_effects import VitalState
from native_gameplay_probe import probe
from role_attributes import AttributeBaseline,derive_attributes,load_attribute_rules
from role_attribute_storage import RoleAttributeSnapshot
from role_attribute_protocol import growth_refresh,role_detail_equipment_fields
from role_equipment import EquipmentAttributeBasis,load_equipment_attribute_rules,project_equipment
from role_growth import GrowthState


def refused(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Unsupported, stale or inexact equipment input accepted')


def original_map(body):
    count=body[0]
    pairs=[struct.unpack_from('>if',body,1+i*8) for i in range(count)]
    obj=0x5001000;head=obj+0x100;nodes=[obj+0x140+i*32 for i in range(count)]
    fields={8:struct.pack('<III',0,head,count),
            0x100:struct.pack('<IIIIIBB2x',nodes[0],nodes[0],nodes[-1],0,0,0,1)}
    for i,(key,value) in enumerate(pairs):
        fields[0x140+i*32]=struct.pack('<IIIifBB2x',head,head if i==0 else nodes[i-1],
            head if i==count-1 else nodes[i+1],key,value,0,0)
    encoded,raw=probe(0xec3590,0xec36b0,0xec3730,fields)
    assert encoded==body and struct.unpack_from('<I',raw,16)[0]==count
    return dict(pairs)


def main():
    growth_rules=load_attribute_rules()
    rules=load_equipment_attribute_rules()
    role_id=2**40
    growth=GrowthState(role_id,2,61,1,0,None,(1,1,1,1,1),(0,0,0,0,0),5,1,growth_rules.growth_policy)
    baseline=AttributeBaseline(role_id,1,0,(10,10,10,10,10),(100,100,20,5,40,20,10,20,5))
    attrs=derive_attributes(baseline,growth,growth_rules)
    bare=RoleAttributeSnapshot(attrs,VitalState(role_id,3,80,110,46,106))
    basis=EquipmentAttributeBasis(role_id,9,0,rules.revision,0,'explicit-test-creation-provenance')
    condition=EquipmentCondition(0,100,100,1)
    detail=EquipmentDetail(1,1,0,((81,25),(811,15),(1231,8)))
    weapon=ItemState(8,role_id,49009,1,-1,0,1,None,condition,detail)
    carried=replace(weapon,slot=0,equipment_slot=None)
    inventory=InventorySnapshot(role_id,7,(weapon,),(),40,8)
    from role_equipment import project_equipment_totals
    totals=project_equipment_totals(attrs,inventory,basis,rules)
    assert (totals.attributes.physical_attack,totals.attributes.magic_attack,totals.seal_strength)==(49,38,8)
    assert not hasattr(totals,'vitals')
    final=project_equipment(bare,inventory,basis,rules)
    assert (final.attributes.physical_attack,final.attributes.magic_attack,final.seal_strength)==(49,38,8)
    assert final.vitals is bare.vitals and (attrs.physical_attack,attrs.magic_attack)==(24,23)
    assert project_equipment(bare,inventory,basis,rules)==final
    from role_equipment import combine_equipment_resources,resource_caps_from_projection
    from role_resource_plan import RoleResources,load_resource_rules
    resources=RoleResources(12,9,6,resource_caps_from_projection(totals),load_resource_rules().revision)
    combined=combine_equipment_resources(totals,resources)
    assert (combined.vitals.hp,combined.vitals.mp,combined.vitals.version)==(9,6,12)
    assert original_map(growth_refresh(growth,combined)[1])[60]==9
    refused(lambda:combine_equipment_resources(totals,replace(resources,caps=replace(resources.caps,
        source=replace(resources.caps.source,inventory_revision=6)))))
    refused(lambda:combine_equipment_resources(totals,replace(resources,caps=replace(resources.caps,hp_max=200))))
    replacement=replace(weapon,id=9,template_id=49006)
    swapped=project_equipment(bare,replace(inventory,inventory_revision=8,items=(carried,replacement)),basis,rules)
    assert (swapped.attributes.physical_attack,swapped.attributes.magic_attack,swapped.seal_strength)==(49,38,8)
    naked=project_equipment(bare,replace(inventory,inventory_revision=9,items=(carried,)),basis,rules)
    broken=project_equipment(bare,replace(inventory,items=(replace(weapon,condition=replace(condition,current=0)),)),basis,rules)
    assert naked.attributes==broken.attributes==bare.attributes and naked.seal_strength==broken.seal_strength==0
    explicit=project_equipment(bare,inventory,replace(basis,seal_strength=11,source_id='known-legacy-basis'),rules)
    assert explicit.seal_strength==19
    kind,body=growth_refresh(growth,final)
    assert kind==0xc32c8
    values=original_map(body)
    assert len(values)==20 and {k:values[k] for k in (80,810,1230,60,70)}=={80:49,810:38,1230:8,60:80,70:46}
    assert role_detail_equipment_fields(role_id,final)==((8,49),(12,38),(14,8))
    assert role_detail_equipment_fields(role_id,bare)==()
    for operation in (
        lambda:project_equipment(final,inventory,basis,rules),
        lambda:project_equipment(bare,inventory,replace(basis,role_id=1),rules),
        lambda:project_equipment(bare,inventory,replace(basis,character_id=1),rules),
        lambda:project_equipment(bare,inventory,replace(basis,policy='unknown'),rules),
        lambda:project_equipment(bare,replace(inventory,inventory_revision=-1),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(weapon,weapon)),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(weapon,replacement)),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(replace(weapon,condition=None),)),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(replace(weapon,detail=None),)),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(replace(weapon,detail=replace(detail,identified=0)),)),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(replace(weapon,detail=replace(detail,base_properties=((81,26),(811,15),(1231,8)))),)),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(replace(weapon,quality=0),)),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(replace(weapon,template_id=40101),)),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(replace(weapon,equipment_slot=True),)),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(replace(weapon,template_id=49009.0),)),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(replace(weapon,slot=0),)),basis,rules),
        lambda:project_equipment(bare,replace(inventory,items=(replace(weapon,role_id=1),)),basis,rules),
        lambda:project_equipment(replace(bare,attributes=replace(attrs,physical_attack=2147483647)),inventory,basis,rules),
        lambda:project_equipment(replace(bare,attributes=replace(attrs,physical_attack=16777200)),inventory,basis,rules),
    ):
        refused(operation)
    result=dict(passed=[
        'original ten starter templates and numeric modifier families validated at startup',
        'naked24/23 plus one weapon25/15 gives absolute49/38 and explicit sealing0+8',
        'recompute/replacement does not double-add; unequip and zero durability remove the contribution',
        'explicit legacy sealing11 becomes19 without silently guessing a missing baseline',
        'current vitals80/110 and46/106 retain values and exact version object',
        'stats-only totals have no vitals; current resource9/6/version12 combines without heal and original codec reads9HP',
        'final profile refuses different resource caps or source inventory revision',
        '20 ordinary attributes match original x86 codec, entry indices8/12/14 share the same total',
        'foreign, duplicate, already projected, unknown/unsupported, overflow and float32 inexact inputs refuse'],
        policy_provenance='designed flat composition and explicit sealing baseline',
        storage_or_shared_runtime_tested=False,native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/role-equipment-verification.json',result)
    print(result)


if __name__=='__main__':
    main()
