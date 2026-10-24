"""Family construction through public organization and role transaction Seams."""
from pathlib import Path
from contextlib import closing
import tempfile
import asyncio
import json,sqlite3,threading
from dataclasses import replace
from inspect_client import OUT,write_json
from faction_domain import OrganizationStore
from verify_family_products import make
from inventory import Inventory,AssetChange,BAG_INFO
from verify_family_maintenance import tick


def setup(directory):
    f,family=make(directory)
    f.accounts.inventory_config=Inventory.prepare(f.accounts)
    inv=Inventory(f.accounts,1111,1,epoch=f.epochs[1],currency_rules=f.rules)
    return f,family,inv


def encode(db,inventory,snapshot,*,replayed):
    return tuple(inventory.equipment_bag_messages(db,inventory.epoch))


def check_first(directory):
    import family_donation as donation
    f,family,inv=setup(directory)
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE family_assets SET construction=19 WHERE family=?',(family,))
    f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-boxes',grants=((36076,2,0),(36201,1,1)))))
    c=f.cmd(1,family,'reserve_family_donation',(2,))
    f.org.execute(c,f.now())
    paid=f.tx(1,lambda db:donation.pay(db,1111,1,f.epochs[1],family,c.request_id,f.now(),
        f.org.donation_rules,inv,precommit=encode))
    assert paid.count==2 and any(kind==BAG_INFO for kind,body in paid.messages)
    assert [(i.template_id,i.quantity) for i in inv.immutable_snapshot().items]==[(36076,1)]
    f.org.execute(f.cmd(1,family,'resolve_family_donation',(c.request_id,)),f.now())
    state=f.org.family_donation_receipt(family,1,c.request_id)
    assert (state.status,state.count,state.level_after,state.construction_after,state.funds_after)==('committed',2,2,1,3200000)
    assert state.prestige_after==(10,10)
    assert f.org.snapshot(family)[0]['level']==2
    assert f.org.family_assets(family).construction==1


def check_paid_before_maintenance(directory):
    import family_donation as donation
    f,family,inv=setup(directory)
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE family_assets SET construction=19,funds=0 WHERE family=?',(family,))
    f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-due-box',grants=((36076,1,0),))))
    c=f.cmd(1,family,'reserve_family_donation',(1,));f.org.execute(c,f.now())
    f.tx(1,lambda db:donation.pay(db,1111,1,f.epochs[1],family,c.request_id,f.now(),f.org.donation_rules,inv,precommit=encode))
    command,hour=tick(f,family)
    assert hour.state=='active' and (hour.level_before,hour.level_after,hour.funds_after)==(2,2,80000)
    assert f.org.family_donation_receipt(family,1,c.request_id).status=='committed'
    assert f.org.maintain_family(command,command.due_ms+1)==hour


async def check_automatic(directory):
    import family_donation as donation
    from game_runtime import GameRuntime
    import runtime_storage
    f,family,inv=setup(directory)
    f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-auto-box',grants=((36076,1,0),))))
    c=f.cmd(1,family,'reserve_family_donation',(1,));f.org.execute(c,f.now())
    f.tx(1,lambda db:donation.pay(db,1111,1,f.epochs[1],family,c.request_id,f.now(),f.org.donation_rules,inv,precommit=encode))
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        await runtime.social_runtime.organizations.family.maintenance.run_once(f.now())
        assert f.org.family_donation_receipt(family,1,c.request_id).status=='committed'
        assert f.org.family_assets(family).funds==3100000
    finally:await runtime.close()


def donation_fixture(directory,count=3):
    import family_donation as donation
    f,family,inv=setup(directory)
    f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-box-stock',grants=((36076,count,0),))))
    c=f.cmd(1,family,'reserve_family_donation',(1,));f.org.execute(c,f.now())
    def pay(precommit=encode):
        return f.tx(1,lambda db:donation.pay(db,1111,1,f.epochs[1],family,c.request_id,f.now(),
            f.org.donation_rules,inv,precommit=precommit))
    return f,family,inv,c,pay


