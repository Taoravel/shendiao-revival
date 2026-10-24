"""Guild research/practice through the public organization transaction seam."""
import asyncio
from dataclasses import replace
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
from verify_guild_offices import setup
from inspect_client import OUT,write_json
from faction_domain import OrganizationStore


def research(f,guild,passed):
    before=f.org.snapshot(guild)[0]['revision']
    command=f.cmd(1,guild,'set_research',(310103,))
    result=f.org.execute(command,f.now())
    assert result['revision']==before+1
    assert f.org.guild_training_snapshot(guild).research_skill==310103
    assert f.org.execute(command,f.now())==result
    assert f.org.snapshot(guild)[0]['revision']==before+1
    passed.append('head selects original furniture-production research; persisted selection and receipt replay agree')


def delegated_research(f,guild,passed):
    def run(actor,op,args=()):return f.org.execute(f.cmd(actor,guild,op,args),f.now())
    run(1,'appoint',(2,'deputy'))
    f.reject(lambda:run(2,'set_research',(300101,)),'permission_denied')
    run(1,'set_authority',(2,0,True))
    run(2,'set_research',(300101,))
    assert f.org.guild_training_snapshot(guild).research_skill==300101
    run(1,'set_authority',(2,0,False));run(1,'set_authority',(2,6,True))
    f.reject(lambda:run(2,'set_research',(310103,)),'permission_denied')
    assert f.org.guild_training_snapshot(guild).research_skill==300101
    passed.append('deputy research requires its own bit zero; revocation and appointment-only authority do not allow research')


def practice_opening(f,guild,passed):
    # Level change is a progression fixture; native level-three UI permits two.
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE organizations SET level=3 WHERE id=?',(guild,))
        db.execute('UPDATE guild_assets SET funds=15000000 WHERE guild=?',(guild,))
    def run(actor,skill,enabled):return f.org.execute(f.cmd(actor,guild,'set_practice_open',(skill,enabled)),f.now())
    run(1,360001,True);run(1,360002,True)
    f.reject(lambda:run(1,360003,True),'practice_slots_full')
    assert f.org.guild_training_snapshot(guild).open_practices==(360001,360002)
    run(1,360002,False);run(1,360003,True)
    assert f.org.guild_training_snapshot(guild).open_practices==(360001,360003)
    f.reject(lambda:run(2,360003,False),'permission_denied')
    f.org.execute(f.cmd(1,guild,'set_authority',(2,1,True)),f.now())
    run(2,360003,False);run(2,360007,True)
    assert f.org.guild_training_snapshot(guild).open_practices==(360001,360007)
    f.org.execute(f.cmd(1,guild,'set_authority',(2,1,False)),f.now())
    f.reject(lambda:run(2,360001,False),'permission_denied')
    assert f.org.guild_assets(guild).funds==3_000_000
    passed.append('level-three guild opens two practice types, close frees a slot, and deputy requires independent practice bit one')


def opening_costs(path,passed):
    f,_,_,guild=setup(path)
    command=f.cmd(1,guild,'set_practice_open',(360001,True))
    cash=f.cash(1)
    f.reject(lambda:f.org.execute(command,f.now()),'insufficient_guild_funds')
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_assets SET funds=5999999 WHERE guild=?',(guild,))
    f.reject(lambda:f.org.execute(command,f.now()),'insufficient_guild_funds')
    assert f.org.guild_training_snapshot(guild).open_practices==()
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_assets SET funds=6000000 WHERE guild=?',(guild,))
    result=f.org.execute(command,f.now())
    assert f.org.guild_assets(guild).funds==3_000_000 and f.cash(1)==cash
    assert f.org.execute(command,f.now())==result
    assert f.org.guild_assets(guild).funds==3_000_000
    f.org.execute(f.cmd(1,guild,'set_practice_open',(360001,False)),f.now())
    assert f.org.guild_assets(guild).funds==3_000_000
    f.reject(lambda:f.org.execute(f.cmd(1,guild,'set_practice_open',(360001,True)),f.now()),'insufficient_guild_funds')
    passed.append('opening requires six million guild funds and spends three million once; closing uses explicit zero fee; role cash is unchanged')


