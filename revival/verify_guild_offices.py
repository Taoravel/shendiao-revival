"""Guild office rules, migration and owner ordering in disposable stores."""
import asyncio
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
from verify_faction_payments import Fixture
from faction_domain import OrganizationStore
from inspect_client import OUT,write_json


def setup(path):
    f=Fixture(path);create=f.family();f.fund(create)
    family=f.org.execute(create,f.now())['organization']
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET level=3 WHERE id=?',(family,))
    c=f.cmd(1,family,'create_guild',('职位帮派','同心协力',create.args[2]));f.fund(c)
    guild=f.org.execute(c,f.now())['organization']
    other=f.family(16,name='入帮家族');f.fund(other);second=f.org.execute(other,f.now())['organization']
    f.org.execute(f.cmd(16,guild,'apply'),f.now());f.org.execute(f.cmd(1,guild,'review',(second,True)),f.now())
    # Guild progression remains an explicit fixture, not a building reward.
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET level=4 WHERE id=?',(guild,))
    return f,family,second,guild


def check(f,family,second,guild,passed):
    def run(actor,op,args=()):return f.org.execute(f.cmd(actor,guild,op,args),f.now())
    def reject(actor,op,args,reason):f.reject(lambda:run(actor,op,args),reason)
    def state():return f.org.guild_office_snapshot(guild)
    run(1,'appoint',(2,'deputy'))
    # Original authority dialog enumerates masks 1..256, nine bits. All are
    # persisted, but only appointment bit six is consumed by this slice.
    for bit in range(9):run(1,'set_authority',(2,bit,True))
    assert state().deputy_authority==511
    reject(1,'set_authority',(2,9,True),'invalid_authority')
    for bit in range(9):run(1,'set_authority',(2,bit,False))
    assert state().deputy_authority==0
    passed.append('nine original authority bits persist independently; bit nine is rejected; unimplemented rights grant no unrelated permission')
    reject(3,'appoint',(4,'left_elder'),'permission_denied')
    reject(2,'appoint',(4,'left_elder'),'permission_denied')
    run(1,'set_authority',(2,6,True));assert state().deputy_authority==64
    run(2,'appoint',(4,'left_elder'));run(1,'appoint',(5,'left_elder'))
    reject(1,'appoint',(6,'left_elder'),'elder_slots_full')
    run(1,'appoint',(6,'right_elder'))
    assert len([r for r in state().offices if r[1]=='left_elder'])==2
    reject(1,'appoint',(3,'deputy'),'deputy_slot_full')
    passed.append('one deputy; two left-elder slots at fixture guild level four; deputy appointment requires delegated bit six')
    run(16,'appoint',(17,'patrol'));run(16,'appoint',(18,'patrol'))
    reject(16,'appoint',(7,'patrol'),'permission_denied')
    reject(1,'appoint',(4,'patrol'),'demote_first')
    assert (17,'patrol') in state().offices and (18,'patrol') in state().offices
    passed.append('family head appoints multiple own ordinary members as patrols; cross-family and officer overwrite denied')
    run(4,'mute',(7,));run(6,'mute',(8,))
    reject(4,'mute',(5,),'protected_office');reject(17,'mute',(7,),'permission_denied')
    reject(4,'change_aim',('长老不能改宗旨',),'permission_denied')
    passed.append('both elder kinds can mute ordinary members; protected officers and nonmanager patrol permissions preserved')
    reject(1,'resign',(),'leadership_tenure')
    run(2,'resign');assert state().deputy_authority==0 and (2,'deputy') not in state().offices
    reject(1,'resign',(),'deputy_required')
    run(1,'appoint',(3,'deputy'));assert state().deputy_authority==0
    run(1,'set_authority',(3,6,True))
    with closing(f.accounts.connect()) as db,db:
        old=f.now()-f.policy['guild_leader_tenure_ms']-10
        db.execute('UPDATE guild_families SET joined_ms=? WHERE guild=?',(old,guild))
        db.execute('UPDATE family_members SET joined_ms=? WHERE role_id=3',(old,))
    run(1,'resign');assert state().leader==3 and state().deputy_authority==0
    assert f.org.snapshot(family)[0]['leader']==1
    run(4,'resign');assert (4,'left_elder') not in state().offices
    passed.append('resignation enforces deputy and 72-hour tenure, clears delegation, and leaves independent family leadership intact')
    run(3,'appoint',(2,'deputy'));run(3,'set_authority',(2,6,True))
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_no_family_office_delete BEFORE DELETE ON guild_offices BEGIN SELECT RAISE(ABORT,'cross_owner_delete'); END")
    f.org.execute(f.cmd(2,family,'leave'),f.now())
    assert state().deputy_authority==0 and (2,'deputy') not in state().offices
    f.org.execute(f.cmd(2,family,'apply'),f.now());f.org.execute(f.cmd(1,family,'review',(2,True)),f.now())
    assert state().deputy_authority==0 and (2,'deputy') not in state().offices
    with closing(f.accounts.connect()) as db,db:
        assert db.execute("SELECT 1 FROM guild_offices WHERE guild=? AND role_id=2 AND position='deputy'",(guild,)).fetchone()
        db.execute('DROP TRIGGER fixture_no_family_office_delete')
    run(3,'appoint',(2,'deputy'));assert state().deputy_authority==0
    passed.append('family exit does not write guild offices; membership generation immediately revokes old delegation across leave/rejoin, then guild owner prunes')
    run(16,'leave',(second,));assert not any(r[0] in (17,18) for r in state().offices)
    f.org.execute(f.cmd(16,guild,'apply'),f.now());run(3,'review',(second,True))
    assert not any(r[0] in (17,18) for r in state().offices)
    passed.append('whole-family departure/rejoin rotates guild-family generation and clears patrols without office resurrection')
    before=state();org_before=f.org.snapshot(guild)
    c=f.cmd(3,guild,'appoint',(7,'right_elder'),'office-atomic')
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_office_receipt BEFORE INSERT ON organization_receipts WHEN NEW.request_id='office-atomic' BEGIN SELECT RAISE(ABORT,'fixture_receipt'); END")
    try:f.org.execute(c,f.now())
    except sqlite3.IntegrityError:pass
    else:raise AssertionError('Receipt failure was ignored')
    assert state()==before and f.org.snapshot(guild)==org_before
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_office_receipt')
    stale=f.cmd(3,guild,'set_authority',(2,6,True))
    f.epochs[3]=f.accounts.acquire_lease(1111,3)
    f.reject(lambda:f.org.execute(stale,f.now()),'stale_epoch')
    run(3,'set_authority',(2,6,True));saved=state()
    f.org=OrganizationStore(f.accounts.path,f.policy);f.org.initialize();assert state()==saved
    passed.append('office/binding/authority/revision and receipt are atomic; stale lease refuses; reopening preserves current state')


