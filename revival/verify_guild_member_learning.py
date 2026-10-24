"""Guild member learning through real owner transactions and disposable stores."""
from pathlib import Path
from contextlib import closing
from dataclasses import replace
import asyncio,json,tempfile,sqlite3,time,threading
from inspect_client import OUT,write_json
from verify_guild_maintenance import make as maintenance_fixture


def baseline(path):
    import role_life_skills as life
    f,guild,start=maintenance_fixture(path)
    rules=life.load_rules()
    with closing(f.accounts.connect()) as db,db:life.prepare(db)
    f.reject(lambda:f.tx(1,lambda db:life.read(db,1111,1,f.epochs[1],rules)),'life_skill_profile_unknown')
    known=tuple(life.LifeSkill(s,0,0) for s in rules.skills)
    current=f.tx(1,lambda db:life.initialize(db,1111,1,f.epochs[1],known,'explicit_migration',rules))
    assert current.revision==0 and current.skills==known
    assert f.tx(1,lambda db:life.read(db,1111,1,f.epochs[1],rules))==current
    f.reject(lambda:f.tx(1,lambda db:life.initialize(db,1111,1,f.epochs[1],known[:-1],'explicit_migration',rules)),
        'complete_life_skill_baseline_required')
    f.reject(lambda:f.tx(1,lambda db:life.initialize(db,1111,1,f.epochs[1],
        (life.LifeSkill(known[0].skill,1,0),*known[1:]),'explicit_migration',rules)),'life_skill_baseline_cannot_reset')
    return f,guild,start,rules


def role_costs(path):
    from inventory import Inventory
    from currency import CurrencyRules,initialize_wallet,read_wallet
    from types import MappingProxyType
    import npc_depot,role_learning_costs as costs
    f,guild,start,rules=baseline(path)
    f.accounts.inventory_config=Inventory.prepare(f.accounts)
    inv=Inventory(f.accounts,1111,16,epoch=f.epochs[16],currency_rules=f.rules)
    # Explicit fixture funding map: permitting bound_silver for skill_training
    # does not change the production currency policy or grant a real wallet.
    spending=dict(f.rules.spend_purposes);spending['bound_silver']=frozenset(('skill_training',))
    currency=CurrencyRules(f.rules.revision,f.rules.currencies,f.rules.task_fields,MappingProxyType(spending))
    with closing(f.accounts.connect()) as db,db:
        npc_depot.prepare(db);costs.prepare(db)
        db.execute('CREATE TABLE IF NOT EXISTS role_progress(role_id INTEGER PRIMARY KEY,experience INTEGER NOT NULL)')
        db.execute('INSERT INTO role_progress VALUES(16,1000)')
        # Isolated payment fixture, not an initialization/reset Interface.
        db.execute("UPDATE role_wallet_balances SET balance=CASE currency WHEN 'bound_silver' THEN 3 WHEN 'cash' THEN 5 ELSE balance END WHERE role_id=16")
    f.tx(16,lambda db:npc_depot.initialize(db,inv,7,'explicit_migration'))
    paid=f.tx(16,lambda db:costs.pay(db,inv,'fixture-source','a'*64,10,16,currency))
    assert paid.spent==(('bound_silver',3),('cash',5),('depot_cash',2))
    assert (paid.experience_before,paid.experience_after,paid.depot_before,paid.depot_after)==(1000,984,7,5)
    assert f.tx(16,lambda db:costs.pay(db,inv,'fixture-source','a'*64,10,16,currency))==paid
    current=f.tx(16,lambda db:costs.current(db,inv,currency))
    assert (current.experience,current.depot)==(984,5)
    f.reject(lambda:f.tx(16,lambda db:costs.pay(db,inv,'fixture-source','b'*64,10,16,currency)),'learning_cost_intent_conflict')
    f.reject(lambda:f.tx(16,lambda db:costs.pay(db,inv,'too-expensive','c'*64,6,16,currency)),'learning_money_insufficient')
    assert f.tx(16,lambda db:costs.current(db,inv,currency))==current


def fixture_policy():
    # Every field mapping and limit below is an explicit local adoption;
    # unbound original server semantics must not become production defaults.
    return dict(revision='isolated-member-learning-1',origin='explicit_test_fixture',level_cap=3,
        minimum_role_level=30,pending_limit=2,minimum_wallet=10000,prestige_need_field='inBangGongNeed',
        prestige_spend_field='inBG',resources_field='inBR',proficiency_field='inSkillLevel')