def check_replay(directory):
    f,family,inv,c,pay=donation_fixture(directory)
    first=pay();cash=f.cash(1)
    f.org.execute(f.cmd(1,family,'resolve_family_donation',(c.request_id,)),f.now())
    receipt=f.org.family_donation_receipt(family,1,c.request_id)
    f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-later-item',grants=((36201,1,1),))))
    current=inv.immutable_snapshot();again=pay()
    assert again.inventory==current and again.items==first.items and f.cash(1)==cash
    f.org.execute(f.cmd(1,family,'resolve_family_donation',(c.request_id,)),f.now())
    assert f.org.family_donation_receipt(family,1,c.request_id)==receipt
    f.org=OrganizationStore(f.accounts.path,f.policy);f.org.initialize()
    assert f.org.family_donation_receipt(family,1,c.request_id)==receipt
    assert f.org.family_assets(family).funds==3100000


def check_failures(directory):
    f,family,inv,c,pay=donation_fixture(directory)
    before=inv.immutable_snapshot();assets=f.org.family_assets(family)
    bad=lambda *args,**kw:((1,'not-bytes'),)
    f.reject(lambda:pay(bad),'NPC precommit')
    assert inv.immutable_snapshot()==before
    pay()
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER fixture_donation_receipt BEFORE INSERT ON family_donation_receipts BEGIN SELECT RAISE(ABORT,'late_donation_receipt'); END")
    try:f.org.execute(f.cmd(1,family,'resolve_family_donation',(c.request_id,)),f.now())
    except sqlite3.IntegrityError:pass
    except ValueError as error:assert 'organization_constraint' in str(error)
    else:raise AssertionError('Late family receipt failure ignored')
    assert f.org.family_assets(family)==assets
    assert inv.immutable_snapshot().items[0].quantity==2
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER fixture_donation_receipt')
    f.org.execute(f.cmd(1,family,'resolve_family_donation',(c.request_id,)),f.now())
    assert f.org.family_assets(family).funds==3100000
    for count in (0,-1,True,101):
        f.reject(lambda count=count:f.org.execute(f.cmd(1,family,'reserve_family_donation',(count,)),f.now()),
            'invalid_family_donation_count')


def check_cancel_and_orphan(directory):
    import family_donation as donation
    f,family,inv,c,pay=donation_fixture(directory)
    before=inv.immutable_snapshot()
    f.org.execute(f.cmd(1,family,'resolve_family_donation',(c.request_id,)),f.now())
    assert f.org.family_donation_receipt(family,1,c.request_id).status=='cancelled'
    f.reject(pay,'expired_or_stale');assert inv.immutable_snapshot()==before
    other=f.cmd(1,family,'reserve_family_donation',(1,));f.org.execute(other,f.now())
    child=donation.child_id(family,1,other.request_id)
    f.tx(1,lambda db:inv.apply_settlement(db,AssetChange(child,debits=((before.items[0].id,1),))))
    f.reject(lambda:f.org.execute(f.cmd(1,family,'resolve_family_donation',(other.request_id,)),f.now()),
        'outcome_unknown')
    assert f.org.family_assets(family).funds==3000000


def check_departed_prestige(directory):
    import family_donation as donation
    f,family,unused=setup(directory)
    inv=Inventory(f.accounts,1111,2,epoch=f.epochs[2],currency_rules=f.rules)
    f.tx(2,lambda db:inv.apply_settlement(db,AssetChange('fixture-member-box',grants=((36076,1,0),))))
    c=f.cmd(2,family,'reserve_family_donation',(1,));f.org.execute(c,f.now())
    f.tx(2,lambda db:donation.pay(db,1111,2,f.epochs[2],family,c.request_id,f.now(),f.org.donation_rules,inv,precommit=encode))
    f.org.execute(f.cmd(2,family,'leave'),f.now())
    f.org.execute(f.cmd(2,family,'apply'),f.now());f.org.execute(f.cmd(1,family,'review',(2,True)),f.now())
    f.org.execute(f.cmd(2,family,'resolve_family_donation',(c.request_id,)),f.now())
    receipt=f.org.family_donation_receipt(family,2,c.request_id)
    assert receipt.status=='committed' and receipt.prestige_after is None
    audience=f.org.family_audience(family);token=dict(audience.members)[2]
    profile=f.org.family_projection(2,f.epochs[2],family,token,())
    assert next(m for m in profile.members if m.role_id==2).prestige_values==(0,0)
    assert f.org.family_assets(family).funds==3100000


