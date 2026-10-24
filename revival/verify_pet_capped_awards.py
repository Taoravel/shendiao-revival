"""Transaction-selected pet and designed role+5 capped XP Interface."""
from contextlib import closing
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory
from accounts import AccountStore
from inventory import Inventory, PetState
from inspect_client import OUT,write_json


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'封顶经验',12,1010101)
        config=Inventory.prepare(store);inv=Inventory(store,1111,role['id'],config)
        pet=inv.grant_pet(500001)
        def change(key,version,operation,value):
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                return inv.change_pet_growth(db,pet,key,version,operation,value)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            assert inv.selected_fighting_pet(db) is None
        inv.fight_pet(pet)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            selected=inv.selected_fighting_pet(db)
            assert isinstance(selected,PetState) and selected.id==pet and selected.progress is not None
            assert inv.read_pet_state(db,pet)==selected
            assert inv.read_pet_state(db,999999) is None
            try:selected.fighting=0
            except FrozenInstanceError:pass
            else:raise AssertionError('Selected snapshot is mutable')
        xp=sum(inv.growth_rules.thresholds[x] for x in range(24))
        grown=change('prepare:24',0,'experience',xp)
        hurt=change('hurt',grown.state.version,'resources',(1,1))
        # The task owner captures role20 before its own reward and passes cap25.
        amount=inv.growth_rules.thresholds[24]+10000
        result=change('task:cap25',hurt.state.version,'experience_capped',(amount,25))
        assert (result.state.level,result.state.experience)==(25,10000)
        assert result.attributes.max_hp-result.state.hp==hurt.attributes.max_hp-hurt.state.hp
        assert result.attributes.max_mp-result.state.mp==hurt.attributes.max_mp-hurt.state.mp
        assert change('task:cap25',hurt.state.version,'experience_capped',(amount,25))==result
        before=inv.snapshot()
        for key,version,value in (('task:cap25',hurt.state.version,(amount,26)),
                                   ('task:stale',hurt.state.version,(1,25)),
                                   ('task:invalid',result.state.version,(1,24)),
                                   ('task:bool',result.state.version,(True,25))):
            try:change(key,version,'experience_capped',value)
            except ValueError:pass
            else:raise AssertionError('Conflicting/stale/over-cap award accepted')
            assert inv.snapshot()==before
        atcap=change('task:at-cap',result.state.version,'experience_capped',(7000,25))
        assert (atcap.state.level,atcap.state.experience)==(25,17000)
        # The public low-level cap check refuses +6 instead of deleveling.
        high=change('prepare:26',atcap.state.version,'experience',inv.growth_rules.thresholds[25])
        assert high.state.level>=26
        before=inv.snapshot()
        try:change('task:+6',high.state.version,'experience_capped',(10000,25))
        except ValueError:pass
        else:raise AssertionError('Above role+5 cap accepted')
        assert inv.snapshot()==before
        dead=change('dead',high.state.version,'resources',(0,1))
        after=change('dead:award',dead.state.version,'experience_capped',(10000,30))
        assert after.state.hp==0  # caller excludes dead pets; module never revives.
        before=inv.snapshot()
        try:
            with closing(store.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                inv.change_pet_growth(db,pet,'task:rollback',after.state.version,'experience_capped',(9000,30))
                raise RuntimeError('later common receipt failure')
        except RuntimeError:pass
        assert inv.snapshot()==before
        # Unknown legacy growth stays explicit on the selected instance.
        inv.fight_pet()
        with closing(store.connect()) as db,db:
            legacy=db.execute('INSERT INTO inventory_pets(role_id,template_id,name,fighting) VALUES(?,?,?,1)',
                (role['id'],500001,'未知成长')).lastrowid
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            old=inv.selected_fighting_pet(db)
            assert old.id==legacy and old.progress is None
            assert inv.read_pet_state(db,legacy)==old
            assert not db.execute('SELECT 1 FROM inventory_pet_growth WHERE pet_id=?',(legacy,)).fetchone()
        inv.fight_pet()
        with closing(store.connect()) as db,db:
            db.execute('BEGIN')
            assert inv.selected_fighting_pet(db) is None
    report={'passed':['owned selected pet frozen in caller transaction','no selected pet returns None',
        'role20 pet24 stops at25 and stores remaining XP','pet at +5 stores XP without leveling',
        'pet at +6 rejects without delevel or XP loss','award cap belongs to retry fingerprint',
        'stale and malformed award refused','upgrade preserves wounds and never revives',
        'outer failure rolls back capped growth and receipt','selected legacy pet retains unknown growth'],
        'source':'designed task-pet-experience-v1','task_workflow_connected_by_this_script':False}
    write_json(OUT/'evidence/pet-capped-awards-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()