def learning(path):
    from faction_domain import OrganizationStore
    from verify_guild_maintenance import fixture_policy as maintenance_policy
    from verify_guild_buildings import fixture_policy as buildings
    from verify_guild_research import fixture_policy as research
    from guild_research import ResearchAward
    from inventory import Inventory
    from currency import CurrencyRules
    from types import MappingProxyType
    import guild_member_learning as guild,role_life_skills as life,npc_depot
    f,identity,start,life_rules=baseline(path)
    f.org=OrganizationStore(path,f.policy,research_policy=research(f),building_policy=buildings(),
        guild_maintenance_policy=maintenance_policy(),member_learning_policy=fixture_policy());f.org.initialize()
    f.org.execute(f.cmd(1,identity,'set_research',(300101,)),f.now())
    f.org.award_guild_research(ResearchAward(identity,'explicit-research-source',10,f.now()+5000),f.now())
    f.accounts.inventory_config=Inventory.prepare(f.accounts)
    inv=Inventory(f.accounts,1111,1,epoch=f.epochs[1],currency_rules=f.rules)
    with closing(f.accounts.connect()) as db,db:
        npc_depot.prepare(db)
        db.execute('INSERT INTO role_progress(role_id,experience) VALUES(1,1000) ON CONFLICT(role_id) DO UPDATE SET experience=1000')
        db.execute('UPDATE guild_member_state SET prestige=50 WHERE guild=? AND role_id=1',(identity,))
        db.execute("UPDATE role_wallet_balances SET balance=CASE currency WHEN 'bound_silver' THEN 6000 WHEN 'cash' THEN 5000 ELSE balance END WHERE role_id=1")
    f.tx(1,lambda db:npc_depot.initialize(db,inv,10,'explicit_migration'))
    spending=dict(f.rules.spend_purposes);spending['bound_silver']=frozenset(('skill_training',))
    currency=CurrencyRules(f.rules.revision,f.rules.currencies,f.rules.task_fields,MappingProxyType(spending))
    command=f.cmd(1,identity,'reserve_member_learning',(300101,0));f.org.execute(command,f.now())
    grant=f.org.guild_learning_permit(1,f.epochs[1],identity,command.request_id)
    assert (grant.before.level,grant.fee.money,grant.fee.experience,grant.fee.prestige_spend,grant.fee.resources)==(0,3,16,1,2)
    assert f.org.guild_maintenance_snapshot(identity).resources.amount==3
    result=f.tx(1,lambda db:guild.settle(db,inv,identity,command.request_id,f.now(),life_rules,
        f.org.learning_rules,currency,popularity=12))
    assert result.state.skills[0]==life.LifeSkill(300101,1,0)
    assert result.cost.spent==(('bound_silver',3),)
    assert result.balances.experience==984 and result.balances.depot==10
    f.org.execute(f.cmd(1,identity,'resolve_member_learning',(command.request_id,)),f.now())
    assert f.org.guild_learning_permit(1,f.epochs[1],identity,command.request_id).status=='committed'
    assert f.tx(1,lambda db:guild.settle(db,inv,identity,command.request_id,f.now(),life_rules,
        None,currency,popularity=None))==result
    return f,identity,start,life_rules,inv,currency


