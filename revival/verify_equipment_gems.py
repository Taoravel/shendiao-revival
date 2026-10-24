"""Original ordinary socket rules, complete separate gem effects and returns."""
from inventory import ItemState
from equipment_detail import EquipmentDetail
from equipment_condition import EquipmentCondition
from equipment_gems import GemRules,GemState,embed,remove
from dataclasses import replace


def refused(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('Invalid sockets or removal accepted')


def main():
    rules=GemRules.load()
    equipment=ItemState(701,7,40104,1,0,None,0,None,EquipmentCondition(0,90,100,1),
        EquipmentDetail(1,1,0,((81,260),(811,260),(1231,100))))
    material=ItemState(901,7,35001,2,1,None,1)
    before=GemState(0,(),rules.revision)
    added=embed(rules,equipment,before,material,0,flags=(0,0))
    assert added.after.templates==(35001,) and added.after.version==1
    assert (added.cash_cost,added.equipment_binding,added.material_debit)==(2500,1,(901,1))
    assert rules.effects(added.after)==((81,12),)
    assert equipment.detail.base_properties==((81,260),(811,260),(1231,100))
    removed=remove(rules,equipment,added.after,35001,0,flags=0)
    assert removed.after.templates==() and removed.tools==((36949,1),)
    assert removed.grants==((35001,1,1),)
    assert len(rules.gems)==210
    # Original hole matrix from the complete native function, no assumption
    # that the required role level equals the equipment's effective level.
    assert (rules.holes(40104,0),rules.holes(40104,410007),rules.holes(40104,410006))==(4,5,15)
    assert rules.holes(40100,0)==0 and rules.holes(40100,410007)==1
    state=GemState(8,(35027,35003,35014),rules.revision) # grade3 cat, grade1 dragon, grade2 cat
    replaced=embed(rules,equipment,state,material,0,flags=(0,0))
    assert replaced.after.templates==(35027,35001,35014) and replaced.replaced_template==35003
    assert state.templates==(35027,35003,35014)
    assert rules.effects(replaced.after)==((81,39),)
    # Resulting families, not a historical count that can never shrink.
    three=GemState(0,(35001,35016,35026),rules.revision) # cat1, dragon2, moon3
    incoming=replace(material,template_id=35046) # olive4: fourth family
    refused(lambda:embed(rules,equipment,three,incoming,0,flags=(0,0)))
    replacement=replace(material,template_id=35007) # olive1 replaces final cat
    assert embed(rules,equipment,three,replacement,0,flags=(0,0)).after.templates==(35007,35016,35026)
    for bad in (replace(material,template_id=35006), # speed belt/shoes cannot weapon
            replace(material,template_id=35053), # grade5 exceeds four ordinary holes
            replace(material,template_id=35221),replace(material,quality=0),replace(material,role_id=8)):
        refused(lambda:embed(rules,equipment,before,bad,0,flags=(0,0)))
    refused(lambda:embed(rules,replace(equipment,detail=replace(equipment.detail,identified=0)),before,material,0,flags=(0,0)))
    refused(lambda:embed(rules,equipment,before,material,None,flags=(0,0)))
    refused(lambda:embed(rules,equipment,before,material,0,flags=(0,32)))
    refused(lambda:rules.effects(GemState(0,(35001,35003),rules.revision))) # same grade
    # Fifteen original holes, both tools, lower-grade advanced returns. A
    # level1 weapon with original infinite skill is sufficient for this oracle.
    high=GemState(0,(35066,35079,35183),rules.revision) # cat6,cat7,cat15
    full=remove(rules,equipment,high,-1,410006,flags=0)
    assert full.tools==((36949,32),(39649,514))
    assert full.grants==((35066,2,1),(35170,1,1))
    assert full.after.templates==()
    single=remove(rules,equipment,high,35079,410006,flags=0)
    assert single.after.templates==(35066,35183) and single.tools==((39649,2),)
    assert single.grants==((35066,1,1),)
    for selection in (0,True,-2,35001):refused(lambda:remove(rules,equipment,high,selection,410006,flags=0))
    refused(lambda:remove(rules,equipment,before,-1,0,flags=0))
    refused(lambda:remove(rules,equipment,high,-1,410006,flags=32))
    for templates in ((35001,35001),(35001,35003),(35001,35016,35026,35046)):
        refused(lambda:rules.validate(GemState(0,templates,rules.revision)))
    # Every original row retains all effect IDs, including currently unknown
    # combat consumers for elemental absorption and treatment.
    assert rules.effects(GemState(0,(35008,35022,35036),rules.revision))==((351,3),(371,3),(381,3))
    assert rules.effects(GemState(0,(35200,35201),rules.revision))==((1531,11),)
    print('PASS all210 original rows, grade/family/order rules,40-level fee2500, both tools and exact return aggregation')


if __name__=='__main__':main()
