"""Nonempty gem vector must reach the actual original complete detail parser."""
from inventory import ItemState
from equipment_detail import EquipmentDetail,encode
from equipment_condition import EquipmentCondition
from equipment_gems import GemRules,GemState,encode_detail
from research_equipment_gem_detail import NativeGemEquipmentDetail
from dataclasses import replace


def main():
    rules=GemRules.load()
    item=ItemState(701,7,40104,1,0,None,0,None,EquipmentCondition(0,42,80,1),
        EquipmentDetail(1,1,0,((81,260),(811,260),(1231,100))))
    native=NativeGemEquipmentDetail(40104)
    for templates,expected in (((35001,),[(81,12)]),((35001,35014),[(81,25)]),
            ((35001,35016),[(81,12),(811,13)]),((),[]),((35014,),[(81,13)])):
        state=GemState(0,templates,rules.revision)
        payload=encode_detail(rules,item,state,0)
        parsed=native.parse(payload)
        assert parsed['gems']==list(templates) and parsed['gem_effects']==expected
        assert parsed['properties']==[(81,260),(811,260),(1231,100)]
        assert (parsed['score'],parsed['color'],parsed['current'],parsed['maximum'])==(0,1,42,80)
        if not templates:assert payload==encode(item.template_id,item.detail,item.condition,rules.detail_rules)
    # Score is separately delivered, not derived from the gem vector. Exact
    # original40104 threshold3366 changes white1 -> green2 at ordinary prefix1.
    scored=replace(item,detail=replace(item.detail,score=3366),condition=replace(item.condition,color_tier=2))
    parsed=native.parse(encode_detail(rules,scored,GemState(0,(35001,),rules.revision),0))
    assert (parsed['score'],parsed['color'],parsed['gem_effects'])==(3366,2,[(81,12)])
    print('PASS complete original gem detail parser; independent base/gem maps; ordered replacement and empty clear')


if __name__=='__main__':main()