def failure_recovery(path):
    import guild_member_learning as g,role_life_skills as life,role_learning_costs as costs
    from guild_research import ResearchAward
    f,guild,_,rules,inv,currency=learning(path)
    f.org.award_guild_research(ResearchAward(guild,'explicit-research-two',20,f.now()+5000),f.now())
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE guild_resources SET amount=20 WHERE guild=?',(guild,))
        db.execute("UPDATE role_wallet_balances SET balance=10000 WHERE role_id=1 AND currency='cash'")
    before=f.tx(1,lambda db:costs.current(db,inv,currency))
    state=f.tx(1,lambda db:life.read(db,1111,1,f.epochs[1],rules))
    c=f.cmd(1,guild,'reserve_member_learning',(300101,1));f.org.execute(c,f.now())
    for popularity in (None,11):
        f.reject(lambda:f.tx(1,lambda db:g.settle(db,inv,guild,c.request_id,f.now(),rules,f.org.learning_rules,
            currency,popularity=popularity)),'member_learning_popularity_')
    assert f.tx(1,lambda db:costs.current(db,inv,currency))==before
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_learning_tail BEFORE INSERT ON role_member_learning_receipts BEGIN SELECT RAISE(ABORT,'learning_tail_failure'); END")
    try:
        try:f.tx(1,lambda db:g.settle(db,inv,guild,c.request_id,f.now(),rules,f.org.learning_rules,currency,popularity=12))
        except sqlite3.IntegrityError as error:assert 'learning_tail_failure' in str(error)
        else:raise AssertionError('role learning partial commit')
        assert f.tx(1,lambda db:costs.current(db,inv,currency))==before
        assert f.tx(1,lambda db:life.read(db,1111,1,f.epochs[1],rules))==state
    finally:
        with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_learning_tail')
    f.org.execute(f.cmd(1,guild,'resolve_member_learning',(c.request_id,)),f.now())
    assert f.org.guild_maintenance_snapshot(guild).resources.amount==20
    assert f.org.guild_learning_permit(1,f.epochs[1],guild,c.request_id).status=='cancelled'
    f.reject(lambda:f.tx(1,lambda db:g.settle(db,inv,guild,c.request_id,f.now(),rules,f.org.learning_rules,currency,popularity=12)),
        'member_learning_permit_expired_or_inactive')
    first=f.cmd(1,guild,'reserve_member_learning',(300101,1));second=f.cmd(1,guild,'reserve_member_learning',(300101,1))
    f.org.execute(first,f.now());f.org.execute(second,f.now())
    result=f.tx(1,lambda db:g.settle(db,inv,guild,first.request_id,f.now(),rules,f.org.learning_rules,currency,popularity=12))
    assert result.state.skills[0].level==2 and result.balances.experience==951
    f.reject(lambda:f.tx(1,lambda db:g.settle(db,inv,guild,second.request_id,f.now(),rules,f.org.learning_rules,currency,popularity=12)),
        'life_skill_revision_conflict')
    f.org.execute(f.cmd(1,guild,'resolve_member_learning',(second.request_id,)),f.now())
    f.org.execute(f.cmd(1,guild,'resolve_member_learning',(first.request_id,)),f.now())
    assert f.org.guild_maintenance_snapshot(guild).resources.amount==18
    assert f.tx(1,lambda db:g.settle(db,inv,guild,first.request_id,f.now(),rules,None,currency,popularity=None))==result


async def runtime_login(f,guild):
    from game_runtime import GameRuntime
    from faction_runtime import OrganizationRuntime
    from verify_runtime import Peer
    from verify_guild_maintenance import fixture_policy as maintenance_policy
    from verify_guild_buildings import fixture_policy as buildings
    from verify_guild_research import fixture_policy as research
    import runtime_storage
    from guild_research import ResearchAward
    f.org.award_guild_research(ResearchAward(guild,'runtime-explicit-research-two',20,f.now()+5000),f.now())
    pending=f.cmd(1,guild,'reserve_member_learning',(300101,1));f.org.execute(pending,f.now())
    assert f.org.guild_maintenance_snapshot(guild).resources.amount==1
    rt=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    await rt.social_runtime.organizations.close()
    policy=dict(f.policy);policy['family_maintenance']=dict(policy['family_maintenance'],scheduler_enabled=False)
    rt.social_runtime.organizations=OrganizationRuntime(rt.social_runtime,policy,research_policy=research(f),
        building_policy=buildings(),guild_maintenance_policy=maintenance_policy(),member_learning_policy=fixture_policy())
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0])
        await asyncio.wait_for(rt.social_runtime.organizations.guild.idle(),5)
        updates=[body for kind,body in peer.initial+await peer.take() if kind==0xc36b7]
        import struct
        decoded=[struct.unpack('>iii',body) for body in updates]
        assert (300101,1,0) in decoded and len([s for s,_,_ in decoded if s in f.org.life_rules.skills])==14
        assert f.org.guild_maintenance_snapshot(guild).resources.amount==3
        epoch=rt.online_snapshot()[1].login_epoch
        assert f.org.guild_learning_permit(1,epoch,guild,pending.request_id).status=='cancelled'
        owner=rt.social_runtime.organizations;f.epochs[1]=epoch
        entered,released=threading.Event(),threading.Event();original=owner.store.execute
        def blocked(c,now):
            if c.operation=='reserve_member_learning':
                entered.set()
                if not released.wait(5):raise TimeoutError('member learning fixture not released')
            return original(c,now)
        owner.store.execute=blocked
        c=f.cmd(1,guild,'reserve_member_learning',(300101,1))
        jobs=[asyncio.create_task(owner.command(c,f.now())) for _ in range(8)]
        try:
            assert await asyncio.to_thread(entered.wait,2)
            family=f.org.membership(1,epoch,'family')
            await asyncio.wait_for(owner.command(f.cmd(1,family,'set_family_products',(1,-1)),f.now()),2)
            assert (100,b'free') in await asyncio.wait_for(peer.request(100,b'free'),2)
            assert not released.is_set()
        finally:released.set()
        results=await asyncio.gather(*jobs)
        assert all(v==results[0] for v in results)
        assert f.org.guild_maintenance_snapshot(guild).resources.amount==1
        assert len(f.org.pending_member_learning(1,epoch))==1
        await owner.command(f.cmd(1,guild,'resolve_member_learning',(c.request_id,)),f.now())
        assert f.org.guild_maintenance_snapshot(guild).resources.amount==3
        import role_practice as practice
        practice_rules=f.org.practice_rules
        f.tx(1,lambda db:practice.initialize(db,1111,1,epoch,tuple(practice.PracticeState(s,0,0,0)
            for s in practice_rules.skills),'explicit_migration',practice_rules))
    finally:await rt.close()
    rt=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        # Disabling learning must not erase already-known skills on login.
        guild_runtime=rt.social_runtime.organizations.guild;original=guild_runtime.store.life_skill_states
        def unavailable(*args):raise sqlite3.OperationalError('fixture optional life presentation unavailable')
        guild_runtime.store.life_skill_states=unavailable
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0])
        decoded=[struct.unpack('>iii',body) for kind,body in peer.initial+await peer.take() if kind==0xc36b7]
        assert {s for s,_,_ in decoded if 360001<=s<=360007}==set(range(360001,360008))
        guild_runtime.store.life_skill_states=original
        await guild_runtime.initial(rt.social_runtime.endpoints[1])
        decoded=[struct.unpack('>iii',body) for kind,body in await peer.take() if kind==0xc36b7]
        assert (300101,1,0) in decoded
    finally:await rt.close()


