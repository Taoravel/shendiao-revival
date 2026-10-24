"""Current score validation never invents a future gem version on a read."""
from inventory import ItemState
from equipment_detail import EquipmentDetail
from equipment_condition import EquipmentCondition
from equipment_gems import GemRules,GemState
from equipment_gem_score import GemScoreRules,GemScoreBasis,validate_current


def main():
    gems=GemRules.load();rules=GemScoreRules.load()
    state=GemState(2**63-2,(35001,),gems.revision)
    item=ItemState(701,7,40100,1,0,None,0,None,EquipmentCondition(0,42,80,2),
        EquipmentDetail(1,1,300,((81,20),(811,20),(1231,6))))
    basis=GemScoreBasis(7,701,rules.revision,250,'known-current-at-version-limit')
    assert validate_current(rules,gems,item,state,basis)==50
    assert state.version==2**63-2 and item.detail.score==300
    print('PASS current known score at last valid gem version is readable without creating a next state')


if __name__=='__main__':main()