def failure_recovery(f,family,guild,passed):
    def run(actor,op,args):return f.org.execute(f.cmd(actor,guild,op,args),f.now())
    before=f.org.guild_training_snapshot(guild);revision=f.org.snapshot(guild)[0]['revision']
    funds=f.org.guild_assets(guild);cash=f.wallet(1)
    for op,args,reason in (
        ('set_research',(360001,),'invalid_research_skill'),
        ('set_research',(True,),'invalid_research_skill'),
        ('set_research',(300101,),'research_unchanged'),
        ('set_practice_open',(380001,True),'invalid_practice_choice'),
        ('set_practice_open',(360004,1),'invalid_practice_choice'),
        ('set_practice_open',(360001,True),'practice_already_open'),
        ('set_practice_open',(360004,False),'practice_already_closed')):
        f.reject(lambda:run(1,op,args),reason)
    f.reject(lambda:run(17,'set_research',(310103,)),'permission_denied')
    f.reject(lambda:f.org.execute(f.cmd(1,family,'set_research',(310103,)),f.now()),'invalid_organization_kind')
    assert f.org.guild_training_snapshot(guild)==before and f.org.guild_assets(guild)==funds and f.wallet(1)==cash
    assert f.org.snapshot(guild)[0]['revision']==revision
    passed.append('invalid skills, flags, repeated state, ordinary member and wrong organization preserve settings, revision and both fund pools')
    # Failure occurs after setting and ledger mutation, at their shared receipt.
    run(1,'set_practice_open',(360007,False))
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE guild_assets SET funds=6000000 WHERE guild=?',(guild,))
        db.execute("CREATE TRIGGER fixture_training_receipt BEFORE INSERT ON organization_receipts WHEN NEW.request_id='training-atomic' BEGIN SELECT RAISE(ABORT,'fixture_training_receipt'); END")
    before=f.org.guild_training_snapshot(guild);revision=f.org.snapshot(guild)[0]['revision']
    command=f.cmd(1,guild,'set_practice_open',(360004,True),'training-atomic')
    try:f.org.execute(command,f.now())
    except sqlite3.IntegrityError:pass
    else:raise AssertionError('Injected receipt failure ignored')
    assert f.org.guild_training_snapshot(guild)==before and f.org.guild_assets(guild).funds==6_000_000
    assert f.org.snapshot(guild)[0]['revision']==revision
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_training_receipt')
    f.org.execute(command,f.now());assert f.org.guild_assets(guild).funds==3_000_000
    f.reject(lambda:f.org.execute(replace(command,args=(360003,True)),f.now()),'request_id_conflict')
    passed.append('late receipt failure rolls back practice, three-million debit, ledger and revision; retry commits once and altered-key replay rejects')
    stale=f.cmd(1,guild,'set_research',(310103,))
    f.epochs[1]=f.accounts.acquire_lease(1111,1)
    f.reject(lambda:f.org.execute(stale,f.now()),'stale_epoch')
    run(1,'set_research',(310103,));saved=f.org.guild_training_snapshot(guild)
    f.org=OrganizationStore(f.accounts.path,f.policy);f.org.initialize()
    assert f.org.guild_training_snapshot(guild)==saved
    passed.append('old login epoch is rejected; replacement lease and startup preserve selected research and open practices')
    run(1,'set_authority',(2,0,True))
    f.org.execute(f.cmd(2,family,'leave'),f.now())
    f.reject(lambda:run(2,'set_research',(300101,)),'not_member')
    f.org.execute(f.cmd(2,family,'apply'),f.now());f.org.execute(f.cmd(1,family,'review',(2,True)),f.now())
    f.reject(lambda:run(2,'set_research',(300101,)),'permission_denied')
    assert f.org.guild_training_snapshot(guild)==saved
    passed.append('deputy loses research authority immediately on family departure and does not recover it by rejoining')


async def owner_check(f,guild,passed):
    from game_runtime import GameRuntime
    from faction_runtime import OrganizationOutcome
    import runtime_storage
    # One remaining slot and exactly one allowed paid opening at six million.
    f.org.execute(f.cmd(1,guild,'set_practice_open',(360004,False)),f.now())
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_assets SET funds=6000000 WHERE guild=?',(guild,))
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        results=await asyncio.gather(*(runtime.social_runtime.organizations.command(
            f.cmd(1,guild,'set_practice_open',(skill,True)),f.now()) for skill in (360002,360003)),return_exceptions=True)
        assert sum(isinstance(r,OrganizationOutcome) for r in results)==1
        assert [str(r) for r in results if isinstance(r,Exception)]==['practice_slots_full']
        assert len(f.org.guild_training_snapshot(guild).open_practices)==2
        assert f.org.guild_assets(guild).funds==3_000_000
    finally:await runtime.close()
    passed.append('actual bounded organization owner serializes competing final paid practice slot: one success and one debit')


def unknown_legacy(path,passed):
    f,_,_,guild=setup(path)
    with closing(f.accounts.connect()) as db,db:db.execute('DELETE FROM guild_training WHERE guild=?',(guild,))
    f.org.initialize()
    f.reject(lambda:f.org.guild_training_snapshot(guild),'guild_training_state_unknown')
    f.reject(lambda:f.org.execute(f.cmd(1,guild,'set_research',(310103,)),f.now()),'guild_training_state_unknown')
    assert f.org.guild_assets(guild).funds==0
    passed.append('unknown legacy settings are not initialized or granted by startup or a failed command')


def main():
    passed=[]
    with tempfile.TemporaryDirectory() as directory:
        f,family,_,guild=setup(Path(directory)/'state.db')
        research(f,guild,passed)
        delegated_research(f,guild,passed)
        opening_costs(Path(directory)/'costs.db',passed)
        practice_opening(f,guild,passed)
        failure_recovery(f,family,guild,passed)
        asyncio.run(owner_check(f,guild,passed))
        unknown_legacy(Path(directory)/'unknown.db',passed)
    report=dict(passed=passed,source_org_owner_integrated=True,native_gui_verified=False,native_npc_routes_integrated=False,
        personal_training_integrated=False,research_progression_integrated=False,live_store_changed=False,
        current_seven_type_capacity_source='inferred from verified legacy level-minus-one path',
        fixtures='explicit disposable guild levels and guild-funds updates only')
    write_json(OUT/'evidence/guild-training-verification.json',report)
    print(json.dumps(report))


if __name__=='__main__':main()