def npc_purchase(path):
    from npc_services import NpcServices,ServiceBinding
    from world_npcs import NpcInteraction
    from world_owner import MapAddress,Location
    from guild_research import ResearchAward
    import member_learning_npc as npc,life_skill_protocol as wire,role_life_skills as life,role_learning_costs as costs
    import struct
    f,guild,_,rules,inv,currency=learning(path)
    f.org.award_guild_research(ResearchAward(guild,'npc-explicit-research-two',20,f.now()+5000),f.now())
    address=MapAddress(1394,2**40+1394,0);location=Location(1,f.epochs[1],address,7,1680,5311)
    residence=npc.LearningResidence(guild,address,'explicit-fixture-residence-1','isolated directory fixture only')
    entity=2**48+1394
    services=NpcServices({121:'学习生活技能'},(ServiceBinding(10076,121,'guild_member_learning','designed','isolated fixture only'),))
    proof=NpcInteraction('learning-npc',1,f.epochs[1],address,7,entity,10076,1)
    command=services.plan(struct.pack('>qi',entity,121),proof,location,request_id=proof.source_id,now_ms=f.now(),deadline_ms=f.now()+5000)
    panel=f.tx(1,lambda db:npc.open_panel(db,1111,command,location,residence,f.now(),f.org.learning_rules))
    assert len(panel)==15 and panel[-1][0]==wire.ASSIST_SKILL_MAX_LEVELS
    assert panel[-1][1]==wire.study_panel(entity,tuple((s,2 if s==300101 else 0) for s in rules.skills))
    body=struct.pack('>QiB',entity,300101,0)
    for popularity in (None,11):
        f.reject(lambda:f.tx(1,lambda db:npc.prepare_purchase(db,1111,command,location,residence,body,f.now(),f.org.learning_rules,
            popularity=popularity)),'member_learning_popularity_')
    for invalid in (struct.pack('>QiB',entity+1,300101,0),struct.pack('>QiB',entity,360001,0),struct.pack('>QiB',entity,300101,1)):
        f.reject(lambda:f.tx(1,lambda db:npc.prepare_purchase(db,1111,command,location,residence,invalid,f.now(),f.org.learning_rules,
            popularity=12)),'unsupported_or_foreign_member_learning_request')
    ready=f.tx(1,lambda db:npc.prepare_purchase(db,1111,command,location,residence,body,f.now(),f.org.learning_rules,popularity=12))
    f.org.execute(ready.command,f.now())
    before=f.tx(1,lambda db:costs.current(db,inv,currency));skills=f.tx(1,lambda db:life.read(db,1111,1,f.epochs[1],rules))
    def broken(*args,**kw):raise ValueError('fixture learning precommit encoding failure')
    f.reject(lambda:f.tx(1,lambda db:npc.finish_purchase(db,1111,ready,command,location,residence,f.now(),f.org.learning_rules,
        inv,currency,popularity=12,precommit=broken)),'fixture learning precommit')
    assert f.tx(1,lambda db:costs.current(db,inv,currency))==before
    assert f.tx(1,lambda db:life.read(db,1111,1,f.epochs[1],rules))==skills
    f.reject(lambda:f.tx(1,lambda db:npc.finish_purchase(db,1111,ready,replace(command,position_version=8),replace(location,version=8),
        residence,f.now(),f.org.learning_rules,inv,currency,popularity=12)),'member_learning_prepared_scope_changed')
    f.reject(lambda:f.tx(1,lambda db:npc.finish_purchase(db,1111,ready,command,location,
        replace(residence,generation='renewed-fixture-generation'),f.now(),f.org.learning_rules,inv,currency,popularity=12)),
        'member_learning_prepared_scope_changed')
    done=f.tx(1,lambda db:npc.finish_purchase(db,1111,ready,command,location,residence,f.now(),f.org.learning_rules,inv,currency,popularity=12))
    assert done.result.state.skills[0].level==2 and done.result.balances.experience==951
    assert len(done.messages)==17 and done.messages[-1][0]==0xc000d
    f.org.execute(f.cmd(1,guild,'resolve_member_learning',(command.request_id,)),f.now())
    assert f.tx(1,lambda db:npc.finish_purchase(db,1111,ready,command,location,residence,f.now(),f.org.learning_rules,
        inv,currency,popularity=None))==done


