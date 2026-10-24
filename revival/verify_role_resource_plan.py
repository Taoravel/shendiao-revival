"""Public pure resource transitions, before storage/profile activation."""
from inspect_client import OUT,write_json
from role_resource_plan import (ResourceProjection,ResourceCaps,RoleResources,
    ResourceRules,load_resource_rules,plan_resource_caps,plan_resource_values)


def refused(call):
    try:call()
    except ValueError:return
    raise AssertionError('Invalid resource transition accepted')


def main():
    rules=load_resource_rules()
    source=ResourceProjection(41,0,0,'attributes.known',1,0,'equipment.known')
    worn=ResourceCaps(source,200,80)
    before=RoleResources(7,10,30,worn,rules.revision)
    bare_source=ResourceProjection(41,0,0,'attributes.known',2,0,'equipment.known')
    bare=plan_resource_caps(before,ResourceCaps(bare_source,100,50),'unequip',rules)
    assert (bare.after.hp,bare.after.mp,bare.after.version)==(10,30,8)
    next_source=ResourceProjection(41,0,0,'attributes.known',3,0,'equipment.known')
    reworn=plan_resource_caps(bare.after,ResourceCaps(next_source,200,80),'equip',rules)
    assert (reworn.after.hp,reworn.after.mp,reworn.after.version)==(10,30,9)
    full=RoleResources(9,180,75,ResourceCaps(next_source,200,80),rules.revision)
    clipped=plan_resource_caps(full,ResourceCaps(ResourceProjection(
        41,0,0,'attributes.known',4,0,'equipment.known'),100,50),'equipment_wear',rules)
    assert (clipped.after.hp,clipped.after.mp)==(100,50)
    grown=plan_resource_caps(reworn.after,ResourceCaps(ResourceProjection(
        41,0,1,'attributes.known',3,0,'equipment.known'),210,86),'ordinary_growth',rules)
    assert (grown.after.hp,grown.after.mp,grown.after.version)==(20,36,10)
    dead=RoleResources(10,0,0,grown.after.caps,rules.revision)
    dead_grown=plan_resource_caps(dead,ResourceCaps(ResourceProjection(
        41,0,2,'attributes.known',3,0,'equipment.known'),220,92),'ordinary_growth',rules)
    assert (dead_grown.after.hp,dead_grown.after.mp)==(0,6)
    medicine=plan_resource_values(reworn.after,180,60,'medicine',rules)
    assert (medicine.after.hp,medicine.after.mp,medicine.after.version)==(180,60,10)
    assert medicine.after.caps==reworn.after.caps
    rested=plan_resource_values(medicine.after,200,80,'inn_rest',rules)
    assert (rested.after.hp,rested.after.mp,rested.after.version)==(200,80,11)
    for hp,mp in ((201,80),(200,81)):
        try:plan_resource_values(rested.after,hp,mp,'medicine',rules)
        except ValueError:pass
        else:raise AssertionError('Resource write exceeded current final caps')
    try:plan_resource_values(dead,1,0,'medicine',rules)
    except ValueError:pass
    else:raise AssertionError('Ordinary medicine revived a dead role')
    known=RoleResources(4,70,40,ResourceCaps(ResourceProjection(
        41,0,0,'attributes.known',0,0,'equipment.known'),100,50),rules.revision)
    migrated=plan_resource_caps(known,worn,'explicit_migration',rules)
    assert (migrated.after.hp,migrated.after.mp,migrated.after.version)==(70,40,5)
    metadata=ResourceCaps(ResourceProjection(41,0,0,'attributes.known',6,0,'equipment.known'),200,80)
    current=plan_resource_caps(migrated.after,metadata,'equipment_repair',rules)
    assert (current.after.hp,current.after.mp,current.after.version)==(70,40,5)
    assert current.changed and current.after.caps.source.inventory_revision==6
    from role_resource_plan import plan_resource_source
    carried_caps=ResourceCaps(ResourceProjection(41,0,0,'attributes.known',7,0,'equipment.known'),200,80)
    carried=plan_resource_source(current.after,carried_caps,'inventory_change',rules)
    assert (carried.after.hp,carried.after.mp,carried.after.version)==(70,40,5)
    assert carried.after.caps.source.inventory_revision==7
    refused(lambda:plan_resource_source(current.after,ResourceCaps(carried_caps.source,201,80),'inventory_change',rules))
    refused(lambda:plan_resource_source(current.after,ResourceCaps(ResourceProjection(
        41,0,1,'attributes.known',7,0,'equipment.known'),200,80),'inventory_change',rules))
    refused(lambda:plan_resource_source(carried.after,metadata,'inventory_change',rules))
    assert plan_resource_caps(current.after,metadata,'equipment_repair',rules).after is current.after
    refused(lambda:plan_resource_caps(current.after,metadata,[],rules))
    refused(lambda:ResourceRules(rules.revision,['equip'],frozenset(('medicine',)),frozenset(('inventory_change',))))
    refused(lambda:ResourceCaps(source,16777217,80))
    refused(lambda:plan_resource_caps(current.after,worn,'equip',rules))
    refused(lambda:plan_resource_caps(current.after,ResourceCaps(ResourceProjection(
        42,0,0,'attributes.known',7,0,'equipment.known'),200,80),'equip',rules))
    refused(lambda:plan_resource_caps(current.after,ResourceCaps(ResourceProjection(
        41,0,1,'attributes.known',7,0,'equipment.known'),210,80),'ordinary_growth',rules))
    exhausted=RoleResources(2**63-1,70,40,metadata,rules.revision)
    refused(lambda:plan_resource_values(exhausted,71,40,'medicine',rules))
    report=dict(passed=['unwear lowHP10/200 then wear200 retains10; caps cycling grants no heal',
        'numeric cap changes increment one resource version each; lower caps clip180/75 to100/50',
        'ordinary growth keeps missing amounts using final caps; deadHP stays0',
        'medicine/rest use final200/80 caps; overflow and ordinary medicine revival refuse',
        'staged known legacy70/40 migrates without heal; source-only update retains resource version and no-op retains state',
        'inventory_change updates only current asset provenance; numeric caps, growth changes and rewound sources refuse',
        'foreign/rewound/mixed-source transitions, mutable rules, inexact native caps and exhausted versions reject'],
        scope='pure policy; not storage, consumer migration or six-slot runtime activation',
        native_gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/role-resource-plan-verification.json',report);print(report)


if __name__=='__main__':main()
