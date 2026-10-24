"""Explicit local equip plan keeps original orb/worn mappings and raw history."""
from dataclasses import asdict,replace
from fractions import Fraction
import json
from inventory import ItemState,PetState
from pet_souls import SoulProfile,SoulBean
from pet_soul_storage import SoulBasis
from pet_soul_item_storage import OrbSource,OrbBasis
from pet_soul_item_data import OrbTips
from pet_soul_actions import SoulActionRules,SoulActionAuthority,plan_wear,plan_remove


def main():
    rules=SoulActionRules.load();rid=9001
    profile=SoulProfile(rid,17,0,rules.orbs.souls.revision,'known-complete-pet-souls',())
    raw=json.dumps(asdict(profile));pet=PetState(17,rid,500001,'小灰狗',1)
    before=SoulBasis(1111,7,pet,profile,'explicit_known_pet_souls',raw,raw)
    item=ItemState(333,rid,31276,1,0,None,1)
    source=OrbSource(rid,333,31276,0,rules.orbs.revision,'known-full-orb',OrbTips(61,10001,-205,204),0,-2)
    encoded=json.dumps(asdict(source));orb=OrbBasis(1111,7,item,source,'explicit_known_orb_instance',encoded,encoded,'[31276,1,1,null]')
    authority=SoulActionAuthority(rid,17,'known-current-epoch','known-role-soul-context',4,True,0,())
    plan=plan_wear(rules,before,orb,authority)
    assert plan.slot==1 and plan.after==replace(profile,version=1,entries=((1,SoulBean(31276,61,10001,204,-205,-2)),))
    assert plan.debits==((333,1),) and plan.grants==() and plan.cash_cost==0
    assert plan.effects==((1,31276,2,2,81,1,Fraction(32)),)
    # New known orb without worn history uses the explicit local binding rule;
    # it does not modify a stored nonboolean historical raw6.
    fresh=replace(orb,source=replace(source,retained_raw6=None))
    assert plan_wear(rules,before,fresh,authority).after.entries[0][1].raw6==1
    assert source.retained_raw6==-2 and source.tips.raw5==-205
    def refused(action):
        try:action()
        except ValueError:return
        raise AssertionError('Unsafe soul equip plan accepted')
    refused(lambda:plan_wear(rules,before,orb,replace(authority,allowed=False)))
    refused(lambda:plan_wear(rules,before,replace(orb,source=replace(source,nonbinding_flags=160)),authority))
    refused(lambda:plan_wear(rules,before,replace(orb,inventory_revision=6),authority))
    refused(lambda:plan_wear(rules,replace(before,profile=plan.after),orb,authority))
    worn=replace(before,inventory_revision=8,profile=plan.after)
    tools=(ItemState(445,rid,38045,4,2,None,0),ItemState(444,rid,38045,1,1,None,1))
    removal_authority=replace(authority,material_flags=((444,0),(445,0)))
    removal=plan_remove(rules,worn,1,tools,removal_authority)
    assert removal.after==replace(profile,version=2)
    assert removal.tool_template==38045 and removal.tool_count==2
    assert removal.debits==((444,1),(445,1)) and removal.grants==((31276,1,1),) and removal.cash_cost==0
    assert removal.returned_tips==OrbTips(61,10001,-205,204) and removal.retained_raw6==-2
    assert removal.effects==()
    refused(lambda:plan_remove(rules,worn,2,tools,removal_authority))
    refused(lambda:plan_remove(rules,worn,1,(tools[1],),replace(authority,material_flags=((444,0),))))
    refused(lambda:plan_remove(rules,worn,1,tools,replace(authority,material_flags=((444,0),(445,160)))))
    print('PASS local first-free wear plan, exact negative raw6 and4→6 mapping, original capped scalar32, '
        'explicit new-history binding design, actual38045 quote and bound-first removal/returned data, '
        'no cash fee, restricted/stale/duplicate/insufficient tools refuses')


if __name__=='__main__':main()