def wallet_threshold(path):
    import guild_member_learning as g,role_learning_costs as costs
    from guild_research import ResearchAward
    f,guild,_,rules,inv,currency=learning(path)
    f.org.award_guild_research(ResearchAward(guild,'threshold-research-two',20,f.now()+5000),f.now())
    c=f.cmd(1,guild,'reserve_member_learning',(300101,1));f.org.execute(c,f.now())
    with closing(f.accounts.connect()) as db,db:
        db.execute("UPDATE role_wallet_balances SET balance=CASE currency WHEN 'bound_silver' THEN 0 WHEN 'cash' THEN 9999 ELSE balance END WHERE role_id=1")
    before=f.tx(1,lambda db:costs.current(db,inv,currency))
    f.reject(lambda:f.tx(1,lambda db:g.settle(db,inv,guild,c.request_id,f.now(),rules,f.org.learning_rules,currency,popularity=12)),
        'member_learning_minimum_wallet')
    assert f.tx(1,lambda db:costs.current(db,inv,currency))==before
    with closing(f.accounts.connect()) as db,db:
        db.execute("UPDATE role_wallet_balances SET balance=10000 WHERE role_id=1 AND currency='cash'")
    done=f.tx(1,lambda db:g.settle(db,inv,guild,c.request_id,f.now(),rules,f.org.learning_rules,currency,popularity=12))
    assert done.cost.spent==(('cash',6),)
    assert next(b.balance for b in done.balances.wallet if b.currency=='cash')==9994


