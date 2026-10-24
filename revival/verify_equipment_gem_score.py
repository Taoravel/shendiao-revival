"""Explicit designed gem score preserves the known pre-gem equipment source."""
from inventory import ItemState
from equipment_detail import EquipmentDetail
from equipment_condition import EquipmentCondition
from equipment_gems import GemRules,GemState
from equipment_gem_score import GemScoreRules,GemScoreBasis,project
from dataclasses import replace
from equipment_gems import encode_detail
from research_equipment_gem_detail import NativeGemEquipmentDetail


def refused(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('Unknown or inconsistent gem score source accepted')


def main():
    gems=GemRules.load();rules=GemScoreRules.load()
    item=ItemState(701,7,40100,1,0,None,0,None,EquipmentCondition(5,42,80,1),
        EquipmentDetail(1,1,250,((81,20),(811,20),(1231,6))))
    before=GemState(0,(),gems.revision);after=GemState(1,(35001,),gems.revision)
    basis=GemScoreBasis(7,701,rules.revision,250,'explicit-known-pre-gem-fixture')
    result=project(rules,gems,item,before,after,basis)
    assert (result.after.detail.score,result.after.condition.color_tier,result.after.condition.version)==(300,2,6)
    assert (result.after.condition.current,result.after.condition.maximum)==(42,80)
    assert result.after.detail.base_properties==item.detail.base_properties
    parsed=NativeGemEquipmentDetail(40100).parse(encode_detail(gems,result.after,after,410006))
    assert (parsed['score'],parsed['color'],parsed['gem_effects'])==(300,2,[(81,12)])
    # Removal recomputes from the same baseline: no drift or cumulative gain.
    removed=project(rules,gems,result.after,after,GemState(2,(),gems.revision),basis)
    assert (removed.after.detail.score,removed.after.condition.color_tier,removed.after.condition.version)==(250,1,7)
    assert (removed.after.condition.current,removed.after.condition.maximum)==(42,80)
    # Same-grade family replacement has the same designed points. Neither
    # condition version nor current/max durability changes with unchanged color.
    swapped=project(rules,gems,result.after,after,GemState(2,(35000,),gems.revision),basis)
    assert swapped.after.detail.score==300 and swapped.after.condition==result.after.condition
    combined=GemState(1,(35001,35014,35183),gems.revision)
    assert rules.contribution(gems,combined)==225 #50+55+120 from the local policy
    assert rules.contribution(gems,GemState(1,(35200,35214),gems.revision))==170
    # Current before score must agree exactly. Missing historical pre-gem
    # sources cannot be reconstructed by subtracting an estimated old bonus.
    for changed in (replace(basis,plain_score=249),replace(basis,item_key=702),replace(basis,role_id=8),replace(basis,policy='other')):
        refused(lambda:project(rules,gems,item,before,after,changed))
    refused(lambda:project(rules,gems,replace(item,detail=replace(item.detail,score=251)),before,after,basis))
    refused(lambda:project(rules,gems,replace(item,condition=replace(item.condition,color_tier=2)),before,after,basis))
    refused(lambda:project(rules,gems,item,before,replace(after,version=2),basis))
    refused(lambda:replace(basis,plain_score=True))
    huge=replace(item,detail=replace(item.detail,score=0x7fffffff),condition=replace(item.condition,color_tier=3))
    refused(lambda:project(rules,gems,huge,before,after,replace(basis,plain_score=0x7fffffff)))
    print('PASS designed score/native color, reversible baseline/no drift, preserved wear, unknown/stale/overflow refusals')


if __name__=='__main__':main()
