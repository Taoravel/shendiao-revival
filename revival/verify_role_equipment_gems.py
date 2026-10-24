"""All ordinary worn gem effects join the actual six-slot base projection."""
from dataclasses import asdict,replace
import json
from inventory import InventorySnapshot,ItemState
from equipment_condition import EquipmentCondition
from equipment_gems import GemState
from equipment_gem_storage import EquipmentGemBasis
from equipment_gem_score import GemScoreBasis
from role_attributes import RoleAttributes
from role_equipment import EquipmentAttributeBasis
from role_equipment_gems import GemEquipmentRules,GemExtraBasis,GemEquipmentSource,project


def refused(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('Unknown, stale or inexact gem role projection accepted')


def source(rules,item,state,revision,plain_score=0):
    socket=EquipmentGemBasis(1111,revision,item,state,0,'socket_change',json.dumps(asdict(state)),
        (rules.gem_rules.detail_rules.revision,'explicit_known_clean_instance',json.dumps(asdict(item.detail))),
        ('2026-10-23.equipment-condition.2',json.dumps(asdict(item.condition))))
    return GemEquipmentSource(socket,GemScoreBasis(item.role_id,item.id,rules.score_rules.revision,plain_score,'known-gem-baseline:'+str(item.id)))


def main():
    rules=GemEquipmentRules.load();rid=9001
    attrs=RoleAttributes(rid,10,0,0,'2026-10-23.attributes.1',(10,10,10,10,10),100,100,20,10,50,10,10,20,10)
    basis=EquipmentAttributeBasis(rid,2,0,rules.revision,0,'explicit-complete-gem-role',seal_resistance=0)
    extra=GemExtraBasis(rid,0,rules.revision,basis.source_id,((350,0),(360,0),(370,0),(380,0),(1130,0),(1530,0)))
    templates=(40101,42002,43001,44002,45001,46001)
    stones=(35001,35001,35004,35005,35006,35007)
    items=[];sources=[]
    for slot,(template,stone) in enumerate(zip(templates,stones)):
        detail=replace(rules.gem_rules.detail_rules.generate(template),score=50)
        item=ItemState(slot+1,rid,template,1,-slot-1,slot,1,None,EquipmentCondition(0,100,100,1),detail)
        state=GemState(1,(stone,),rules.gem_rules.revision)
        items.append(item);sources.append(source(rules,item,state,7))
    inventory=InventorySnapshot(rid,7,tuple(items),(),40,8)
    result=project(rules,attrs,inventory,basis,extra,tuple(sources))
    a=result.core.attributes
    assert (a.hp_max,a.mp_max,a.physical_attack,a.physical_defense,a.hit,a.dodge,a.speed,a.magic_attack,a.magic_defense)==(
        215,130,124,118,140,50,21,100,59)
    assert (result.core.seal_strength,result.core.seal_resistance)==(30,30)
    assert result.extras==extra.values
    assert result.raw_modifiers==((81,24),(121,24),(131,5),(141,55),(821,14))
    assert result.core.inventory_revision==7 and result.core.equipment_policy==rules.revision
    # Original first-grade rows and numid links provide an independent literal
    # table for every family. Base totals are from the six original templates.
    expected_base={80:100,100:118,110:140,120:26,130:16,140:160,150:130,810:100,820:45,
        350:-2,360:1,370:2,380:4,1130:5,1530:6}
    known_extra=replace(extra,values=((350,-2),(360,1),(370,2),(380,4),(1130,5),(1530,6)))
    cases=((35000,0,110,40),(35001,0,80,12),(35002,3,100,16),(35003,0,810,12),
        (35004,2,820,14),(35005,3,140,55),(35006,4,130,5),(35007,0,120,24),
        (35008,2,380,3),(35009,2,370,3),(35010,2,350,3),(35011,2,360,3),
        (35012,2,1130,3),(35200,0,1530,5))
    names={80:'physical_attack',100:'physical_defense',110:'hit',120:'dodge',130:'speed',
        140:'hp_max',150:'mp_max',810:'magic_attack',820:'magic_defense'}
    for stone,slot,target,delta in cases:
        current=[];parts=[]
        for index,old in enumerate(items):
            state=GemState(1,(stone,) if index==slot else (),rules.gem_rules.revision)
            item=replace(old,detail=replace(old.detail,score=50 if index==slot else 0))
            current.append(item);parts.append(source(rules,item,state,7))
        actual=project(rules,attrs,replace(inventory,items=tuple(current)),basis,known_extra,tuple(parts))
        values={key:getattr(actual.core.attributes,name) for key,name in names.items()};values.update(actual.extras)
        expected=dict(expected_base);expected[target]+=delta
        assert values==expected,(stone,values,expected)
    # Broken equipment loses both canonical base and gem effects. Stored
    # source, score and gems survive; repair restores exactly one contribution.
    broken_items=list(items);broken_items[3]=replace(items[3],condition=replace(items[3].condition,current=0,version=1))
    broken_inventory=replace(inventory,inventory_revision=8,items=tuple(broken_items))
    broken_sources=tuple(source(rules,i,s.socket.state,8) for i,s in zip(broken_items,sources))
    broken=project(rules,attrs,broken_inventory,basis,extra,broken_sources)
    assert (broken.core.attributes.hp_max,broken.core.attributes.physical_defense)==(148,46)
    assert 141 not in dict(broken.raw_modifiers) and broken_sources[3].socket.state.templates==(35005,)
    repaired_items=list(broken_items);repaired_items[3]=replace(items[3],condition=replace(items[3].condition,version=2))
    repaired=project(rules,attrs,replace(inventory,inventory_revision=9,items=tuple(repaired_items)),basis,extra,
        tuple(source(rules,i,s.socket.state,9) for i,s in zip(repaired_items,sources)))
    assert repaired.core.attributes==result.core.attributes
    # Unequipped gemmed gear contributes nothing and needs no guessed active
    # source for its carried state; all still-worn sources remain mandatory.
    unworn_items=list(items);unworn_items[0]=replace(items[0],slot=0,equipment_slot=None)
    unworn=project(rules,attrs,replace(inventory,inventory_revision=10,items=tuple(unworn_items)),basis,extra,
        tuple(source(rules,i,s.socket.state,10) for i,s in zip(unworn_items[1:],sources[1:])))
    assert (unworn.core.attributes.physical_attack,unworn.core.attributes.magic_attack,unworn.core.seal_strength)==(32,20,0)
    for bad_sources in (tuple(sources[:-1]),tuple(sources)+tuple(sources[:1]),list(sources),
            (replace(sources[0],socket=replace(sources[0].socket,inventory_revision=6)),)+tuple(sources[1:]),
            (replace(sources[0],score_basis=replace(sources[0].score_basis,plain_score=1)),)+tuple(sources[1:])):
        refused(lambda:project(rules,attrs,inventory,basis,extra,bad_sources))
    for bad_extra in (None,replace(extra,source_ref='unknown'),replace(extra,equipment_basis_revision=1),replace(extra,policy='other')):
        refused(lambda:project(rules,attrs,inventory,basis,bad_extra,tuple(sources)))
    refused(lambda:project(rules,attrs,inventory,replace(basis,seal_resistance=None),extra,tuple(sources)))
    refused(lambda:replace(extra,values=extra.values[:-1]))
    refused(lambda:replace(extra,values=((350,True),)+extra.values[1:]))
    from role_equipment import project_equipment_totals,load_equipment_attribute_policies
    refused(lambda:project_equipment_totals(attrs,inventory,replace(basis,policy=rules.base_rules.revision),rules.base_rules))
    assert rules.revision not in load_equipment_attribute_policies()
    print('PASS all14 gem families/extra totals,215/130 caps, broken/repair/unequip, no double count and unknown/stale policy refusals')


if __name__=='__main__':main()