def high_level_depot(path):
    from verify_faction_payments import Fixture
    from faction_domain import OrganizationStore
    from verify_guild_maintenance import fixture_policy as maintenance_policy
    from verify_guild_buildings import fixture_policy as buildings
    from guild_research_protocol import RESEARCH_SKILLS
    from guild_research import ResearchAward
    from inventory import Inventory
    from currency import CurrencyRules
    from types import MappingProxyType
    import guild_member_learning as g,role_life_skills as life,npc_depot
    f=Fixture(path);f.policy['guild_initial_funds']=10000000;f.policy['guild_funds_origin']='explicit_test_fixture'
    r=dict(revision='explicit-high-research-fixture',origin='explicit_test_fixture',costs=tuple((s,(1,)*155) for s in sorted(RESEARCH_SKILLS)))
    f.org=OrganizationStore(path,f.policy,research_policy=r,building_policy=buildings(),
        guild_maintenance_policy=dict(maintenance_policy(),initial_resources=100),member_learning_policy=dict(fixture_policy(),level_cap=155))
    f.org.initialize();c=f.family();f.fund(c);family=f.org.execute(c,f.now())['organization']
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET level=3 WHERE id=?',(family,))
    create=f.cmd(1,family,'create_guild',('高阶测试','同心协力',c.args[2]));f.fund(create)
    guild=f.org.execute(create,f.now())['organization'];rules=f.org.life_rules
    f.tx(1,lambda db:life.initialize(db,1111,1,f.epochs[1],tuple(life.LifeSkill(s,154,2250) if s==300101 else life.LifeSkill(s,0,0)
        for s in rules.skills),'explicit_migration',rules))
    f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
    f.org.award_guild_research(ResearchAward(guild,'explicit-high-research-source',155,f.now()+5000),f.now())
    f.accounts.inventory_config=Inventory.prepare(f.accounts)
    inv=Inventory(f.accounts,1111,1,epoch=f.epochs[1],currency_rules=f.rules)
    with closing(f.accounts.connect()) as db,db:
        npc_depot.prepare(db)
        db.execute('INSERT INTO role_progress VALUES(1,22060446)')
        db.execute('UPDATE guild_member_state SET prestige=775 WHERE guild=? AND role_id=1',(guild,))
        db.execute("UPDATE role_wallet_balances SET balance=CASE currency WHEN 'bound_silver' THEN 2000 WHEN 'cash' THEN 8000 ELSE balance END WHERE role_id=1")
    f.tx(1,lambda db:npc_depot.initialize(db,inv,685472,'explicit_migration'))
    spending=dict(f.rules.spend_purposes);spending['bound_silver']=frozenset(('skill_training',))
    currency=CurrencyRules(f.rules.revision,f.rules.currencies,f.rules.task_fields,MappingProxyType(spending))
    c=f.cmd(1,guild,'reserve_member_learning',(300101,0));f.org.execute(c,f.now())
    result=f.tx(1,lambda db:g.settle(db,inv,guild,c.request_id,f.now(),rules,f.org.learning_rules,currency,popularity=0))
    assert result.state.skills[0]==life.LifeSkill(300101,155,2250)
    assert result.cost.spent==(('bound_silver',2000),('cash',8000),('depot_cash',685472))
    assert (result.balances.experience,result.balances.depot)==(0,0)
    assert f.org.guild_maintenance_snapshot(guild).resources.amount==36
    f.org.execute(f.cmd(1,guild,'resolve_member_learning',(c.request_id,)),f.now())


def membership_and_orphans(path):
    from inventory import Inventory
    import guild_member_learning as g,role_life_skills as life
    f,guild,_,rules,_,currency=learning(path)
    f.tx(2,lambda db:life.initialize(db,1111,2,f.epochs[2],tuple(life.LifeSkill(s,0,0) for s in rules.skills),'explicit_migration',rules))
    inv=Inventory(f.accounts,1111,2,epoch=f.epochs[2],currency_rules=currency)
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_member_state SET prestige=50 WHERE guild=? AND role_id=2',(guild,))
    c=f.cmd(2,guild,'reserve_member_learning',(300101,0));f.org.execute(c,f.now())
    family=f.org.membership(2,f.epochs[2],'family')
    f.org.execute(f.cmd(2,family,'leave'),f.now())
    f.org.execute(f.cmd(2,family,'apply'),f.now());f.org.execute(f.cmd(1,family,'review',(2,True)),f.now())
    f.org.refresh_guild(guild)
    f.reject(lambda:f.tx(2,lambda db:g.settle(db,inv,guild,c.request_id,f.now(),rules,f.org.learning_rules,currency,popularity=12)),
        'member_learning_membership_changed')
    f.org.execute(f.cmd(2,guild,'resolve_member_learning',(c.request_id,)),f.now())
    current=f.org.guild_scope(2,f.epochs[2])
    projected=f.org.guild_projection(2,f.epochs[2],guild,*current[1:],())
    assert next(m.prestige for m in projected.members if m.role_id==2)[0]==0
    assert f.org.guild_maintenance_snapshot(guild).resources.amount==3
    assert f.tx(2,lambda db:life.read(db,1111,2,f.epochs[2],rules)).skills[0].level==0