def check_multi_level(directory):
    import family_donation as donation
    f,family,inv=setup(directory)
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE family_assets SET construction=19 WHERE family=?',(family,))
    expected=((3,49,13000000),(4,69,23000000),(5,0,33000000),(5,0,43000000))
    for index,(level,construction,funds) in enumerate(expected):
        f.tx(1,lambda db,index=index:inv.apply_settlement(db,AssetChange('fixture-batch-'+str(index),grants=((36076,100,0),))))
        c=f.cmd(1,family,'reserve_family_donation',(100,));f.org.execute(c,f.now())
        f.tx(1,lambda db:donation.pay(db,1111,1,f.epochs[1],family,c.request_id,f.now(),f.org.donation_rules,inv,precommit=encode))
        f.org.execute(f.cmd(1,family,'resolve_family_donation',(c.request_id,)),f.now())
        result=f.org.family_donation_receipt(family,1,c.request_id)
        assert (result.level_after,result.construction_after,result.funds_after)==(level,construction,funds)
        assert result.prestige_after==(500*(index+1),500*(index+1))


def check_unpaid_maintenance(directory):
    import family_donation as donation
    f,family,inv,c,pay=donation_fixture(directory)
    before=inv.immutable_snapshot()
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE family_assets SET funds=0 WHERE family=?',(family,))
    command,hour=tick(f,family)
    assert hour.state=='dissolution_pending'
    assert f.org.family_donation_receipt(family,1,c.request_id).status=='cancelled'
    f.reject(pay,'expired_or_stale');assert inv.immutable_snapshot()==before


def check_unknown_member_after_payment(directory):
    f,family,inv,c,pay=donation_fixture(directory);pay()
    assets=f.org.family_assets(family)
    with closing(f.accounts.connect()) as db,db:
        # Fault fixture: original family relationship remains, only its
        # prestige profile is missing. This is not a legitimate departure.
        db.execute('DELETE FROM family_member_state WHERE role_id=1')
    f.reject(lambda:f.org.execute(f.cmd(1,family,'resolve_family_donation',(c.request_id,)),f.now()),
        'family_donation_membership_unknown')
    assert f.org.family_assets(family)==assets
    f.reject(lambda:f.org.family_donation_receipt(family,1,c.request_id),'receipt_missing')


async def check_periodic_native(directory):
    import family_donation as donation
    import faction_protocol as p
    from game_runtime import GameRuntime
    from verify_runtime import Peer
    import runtime_storage
    f,family,inv,c,pay=donation_fixture(directory)
    pay()
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts));completed=threading.Event()
    repository=runtime.social_runtime.organizations.store;original=repository.sweep_family_donations
    def observe(command,now):
        result=original(command,now)
        if result:completed.set()
        return result
    repository.sweep_family_donations=observe
    try:
        peer=Peer(runtime);await peer.login(f.accounts.roles(1111)[0]);await peer.take()
        assert await asyncio.to_thread(completed.wait,8),'Periodic donation source did not dispatch'
        await runtime.social_runtime.organizations.family.maintenance.idle()
        messages=await peer.take()
        current=runtime.online_snapshot()[1]
        generation=dict(f.org.family_audience(family).members)[1]
        projection=f.org.family_projection(1,current.login_epoch,family,generation,((1,current.login_epoch),))
        assert (p.UPDATE_FAMILY,p.family_update(projection.view)) in messages
        assert projection.view.funds==3100000 and projection.view.construction==1
        assert next(m for m in projection.members if m.role_id==1).prestige_values==(5,5)
    finally:await runtime.close()


