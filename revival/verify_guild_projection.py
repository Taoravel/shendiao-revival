"""Guild read model and durable family-join handoff through public storage."""
import json
from contextlib import closing
from pathlib import Path
import tempfile
from verify_guild_offices import setup
from inspect_client import OUT,write_json
from faction_domain import OrganizationStore


def initial(f,guild,passed):
    scope=f.org.guild_scope(1,f.epochs[1])
    assert scope[0]==guild
    view=f.org.guild_projection(1,f.epochs[1],*scope,tuple(f.epochs.items()))
    assert view.view.identity==guild and view.view.name=='职位帮派' and view.view.level==4
    assert len(view.members)==18 and {m.family for m in view.members}=={1,3}
    own=next(m for m in view.members if m.role_id==1)
    assert own.guild_position==own.family_position=='leader'
    assert own.name=='费用角色1' and own.school==12 and own.level==40
    assert next(m for m in view.members if m.role_id==16).guild_position=='family_leader'
    assert all(m.metadata==(0,0,0) and m.prestige==(0,0) and m.weekly_dues==m.historical_dues==0 for m in view.members)
    assert all(m.offline_text=='' for m in view.members) and view.authority==0
    passed.append('new guild and admitted family project all members, original positions and explicit new-membership baselines')


def join_handoff(f,family,guild,passed):
    with closing(f.accounts.connect()) as db,db:
        db.execute("INSERT INTO roles(id,account_id,name,school,shape,level) VALUES(19,1111,'后来侠客',12,1010101,40)")
        db.execute("CREATE TRIGGER fixture_guild_writer BEFORE INSERT ON guild_member_state BEGIN SELECT RAISE(ABORT,'family_wrote_guild'); END")
    f.epochs[19]=f.accounts.acquire_lease(1111,19)
    f.org.execute(f.cmd(19,family,'apply'),f.now());f.org.execute(f.cmd(1,family,'review',(19,True)),f.now())
    old=f.org.guild_scope(19,f.epochs[19])
    f.reject(lambda:f.org.guild_projection(19,f.epochs[19],*old,tuple(f.epochs.items())),'guild_member_state_unknown')
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_guild_writer')
    change=f.org.refresh_guild(guild,(1,f.epochs[1]))
    assert len(change.before.members)==18 and len(change.after.members)==19
    view=f.org.guild_projection(19,f.epochs[19],*old,tuple(f.epochs.items()))
    assert len(view.members)==19
    # A progress fixture proves the next membership cannot inherit old dues.
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE guild_member_state SET weekly_dues=?,prestige=12 WHERE guild=? AND role_id=19 AND active=1',(2**40,guild))
    view=f.org.guild_projection(19,f.epochs[19],*old,tuple(f.epochs.items()))
    assert next(m for m in view.members if m.role_id==19).weekly_dues==2**40
    f.org.execute(f.cmd(19,family,'leave'),f.now())
    f.reject(lambda:f.org.guild_projection(19,f.epochs[19],*old,tuple(f.epochs.items())),'not_in_guild')
    change=f.org.refresh_guild(guild);assert len(change.after.members)==18
    f.org.execute(f.cmd(19,family,'apply'),f.now());f.org.execute(f.cmd(1,family,'review',(19,True)),f.now())
    current=f.org.guild_scope(19,f.epochs[19]);assert current!=old
    f.org.refresh_guild(guild)
    f.reject(lambda:f.org.guild_projection(19,f.epochs[19],*old,tuple(f.epochs.items())),'stale_guild_membership')
    view=f.org.guild_projection(19,f.epochs[19],*current,tuple(f.epochs.items()))
    joined=next(m for m in view.members if m.role_id==19)
    assert joined.weekly_dues==0 and joined.prestige==(0,0)
    f.org=OrganizationStore(f.accounts.path,f.policy);f.org.initialize();f.org.refresh_guild(guild)
    assert f.org.guild_projection(19,f.epochs[19],*current,tuple(f.epochs.items()))==view
    passed.append('family join only records its durable handoff; guild owner initializes once, removes departures, fences rejoin and restores after restart')


