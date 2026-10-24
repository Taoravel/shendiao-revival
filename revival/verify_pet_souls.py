"""Original pet soul cumulative XP, template-uselevel caps and exact scalars."""
from dataclasses import replace
from fractions import Fraction
from pet_souls import SoulBean,SoulProfile,SoulRules


def main():
    rules=SoulRules.load()
    bean=SoulBean(31276,140,0,104,-105,106)
    profile=SoulProfile(9001,17,0,rules.revision,'explicit-known-six-fields',((1,bean),))
    cases=((0,1,1),(19,1,1),(20,1,1),(59,1,1),(60,2,1),(119,2,1),(120,2,2),
        (139,2,2),(140,3,2),(279,3,2),(280,3,3),(655339,14,14),(655340,15,14),(1310680,15,15))
    for xp,ordinary,advanced in cases:
        assert rules.grade(replace(bean,cumulative_exp=xp))==ordinary
        assert rules.grade(replace(bean,item_id=31277,cumulative_exp=xp))==advanced
    # These expected caps were independently executed in the original client.
    for template,without,with_flag in ((500001,1,2),(500023,6,7),(500043,9,10),(500069,15,15)):
        assert rules.effective_cap(template,profile,0)==without
        assert rules.effective_cap(template,profile,1)==with_flag
        simple=replace(profile,entries=((1,replace(bean,soul_skill_id=10001)),))
        assert rules.effective_cap(template,simple,0)==(15 if template==500069 else without+1)
        assert rules.effective_cap(template,simple,1)==(15 if template==500069 else with_flag+1)
        unlimited=replace(profile,entries=((1,replace(bean,soul_skill_id=10002)),))
        assert rules.effective_cap(template,unlimited,0)==15
        assert rules.effective_cap(template,unlimited,1)==15
    assert rules.has_template(profile,31276) is True
    assert rules.has_template(profile,31277) is False
    assert rules.has_template(profile,31278) is False
    effect=rules.effects(500001,profile,0)
    assert effect==((1,31276,3,1,81,1,Fraction(11)),)
    assert rules.effects(500023,profile,0)==((1,31276,3,3,81,1,Fraction(62)),)
    negative=replace(profile,entries=((5,SoulBean(31295,1310680,0,204,-205,206)),))
    assert rules.effects(500069,negative,0)==((5,31295,15,15,741,2,Fraction(-1,5)),)
    assert rules.removal_quote(bean)==(38045,4)
    assert rules.removal_quote(replace(bean,item_id=31277,cumulative_exp=280))==(38045,6)
    assert len(rules.souls)==28 and len(rules.pet_templates)==158 and len(rules.skill_ids)==22
    for row in rules.souls.values():assert len(row.values)==15 and all(type(v) is Fraction for v in row.values)
    def refused(action):
        try:action()
        except ValueError:return
        raise AssertionError('Unknown or partial soul source accepted')
    refused(lambda:rules.effective_cap(999999,profile,0))
    refused(lambda:rules.effective_cap(500001,profile,None))
    refused(lambda:rules.effective_cap(500001,profile,False))
    refused(lambda:rules.grade(replace(bean,item_id=999999)))
    refused(lambda:rules.grade(replace(bean,soul_skill_id=103)))
    refused(lambda:replace(bean,cumulative_exp=-1))
    refused(lambda:replace(profile,entries=((1,bean),(1,bean))))
    refused(lambda:replace(profile,entries=[(1,bean)]))
    assert bean.raw5==-105 and bean.cumulative_exp==140
    print('PASS28 original XP boundaries;24 original template/skill/flag caps;3 exact-ID duplicates; '
        '420 rational scalars, negative fractions and raw fields preserved; known removal38045; unknown refuses')


if __name__=='__main__':main()
