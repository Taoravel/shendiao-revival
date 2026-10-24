"""Resource-free growth math accepts real resources above naked caps."""
from pet_growth import GrowthRules,Profile,PetGrowth


def main():
    rules=GrowthRules.load();profile=Profile(500001,1006,(1130,1235,960,657,1122))
    state=PetGrowth(3,1,0,(0,0,0,0,0),195,30)
    plan=rules.plan_award(profile,state,200)
    assert (plan.version,plan.level,plan.experience,plan.allocated)==(4,2,0,(0,)*5)
    assert state.hp==195 and state.mp==30
    try:rules.award(profile,state,200)
    except ValueError:pass
    else:raise AssertionError('Legacy naked-caps writer accepted final-soul resources')
    print('PASS resource-free original XP plan L1+200→L2/xp0; real195HP retained; legacy naked resource guard remains')


if __name__=='__main__':main()
