"""Known six-slot flat totals through public immutable projection and codecs."""
from dataclasses import replace
import struct
from equipment_condition import EquipmentCondition
from equipment_detail import DetailRules
from inventory import InventorySnapshot,ItemState
from inspect_client import OUT,write_json
from role_attributes import load_attribute_rules
from role_equipment import EquipmentAttributeBasis,project_equipment_totals,combine_equipment_resources,resource_caps_from_projection,project_equipment
from role_growth import GrowthState,load_growth_rules,plan_growth_credit
from role_resource_plan import RoleResources,load_resource_rules,plan_resource_caps
from role_attribute_protocol import growth_refresh,role_detail_profile,role_detail_equipment_fields
from verify_role_equipment import original_map
from role_attribute_storage import RoleAttributeSnapshot
from world_protocol import world_snapshot
from native_gameplay_probe import probe


def refused(call):
    try:call()
    except ValueError:return
    raise AssertionError('Unknown or ineligible ordinary equipment projection accepted')


def main():
    from role_equipment import load_ordinary_equipment_attribute_rules
    rules=load_ordinary_equipment_attribute_rules()
    attrs_rules=load_attribute_rules();role_id=9001
    from role_attributes import derive_attributes
    growth=GrowthState(role_id,1,0,1,0,None,(0,0,0,0,0),(0,0,0,0,0),0,0,load_growth_rules().revision)
    attrs=derive_attributes(attrs_rules.initial_profile.baseline(role_id),growth,attrs_rules)
    basis=EquipmentAttributeBasis(role_id,1,0,rules.revision,0,'explicit-clean-six-slot',seal_resistance=0)
    detail_rules=DetailRules.load()
    keys=(49001,42000,43000,44000,45000,46000)
    items=tuple(ItemState(slot+1,role_id,template,1,-slot-1,slot,1,None,
        EquipmentCondition(0,100,100,1),detail_rules.generate(template)) for slot,template in enumerate(keys))
    bare=InventorySnapshot(role_id,0,(),(),40,8)
    worn=replace(bare,inventory_revision=1,items=items)
    bare_totals=project_equipment_totals(attrs,bare,basis,rules)
    totals=project_equipment_totals(attrs,worn,basis,rules)
    a=totals.attributes
    assert (a.hp_max,a.mp_max,a.physical_attack,a.physical_defense,a.hit,a.dodge,a.speed,a.magic_attack,a.magic_defense,
        totals.seal_strength,totals.seal_resistance)==(120,110,45,55,60,30,14,35,15,8,6)
    resources_rules=load_resource_rules()
    before=RoleResources(3,70,40,resource_caps_from_projection(bare_totals),resources_rules.revision)
    equipped=plan_resource_caps(before,resource_caps_from_projection(totals),'equip',resources_rules).after
    final=combine_equipment_resources(totals,equipped)
    values=original_map(growth_refresh(growth,final)[1])
    assert len(values)==21 and {k:values[k] for k in (60,70,140,150,640,100,1240)}=={
        60:70,70:40,140:120,150:110,640:120,100:55,1240:6}
    detail=role_detail_profile(growth,final)
    assert detail.values[:5]==(70,120,120,40,110) and detail.values[15]==6
    assert role_detail_equipment_fields(role_id,final)==((8,45),(12,35),(14,8),(15,6))
    role=dict(id=role_id,name='六槽原值',level=1,school=11,shape=1010101,experience=0)
    _,native=probe(0xfe4160,0xfe45f0,0xfe4630,
        payload=world_snapshot(role,final,growth_snapshot=growth,intro_discriminator=1))
    assert struct.unpack_from('<5i',native,0x50)==(70,120,120,40,110)
    assert tuple(struct.unpack_from('<i',native,o)[0] for o in (0x70,0x74,0x80,0x84,0x88,0x8c))==(45,55,35,15,8,6)
    full=replace(equipped,hp=119,mp=109)
    unworn=project_equipment_totals(attrs,replace(bare,inventory_revision=2),basis,rules)
    clipped=plan_resource_caps(full,resource_caps_from_projection(unworn),'unequip',resources_rules).after
    assert (clipped.hp,clipped.mp,clipped.caps.hp_max,clipped.caps.mp_max)==(100,100,100,100)
    reworn=project_equipment_totals(attrs,replace(worn,inventory_revision=3),basis,rules)
    returned=plan_resource_caps(clipped,resource_caps_from_projection(reworn),'equip',resources_rules).after
    assert (returned.hp,returned.mp,returned.caps.hp_max,returned.caps.mp_max)==(100,100,120,110)
    grown=plan_growth_credit(growth,120,load_growth_rules()).after
    grown_attrs=derive_attributes(attrs_rules.initial_profile.baseline(role_id),grown,attrs_rules)
    grown_totals=project_equipment_totals(grown_attrs,worn,basis,rules)
    grown_resources=plan_resource_caps(equipped,resource_caps_from_projection(grown_totals),'ordinary_growth',resources_rules).after
    assert (grown_resources.hp,grown_resources.mp,grown_resources.caps.hp_max,grown_resources.caps.mp_max)==(80,46,130,116)
    explicit=project_equipment_totals(attrs,worn,replace(basis,seal_resistance=11),rules)
    assert explicit.seal_resistance==17
    assert rules.templates[49197].allowed_characters==(20,21)
    assert len(rules.templates)==973 and sum(t.suiting==0 for t in rules.templates.values())==761
    def one(template,slot):
        return replace(worn,items=(ItemState(50,role_id,template,1,-slot-1,slot,1,None,
            EquipmentCondition(0,100,100,1),detail_rules.generate(template)),))
    for action in (
        lambda:project_equipment_totals(attrs,bare,replace(basis,seal_resistance=None),rules),
        lambda:project_equipment_totals(attrs,one(42000,1),replace(basis,character_id=9),rules),
        lambda:project_equipment_totals(attrs,one(42002,1),basis,rules),
        lambda:project_equipment_totals(replace(attrs,level=10),one(49197,0),basis,rules),
        lambda:project_equipment_totals(replace(attrs,level=40),one(49031,3),basis,rules),
        lambda:project_equipment_totals(attrs,one(49192,3),basis,rules),
        lambda:project_equipment_totals(attrs,one(41109,0),basis,rules),
        lambda:project_equipment_totals(attrs,replace(worn,items=(replace(items[1],slot=-1),)),basis,rules),
        lambda:project_equipment_totals(attrs,replace(worn,items=(replace(items[1],detail=replace(items[1].detail,prefix_quality=2)),)),basis,rules),
        lambda:project_equipment_totals(attrs,replace(worn,items=(replace(items[1],detail=replace(items[1].detail,score=1)),)),basis,rules),
        lambda:project_equipment_totals(replace(attrs,hit=16777217),worn,basis,rules),
        lambda:project_equipment(RoleAttributeSnapshot(attrs,attrs_rules.initial_profile.vitals(role_id)),bare,basis,rules),
    ):refused(action)
    report=dict(passed=['actual original six-slot base properties produce120/110 caps,45/55/60/30/14/35/15 and sealing8/resistance6',
        'equipping preserves known70/40; original ordinary21map and original SEnterWorld decoder share full current totals including resistance index15',
        'unequip clips119/109 to100/100, rewear120/110 does not heal; same gear growth gives80/130HP46/116MP',
        'known resistance11 becomes17; missing is refused rather than default0',
        'original973 flat templates retain metadata;212 unresolved sets, percentage/empty, incompatible sex/role/level and advanced instances refuse',
        'real slot bookkeeping -slot-1 required; old mixed vital projection and inexact final native totals refuse'],
        scope='explicit v2 pure projection; no shared activation, database basis migration or GUI',
        native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/ordinary-equipment-projection-verification.json',report);print(report)


if __name__=='__main__':main()