def receipt_and_growth(path):
    from guild_research import ResearchAward
    from role_growth import initialize_growth,load_growth_rules,read_growth,plan_growth_credit,apply_growth_plan,prepare_growth_storage
    from progression import credit_experience
    import guild_member_learning as g,role_learning_costs as costs
    f,guild,_,rules,inv,currency=learning(path)
    f.org.award_guild_research(ResearchAward(guild,'growth-research-two',20,f.now()+5000),f.now())
    with closing(f.accounts.connect()) as db,db:prepare_growth_storage(db)
    growth_rules=load_growth_rules()
    before=f.tx(1,lambda db:initialize_growth(db,1111,1,f.epochs[1],growth_rules,expected_level=40,free_points=0))
    proposal=plan_growth_credit(before,0,growth_rules)
    c=f.cmd(1,guild,'reserve_member_learning',(300101,1));f.org.execute(c,f.now())
    paid=f.tx(1,lambda db:g.settle(db,inv,guild,c.request_id,f.now(),rules,f.org.learning_rules,currency,popularity=12))
    assert paid.balances.experience==951
    after=f.tx(1,lambda db:read_growth(db,1111,1))
    assert (after.level,after.revision,after.automatic_points,after.allocated_points)==(
        before.level,before.revision,before.automatic_points,before.allocated_points)
    f.reject(lambda:f.tx(1,lambda db:apply_growth_plan(db,1111,1,f.epochs[1],proposal,'stale-growth-after-learning',growth_rules)),
        'Stale growth snapshot')
    # A lost role parent with a durable cost proof is indeterminate, never a
    # reason for the guild to refund or for the role to charge again.
    with closing(f.accounts.connect()) as db,db:
        db.execute('DELETE FROM role_member_learning_receipts WHERE role_id=1 AND guild=? AND reservation=?',(guild,c.request_id))
    f.reject(lambda:f.org.execute(f.cmd(1,guild,'resolve_member_learning',(c.request_id,)),f.now()),'member_learning_outcome_unknown')
    f.reject(lambda:f.tx(1,lambda db:g.settle(db,inv,guild,c.request_id,f.now(),rules,f.org.learning_rules,currency,popularity=12)),
        'member_learning_outcome_unknown')
    assert f.tx(1,lambda db:costs.current(db,inv,currency))==paid.balances


def missing_experience_replay(path):
    import guild_member_learning as g
    f,guild,_,rules,inv,currency=learning(path)
    # The original successful source remains available through its public
    # permit Interface; a missing current EXP row is unknown, never zero.
    with closing(f.accounts.connect()) as db:
        source=db.execute('SELECT reservation FROM role_member_learning_receipts WHERE role_id=1 AND guild=?',(guild,)).fetchone()[0]
    with closing(f.accounts.connect()) as db,db:db.execute('DELETE FROM role_progress WHERE role_id=1')
    f.reject(lambda:f.tx(1,lambda db:g.settle(db,inv,guild,source,f.now(),rules,None,currency,popularity=None)),
        'learning_experience_unknown')


async def recovery_fault_isolation(path):
    from game_runtime import GameRuntime
    from verify_runtime import Peer
    from guild_research import ResearchAward
    from faction_types import GuildRecoveryProblem
    import runtime_storage,role_practice as practice
    f,guild,_,rules,_,_=learning(path)
    p=f.org.practice_rules
    f.tx(1,lambda db:practice.initialize(db,1111,1,f.epochs[1],tuple(practice.PracticeState(s,0,0,0) for s in p.skills),'explicit_migration',p))
    f.org.award_guild_research(ResearchAward(guild,'recovery-isolation-research-two',20,f.now()+5000),f.now())
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE organizations SET level=4 WHERE id=?',(guild,))
        db.execute('UPDATE family_members SET joined_ms=?',(f.now()-p.tenure_ms-1000,))
        db.execute('UPDATE guild_families SET joined_ms=?',(f.now()-p.tenure_ms-1000,))
        db.execute('UPDATE guild_member_state SET prestige=500 WHERE guild=? AND role_id=1',(guild,))
        db.execute('UPDATE guild_resources SET amount=20 WHERE guild=?',(guild,))
        db.execute('UPDATE guild_practice_materials SET available=9 WHERE guild=?',(guild,))
    f.org.execute(f.cmd(1,guild,'set_practice_open',(360001,True)),f.now())
    old=f.cmd(1,guild,'reserve_practice',(360001,0));f.org.execute(old,f.now())
    bad=f.cmd(1,guild,'reserve_member_learning',(300101,1));healthy=f.cmd(1,guild,'reserve_member_learning',(300101,1))
    f.org.execute(bad,f.now());f.org.execute(healthy,f.now())
    with closing(f.accounts.connect()) as db,db:
        db.execute("UPDATE guild_member_learning_permits SET body='{}' WHERE guild=? AND role_id=1 AND reservation=?",(guild,bad.request_id))
    events=[]
    class Capture:
        def emit(self,**event):events.append(event)
    rt=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts),logger=Capture())
    try:
        peer=Peer(rt);await peer.login(f.accounts.roles(1111)[0]);await peer.take()
        await asyncio.wait_for(rt.social_runtime.organizations.guild.idle(),5)
        epoch=rt.online_snapshot()[1].login_epoch
        assert f.org.guild_practice_materials(guild).available==9
        assert f.org.guild_practice_permit(1,epoch,guild,old.request_id).status=='cancelled'
        assert f.org.guild_learning_permit(1,epoch,guild,healthy.request_id).status=='cancelled',events
        pending=f.org.pending_member_learning(1,epoch)
        assert len(pending)==1 and type(pending[0]) is GuildRecoveryProblem and pending[0].reservation==bad.request_id
        assert f.org.guild_maintenance_snapshot(guild).resources.amount==18
        assert any(v.get('event')=='guild_recovery_source_deferred' and v.get('reservation')==bad.request_id for v in events)
        f.epochs[1]=epoch
        with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_member_state SET prestige=500 WHERE guild=? AND role_id=1 AND active=1',(guild,))
        corrupt=replace(f.cmd(1,guild,'reserve_practice',(360001,0)),deadline_ms=f.now()+1000)
        good=replace(f.cmd(1,guild,'reserve_practice',(360001,0)),deadline_ms=f.now()+1000)
        f.org.execute(corrupt,f.now());f.org.execute(good,f.now())
        with closing(f.accounts.connect()) as db,db:
            row=db.execute('SELECT body FROM guild_practice_permits WHERE guild=? AND role_id=1 AND reservation=?',(guild,corrupt.request_id)).fetchone()
            body=json.loads(row[0]);body['materials']=100
            db.execute('UPDATE guild_practice_permits SET body=? WHERE guild=? AND role_id=1 AND reservation=?',
                (json.dumps(body,sort_keys=True,separators=(',',':')),guild,corrupt.request_id))
        found=f.org.pending_practices(1,epoch)
        assert any(type(v) is GuildRecoveryProblem and v.reservation==corrupt.request_id for v in found),'Unverified practice refund source accepted'
        f.reject(lambda:f.org.execute(f.cmd(1,guild,'resolve_practice',(corrupt.request_id,)),f.now()),'practice_permit_invalid')
        await asyncio.sleep(1.05)
        assert rt.social_runtime.organizations.guild.nudge_recovery(1,epoch)
        await asyncio.wait_for(rt.social_runtime.organizations.guild.idle(),5)
        assert f.org.guild_practice_permit(1,epoch,guild,good.request_id).status=='cancelled'
        assert f.org.guild_practice_materials(guild).available==6
    finally:await rt.close()