async def check_independence(directory):
    from game_runtime import GameRuntime
    from verify_runtime import Peer
    from family_donation import DonationSweepCommand
    import runtime_storage
    f,family,inv,c,pay=donation_fixture(directory);pay()
    other=f.family(16,name='独立建设');f.fund(other)
    second=f.org.execute(other,f.now())['organization']
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    entered,released=threading.Event(),threading.Event()
    repository=runtime.social_runtime.organizations.store;original=repository.sweep_family_donations
    def slow(command,now):
        if command.family==family:
            entered.set()
            if not released.wait(5):raise TimeoutError('fixture donation release')
        return original(command,now)
    repository.sweep_family_donations=slow
    try:
        peer=Peer(runtime);await peer.login(next(r for r in f.accounts.roles(1111) if r['id']==18))
        owner=runtime.social_runtime.organizations;now=f.now()
        pending=asyncio.create_task(owner.sweep_family_donations(DonationSweepCommand(family,'slow-donation',now+5000),now))
        assert await asyncio.to_thread(entered.wait,2)
        await asyncio.wait_for(owner.command(f.cmd(16,second,'set_family_products',(1,-1)),f.now()),1)
        response=await asyncio.wait_for(peer.request(100,b'ping'),1)
        assert response.count((100,b'ping'))==1 and not pending.done()
        released.set();assert (await pending)[0].status=='committed'
    finally:
        released.set();await runtime.close()


if __name__=='__main__':
    with tempfile.TemporaryDirectory() as directory:check_first(directory)
    with tempfile.TemporaryDirectory() as directory:check_paid_before_maintenance(directory)
    with tempfile.TemporaryDirectory() as directory:asyncio.run(check_automatic(directory))
    for check in (check_replay,check_failures,check_cancel_and_orphan,check_departed_prestige,check_multi_level,
            check_unpaid_maintenance,check_unknown_member_after_payment):
        with tempfile.TemporaryDirectory() as directory:check(directory)
    with tempfile.TemporaryDirectory() as directory:asyncio.run(check_periodic_native(directory))
    with tempfile.TemporaryDirectory() as directory:asyncio.run(check_independence(directory))
    result=dict(passed=['both original silver-box templates; bound-first selection spans stacks atomically',
        'threshold twenty upgrades level one; designed remainder is carried',
        'one inventory transaction includes common payment proof and current encoded bags',
        'paid contribution is settled before hourly maintenance and its new level fee',
        'partitioned runtime directory recovers paid donations without a client retry',
        'role replay returns current absolute inventory and never consumes again',
        'family replay and restart preserve one funds/construction/prestige result',
        'native precommit failure rolls back inventory version, debits and payment proof',
        'late family receipt failure rolls back funds, construction, prestige and ledger',
        'invalid count and explicit cancellation cannot spend items',
        'orphan child-only debit remains unknown and cannot grant or cancel',
        'paid contribution stays with source family but old prestige never reaches a rejoined membership',
        'multi-level batches consume thresholds; level five keeps construction zero while other gains continue',
        'unpaid reservation is cancelled before terminal family maintenance',
        'actual periodic source sends current family funds/construction/prestige through original encrypted messages',
        'controlled blocked family settlement leaves another family command and encrypted heartbeat independent',
        'missing current membership prestige after payment stays unknown instead of being mistaken for departure'],
        live_server_changed=False,native_gui_verified=False,shared_entry_files_edited=False,
        original_donation_request_decoder_verified=False,npc_service296_registered=False,
        numeric_review=json.loads((OUT/'design/recovery-baseline.json').read_text(encoding='utf-8'))['organizations']['family_donation']['numeric_review'],
        full_family_gameplay_complete=False)
    write_json(OUT/'evidence/family-donation-verification.json',result);print(json.dumps(result))