def scope_and_authority(f,family,second,guild,passed):
    def view(rid):return f.org.guild_projection(rid,f.epochs[rid],*f.org.guild_scope(rid,f.epochs[rid]),tuple(f.epochs.items()))
    f.org.execute(f.cmd(1,guild,'appoint',(2,'deputy')),f.now())
    f.org.execute(f.cmd(1,guild,'set_authority',(2,6,True)),f.now())
    assert view(1).authority==view(2).authority==64 and view(17).authority==0
    scope=f.org.guild_scope(1,f.epochs[1]);old_epoch=f.epochs[1]
    f.epochs[1]=f.accounts.acquire_lease(1111,1)
    f.reject(lambda:f.org.guild_projection(1,old_epoch,*scope,()),'stale_epoch')
    f.org.family_presence(family,1,f.epochs[1],False,f.now())
    offline=f.org.guild_projection(1,f.epochs[1],*scope,())
    assert len(next(m for m in offline.members if m.role_id==1).offline_text)==19
    assert next(m for m in offline.members if m.role_id==17).offline_text=='离线'
    passed.append('only head/deputy see delegated authority; login lease, actual online directory and known/unknown offline times remain distinct')
    old=f.org.guild_scope(17,f.epochs[17])
    f.org.execute(f.cmd(16,guild,'leave',(second,)),f.now());f.org.refresh_guild(guild)
    f.reject(lambda:f.org.guild_scope(17,f.epochs[17]),'not_in_guild')
    f.org.execute(f.cmd(16,guild,'apply'),f.now());f.org.execute(f.cmd(1,guild,'review',(second,True)),f.now())
    current=f.org.guild_scope(17,f.epochs[17]);assert current!=old
    f.reject(lambda:f.org.guild_projection(17,f.epochs[17],*old,()),'stale_guild_membership')
    audience=f.org.guild_audience(guild)
    assert len({m[0] for m in audience.members})==len(audience.members)==19
    saved=view(17)
    f.org=OrganizationStore(f.accounts.path,dict(f.policy,guild_new_member_metadata=[7,8,9]))
    f.org.initialize();f.org.refresh_guild(guild)
    assert view(17)==saved
    passed.append('whole-family re-admission rotates its guild token without duplicate active recipients; changing new-member policy does not rewrite existing values')


def unknown_state(path,passed):
    f,_,_,guild=setup(path);f.org.refresh_guild(guild)
    with closing(f.accounts.connect()) as db,db:db.execute('DELETE FROM guild_member_state WHERE guild=? AND role_id=12',(guild,))
    f.org.initialize()
    f.reject(lambda:f.org.refresh_guild(guild),'guild_member_state_unknown')
    f.reject(lambda:f.org.guild_projection(1,f.epochs[1],*f.org.guild_scope(1,f.epochs[1]),()),'guild_member_state_unknown')
    with closing(f.accounts.connect()) as db,db:
        db.execute('DELETE FROM guild_member_state WHERE guild=?',(guild,))
        db.execute('DELETE FROM guild_view_state WHERE guild=?',(guild,))
    f.org.initialize()
    f.reject(lambda:f.org.refresh_guild(guild),'guild_panel_unknown')
    f.reject(lambda:f.org.guild_projection(1,f.epochs[1],*f.org.guild_scope(1,f.epochs[1]),()),'guild_panel_unknown')
    passed.append('missing previously consumed member data and legacy unknown guild panels are deferred, never reconstructed as zero on startup/read')


def main():
    passed=[]
    with tempfile.TemporaryDirectory() as directory:
        f,family,second,guild=setup(Path(directory)/'state.db')
        initial(f,guild,passed)
        join_handoff(f,family,guild,passed)
        scope_and_authority(f,family,second,guild,passed)
        unknown_state(Path(directory)/'unknown.db',passed)
    report=dict(passed=passed,native_gui_verified=False,native_guild_routes_tested_here=False,live_store_changed=False)
    write_json(OUT/'evidence/guild-projection-verification.json',report);print(json.dumps(report))


if __name__=='__main__':main()