def main():
    with tempfile.TemporaryDirectory() as directory:
        baseline(Path(directory)/'learning.db');role_costs(Path(directory)/'costs.db')
        learning(Path(directory)/'full-learning.db')
        failure_recovery(Path(directory)/'failures.db')
        f,guild,_,_,_,_=learning(Path(directory)/'runtime.db');asyncio.run(runtime_login(f,guild))
        npc_purchase(Path(directory)/'npc.db')
        wallet_threshold(Path(directory)/'threshold.db');high_level_depot(Path(directory)/'high-level.db')
        membership_and_orphans(Path(directory)/'membership.db');receipt_and_growth(Path(directory)/'growth.db')
        missing_experience_replay(Path(directory)/'missing-xp.db')
        asyncio.run(recovery_fault_isolation(Path(directory)/'recovery-fault.db'))
    result=dict(passed=['explicit complete14-life-skill baseline persists without inferring unknown historical skills or resetting known values',
        'explicit authorized bound-silver/cash/depot priority and EXP expense share one role transaction, prove historical payment and reject insufficient or conflicting intents',
        'real guild resource/prestige hold, role cost and one-level learning, acknowledgement and historical replay settle once without writing another owners state',
        'unknown or low personal popularity, late role receipt failure and competing stale revision leave role assets unchanged; unpaid holds refund once',
        'fresh service121 and authoritative full residence fixtures produce original14-cap panel and current native updates; moved/renewed/foreign/unsupported requests reject and late encoding rolls back',
        'actual encrypted login restores14 known incremental skills even with learning disabled and recovers a stale unpaid hold; eight guild duplicates reserve once while another family and heartbeat advance',
        'original carried-wallet10000 threshold applies even to tiny fees; high target155 consumes exact22060446EXP and695472 money across three explicit sources',
        'leave and rejoin fences old learning holds, refunds archived prestige without crediting a new membership and retains current personal skills',
        'EXP spending preserves level/stat revision and invalidates stale complete growth proposals; orphan role parent proof cannot refund or charge twice',
        'historical learning replay rejects a missing current experience row instead of projecting a fabricated zero balance',
        'malformed learning or tampered practice proofs remain held and reported while healthy sources recover without an inflated refund; optional life display SQLite failure leaves login and seven practices intact'],
        production_policy_configured=False,shared_entry_files_edited=False,native_gui_verified=False)
    write_json(OUT/'evidence/guild-member-learning-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