async def owner_check(f,guild,passed):
    from game_runtime import GameRuntime
    from faction_runtime import OrganizationOutcome
    import runtime_storage
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        # One remaining left-elder slot, two independent caller requests.
        results=await asyncio.gather(*(runtime.social_runtime.organizations.command(
            f.cmd(3,guild,'appoint',(rid,'left_elder')),f.now()) for rid in (8,9)),return_exceptions=True)
        assert sum(isinstance(r,OrganizationOutcome) for r in results)==1
        assert [str(r) for r in results if isinstance(r,Exception)]==['elder_slots_full']
        assert len([r for r in f.org.guild_office_snapshot(guild).offices if r[1]=='left_elder'])==2
    finally:await runtime.close()
    passed.append('actual bounded guild owner serializes competing final elder-slot appointments without exceeding quota')


def migration(path,passed):
    f,_,_,guild=setup(path)
    f.org.execute(f.cmd(1,guild,'appoint',(2,'deputy')),f.now())
    f.org.execute(f.cmd(1,guild,'set_authority',(2,6,True)),f.now())
    before=f.org.guild_office_snapshot(guild)
    with closing(f.accounts.connect()) as db,db:
        db.execute('DROP INDEX guild_deputy_slot')
        db.execute('ALTER TABLE guild_offices RENAME TO fixture_offices')
        db.execute('''CREATE TABLE guild_offices(guild INTEGER NOT NULL,role_id INTEGER NOT NULL,position TEXT NOT NULL,
            PRIMARY KEY(guild,role_id),UNIQUE(guild,position))''')
        db.execute('INSERT INTO guild_offices SELECT * FROM fixture_offices');db.execute('DROP TABLE fixture_offices')
    f.org.initialize();assert f.org.guild_office_snapshot(guild)==before
    f.org.execute(f.cmd(1,guild,'appoint',(4,'left_elder')),f.now())
    f.org.execute(f.cmd(1,guild,'appoint',(5,'left_elder')),f.now())
    with closing(f.accounts.connect()) as db:
        assert db.execute('SELECT COUNT(*) FROM guild_offices_legacy_v1').fetchone()[0]==1
    f.org.execute(f.cmd(1,guild,'appoint',(2,'member')),f.now());f.org.initialize()
    assert (2,'deputy') not in f.org.guild_office_snapshot(guild).offices
    passed.append('old one-position unique schema migrates once preserving deputy/delegation; archive never resurrects a later removed office')


def main():
    passed=[]
    with tempfile.TemporaryDirectory() as directory:
        f,family,second,guild=setup(Path(directory)/'state.db');check(f,family,second,guild,passed)
        asyncio.run(owner_check(f,guild,passed));migration(Path(directory)/'migration.db',passed)
    result=dict(passed=passed,source_org_runtime_integrated=True,native_guild_management_routes_tested_here=False,
        native_gui_verified=False,live_store_changed=False,progression='explicit level-four/tenure fixtures only')
    write_json(OUT/'evidence/guild-offices-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
