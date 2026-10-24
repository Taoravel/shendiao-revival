"""Literal worked examples cover all14 families including signed ratios."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
from dataclasses import replace
from fractions import Fraction
from accounts import AccountStore
from inventory import Inventory
from pet_souls import SoulProfile,SoulBean
from pet_soul_totals import PetSoulTotalsRules,PetSoulExtraBasis,project
import runtime_storage


def main():
    with TemporaryDirectory(prefix='all-pet-soul-totals-') as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3');runtime_storage.prepare(store)
        role=store.create_role(1111,'全14类宠物属性',12,1010101);rid=role['id'];epoch=store.acquire_lease(1111,rid)
        inv=Inventory(store.leased(1111,rid,epoch),1111,rid);pet=inv.grant_pet(500001)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.change_pet_growth(db,pet,'known-all-L1',0,'experience',50)
            bare=inv.pet_progress(db,pet)
        rules=PetSoulTotalsRules.load()
        extra=PetSoulExtraBasis(rid,pet,rules.revision,'explicit-all-seven',
            ((110,101,1),(120,83,1),(740,-1,10),(1550,1,8),(1560,1,10),(1580,-1,5),(1590,-1,20)))
        initial={key:Fraction(n,d) for key,n,d in extra.values}
        def calculate(entries,source=extra):
            return project(rules,bare,SoulProfile(rid,pet,0,rules.souls.revision,'literal-all-profile',entries),0,source)
        # These are literal original first-grade values over the independently
        # known L1 worked baseline, not recomputation of configured vectors.
        flats=((31276,'physical_attack',41),(31277,'physical_attack',46),
            (31278,'magic_attack',27),(31279,'magic_attack',30),
            (31280,'physical_defense',34),(31281,'physical_defense',39),
            (31282,'magic_defense',26),(31283,'magic_defense',29),
            (31284,'max_mp',93),(31285,'max_mp',106),
            (31286,'max_hp',202),(31287,'max_hp',225),(31288,'speed',21),(31289,'speed',23))
        for template,field,want in flats:
            core,values=calculate(((1,SoulBean(template,0,0,0,0,0)),))
            assert getattr(core,field)==want and core==replace(bare.attributes,**{field:want})
            assert {key:Fraction(n,d) for key,n,d in values}==initial
        ratios=((31290,1550,Fraction(27,200)),(31291,1550,Fraction(31,200)),
            (31292,1560,Fraction(11,100)),(31293,1560,Fraction(13,100)),
            (31294,740,Fraction(-11,100)),(31295,740,Fraction(-13,100)),
            (31296,1580,Fraction(-21,100)),(31297,1580,Fraction(-23,100)),
            (31298,1590,Fraction(-3,50)),(31299,1590,Fraction(-2,25)),
            (31300,110,Fraction(106)),(31301,110,Fraction(108)),(31302,120,Fraction(87)),(31303,120,Fraction(88)))
        for template,key,want in ratios:
            core,values=calculate(((1,SoulBean(template,0,0,0,0,0)),))
            assert core==bare.attributes
            assert {key:Fraction(n,d) for key,n,d in values}==initial|{key:want}
        combined=tuple((i,SoulBean(template,0,0,0,0,0)) for i,template in enumerate((31286,31300,31301,31294,31295),1))
        core,values=calculate(combined);values={key:Fraction(n,d) for key,n,d in values}
        assert core.max_hp==202 and values[110]==113 and values[740]==Fraction(-7,50)
        for bad in (lambda:replace(extra,values=extra.values[:-1]),
                lambda:replace(extra,values=extra.values[:2]+((740,-2,20),)+extra.values[3:]),
                lambda:calculate(((1,SoulBean(31294,0,0,0,0,0)),),replace(extra,values=extra.values[:2]+((740,-1,1),)+extra.values[3:])),
                lambda:calculate(((1,SoulBean(31300,0,0,0,0,0)),),replace(extra,values=((110,0x7fffffff,1),)+extra.values[1:]))):
            try:bad()
            except ValueError:pass
            else:raise AssertionError('Missing/noncanonical/overflow extra source accepted')
        print('PASS all28 original first-grade templates/all14 mappings against literal totals, exact signed ratios, '
            'single-floor stacked hit113/negative-7/50, explicit7 extras required and overflow/ratio bounds refused')


if __name__=='__main__':main()
